# LocalFlow

A professional, system-wide AI dictation application for macOS (optimized for M4 Pro). LocalFlow captures audio via a global hotkey, visualizes the waveform in real-time, transcribes using MLX-Whisper (Metal-accelerated), and injects text directly into any application using the Accessibility API.

## Features

- **Local-First**: All processing happens on-device using Apple Silicon (MLX)
- **Global Hotkey**: Trigger recording from anywhere with a customizable hotkey
- **Real-Time Visualization**: Oscilloscope-style waveform display during recording
- **MLX-Whisper**: Fast, Metal-accelerated transcription using Whisper large-v3-turbo
- **Silero VAD**: Professional voice activity detection (ONNX, no PyTorch overhead)
- **Direct Text Injection**: Uses Accessibility API (no clipboard) to inject text into any app
- **Model Management**: Download and switch between Whisper model variants
- **Menubar Integration**: Runs quietly in the macOS status bar

## Requirements

- macOS (Apple Silicon recommended for best performance)
- Python 3.12+
- UV package manager
- Accessibility permissions (granted on first run)

## Installation

1. Clone the repository:

```bash
git clone <repository-url>
cd local-flow
```

1. Install dependencies using UV:

```bash
uv sync
```

1. Run the application:

```bash
uv run python main.py
```

## Usage

### First Run

1. **Grant Permissions**: On first launch, macOS will prompt for Accessibility permissions. Grant them in System Settings > Privacy & Security > Accessibility.

2. **Set Hotkey**:
   - Click the LocalFlow icon in the menu bar
   - Select "Preferences"
   - Click "Listen for Shortcut" and press your desired key combination (e.g., Cmd+Shift+Space)
   - Choose recording mode: Toggle or Hold-to-Talk
   - Click "Save Preferences"

3. **Download Model** (if needed):
   - Click "Model Manager" from the menu bar
   - Select a model variant (default: large-turbo for M4 Pro)
   - Click "Download" and wait for completion

### Recording

1. **Start Recording**: Press your configured hotkey (or hold it in Hold-to-Talk mode)
2. **Speak**: The overlay will show a real-time waveform visualization
3. **Stop Recording**:
   - Press the hotkey again (Toggle mode) or release it (Hold mode)
   - Or press Enter in the overlay
   - Or click "Stop" in the overlay
4. **Text Injection**: The transcribed text will automatically appear in the focused text field

### Canceling

- Press Esc in the overlay
- Or click "Cancel" in the overlay

## Configuration

Configuration is stored in `config.json`:

```json
{
  "hotkey": {
    "modifiers": ["cmd", "shift"],
    "key": "space"
  },
  "model": "mlx-community/whisper-large-v3-turbo",
  "mode": "toggle",
  "cache_dir": "~/.cache/local_whisper",
  "vad_enabled": true
}
```

## Model Variants

Available Whisper models (from fastest to most accurate):

- **tiny**: Fastest, least accurate
- **base**: Good balance
- **small**: Better accuracy
- **medium**: High accuracy
- **large**: Very high accuracy
- **large-turbo**: Best accuracy, optimized for Apple Silicon (recommended for M4 Pro)

## Architecture

```javascript
main.py (Entry Point)
├── Menubar (rumps) → Preferences, Model Manager, About, Quit
├── ui/
│   ├── overlay.py → Recording overlay with oscilloscope waveform
│   └── settings.py → Preferences & Model Manager windows
└── engine/
    ├── transcriber.py → MLX-Whisper model loading & inference
    ├── vad.py → Silero VAD (ONNX) for voice activity detection
    ├── audio.py → Audio capture & waveform processing
    └── injector.py → Accessibility API text injection (no clipboard)
```

## Troubleshooting

### Accessibility Permissions

If text injection doesn't work, ensure LocalFlow has Accessibility permissions:

- System Settings > Privacy & Security > Accessibility
- Enable LocalFlow

### Audio Issues

- Check microphone permissions in System Settings
- Ensure a microphone is connected and working
- Try restarting the application

### Model Download Issues

- Check internet connection
- Ensure sufficient disk space (~3-5GB for large models)
- Models are cached in `~/.cache/local_whisper/`

### Hotkey Conflicts

If your hotkey doesn't work:

- Try a different key combination
- Check if another app is using the same hotkey
- Restart LocalFlow after changing hotkey

## License

Apache License 2.0
