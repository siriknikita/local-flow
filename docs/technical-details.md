# Technical Details

## Audio Processing

### Audio Format

LocalFlow processes audio in a standardized format optimized for Whisper transcription:

- **Sample Rate**: 16,000 Hz (16 kHz)
  - Whisper standard sample rate
  - Balances quality and processing speed
  - Reduces memory usage compared to higher rates

- **Channels**: Mono (1 channel)
  - Whisper expects mono input
  - Stereo is converted to mono by averaging channels
  - Reduces processing overhead

- **Format**: Float32 (32-bit floating point)
  - Range: -1.0 to 1.0
  - Standard for audio processing
  - Compatible with numpy and MLX

- **Buffer Size**: 1,024 samples
  - ~64ms of audio per buffer
  - Balances latency and efficiency
  - Provides responsive waveform visualization

### Audio Capture

#### Microphone Capture

```python
# Single microphone stream
mic_stream = sd.InputStream(
    device=microphone_device,
    samplerate=16000,
    channels=1,
    blocksize=1024,
    callback=mic_callback,
    dtype=np.float32
)
```

**Process:**

1. Open input stream from selected device
2. Callback receives audio chunks (1024 samples)
3. Convert to mono if stereo
4. Store in buffer for processing

#### System Audio Capture

System audio capture requires a virtual audio driver (BlackHole):

```python
# System audio stream (BlackHole)
system_stream = sd.InputStream(
    device=blackhole_device,
    samplerate=16000,
    channels=1,
    blocksize=1024,
    callback=system_callback,
    dtype=np.float32
)
```

**Requirements:**

- BlackHole virtual audio driver installed
- System audio routed to BlackHole (via Multi-Output Device)
- BlackHole device detected automatically

#### Dual Audio Mixing

When both microphone and system audio are enabled:

```python
# Mixing algorithm
mixed_audio = mic_chunk + system_chunk
```

**Process:**

1. Capture both streams simultaneously
2. Mix in real-time using separate threads
3. Add audio samples (simple addition)
4. Store mixed audio in main buffer

**Considerations:**

- No normalization (may clip if both sources are loud)
- Mixing happens in chunks for efficiency
- Separate buffers prevent blocking

### Waveform Visualization

Real-time waveform data is calculated from audio amplitude:

```python
amplitude = np.abs(audio_data).mean()
```

**Process:**

1. Calculate mean absolute amplitude per buffer
2. Store in circular buffer (200 samples max)
3. Stream via WebSocket at ~20 FPS
4. Frontend renders as oscilloscope visualization

**Visualization:**

- Green line showing amplitude over time
- Center line at zero amplitude
- Yellow indicator for current amplitude
- Updates in real-time during recording

## Transcription Pipeline

### MLX-Whisper Integration

MLX-Whisper is a Metal-accelerated implementation of OpenAI's Whisper model, optimized for Apple Silicon.

#### Model Loading

```python
from mlx_whisper.load_models import load_model

# Load from local cache
model = load_model(model_path)

# Or load from Hugging Face directly
model = load_model("mlx-community/whisper-large-v3-turbo")
```

**Process:**

1. Check if model exists in cache
2. Download from Hugging Face if not found
3. Load model weights into MLX arrays
4. Initialize model on Metal device (GPU)

**Model Variants:**

| Variant | Parameters | Size | Speed | Accuracy |
|---------|-----------|------|-------|----------|
| tiny | ~39M | ~75MB | Fastest | Lowest |
| base | ~74M | ~150MB | Fast | Low |
| small | ~244M | ~500MB | Medium | Good |
| medium | ~769M | ~1.5GB | Slower | High |
| large | ~1550M | ~3GB | Slow | Very High |
| large-turbo | ~1550M | ~3GB | Medium | Very High |

**large-turbo** is optimized for Apple Silicon with:

- Quantized weights (INT8)
- Optimized attention mechanisms
- Metal shader optimizations

#### Transcription Process

```python
import mlx_whisper

# Transcribe audio
result = mlx_whisper.transcribe(
    audio_data,
    path_or_hf_repo="mlx-community/whisper-large-v3-turbo"
)

# Extract text
text = result.get('text', '')
```

**Pipeline:**

1. **Preprocessing**: Normalize audio to [-1, 1] range
2. **Feature Extraction**: Convert to mel-spectrogram
3. **Encoding**: Process through encoder (Transformer)
4. **Decoding**: Generate text tokens (autoregressive)
5. **Post-processing**: Convert tokens to text

**Performance:**

- Real-time factor: 0.5x to 2x (depending on model)
- Metal acceleration: 5-10x faster than CPU
- Memory usage: ~4GB for large models

### Async Transcription

Transcription runs asynchronously to avoid blocking:

```python
def transcribe_async(audio_data, callback):
    def _transcribe():
        text = transcribe(audio_data)
        callback(text)
    
    thread = threading.Thread(target=_transcribe, daemon=True)
    thread.start()
```

**Benefits:**

