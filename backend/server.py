"""HTTP/WebSocket server for LocalFlow SwiftUI app."""
import asyncio
import json
import logging
import threading
import time
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import config
from engine.audio import AudioRecorder
from engine.injector import TextInjector
from engine.transcriber import WhisperTranscriber
from engine.vad import SileroVAD

logger = logging.getLogger(__name__)

app = FastAPI(title="LocalFlow API")

# Enable CORS for SwiftUI app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
audio_recorder: Optional[AudioRecorder] = None
transcriber: Optional[WhisperTranscriber] = None
injector: Optional[TextInjector] = None
vad: Optional[SileroVAD] = None
is_recording = False
active_websockets = set()
waveform_update_task: Optional[asyncio.Task] = None
event_loop: Optional[asyncio.AbstractEventLoop] = None


# Pydantic models for request/response
class HotkeyConfig(BaseModel):
    modifiers: list[str]
    key: str


class ConfigUpdate(BaseModel):
    hotkey: Optional[HotkeyConfig] = None
    mode: Optional[str] = None
    model: Optional[str] = None
    vad_enabled: Optional[bool] = None
    audio: Optional[dict] = None


class ModelSwitchRequest(BaseModel):
    variant: str


class ModelDownloadRequest(BaseModel):
    variant: str


def initialize_components():
    """Initialize engine components."""
    global audio_recorder, transcriber, injector, vad
    
    logger.info("Initializing LocalFlow components")
    
    # Load configuration
    cfg = config.load_config()
    
    # Initialize components
    audio_recorder = AudioRecorder()
    transcriber = WhisperTranscriber(
        cache_dir=config.expand_cache_dir(cfg.get("cache_dir", "~/.cache/local_whisper"))
    )
    injector = TextInjector()
    
    # Initialize VAD if enabled
    if cfg.get("vad_enabled", True):
        vad = SileroVAD()
        vad.load_vad_model()
    
    # Load default model
    model_name = cfg.get("model", "mlx-community/whisper-large-v3-turbo")
    model_variant = _extract_model_variant(model_name)
    if model_variant:
        transcriber.load_model(model_variant)
    
    logger.info("Components initialized successfully")


def _extract_model_variant(model_name: str) -> Optional[str]:
    """Extract model variant from full model name."""
    model_lower = model_name.lower()
    
    if "large-v3-turbo" in model_lower or "large-turbo" in model_lower:
        return "large-turbo"
    elif "large-v3" in model_lower or "large" in model_lower:
        return "large"
    elif "medium" in model_lower:
        return "medium"
    elif "small" in model_lower:
        return "small"
    elif "base" in model_lower:
        return "base"
    elif "tiny" in model_lower:
        return "tiny"
    
    return None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global event_loop
    event_loop = asyncio.get_event_loop()
    initialize_components()


@app.get("/api/status")
async def get_status():
    """Get current application status."""
    return {
        "is_recording": is_recording,
        "model_loaded": transcriber.current_model if transcriber else None,
        "vad_enabled": vad is not None and vad.session is not None,
    }


@app.post("/api/recording/start")
async def start_recording():
    """Start recording audio."""
    global is_recording
    
    if is_recording:
        return {"success": False, "error": "Already recording"}
    
    try:
        cfg = config.load_config()
        mic_device, system_device = _detect_audio_devices(cfg)
        
        if mic_device is None:
            return {"success": False, "error": "No microphone device available"}
        
        audio_config = cfg.get("audio", {})
        mix_audio = audio_config.get("mix_audio", True)
        
        audio_recorder.start_recording(
            microphone_device=mic_device,
            system_audio_device=system_device,
            mix_audio=mix_audio
        )
        
        is_recording = True
        
        # Start waveform update task
        _start_waveform_updates()
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to start recording: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.post("/api/recording/stop")
async def stop_recording():
    """Stop recording and process audio."""
    global is_recording
    
    if not is_recording:
        return {"success": False, "error": "Not recording"}
    
    try:
        is_recording = False
        _stop_waveform_updates()
        
        # Stop audio recording
        audio_data = audio_recorder.stop_recording()
        
        if len(audio_data) == 0:
            return {"success": True, "transcription": None, "error": "No audio recorded"}
        
        # Process audio in background
        def process_audio():
            try:
                # Trim silence using VAD if available
                audio_to_transcribe = audio_data
                if vad and vad.session is not None:
                    try:
                        start_idx, end_idx = vad.find_speech_boundaries(audio_data, padding_ms=100)
                        if start_idx < end_idx:
                            audio_to_transcribe = audio_data[start_idx:end_idx]
                    except Exception as e:
                        logger.warning(f"VAD trimming failed: {e}")
                
                # Transcribe
                def on_complete(text: str):
                    logger.info(f"Transcription complete: {text}")
                    # Broadcast transcription result to WebSocket clients
                    if event_loop:
                        asyncio.run_coroutine_threadsafe(
                            _broadcast_message({"type": "transcription", "text": text}),
                            event_loop
                        )
                    # Inject text if enabled
                    if injector and text:
                        injector.inject_text(text)
                
                transcriber.transcribe_async(audio_to_transcribe, on_complete)
            except Exception as e:
                logger.error(f"Error processing audio: {e}", exc_info=True)
                if event_loop:
                    asyncio.run_coroutine_threadsafe(
                        _broadcast_message({"type": "error", "message": str(e)}),
                        event_loop
                    )
        
        threading.Thread(target=process_audio, daemon=True).start()
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Failed to stop recording: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    return config.load_config()


