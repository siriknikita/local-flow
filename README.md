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
- Python 3.12+
- UV package manager
- Accessibility permissions (granted on first run)

## Installation

### Python Backend

1. Clone the repository:

```bash
git clone <repository-url>
cd local-flow
```

2. Install dependencies using UV:

```bash
uv sync
```

3. Run the application:

**Option A: SwiftUI App (Recommended)**
```bash
# Start the backend server
uv run python main.py --server

# Then build and run the SwiftUI app (see SwiftUI App section below)
```

**Option B: Python UI (Legacy)**
```bash
uv run python main.py
```

### SwiftUI App

The SwiftUI app provides a native macOS experience. **Important: The SwiftUI app requires the Python backend server to be running.**

1. **Build the app:**
   ```bash
   ./build.sh
   ```

2. **Start the backend server first:**
   ```bash
   uv run python main.py --server
   ```
   
   The server will start on `http://127.0.0.1:8000`. Keep this terminal window open.

3. **Run the SwiftUI app:**
   ```bash
   open build/LocalFlow.app
   ```

4. **Find the menu bar icon:**
   - Look for a microphone icon (🎤) in the top-right menu bar
   - If you don't see it, check System Settings > Dock & Menu Bar to ensure menu bar icons aren't hidden
   - The icon should appear even if the backend isn't connected (it will show connection status in the menu)

**Note:** The build script will create an Xcode project if one doesn't exist, or you can create one manually:

1. Open Xcode
2. Create a new macOS App project
3. Set the project name to "LocalFlow"
4. Copy the Swift files from `LocalFlowApp/LocalFlowApp/` into the Xcode project
5. Build and run

## Usage

### First Run

1. **Start the backend server:**
   ```bash
   uv run python main.py --server
   ```
   Keep this terminal window open while using the app.

2. **Launch the SwiftUI app:**
   ```bash
   open build/LocalFlow.app
   ```

3. **Find the menu bar icon:**
   - Look for the microphone icon (🎤) in the top-right menu bar
   - Click it to open the menu
   - Verify you see "✓ Backend Connected" at the top of the menu

4. **Grant Permissions**: On first launch, macOS will prompt for Accessibility permissions. Grant them in System Settings > Privacy & Security > Accessibility.

5. **Set Hotkey**:
   - Click the LocalFlow icon in the menu bar
   - Select "Preferences"
   - Click "Listen for Shortcut" and press your desired key combination (e.g., Cmd+Shift+Space)
   - Choose recording mode: Toggle or Hold-to-Talk
   - Click "Save Preferences"

6. **Download Model** (if needed):
   - Click "Model Manager" from the menu bar
   - Select a model variant (default: large-turbo for M4 Pro)
   - Click "Download" and wait for completion

4. **Set Up System Audio Capture** (optional):
   - To capture audio from headphones/system audio, install BlackHole:
     - Download from: https://github.com/ExistentialAudio/BlackHole
     - Install the virtual audio driver
     - Configure in Audio MIDI Setup (Applications > Utilities)
   - LocalFlow will automatically detect BlackHole if installed
   - Without BlackHole, only microphone audio will be captured

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
  "vad_enabled": true,
  "audio": {
    "microphone_device": null,
    "system_audio_device": null,
    "mix_audio": true,
    "auto_detect_devices": true
  }
}
```

### Audio Configuration

- **microphone_device**: Device index for microphone (null = auto-detect default)
- **system_audio_device**: Device index for system audio/loopback (null = auto-detect BlackHole)
- **mix_audio**: Enable mixing of microphone and system audio (default: true)
- **auto_detect_devices**: Automatically find suitable devices (default: true)

To find available audio devices, you can list them programmatically or check System Settings > Sound.

## Model Variants

Available Whisper models (from fastest to most accurate):

- **tiny**: Fastest, least accurate
- **base**: Good balance
- **small**: Better accuracy
- **medium**: High accuracy
- **large**: Very high accuracy
- **large-turbo**: Best accuracy, optimized for Apple Silicon (recommended for M4 Pro)

## Architecture

### SwiftUI App (New)
```
LocalFlowApp/
├── LocalFlowApp.swift → Main app with menubar integration
├── Views/
│   ├── RecordingOverlayView.swift → Recording window with waveform
│   ├── PreferencesView.swift → Settings and hotkey configuration
│   └── ModelManagerView.swift → Model download and switching
├── Services/
│   ├── BackendService.swift → HTTP client for API communication
│   └── WebSocketService.swift → WebSocket client for real-time updates
└── Models/
    └── DataModels.swift → Data models for API responses
```

### Python Backend
```
main.py (Entry Point)
├── server.py → HTTP/WebSocket server for SwiftUI app
├── Menubar (rumps) → Legacy Python UI (optional)
├── ui/ → Legacy Python UI (optional)
└── engine/
    ├── transcriber.py → MLX-Whisper model loading & inference
    ├── vad.py → Silero VAD (ONNX) for voice activity detection
    ├── audio.py → Audio capture & waveform processing
    └── injector.py → Accessibility API text injection (no clipboard)
```

## Troubleshooting

### Menu Bar Icon Not Visible

If you don't see the LocalFlow menu bar icon:

1. **Check menu bar visibility settings:**
   - Open System Settings > Dock & Menu Bar
   - Ensure menu bar icons are not hidden
   - Some macOS versions hide menu bar icons when there are too many

2. **Verify the app is running:**
   - Check Activity Monitor for "LocalFlow" process
   - The app runs as a menu bar app (no dock icon)

3. **Restart the app:**
   - Quit LocalFlow completely
   - Reopen `build/LocalFlow.app`

4. **Check backend connection:**
   - Click the menu bar icon (if visible) to see connection status
   - If backend is disconnected, start the server: `uv run python main.py --server`

### Backend Server Not Running

If you see "Backend Disconnected" in the menu:

1. **Start the backend server:**
   ```bash
   uv run python main.py --server
   ```

2. **Verify the server is running:**
   - Check terminal output for "Uvicorn running on http://127.0.0.1:8000"
   - The app will automatically reconnect when the server starts

3. **Check connection status:**
   - Click the menu bar icon
   - Look for "✓ Backend Connected" or "✗ Backend Disconnected" at the top of the menu
   - Use "Check Backend Connection" menu item to manually reconnect

### Accessibility Permissions

If text injection doesn't work, ensure LocalFlow has Accessibility permissions:

- System Settings > Privacy & Security > Accessibility
- Enable LocalFlow

### Audio Issues

- Check microphone permissions in System Settings
- Ensure a microphone is connected and working
- Try restarting the application

### System Audio Capture

If you want to capture system audio (what you hear from headphones):

1. **Install BlackHole**:
   - Download from: https://github.com/ExistentialAudio/BlackHole
   - Install the virtual audio driver
   - Restart your Mac if prompted

2. **Configure BlackHole** (optional):
   - Open Audio MIDI Setup (Applications > Utilities)
   - Create a Multi-Output Device that includes both your speakers/headphones and BlackHole
   - Set this as your system output to route audio to BlackHole

3. **LocalFlow will automatically detect BlackHole** when you start recording
   - If BlackHole is not found, it will fall back to microphone-only recording
   - You'll see a log message indicating whether system audio capture is available

**Note**: Without BlackHole or another virtual audio driver, macOS does not provide direct access to system audio. LocalFlow will work perfectly fine with just microphone input.

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
