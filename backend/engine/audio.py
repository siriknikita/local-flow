"""Audio capture and waveform processing for LocalFlow."""
import logging
import threading
from collections import deque
from typing import Callable, Dict, List, Optional

import numpy as np
import sounddevice as sd

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Audio recorder with real-time waveform calculation."""
    
    SAMPLE_RATE = 16000  # Whisper standard
    CHANNELS = 1  # Mono
    BUFFER_SIZE = 1024  # Samples per buffer for responsive visualization
    
    def __init__(self):
        """Initialize audio recorder."""
        logger.info("Initializing AudioRecorder")
        self.stream: Optional[sd.InputStream] = None
        self.mic_stream: Optional[sd.InputStream] = None
        self.system_stream: Optional[sd.InputStream] = None
        self.audio_buffer: deque = deque()  # Unbounded buffer to preserve all audio
        self.mic_buffer: deque = deque()  # Buffer for microphone audio
        self.system_buffer: deque = deque()  # Buffer for system audio
        self.waveform_buffer: deque = deque(maxlen=200)  # Store waveform points for visualization
        self.is_recording = False
        self.waveform_callback: Optional[Callable[[float], None]] = None
        self._lock = threading.Lock()
        self._mix_audio = True
        logger.info("AudioRecorder initialized successfully")
    
    @staticmethod
    def list_audio_devices() -> List[Dict]:
        """List all available audio input devices.
        
        Returns:
            List of dictionaries containing device information:
            - index: Device index
            - name: Device name
            - channels: Number of input channels
            - sample_rate: Default sample rate
        """
        devices = []
        try:
            all_devices = sd.query_devices()
            for i, device in enumerate(all_devices):
                if device['max_input_channels'] > 0:
                    devices.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels'],
                        'sample_rate': device['default_samplerate'],
                        'hostapi': device['hostapi']
                    })
        except Exception as e:
            logger.error(f"Error listing audio devices: {e}", exc_info=True)
        return devices
    
    @staticmethod
    def find_device_by_name(name_pattern: str) -> Optional[int]:
        """Find device index by name pattern (case-insensitive).
        
        Args:
            name_pattern: Pattern to search for in device name
            
        Returns:
            Device index if found, None otherwise
        """
        devices = AudioRecorder.list_audio_devices()
        name_lower = name_pattern.lower()
        for device in devices:
            if name_lower in device['name'].lower():
                return device['index']
        return None
    
    @staticmethod
    def find_blackhole_device() -> Optional[int]:
        """Find BlackHole virtual audio device.
        
        Returns:
            Device index if found, None otherwise
        """
        return AudioRecorder.find_device_by_name("BlackHole")
    
    @staticmethod
    def get_default_input_device() -> Optional[int]:
        """Get the default input device index.
        
        Returns:
            Default input device index, or None if not available
        """
        try:
            default_device = sd.query_devices(kind='input')
            return default_device['index']
        except Exception as e:
            logger.warning(f"Could not get default input device: {e}")
            return None
        
    def start_recording(
        self,
        microphone_device: Optional[int] = None,
        system_audio_device: Optional[int] = None,
        mix_audio: bool = True,
        waveform_callback: Optional[Callable[[float], None]] = None
    ):
        """Start recording audio stream from one or two devices.
        
        Args:
            microphone_device: Device index for microphone input (None for default)
            system_audio_device: Device index for system audio/loopback (None to skip)
            mix_audio: If True, mix both streams; if False, use only microphone
            waveform_callback: Optional callback function that receives amplitude values
        """
        if self.is_recording:
            logger.warning("Recording already in progress, ignoring start request")
            return
        
        logger.info("Step 1: Starting audio recording")
        self.waveform_callback = waveform_callback
        self._mix_audio = mix_audio
        self.audio_buffer.clear()
        self.mic_buffer.clear()
        self.system_buffer.clear()
        self.waveform_buffer.clear()
        logger.debug("Step 2: Audio buffers cleared")
        
        # Determine which devices to use
        use_mic = True
        use_system = system_audio_device is not None
        
        if microphone_device is None:
            microphone_device = self.get_default_input_device()
            if microphone_device is None:
                logger.error("No microphone device available")
                raise RuntimeError("No microphone device available")
        
        # Verify devices exist
        try:
            if use_mic:
                mic_info = sd.query_devices(microphone_device)
                logger.info(f"Using microphone device: {mic_info['name']} (index {microphone_device})")
        except Exception as e:
            logger.error(f"Microphone device {microphone_device} not available: {e}")
            raise RuntimeError(f"Microphone device {microphone_device} not available: {e}")
        
        if use_system:
            try:
                system_info = sd.query_devices(system_audio_device)
                logger.info(f"Using system audio device: {system_info['name']} (index {system_audio_device})")
            except Exception as e:
                logger.warning(f"System audio device {system_audio_device} not available: {e}")
                logger.warning("Falling back to microphone-only recording")
                use_system = False
        
        def mic_callback(indata, frames, time, status):
            """Callback for microphone audio stream."""
            if status:
                logger.warning(f"Microphone callback status: {status}")
            
            with self._lock:
                # Convert to mono if stereo
                if indata.ndim > 1:
                    audio_data = np.mean(indata, axis=1)
                else:
                    audio_data = indata.flatten()
                
                # If mixing with system audio, store in mic_buffer for mixing thread
                # Otherwise, add directly to audio_buffer to avoid duplication
                if use_system and self._mix_audio:
                    self.mic_buffer.extend(audio_data)
                else:
                    # Not mixing - add directly to audio_buffer
                    self.audio_buffer.extend(audio_data)
                    amplitude = np.abs(audio_data).mean()
                    self.waveform_buffer.append(amplitude)
                    
                    if self.waveform_callback:
                        try:
                            self.waveform_callback(float(amplitude))
                        except Exception as e:
                            logger.error(f"Error in waveform callback: {e}", exc_info=True)
        
        def system_callback(indata, frames, time, status):
            """Callback for system audio stream."""
            if status:
                logger.warning(f"System audio callback status: {status}")
            
            with self._lock:
                # Convert to mono if stereo
                if indata.ndim > 1:
                    audio_data = np.mean(indata, axis=1)
                else:
                    audio_data = indata.flatten()
                
                # Store system audio
                self.system_buffer.extend(audio_data)
        
        def mix_audio_thread():
            """Thread to mix microphone and system audio streams."""
            mix_event = threading.Event()
            while self.is_recording:
                mixed_any = False
                with self._lock:
                    # Get minimum length of both buffers (mix in chunks of BUFFER_SIZE for efficiency)
                    if len(self.mic_buffer) >= self.BUFFER_SIZE and len(self.system_buffer) >= self.BUFFER_SIZE:
                        chunk_size = self.BUFFER_SIZE
                        
                        # Extract and mix audio
                        mic_chunk = np.array([self.mic_buffer.popleft() for _ in range(chunk_size)], dtype=np.float32)
                        system_chunk = np.array([self.system_buffer.popleft() for _ in range(chunk_size)], dtype=np.float32)
                        
                        # Mix audio (simple addition, can be normalized if needed)
                        mixed = mic_chunk + system_chunk
                        
                        # Store mixed audio
                        self.audio_buffer.extend(mixed)
                        
                        # Calculate amplitude for waveform visualization
                        amplitude = np.abs(mixed).mean()
                        self.waveform_buffer.append(amplitude)
                        
                        mixed_any = True
                        
                        # Call waveform callback if provided
                        if self.waveform_callback:
                            try:
                                self.waveform_callback(float(amplitude))
                            except Exception as e:
                                logger.error(f"Error in waveform callback: {e}", exc_info=True)
                
                if not mixed_any:
                    # Small sleep to avoid busy waiting
                    mix_event.wait(0.01)
                else:
                    mix_event.clear()
        
        try:
            # Start microphone stream
            if use_mic:
                logger.info(f"Step 3: Creating microphone stream (sample_rate={self.SAMPLE_RATE}, channels={self.CHANNELS}, buffer_size={self.BUFFER_SIZE})")
                self.mic_stream = sd.InputStream(
                    device=microphone_device,
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    blocksize=self.BUFFER_SIZE,
                    callback=mic_callback,
                    dtype=np.float32
                )
                logger.debug("Step 4: Starting microphone stream")
                self.mic_stream.start()
            
            # Start system audio stream if available
            if use_system:
                logger.info(f"Step 3b: Creating system audio stream (sample_rate={self.SAMPLE_RATE}, channels={self.CHANNELS}, buffer_size={self.BUFFER_SIZE})")
                self.system_stream = sd.InputStream(
                    device=system_audio_device,
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    blocksize=self.BUFFER_SIZE,
                    callback=system_callback,
                    dtype=np.float32
                )
                logger.debug("Step 4b: Starting system audio stream")
                self.system_stream.start()
                
                # Start mixing thread if both streams are active
                if self._mix_audio and use_system:
                    mixing_thread = threading.Thread(target=mix_audio_thread, daemon=True)
                    mixing_thread.start()
                    logger.debug("Step 4c: Audio mixing thread started")
            
            self.is_recording = True
            logger.info("Step 5: Audio recording started successfully")
        except Exception as e:
            logger.error(f"Step 3: Error starting audio stream: {e}", exc_info=True)
            # Clean up on error
            if self.mic_stream:
                try:
                    self.mic_stream.stop()
                    self.mic_stream.close()
                except Exception:
                    pass
                self.mic_stream = None
            if self.system_stream:
                try:
                    self.system_stream.stop()
                    self.system_stream.close()
                except Exception:
                    pass
                self.system_stream = None
            raise
    
    def stop_recording(self) -> np.ndarray:
        """Stop recording and return audio buffer.
        
        Returns:
            Audio data as numpy array
        """
        if not self.is_recording:
            logger.warning("Not recording, nothing to stop")
            return np.array([], dtype=np.float32)
        
        logger.info("Step 1: Stopping audio recording")
        self.is_recording = False
        
        # Stop and close microphone stream
        if self.mic_stream:
            try:
                logger.debug("Step 2: Stopping microphone stream")
                self.mic_stream.stop()
                logger.debug("Step 3: Closing microphone stream")
                self.mic_stream.close()
                logger.info("Step 4: Microphone stream stopped and closed successfully")
            except Exception as e:
                logger.error(f"Step 2: Error stopping microphone stream: {e}", exc_info=True)
            finally:
                self.mic_stream = None
        
        # Stop and close system audio stream
        if self.system_stream:
            try:
                logger.debug("Step 2b: Stopping system audio stream")
                self.system_stream.stop()
                logger.debug("Step 3b: Closing system audio stream")
                self.system_stream.close()
                logger.info("Step 4b: System audio stream stopped and closed successfully")
            except Exception as e:
                logger.error(f"Step 2b: Error stopping system audio stream: {e}", exc_info=True)
            finally:
                self.system_stream = None
        
        # Stop legacy single stream if it exists
        if self.stream:
            try:
                logger.debug("Step 2c: Stopping legacy audio stream")
                self.stream.stop()
                logger.debug("Step 3c: Closing legacy audio stream")
                self.stream.close()
            except Exception as e:
                logger.error(f"Step 2c: Error stopping legacy audio stream: {e}", exc_info=True)
            finally:
                self.stream = None
        
        # Final mix of any remaining audio in buffers
        with self._lock:
            # If we were mixing and have remaining buffers, mix them now
            if self._mix_audio and len(self.mic_buffer) > 0 and len(self.system_buffer) > 0:
                min_len = min(len(self.mic_buffer), len(self.system_buffer))
                mic_remaining = np.array([self.mic_buffer.popleft() for _ in range(min_len)], dtype=np.float32)
                system_remaining = np.array([self.system_buffer.popleft() for _ in range(min_len)], dtype=np.float32)
                mixed_remaining = mic_remaining + system_remaining
                self.audio_buffer.extend(mixed_remaining)
            
            # Add any remaining microphone-only audio (only if we were mixing)
            # If we weren't mixing, mic_buffer should be empty (audio went directly to audio_buffer)
            if self._mix_audio and len(self.mic_buffer) > 0:
                mic_remaining = np.array(list(self.mic_buffer), dtype=np.float32)
                self.audio_buffer.extend(mic_remaining)
            
            # Clear all buffers
            self.mic_buffer.clear()
            self.system_buffer.clear()
            
            # Convert buffer to numpy array
            audio_data = np.array(list(self.audio_buffer), dtype=np.float32)
            buffer_length = len(audio_data)
            self.audio_buffer.clear()
            self.mic_buffer.clear()
            self.system_buffer.clear()
            self.waveform_buffer.clear()
        
        logger.info(f"Step 5: Audio recording stopped. Captured {buffer_length} samples ({buffer_length / self.SAMPLE_RATE:.2f} seconds)")
        return audio_data
    
    def get_waveform_data(self) -> list[float]:
        """Get current waveform amplitude data for visualization.
        
        Returns:
            List of amplitude values for oscilloscope visualization
        """
        with self._lock:
            return list(self.waveform_buffer)
    
    def get_current_amplitude(self) -> float:
        """Get the most recent amplitude value.
        
        Returns:
            Current amplitude (0.0 if no data)
        """
        with self._lock:
            if self.waveform_buffer:
                return float(self.waveform_buffer[-1])
            return 0.0
    
    def is_active(self) -> bool:
        """Check if recording is active.
        
        Returns:
            True if recording, False otherwise
        """
        return self.is_recording

