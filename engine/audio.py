"""Audio capture and waveform processing for LocalFlow."""
import logging
import threading
from collections import deque
from typing import Callable, Optional

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
        self.audio_buffer: deque = deque()  # Unbounded buffer to preserve all audio
        self.waveform_buffer: deque = deque(maxlen=200)  # Store waveform points for visualization
        self.is_recording = False
        self.waveform_callback: Optional[Callable[[float], None]] = None
        self._lock = threading.Lock()
        logger.info("AudioRecorder initialized successfully")
        
    def start_recording(self, waveform_callback: Optional[Callable[[float], None]] = None):
        """Start recording audio stream.
        
        Args:
            waveform_callback: Optional callback function that receives amplitude values
        """
        if self.is_recording:
            logger.warning("Recording already in progress, ignoring start request")
            return
        
        logger.info("Step 1: Starting audio recording")
        self.waveform_callback = waveform_callback
        self.audio_buffer.clear()
        self.waveform_buffer.clear()
        logger.debug("Step 2: Audio buffers cleared")
        
        def audio_callback(indata, frames, time, status):
            """Callback for audio stream."""
            if status:
                logger.warning(f"Audio callback status: {status}")
            
            with self._lock:
                # Convert to mono if stereo
                if indata.ndim > 1:
                    audio_data = np.mean(indata, axis=1)
                else:
                    audio_data = indata.flatten()
                
                # Store audio data
                self.audio_buffer.extend(audio_data)
                
                # Calculate amplitude for waveform visualization
                amplitude = np.abs(audio_data).mean()
                self.waveform_buffer.append(amplitude)
                
                # Call waveform callback if provided
                if self.waveform_callback:
                    try:
                        self.waveform_callback(float(amplitude))
                    except Exception as e:
                        logger.error(f"Error in waveform callback: {e}", exc_info=True)
        
        try:
            logger.info(f"Step 3: Creating audio stream (sample_rate={self.SAMPLE_RATE}, channels={self.CHANNELS}, buffer_size={self.BUFFER_SIZE})")
            self.stream = sd.InputStream(
                samplerate=self.SAMPLE_RATE,
                channels=self.CHANNELS,
                blocksize=self.BUFFER_SIZE,
                callback=audio_callback,
                dtype=np.float32
            )
            logger.debug("Step 4: Starting audio stream")
            self.stream.start()
            self.is_recording = True
            logger.info("Step 5: Audio recording started successfully")
        except Exception as e:
            logger.error(f"Step 3: Error starting audio stream: {e}", exc_info=True)
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
        
        if self.stream:
            try:
                logger.debug("Step 2: Stopping audio stream")
                self.stream.stop()
                logger.debug("Step 3: Closing audio stream")
                self.stream.close()
                logger.info("Step 4: Audio stream stopped and closed successfully")
            except Exception as e:
                logger.error(f"Step 2: Error stopping audio stream: {e}", exc_info=True)
            finally:
                self.stream = None
        
        # Convert buffer to numpy array
        with self._lock:
            audio_data = np.array(list(self.audio_buffer), dtype=np.float32)
            buffer_length = len(audio_data)
            self.audio_buffer.clear()
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

