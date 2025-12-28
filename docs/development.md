# Development Guide

## Development Environment Setup

### Prerequisites

- **macOS** (Apple Silicon recommended)
- **Python 3.12+** with `uv` package manager
- **Xcode 15.0+** (for SwiftUI app development)
- **Git** (for version control)

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd local-flow
```

### Step 2: Install Python Dependencies

```bash
cd backend
uv sync
cd ..
```

This installs all development dependencies including:

- FastAPI and Uvicorn
- MLX-Whisper
- Development tools

### Step 3: Set Up Xcode Project

**Option A: Using xcodegen (Recommended)**

```bash
cd LocalFlowApp
xcodegen generate
open LocalFlow.xcodeproj
```

**Option B: Manual Setup**

1. Open Xcode
2. Create new macOS App project
3. Name it "LocalFlow"
4. Copy Swift files from `LocalFlowApp/LocalFlowApp/` into project
5. Add `Info.plist` and `LocalFlowApp.entitlements`

### Step 4: Verify Setup

```bash
# Test backend
cd backend
uv run python -m server

# Test SwiftUI build
cd ..
./scripts/build.sh
```

## Project Structure

```javascript
local-flow/
├── backend/                 # Python backend
│   ├── main.py              # Entry point (CLI or server mode)
│   ├── server.py            # FastAPI HTTP/WebSocket server
│   ├── config.py            # Configuration management
│   ├── engine/               # Core processing modules
│   │   ├── __init__.py
│   │   ├── audio.py          # Audio capture and waveform
│   │   ├── transcriber.py    # MLX-Whisper transcription
│   │   ├── vad.py            # Silero VAD
│   │   └── injector.py       # Text injection
│   ├── pyproject.toml        # Python dependencies
│   └── uv.lock               # Dependency lock file
├── LocalFlowApp/             # SwiftUI frontend
│   ├── LocalFlowApp/
│   │   ├── LocalFlowApp.swift        # Main app entry
│   │   ├── Views/                    # SwiftUI views
│   │   │   ├── RecordingOverlayView.swift
│   │   │   ├── PreferencesView.swift
│   │   │   └── ModelManagerView.swift
│   │   ├── Services/                 # Backend communication
│   │   │   ├── BackendService.swift
│   │   │   ├── WebSocketService.swift
│   │   │   ├── BackendServerManager.swift
│   │   │   └── NotificationService.swift
│   │   ├── Models/                   # Data models
│   │   │   └── DataModels.swift
│   │   └── Info.plist                # App configuration
│   ├── LocalFlowApp.entitlements     # App entitlements
│   ├── project.yml                   # xcodegen configuration
│   └── Package.swift                 # Swift Package Manager
├── configs/
│   └── config.json                   # Application configuration
├── docs/                              # Documentation
├── scripts/
│   ├── build.sh                       # Build SwiftUI app
│   └── run-backend.sh                 # Run backend server
├── build/                              # Build output
│   └── LocalFlow.app                  # Built app bundle
├── run.sh                              # Interactive menu script
└── README.md                           # Project overview
```

## Building the Application

### SwiftUI App
checks
**Using build script (Recommended):**

```bash
./scripts/build.sh
```

This script:

1. Checks for Xcode and dependencies
2. Creates Xcode project if needed
3. Builds the app with xcodebuild
4. Creates app bundle at `build/LocalFlow.app`
5. Bundles Python backend files

**Using Xcode:**

1. Open `LocalFlowApp/LocalFlow.xcodeproj`
2. Select scheme: **LocalFlowApp**
3. Select configuration: **Release** or **Debug**
4. Build: **Cmd+B**
5. Run: **Cmd+R**

**Build Configuration:**

- **Release**: Optimized build for distribution
- **Debug**: Debug symbols, no optimization

### Python Backend

The backend doesn't require building (Python is interpreted), but dependencies must be installed:

```bash
cd backend
uv sync
```

## Running in Development Mode

### Backend Server

**Option 1: Direct Python**

```bash
cd backend
uv run python server.py
```

**Option 2: Using script**

```bash
./scripts/run-backend.sh
```

**Option 3: Using main.py**

```bash
cd backend
uv run python main.py --server --host 127.0.0.1 --port 8000
```

**Development Tips:**

- Server auto-reloads on code changes (if using uvicorn with `--reload`)
- Check logs in terminal for debugging
- Use `--host 0.0.0.0` to allow network access (not recommended for security)

### SwiftUI App

**Option 1: From Xcode**

1. Open `LocalFlowApp/LocalFlow.xcodeproj`
2. Select **LocalFlowApp** scheme
3. Press **Cmd+R** to run

**Option 2: From command line**

```bash
# Build first
./scripts/build.sh