- UI remains responsive
- Can process multiple recordings
- Non-blocking audio capture

## Voice Activity Detection (VAD)

### Silero VAD

Silero VAD is an ONNX-based voice activity detection model that identifies speech segments in audio.

#### Model Architecture

- **Format**: ONNX (Open Neural Network Exchange)
- **Input**: 512 samples (32ms at 16kHz)
- **Output**: Speech probability (0.0 to 1.0)
- **State**: Hidden state for streaming (2 layers, 128 hidden units)

#### VAD Process

```python
# Process audio chunk
is_speech = vad.is_speech(audio_chunk)

# Find speech boundaries
start_idx, end_idx = vad.find_speech_boundaries(
    audio_stream,
    padding_ms=100
)
```

**Steps:**

1. **Chunking**: Split audio into 512-sample chunks
2. **Inference**: Run ONNX model on each chunk
3. **Thresholding**: Classify as speech if probability > 0.5
4. **Boundary Detection**: Find first and last speech chunks
5. **Padding**: Add padding (100ms default) around speech

#### Speech Boundary Detection

```python
def find_speech_boundaries(audio_stream, padding_ms=100):
    # Process stream
    speech_results = process_stream(audio_stream)
    
    # Find first and last speech
    first_speech = first_index_where(speech_results, is_speech=True)
    last_speech = last_index_where(speech_results, is_speech=True)
    
    # Convert to sample indices
    start = first_speech * CHUNK_SIZE
    end = (last_speech + 1) * CHUNK_SIZE
    
    # Add padding
    padding_samples = int((padding_ms / 1000.0) * SAMPLE_RATE)
    start = max(0, start - padding_samples)
    end = min(len(audio_stream), end + padding_samples)
    
    return (start, end)
```

**Benefits:**

- Removes leading/trailing silence
- Reduces transcription time
- Improves accuracy by focusing on speech
- Handles variable-length recordings

#### State Management

VAD maintains hidden state for streaming:

```python
# Initialize state
state = np.zeros((2, 1, 128), dtype=np.float32)

# Update state during inference
outputs = session.run(None, {
    'input': audio_chunk,
    'state': state,
    'sr': np.array(16000, dtype=np.int64)
})
state = outputs[1]  # Update state
```

**Purpose:**

- Maintains context across chunks
- Improves accuracy for continuous audio
- Enables real-time streaming VAD

## Text Injection

### Accessibility API

LocalFlow uses macOS Accessibility API for direct text injection (no clipboard).

#### Permission Requirements

```python
import Quartz

# Check permissions
trusted = Quartz.AXIsProcessTrustedWithOptions(options)

# Request permissions (shows system dialog)
options = NSDictionary.dictionaryWithObject_forKey_(
    True,
    Quartz.kAXTrustedCheckOptionPrompt
)
```

**Required for:**

- Getting focused UI element
- Setting text value
- Simulating keyboard input

#### Focused Element Detection

```python
def get_focused_element():
    # Get system-wide accessibility element
    system_wide = Quartz.AXUIElementCreateSystemWide()
    
    # Get focused application
    focused_app_ref = Quartz.AXUIElementCopyAttributeValue(
        system_wide,
        Quartz.kAXFocusedApplicationAttribute,
        NoneObj
    )
    
    # Get focused UI element
    focused_element_ref = Quartz.AXUIElementCopyAttributeValue(
        focused_app,
        Quartz.kAXFocusedUIElementAttribute,
        NoneObj
    )
    
    return focused_element_ref[1]
```

**Process:**

1. Get system-wide accessibility element
2. Find focused application
3. Get focused UI element within application
4. Return element for text injection

#### Direct Text Injection

**Method 1: Set Value Attribute**

```python
def set_text_value(element, text):
    text_value = AppKit.NSString.stringWithString_(text)
    error = Quartz.AXUIElementSetAttributeValue(
        element,
        Quartz.kAXValueAttribute,
        text_value
    )
    return error == Quartz.kAXErrorSuccess
```

**Method 2: Set Selected Text**

```python
def set_text_via_selection(element, text):
    # Get selected text range
    selected_range = Quartz.AXUIElementCopyAttributeValue(
        element,
        Quartz.kAXSelectedTextRangeAttribute,
        NoneObj
    )
    
    # Set selected text
    text_value = AppKit.NSString.stringWithString_(text)
    error = Quartz.AXUIElementSetAttributeValue(
        element,
        Quartz.kAXSelectedTextAttribute,
        text_value
    )
    return error == Quartz.kAXErrorSuccess
```

**Fallback: Simulated Typing**

If direct methods fail, simulate keyboard input:

```python
def simulate_typing(element, text):
    # Get application PID
    pid = Quartz.AXUIElementGetPid(element)
    
    # Type each character
    for char in text:
        key_code = char_to_keycode(char)
        key_down = Quartz.CGEventCreateKeyboardEvent(None, key_code, True)
        key_up = Quartz.CGEventCreateKeyboardEvent(None, key_code, False)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_down)
        Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_up)
        time.sleep(0.01)
```

