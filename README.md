# LocalFlow

A professional, system-wide AI dictation application for macOS (optimized for M4 Pro). LocalFlow captures audio via a global hotkey, visualizes the waveform in real-time, transcribes using MLX-Whisper (Metal-accelerated), and injects text directly into any application using the Accessibility API.

## Features

- **Local-First**: All processing happens on-device using Apple Silicon (MLX)
- **Global Hotkey**: Trigger recording from anywhere with a customizable hotkey
- **Dual Audio Capture**: Record from both microphone and system audio (headphones) simultaneously
- **Real-Time Visualization**: Oscilloscope-style waveform display during recording
- **MLX-Whisper**: Fast, Metal-accelerated transcription using Whisper large-v3-turbo
- **Silero VAD**: Professional voice activity detection (ONNX, no PyTorch overhead)
- **Direct Text Injection**: Uses Accessibility API (no clipboard) to inject text into any app
- **Model Management**: Download and switch between Whisper model variants
- **Menubar Integration**: Runs quietly in the macOS status bar

## Requirements

- macOS (Apple Silicon recommended for best performance)
- Python 3.12+ with `uv` package manager
- Xcode (for building the SwiftUI app)
- Accessibility permissions (granted on first run)

## Quick Start

### 1. Install Dependencies

```bash
git clone <repository-url>
cd local-flow
cd backend
uv sync
cd ..
```

### 2. Build the App

```bash
./scripts/build.sh
```

### 3. Start Backend Server

```bash
./scripts/run-backend.sh
```

Keep this terminal window open.

### 4. Launch the App

```bash
open build/LocalFlow.app
```

### 5. First-Time Setup

1. **Grant Permissions**: macOS will prompt for Accessibility permissions. Grant them in **System Settings > Privacy & Security > Accessibility**.

2. **Configure Hotkey**:
   - Click the menu bar icon (🎤)
   - Select **Preferences**
   - Click **"Listen for Shortcut"** and press your desired key combination
   - Choose recording mode (Toggle or Hold-to-Talk)
   - Click **Save Preferences**

3. **Download Model**:
   - Click **Model Manager** from the menu bar
   - Select a model variant (default: **large-turbo** for M4 Pro)
   - Click **Download** and wait for completion

## Usage

1. **Start Recording**: Press your configured hotkey (or hold it in Hold-to-Talk mode)
2. **Speak**: The overlay shows a real-time waveform visualization
3. **Stop Recording**: Press the hotkey again (Toggle) or release it (Hold mode)
4. **Text Injection**: Transcribed text automatically appears in the focused text field

**Cancel Recording**: Press **Esc** in the overlay or click **Cancel**

## Documentation

Comprehensive documentation is available in the [`docs/`](docs/) folder:

- **[User Guide](docs/user-guide.md)** - Detailed installation, setup, and usage instructions
- **[Configuration Reference](docs/configuration.md)** - All configuration options and examples
- **[API Reference](docs/api-reference.md)** - REST API and WebSocket documentation
- **[Architecture](docs/architecture.md)** - System architecture and component breakdown
- **[Development Guide](docs/development.md)** - Development setup and build process
- **[Technical Details](docs/technical-details.md)** - Deep technical information

## Architecture Overview

LocalFlow uses a client-server architecture:

- **SwiftUI Frontend**: Native macOS menubar app with real-time waveform visualization
- **Python Backend**: FastAPI server handling audio processing, transcription, and text injection
- **Communication**: HTTP REST API + WebSocket for real-time updates

```
┌─────────────┐         ┌──────────────┐
│  SwiftUI    │◄──HTTP──►│   FastAPI    │
│   Frontend  │◄──WS────►│   Backend    │
└─────────────┘         └──────┬───────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
              ┌─────▼─────┐         ┌──────▼─────┐
              │  MLX-     │         │  Silero    │
              │  Whisper  │         │  VAD       │
              └───────────┘         └────────────┘
```

See [Architecture Documentation](docs/architecture.md) for detailed diagrams and component descriptions.

## Configuration

Configuration is stored in `configs/config.json`. Basic structure:

```json
{
  "hotkey": {
    "modifiers": ["cmd", "shift"],
    "key": "space"
  },
  "model": "mlx-community/whisper-large-v3-turbo",
  "mode": "toggle",
  "vad_enabled": true,
  "audio": {
    "auto_detect_devices": true,
    "mix_audio": true
  }
}
```

See [Configuration Reference](docs/configuration.md) for all available options.

## Model Variants

Available Whisper models (from fastest to most accurate):

- **tiny**: Fastest, least accurate
- **base**: Good balance
- **small**: Better accuracy
- **medium**: High accuracy
- **large**: Very high accuracy
- **large-turbo**: Best accuracy, optimized for Apple Silicon (recommended for M4 Pro)

## System Audio Capture (Optional)

To capture audio from headphones/system audio:

1. Install [BlackHole](https://github.com/ExistentialAudio/BlackHole) virtual audio driver
2. LocalFlow automatically detects BlackHole when recording starts
3. Microphone and system audio are mixed together

Without BlackHole, only microphone audio is captured (sufficient for most use cases).

## Troubleshooting

### Menu Bar Icon Not Visible

- Check **System Settings > Dock & Menu Bar** to ensure menu bar icons aren't hidden
- Verify app is running in Activity Monitor
- Restart the app

### Backend Disconnected

- Start backend server: `./scripts/run-backend.sh`
- Check terminal for "Uvicorn running on <http://127.0.0.1:8000>"
- Enable "Auto-start backend server" in Preferences

### Hotkey Not Working

- Verify Accessibility permissions in **System Settings > Privacy & Security > Accessibility**
- Check for conflicts with other apps
- Try a different key combination

### Audio Issues

- Check microphone permissions in System Settings
- Verify microphone is connected and working
- For system audio, ensure BlackHole is installed

See [User Guide - Troubleshooting](docs/user-guide.md#troubleshooting) for more detailed solutions.

## Development

For development setup, build process, and contributing guidelines, see the [Development Guide](docs/development.md).

## License

Apache License 2.0
