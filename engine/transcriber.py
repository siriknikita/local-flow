"""MLX-Whisper transcription engine for LocalFlow."""
import logging
import os
import threading
from pathlib import Path
from typing import Callable, Optional

import mlx_whisper
import numpy as np
from huggingface_hub import snapshot_download
from mlx_whisper.load_models import load_model

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """MLX-Whisper transcriber with model management."""
    
    # Available model variants
    MODEL_VARIANTS = {
        "tiny": "mlx-community/whisper-tiny",
        "base": "mlx-community/whisper-base",
        "small": "mlx-community/whisper-small",
        "medium": "mlx-community/whisper-medium",
        "large": "mlx-community/whisper-large-v3",
        "large-turbo": "mlx-community/whisper-large-v3-turbo"
    }
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize transcriber.
        
        Args:
            cache_dir: Directory to cache models. Defaults to ~/.cache/local_whisper
        """
        logger.info("Initializing WhisperTranscriber")
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/local_whisper")
        logger.debug(f"Cache directory: {self.cache_dir}")
        self.current_model: Optional[str] = None
        self.model = None
        self._lock = threading.Lock()
        logger.info("WhisperTranscriber initialized successfully")
        
    def get_available_models(self) -> dict[str, dict]:
        """Get list of available models and their status.
        
        Returns:
            Dictionary mapping model names to their info (downloaded, path, size)
        """
        models_info = {}
        
        for variant, repo_id in self.MODEL_VARIANTS.items():
            model_path = Path(self.cache_dir) / repo_id.replace("/", "_")
            is_downloaded = model_path.exists() and any(model_path.iterdir())
            
            models_info[variant] = {
                "repo_id": repo_id,
                "downloaded": is_downloaded,
                "path": str(model_path) if is_downloaded else None,
                "active": variant == self.current_model
            }
        
        return models_info
    
    def download_model(self, model_name: str, progress_callback: Optional[Callable[[float], None]] = None) -> bool:
        """Download model from Hugging Face.
        
        Args:
            model_name: Model variant name (tiny, base, small, medium, large, large-turbo)
            progress_callback: Optional callback for download progress (0.0 to 1.0)
            
        Returns:
            True if download successful, False otherwise
        """
        if model_name not in self.MODEL_VARIANTS:
            logger.error(f"Unknown model variant: {model_name}")
            return False
        
        repo_id = self.MODEL_VARIANTS[model_name]
        
        try:
            logger.info(f"Step 1: Starting download of model {repo_id}")
            
            # Create cache directory
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.debug(f"Cache directory ready: {self.cache_dir}")
            
            # Download from Hugging Face
            # Note: snapshot_download doesn't have built-in progress, but we can simulate it
            if progress_callback:
                progress_callback(0.1)
            
            logger.info(f"Step 2: Downloading from Hugging Face repository {repo_id}")
            model_path = snapshot_download(
                repo_id=repo_id,
                cache_dir=self.cache_dir,
                local_dir=Path(self.cache_dir) / repo_id.replace("/", "_")
            )
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info(f"Step 3: Model download completed successfully to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Step 3: Model download failed - {e}", exc_info=True)
            if progress_callback:
                progress_callback(-1.0)  # Signal error
            return False
    
    def load_model(self, model_name: str) -> bool:
        """Load model from cache or download if needed.
        
        Args:
            model_name: Model variant name (tiny, base, small, medium, large, large-turbo)
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        logger.info(f"Step 1: Loading model '{model_name}'")
        
        if model_name not in self.MODEL_VARIANTS:
            logger.error(f"Unknown model variant: {model_name}")
            return False
        
        repo_id = self.MODEL_VARIANTS[model_name]
        model_path = Path(self.cache_dir) / repo_id.replace("/", "_")
        
        # Check if model exists, download if not
        logger.debug(f"Step 2: Checking if model exists locally at {model_path}")
        if not model_path.exists() or not any(model_path.iterdir()):
            logger.info(f"Step 2: Model not found locally. Downloading {repo_id}...")
            if not self.download_model(model_name):
                logger.error("Step 2: Model download failed, cannot load model")
                return False
        else:
            logger.info(f"Step 2: Model found in cache at {model_path}")
        
        try:
            with self._lock:
                logger.info(f"Step 3: Loading model from {model_path}")
                # Use the correct mlx-whisper API
                self.model = load_model(str(model_path))
                self.current_model = model_name
                logger.info(f"Step 4: Model '{model_name}' loaded successfully")
                return True
                
        except Exception as e:
            logger.error(f"Step 3: Error loading model - {e}", exc_info=True)
            # Try using the repo ID directly
            try:
                logger.info(f"Step 3 (retry): Attempting to load model using repo ID: {repo_id}")
                self.model = load_model(repo_id)
                self.current_model = model_name
                logger.info(f"Step 4: Model '{model_name}' loaded successfully using repo ID")
                return True
            except Exception as e2:
                logger.error(f"Step 3 (retry): Alternative loading also failed - {e2}", exc_info=True)
                return False
    
    def transcribe(self, audio_data: np.ndarray, callback: Optional[Callable[[str], None]] = None) -> str:
        """Transcribe audio data using loaded model.
        
        Args:
            audio_data: Audio data as numpy array (16kHz, mono, float32)
            callback: Optional callback function called with transcription result
            
        Returns:
            Transcribed text
        """
        logger.info("Step 1: Starting transcription")
        
        if self.model is None and self.current_model is None:
            logger.error("No model loaded. Cannot transcribe.")
            raise RuntimeError("No model loaded. Call load_model() first.")
        
        def _transcribe_in_thread():
            """Run transcription in background thread."""
            try:
                logger.info("Step 2: Preparing audio data for transcription")
                # Ensure audio is the right format
                if audio_data.dtype != np.float32:
                    audio_data_float = audio_data.astype(np.float32)
                    logger.debug("Converted audio to float32")
                else:
                    audio_data_float = audio_data
                
                # Normalize audio to [-1, 1] range if needed
                if audio_data_float.max() > 1.0 or audio_data_float.min() < -1.0:
                    audio_data_float = audio_data_float / np.max(np.abs(audio_data_float))
                    logger.debug("Normalized audio to [-1, 1] range")
                
                logger.info(f"Step 3: Running transcription (audio length: {len(audio_data_float)} samples)")
                
                # Use mlx_whisper.transcribe with path_or_hf_repo parameter
                # Get the repo ID for the current model
                repo_id = self.MODEL_VARIANTS.get(self.current_model, "mlx-community/whisper-tiny")
                logger.debug(f"Using model repo: {repo_id}")
                
                # mlx_whisper.transcribe can work with repo ID directly
                result = mlx_whisper.transcribe(audio_data_float, path_or_hf_repo=repo_id)
                
                logger.info("Step 4: Transcription completed, extracting text")
                
                # Extract text from result
                # Result format may vary, but typically has 'text' field
                if isinstance(result, dict):
                    text = result.get('text', '')
                elif isinstance(result, str):
                    text = result
                else:
                    # Try to get text from segments
                    text = ' '.join([seg.get('text', '') for seg in result.get('segments', [])])
                
                logger.info(f"Step 5: Transcription result: '{text[:50]}...' (length: {len(text)} chars)")
                
                if callback:
                    callback(text)
                
                return text
                
            except Exception as e:
                error_msg = f"Transcription error: {e}"
                logger.error(f"Step 3: {error_msg}", exc_info=True)
                if callback:
                    callback("")
                return ""
        
        # Run in background thread to prevent blocking
        result_container = {"text": ""}
        
        def _thread_target():
            result_container["text"] = _transcribe_in_thread()
        
        thread = threading.Thread(target=_thread_target, daemon=True)
        thread.start()
        thread.join()  # Wait for completion
        
        return result_container["text"]
    
    def transcribe_async(self, audio_data: np.ndarray, callback: Callable[[str], None]):
        """Transcribe audio asynchronously in background thread.
        
        Args:
            audio_data: Audio data as numpy array
            callback: Callback function called with transcription result
        """
        logger.info("Starting async transcription")
        def _transcribe():
            try:
                text = self.transcribe(audio_data)
                logger.info("Async transcription completed successfully")
                callback(text)
            except Exception as e:
                logger.error(f"Async transcription error: {e}", exc_info=True)
                callback("")
        
        thread = threading.Thread(target=_transcribe, daemon=True)
        thread.start()
        logger.debug("Async transcription thread started")