**Injection Strategy:**

1. Try direct value setting (fastest)
2. Try selected text replacement
3. Fallback to simulated typing (slowest but most compatible)

## Hotkey System

### Global Hotkey Monitoring

LocalFlow uses `pynput` for global hotkey monitoring (legacy CLI mode) and native macOS APIs (SwiftUI app).

#### Permission Requirements

Accessibility permissions are required for:

- Monitoring keyboard events globally
- Detecting key combinations
- Distinguishing modifier keys

#### Hotkey Detection

```python
from pynput import keyboard

# Track pressed keys
pressed_keys = set()

def on_press(key):
    pressed_keys.add(key)
    if check_hotkey_combination():
        trigger_recording()

def on_release(key):
    pressed_keys.discard(key)
    if mode == "hold" and key == main_key:
        stop_recording()
```

**Process:**

1. Monitor all key press/release events
2. Track currently pressed keys
3. Check if hotkey combination is pressed
4. Trigger recording callback
5. Debounce to prevent multiple triggers

#### Debouncing

```python
last_trigger_time = 0.0
debounce_interval = 0.2  # 200ms

def check_hotkey_combination():
    current_time = time.time()
    if current_time - last_trigger_time >= debounce_interval:
        last_trigger_time = current_time
        return True
    return False
```

**Purpose:**

- Prevents multiple triggers from single key press
- Handles key repeat events
- Improves reliability

#### Recording Modes

**Toggle Mode:**

- Press hotkey to start recording
- Press again to stop
- State toggles between recording/stopped

**Hold Mode:**

- Hold hotkey to record
- Release to stop and transcribe
- Continuous recording while held

## Performance Characteristics

### Memory Usage

- **Base Application**: ~50MB
- **With large-turbo Model**: ~4GB
- **During Transcription**: +500MB (temporary)
- **Audio Buffers**: ~10MB (during recording)

### CPU Usage

- **Idle**: < 1%
- **Recording**: 5-10% (audio capture)
- **Transcription**: 50-100% single core (Metal-accelerated)
- **VAD Processing**: < 5% (lightweight)

### Latency

- **Audio Capture**: < 10ms (buffer latency)
- **Waveform Update**: ~50ms (20 FPS)
- **Transcription**: 0.5x to 2x audio duration
- **Text Injection**: < 50ms

### Throughput

- **Real-time Factor**: 0.5x to 2x (depending on model)
- **large-turbo on M4 Pro**: ~1x real-time (1 second audio = 1 second transcription)
- **base model**: ~2x real-time (faster than real-time)

## Optimization Techniques

### Metal Acceleration

MLX-Whisper uses Metal for GPU acceleration:

- Model weights stored in Metal buffers
- Matrix operations on GPU
- 5-10x faster than CPU
- Automatic memory management

### Async Processing

- Audio capture: Separate thread
- Transcription: Background thread
- WebSocket: Async event loop
- Non-blocking UI updates

### Memory Management

- Model weights: Lazy loading
- Audio buffers: Circular buffers
- Transcription results: Immediate cleanup
- State management: Minimal retention

### Caching

- Models: Cached in `~/.cache/local_whisper`
- VAD model: Loaded once, reused
- Configuration: Loaded on startup
- Device detection: Cached per session

## Limitations and Considerations

### Audio Quality

- **Sample Rate**: Fixed at 16kHz (Whisper requirement)
- **Format**: Mono only (stereo converted)
- **Latency**: ~64ms buffer latency
- **Quality**: Depends on microphone and environment

### Transcription Accuracy

- **Language**: Primarily English (Whisper supports many languages)
- **Accents**: Varies by model size
- **Background Noise**: VAD helps but may affect accuracy
- **Technical Terms**: May require larger models

### System Compatibility

- **macOS Only**: Uses macOS-specific APIs
- **Apple Silicon**: Optimized for M1/M2/M3/M4
- **Permissions**: Requires Accessibility permissions
- **Audio Drivers**: BlackHole required for system audio

### Performance Trade-offs

- **Model Size**: Larger = better accuracy, slower speed
- **VAD**: Improves accuracy but adds processing
- **System Audio**: Increases processing overhead
- **Real-time**: May not be truly real-time for all models

## Future Improvements

### Potential Enhancements

1. **Streaming Transcription**: Real-time transcription during recording
2. **Language Detection**: Automatic language detection
3. **Custom Models**: Support for fine-tuned models
4. **Multi-language**: Better multi-language support
5. **Noise Reduction**: Audio preprocessing for better accuracy
6. **Speaker Diarization**: Identify different speakers
7. **Punctuation**: Better punctuation handling
8. **Formatting**: Smart formatting of transcribed text

### Technical Optimizations

1. **Model Quantization**: Further reduce model size
2. **Batch Processing**: Process multiple recordings
3. **Caching**: Cache transcription results
4. **Parallel Processing**: Multi-core transcription
5. **Streaming VAD**: Real-time VAD during recording
