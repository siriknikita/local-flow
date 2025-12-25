"""Silero VAD (ONNX) for voice activity detection."""
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)


class SileroVAD:
    """Silero VAD model for voice activity detection using ONNX."""
    
    SAMPLE_RATE = 16000
    CHUNK_SIZE = 512  # 32ms at 16kHz
    
    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize Silero VAD.
        
        Args:
            cache_dir: Directory to cache the ONNX model. Defaults to ~/.cache/silero_vad
        """
        logger.info("Initializing SileroVAD")
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/silero_vad")
        logger.debug(f"VAD cache directory: {self.cache_dir}")
        self.model_path: Optional[Path] = None
        self.session: Optional[ort.InferenceSession] = None
        self._state = None  # State for streaming (shape: [2, batch, 128])
        logger.info("SileroVAD initialized successfully")
        
    def load_vad_model(self) -> bool:
        """Load ONNX model from silero-vad package.
        
        Returns:
            True if model loaded successfully, False otherwise
        """
        logger.info("Step 1: Starting VAD model loading")
        try:
            # Try to get model path from silero-vad package
            try:
                import silero_vad
                import silero_vad.data
                
                # Get the package directory
                package_dir = Path(silero_vad.__file__).parent
                # Look for ONNX model in the data directory
                model_path = package_dir / "data" / "silero_vad.onnx"
                
                if not model_path.exists():
                    # Try alternative model name
                    model_path = package_dir / "data" / "silero_vad_16k_op15.onnx"
                
                if not model_path.exists():
                    logger.warning("Step 2: ONNX model not found in silero-vad package")
                    return False
                
                logger.info(f"Step 2: Found ONNX model in package at {model_path}")
                self.model_path = model_path
                
            except ImportError:
                logger.warning("Step 2: silero-vad package not available, VAD will be disabled")
                logger.info("Step 2: Install silero-vad package: uv add silero-vad")
                return False
            except Exception as e:
                logger.warning(f"Step 2: Error locating VAD model in package: {e}")
                return False
            
            # Create ONNX Runtime session
            # Use CPU provider for compatibility (can be optimized later)
            logger.info("Step 3: Creating ONNX Runtime session")
            providers = ['CPUExecutionProvider']
            self.session = ort.InferenceSession(
                str(self.model_path),
                providers=providers
            )
            logger.debug(f"Step 3: ONNX Runtime session created with providers: {providers}")
            
            # Initialize hidden states for streaming
            self._reset_states()
            logger.debug("Step 4: Hidden states initialized")
            
            logger.info(f"Step 5: Silero VAD model loaded successfully from {self.model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading VAD model: {e}", exc_info=True)
            return False
    
    def _reset_states(self):
        """Reset state for new audio stream."""
        # Get model input shape to determine state size
        if self.session is None:
            return
        
        # Silero VAD state shape: (2, batch, 128) for (num_layers, batch, hidden_size)
        # Initialize with batch size 1
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
    
    def is_speech(self, audio_chunk: np.ndarray) -> bool:
        """Check if audio chunk contains speech.
        
        Args:
            audio_chunk: Audio data as numpy array (should be 512 samples at 16kHz)
            
        Returns:
            True if speech detected, False otherwise
        """
        if self.session is None:
            raise RuntimeError("VAD model not loaded. Call load_vad_model() first.")
        
        # Ensure audio is the right shape and type
        if len(audio_chunk) != self.CHUNK_SIZE:
            # Pad or truncate if necessary
            if len(audio_chunk) < self.CHUNK_SIZE:
                audio_chunk = np.pad(audio_chunk, (0, self.CHUNK_SIZE - len(audio_chunk)))
            else:
                audio_chunk = audio_chunk[:self.CHUNK_SIZE]
        
        # Normalize to float32 and ensure correct shape
        audio_chunk = audio_chunk.astype(np.float32)
        if audio_chunk.ndim == 1:
            audio_chunk = audio_chunk.reshape(1, -1)  # (batch, samples)
        
        # Initialize state if not set
        if self._state is None:
            self._reset_states()
        
        # Prepare inputs for ONNX model
        # Silero VAD expects: input (audio), state, sr (sample rate)
        # sr needs to be a numpy array with shape [] (scalar)
        sr_array = np.array(self.SAMPLE_RATE, dtype=np.int64)
        inputs = {
            'input': audio_chunk,
            'state': self._state,
            'sr': sr_array
        }
        
        try:
            # Run inference
            outputs = self.session.run(None, inputs)
            
            # Update state for next iteration
            # Outputs: [output, stateN]
            if len(outputs) >= 2:
                speech_prob = outputs[0][0, 0]  # Extract speech probability from output
                self._state = outputs[1]  # Update state from stateN
            else:
                # Fallback if output format is different
                speech_prob = outputs[0][0, 0] if len(outputs[0].shape) > 1 else outputs[0][0]
            
            # Threshold for speech detection (typically 0.5)
            is_speech = speech_prob > 0.5
            logger.debug(f"VAD inference: speech_prob={speech_prob:.3f}, is_speech={is_speech}")
            return is_speech
            
        except Exception as e:
            logger.error(f"Error in VAD inference: {e}", exc_info=True)
            # Fallback: return True to avoid blocking
            return True
    
    def process_stream(self, audio_stream: np.ndarray) -> list[bool]:
        """Process continuous audio stream and return speech detection results.
        
        Args:
            audio_stream: Continuous audio stream as numpy array
            
        Returns:
            List of boolean values indicating speech for each chunk
        """
        results = []
        self._reset_states()
        
        # Process in chunks
        for i in range(0, len(audio_stream), self.CHUNK_SIZE):
            chunk = audio_stream[i:i + self.CHUNK_SIZE]
            if len(chunk) == self.CHUNK_SIZE:
                results.append(self.is_speech(chunk))
            elif len(chunk) > 0:
                # Pad last chunk if incomplete
                padded_chunk = np.pad(chunk, (0, self.CHUNK_SIZE - len(chunk)))
                results.append(self.is_speech(padded_chunk))
        
        return results
    
    def reset(self):
        """Reset VAD state for a new recording session."""
        self._reset_states()
    
    def find_speech_boundaries(self, audio_stream: np.ndarray, padding_ms: int = 100) -> Tuple[int, int]:
        """Find speech boundaries in audio stream with padding.
        
        Args:
            audio_stream: Audio data as numpy array (16kHz, mono, float32)
            padding_ms: Padding in milliseconds to add before first speech and after last speech
            
        Returns:
            Tuple of (start_index, end_index) representing the speech segment with padding.
            Returns (0, len(audio_stream)) if no speech detected or VAD not available.
        """
        if self.session is None:
            logger.warning("VAD model not loaded, returning full audio range")
            return (0, len(audio_stream))
        
        if len(audio_stream) == 0:
            return (0, 0)
        
        logger.info(f"Finding speech boundaries in audio stream ({len(audio_stream)} samples)")
        
        # Process stream to get speech detection results
        speech_results = self.process_stream(audio_stream)
        
        if not speech_results:
            logger.warning("No speech detection results, returning full audio range")
            return (0, len(audio_stream))
        
        # Find first and last speech indices
        first_speech_idx = None
        last_speech_idx = None
        
        for i, is_speech in enumerate(speech_results):
            if is_speech:
                if first_speech_idx is None:
                    first_speech_idx = i
                last_speech_idx = i
        
        # If no speech detected, return full range
        if first_speech_idx is None:
            logger.info("No speech detected in audio, returning full range")
            return (0, len(audio_stream))
        
        # Convert chunk indices to sample indices
        first_sample = first_speech_idx * self.CHUNK_SIZE
        last_sample = (last_speech_idx + 1) * self.CHUNK_SIZE
        
        # Add padding (convert ms to samples)
        padding_samples = int((padding_ms / 1000.0) * self.SAMPLE_RATE)
        
        # Apply padding, ensuring we don't go out of bounds
        start_index = max(0, first_sample - padding_samples)
        end_index = min(len(audio_stream), last_sample + padding_samples)
        
        logger.info(f"Speech boundaries found: start={start_index} ({start_index/self.SAMPLE_RATE:.2f}s), "
                   f"end={end_index} ({end_index/self.SAMPLE_RATE:.2f}s), "
                   f"duration={(end_index-start_index)/self.SAMPLE_RATE:.2f}s")
        
        return (start_index, end_index)