@app.put("/api/config")
async def update_config(config_update: ConfigUpdate):
    """Update configuration."""
    try:
        current_config = config.load_config()
        
        if config_update.hotkey:
            current_config["hotkey"] = {
                "modifiers": config_update.hotkey.modifiers,
                "key": config_update.hotkey.key
            }
        
        if config_update.mode:
            current_config["mode"] = config_update.mode
        
        if config_update.model:
            current_config["model"] = config_update.model
        
        if config_update.vad_enabled is not None:
            current_config["vad_enabled"] = config_update.vad_enabled
        
        if config_update.audio:
            if "audio" not in current_config:
                current_config["audio"] = {}
            current_config["audio"].update(config_update.audio)
        
        if config.save_config(current_config):
            return {"success": True, "config": current_config}
        else:
            return {"success": False, "error": "Failed to save config"}
    except Exception as e:
        logger.error(f"Failed to update config: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.get("/api/models")
async def list_models():
    """List available models and their status."""
    if not transcriber:
        return {"success": False, "error": "Transcriber not initialized"}
    
    try:
        models_info = transcriber.get_available_models()
        current_config = config.load_config()
        active_model = current_config.get("model", "")
        
        return {
            "success": True,
            "models": models_info,
            "active_model": active_model
        }
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.post("/api/models/download")
async def download_model(request: ModelDownloadRequest):
    """Download a model."""
    if not transcriber:
        return {"success": False, "error": "Transcriber not initialized"}
    
    try:
        def progress_callback(progress: float):
            # Broadcast progress to WebSocket clients
            if event_loop:
                asyncio.run_coroutine_threadsafe(
                    _broadcast_message({
                        "type": "model_download_progress",
                        "variant": request.variant,
                        "progress": progress
                    }),
                    event_loop
                )
        
        success = transcriber.download_model(request.variant, progress_callback)
        
        if success:
            return {"success": True, "variant": request.variant}
        else:
            return {"success": False, "error": "Download failed"}
    except Exception as e:
        logger.error(f"Failed to download model: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.post("/api/models/switch")
async def switch_model(request: ModelSwitchRequest):
    """Switch to a different model."""
    if not transcriber:
        return {"success": False, "error": "Transcriber not initialized"}
    
    try:
        if transcriber.load_model(request.variant):
            # Update config
            current_config = config.load_config()
            repo_id = transcriber.MODEL_VARIANTS.get(request.variant)
            if repo_id:
                current_config["model"] = repo_id
                config.save_config(current_config)
            
            return {"success": True, "variant": request.variant}
        else:
            return {"success": False, "error": "Failed to load model"}
    except Exception as e:
        logger.error(f"Failed to switch model: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    active_websockets.add(websocket)
    
    try:
        while True:
            # Keep connection alive and handle any incoming messages
            data = await websocket.receive_text()
            # Echo back or handle client messages if needed
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        active_websockets.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        active_websockets.discard(websocket)


async def _broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    if not active_websockets:
        return
    
    disconnected = set()
    for websocket in active_websockets:
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.debug(f"Failed to send to WebSocket: {e}")
            disconnected.add(websocket)
    
    # Remove disconnected websockets
    active_websockets.difference_update(disconnected)


def _start_waveform_updates():
    """Start sending waveform updates via WebSocket."""
    global waveform_update_task
    
    if waveform_update_task and not waveform_update_task.done():
        return
    
    async def update_loop():
        while is_recording and audio_recorder:
            try:
                waveform_data = audio_recorder.get_waveform_data()
                if waveform_data:
                    # Convert to list of floats (JSON serializable)
                    waveform_list = [float(x) for x in waveform_data]
                    await _broadcast_message({
                        "type": "waveform",
                        "data": waveform_list
                    })
                await asyncio.sleep(0.05)  # ~20 FPS
            except Exception as e:
                logger.error(f"Error in waveform update loop: {e}")
                break
    
    waveform_update_task = asyncio.create_task(update_loop())


def _stop_waveform_updates():
    """Stop waveform updates."""
    global waveform_update_task
    if waveform_update_task and not waveform_update_task.done():
        waveform_update_task.cancel()


def _detect_audio_devices(cfg: dict):
    """Detect and return microphone and system audio device indices."""
    audio_config = cfg.get("audio", {})
    auto_detect = audio_config.get("auto_detect_devices", True)
    
    mic_device = audio_config.get("microphone_device")
    system_device = audio_config.get("system_audio_device")
    
    if auto_detect:
        if mic_device is None:
            mic_device = audio_recorder.get_default_input_device()
        
        if system_device is None:
            system_device = audio_recorder.find_blackhole_device()
    
    return mic_device, system_device


if __name__ == "__main__":
    import uvicorn
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    uvicorn.run(app, host="127.0.0.1", port=8000)