# Then run
open build/LocalFlow.app
```

**Option 3: Using xcodebuild**

```bash
cd LocalFlowApp
xcodebuild -scheme LocalFlowApp -configuration Debug
open build/LocalFlow.app
```

### Full Development Workflow

1. **Start backend server:**

   ```bash
   ./scripts/run-backend.sh
   ```

2. **In another terminal, build and run SwiftUI app:**

   ```bash
   ./scripts/build.sh
   open build/LocalFlow.app
   ```

3. **Make changes:**
   - Backend: Edit Python files, restart server
   - Frontend: Edit Swift files, rebuild app

4. **Test changes:**
   - Check backend logs
   - Test features in SwiftUI app
   - Verify API endpoints

## Code Organization

### Backend Structure

#### `server.py`

FastAPI application with:

- REST API endpoints
- WebSocket endpoint
- CORS middleware
- Global state management

**Key Functions:**

- `initialize_components()`: Initialize engine modules
- `start_recording()`: Start audio capture
- `stop_recording()`: Stop and process audio
- `_broadcast_message()`: Send WebSocket messages

#### `engine/audio.py`

Audio capture and processing:

- `AudioRecorder`: Main audio recording class
- Dual stream support (microphone + system audio)
- Real-time waveform calculation
- Audio mixing

**Key Methods:**

- `start_recording()`: Start audio streams
- `stop_recording()`: Stop and return audio data
- `get_waveform_data()`: Get current waveform for visualization

#### `engine/transcriber.py`

MLX-Whisper transcription:

- `WhisperTranscriber`: Model management and transcription
- Model downloading from Hugging Face
- Async transcription processing

**Key Methods:**

- `load_model()`: Load Whisper model
- `download_model()`: Download from Hugging Face
- `transcribe_async()`: Transcribe audio asynchronously

#### `engine/vad.py`

Voice Activity Detection:

- `SileroVAD`: ONNX-based VAD
- Speech boundary detection
- Silence trimming

**Key Methods:**

- `load_vad_model()`: Load ONNX model
- `find_speech_boundaries()`: Detect speech segments
- `is_speech()`: Check if audio chunk contains speech

#### `engine/injector.py`

Text injection:

- `TextInjector`: Accessibility API integration
- Focused element detection
- Direct text injection (no clipboard)

**Key Methods:**

- `inject_text()`: Inject text into focused element
- `get_focused_element()`: Get currently focused UI element
- `set_text_value()`: Set text via Accessibility API

### Frontend Structure

#### `LocalFlowApp.swift`

Main application:

- Menubar setup
- App lifecycle management
- Backend connection monitoring
- Menu creation

**Key Components:**

- `AppDelegate`: NSApplicationDelegate implementation
- `AppState`: Observable state management

#### `Views/`

SwiftUI views:

- `RecordingOverlayView`: Recording window with waveform
- `PreferencesView`: Settings and configuration UI
- `ModelManagerView`: Model download and switching

#### `Services/`

Backend communication:

- `BackendService`: HTTP REST API client
- `WebSocketService`: WebSocket client for real-time updates
- `BackendServerManager`: Backend server lifecycle
- `NotificationService`: System notifications

#### `Models/`

Data models:

- `DataModels.swift`: Swift structs for API responses
- Codable conformance for JSON encoding/decoding

## Development Workflow

### Making Backend Changes

1. **Edit Python files** in `backend/` or `backend/engine/`
2. **Restart backend server:**

   ```bash
   # Stop current server (Ctrl+C)
   ./scripts/run-backend.sh
   ```

3. **Test changes** via API or SwiftUI app

### Making Frontend Changes

1. **Edit Swift files** in `LocalFlowApp/LocalFlowApp/`
2. **Rebuild app:**

   ```bash
   ./scripts/build.sh
   ```

3. **Run app:**

   ```bash
   open build/LocalFlow.app
   ```

4. **Test changes** in running app

### Testing API Endpoints

**Using curl:**

```bash
# Check status
curl http://127.0.0.1:8000/api/status

# Start recording
curl -X POST http://127.0.0.1:8000/api/recording/start

# Stop recording
curl -X POST http://127.0.0.1:8000/api/recording/stop
```

**Using Python:**

```python
import requests

# Check status
response = requests.get("http://127.0.0.1:8000/api/status")
print(response.json())

# Start recording
response = requests.post("http://127.0.0.1:8000/api/recording/start")
print(response.json())
```

### Debugging

#### Backend Debugging

1. **Check logs** in terminal where server is running
2. **Enable debug logging:**

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Use Python debugger:**

   ```python
   import pdb
   pdb.set_trace()  # Breakpoint
   ```

#### Frontend Debugging

1. **Use Xcode debugger:**
   - Set breakpoints in Swift code
   - Run in Debug configuration
   - Use debug console

2. **Check console output:**
   - View logs in Xcode console
   - Use `print()` statements

3. **Inspect network:**
   - Use Network tab in Xcode
   - Check API requests/responses

## Dependencies

### Python Dependencies

Managed via `uv` and `pyproject.toml`:

```toml
dependencies = [
    "fastapi>=0.115.0",
    "mlx-whisper>=0.4.3",
    "numpy>=2.3.5",
    "onnxruntime>=1.23.2",
    "pynput>=1.8.1",
    "rumps>=0.4.0",
    "silero-vad>=6.2.0",
    "sounddevice>=0.5.3",
    "uvicorn[standard]>=0.32.0",
    "websockets>=14.0",
]
```

**Adding dependencies:**

```bash
cd backend
uv add package-name
```

**Updating dependencies:**

```bash
cd backend
uv sync
```

### Swift Dependencies

Currently no external Swift dependencies. All functionality uses:

- SwiftUI (built-in)
- AppKit (built-in)
- Foundation (built-in)

**Adding Swift Package Manager dependencies:**

1. Open Xcode project
2. File > Add Package Dependencies
3. Enter package URL
4. Select version
5. Add to target

## Testing

### Manual Testing

1. **Test recording:**
   - Start recording via hotkey or menu
   - Verify waveform appears
   - Stop recording
   - Verify transcription appears

2. **Test model management:**
   - Download a model
   - Switch models
   - Verify model loads

3. **Test configuration:**
   - Update hotkey
   - Change recording mode
   - Verify changes persist

### Automated Testing

Currently no automated tests. To add:

**Backend (Python):**

- Use `pytest` for unit tests
- Test engine modules independently
- Mock external dependencies

**Frontend (Swift):**

- Use XCTest for unit tests
- Test view models
- Test API client

## Code Style

### Python

- Follow PEP 8 style guide
- Use type hints where possible
- Document functions with docstrings
- Keep functions focused and small

**Example:**

```python
def process_audio(audio_data: np.ndarray) -> str:
    """Process audio data and return transcription.
    
    Args:
        audio_data: Audio samples as numpy array
        
    Returns:
        Transcribed text
    """
    # Implementation
```

### Swift

- Follow Swift API Design Guidelines
- Use meaningful names
- Document public APIs
- Prefer value types

**Example:**

```swift
/// Starts recording audio from configured devices.
/// - Returns: True if recording started successfully
func startRecording() async -> Bool {
    // Implementation
}
```

## Contributing

### Development Process

1. **Create feature branch:**

   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes:**
   - Write code
   - Test thoroughly
   - Update documentation

3. **Commit changes:**

   ```bash
   git add .
   git commit -m "Add feature description"
   ```

4. **Push and create PR:**

   ```bash
   git push origin feature/my-feature
   # Create pull request on GitHub
   ```

### Code Review Guidelines

- Ensure code follows style guidelines
- Add tests for new features
- Update documentation
- Verify backward compatibility
- Test on Apple Silicon hardware

### Release Process

1. **Update version numbers**
2. **Update CHANGELOG.md**
3. **Build release:**

   ```bash
   ./scripts/build.sh
   ```

4. **Test release build**
5. **Create GitHub release**
6. **Tag release:**

   ```bash
   git tag v1.0.0
   git push --tags
   ```

## Troubleshooting Development Issues

### Backend Won't Start

1. Check Python version: `python --version` (should be 3.12+)
2. Verify dependencies: `uv sync`
3. Check port 8000 is available
4. Review error logs

### SwiftUI App Won't Build

1. Verify Xcode is installed
2. Check Swift version compatibility
3. Clean build: `xcodebuild clean`
4. Delete derived data
5. Rebuild project

### API Connection Fails

1. Verify backend is running
2. Check URL: `http://127.0.0.1:8000`
3. Test with curl: `curl http://127.0.0.1:8000/api/status`
4. Check CORS settings
5. Review network logs

### Model Loading Fails

1. Verify model is downloaded
2. Check cache directory permissions
3. Verify disk space
4. Check Hugging Face Hub connectivity
5. Review backend logs

## Additional Resources

- [Architecture Documentation](architecture.md)
- [API Reference](api-reference.md)
- [Technical Details](technical-details.md)
- [MLX-Whisper Documentation](https://github.com/ml-explore/mlx-examples/tree/main/whisper)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SwiftUI Documentation](https://developer.apple.com/documentation/swiftui/)
