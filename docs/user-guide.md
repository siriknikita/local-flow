# LocalFlow User Guide

## Installation

### Prerequisites

- **macOS** (Apple Silicon recommended for best performance)
- **Python 3.12+** with `uv` package manager
- **Xcode** (for building the SwiftUI app)
- **Accessibility permissions** (granted on first run)

### Step 1: Clone the Repository

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

This installs all required Python packages including:

- FastAPI and Uvicorn (web server)
- MLX-Whisper (transcription)
- Silero VAD (voice activity detection)
- sounddevice (audio capture)
- PyObjC (macOS integration)

### Step 3: Build the SwiftUI App

```bash
./scripts/build.sh
```

This creates the app bundle at `build/LocalFlow.app`.

**Alternative:** Use the interactive menu script:

```bash
./run.sh
# Select option 1 to build
```

## First-Time Setup

### 1. Start the Backend Server

The SwiftUI app requires the Python backend server to be running.

**Option A: Using the menu script**

```bash
./run.sh
# Select option 2 to start backend
```

**Option B: Direct command**

```bash
./scripts/run-backend.sh
```

The server starts on `http://127.0.0.1:8000`. Keep this terminal window open.

### 2. Launch the SwiftUI App

```bash
open build/LocalFlow.app
```

### 3. Find the Menu Bar Icon

- Look for the microphone icon (🎤) in the top-right menu bar
- If you don't see it, check **System Settings > Dock & Menu Bar** to ensure menu bar icons aren't hidden
- The icon appears even if the backend isn't connected (it will show connection status)

### 4. Grant Accessibility Permissions

On first launch, macOS will prompt for Accessibility permissions. If not:

1. Open **System Settings > Privacy & Security > Accessibility**
2. Enable **LocalFlow**
3. Restart the app if needed

**Why needed:**

- Global hotkey monitoring
- Text injection into applications

### 5. Configure Hotkey

1. Click the LocalFlow icon in the menu bar
2. Select **Preferences**
3. Click **"Listen for Shortcut"** and press your desired key combination
   - Recommended: `Cmd+Shift+Space`
   - Avoid conflicts with system shortcuts
4. Choose recording mode:
   - **Toggle**: Press to start, press again to stop
   - **Hold-to-Talk**: Hold while speaking, release to stop
5. Click **Save Preferences**

### 6. Download a Model

1. Click **Model Manager** from the menu bar
2. Select a model variant:
   - **large-turbo** (recommended for M4 Pro): Best accuracy, optimized for Apple Silicon
   - **large**: Very high accuracy
   - **medium**: High accuracy, faster
   - **small**: Good balance
   - **base**: Faster, less accurate
   - **tiny**: Fastest, least accurate
3. Click **Download** and wait for completion
   - Large models can be 3-5GB and take several minutes
   - Progress is shown in notifications

### 7. (Optional) Set Up System Audio Capture

To capture audio from headphones/system audio:

1. **Install BlackHole**:
   - Download from: <https://github.com/ExistentialAudio/BlackHole>
   - Install the virtual audio driver
   - Restart your Mac if prompted

2. **Configure BlackHole** (optional):
   - Open **Audio MIDI Setup** (Applications > Utilities)
   - Create a **Multi-Output Device** that includes:
     - Your speakers/headphones
     - BlackHole
   - Set this as your system output

3. **LocalFlow automatically detects BlackHole** when recording starts
   - If not found, falls back to microphone-only recording
   - You'll see a log message indicating system audio availability

**Note:** Without BlackHole, only microphone audio will be captured. This is sufficient for most use cases.

## Usage

### Basic Dictation

1. **Start Recording**:
   - Press your configured hotkey (or hold it in Hold-to-Talk mode)
   - Or click **Start Recording** from the menu bar

2. **Speak**:
   - The overlay window shows a real-time waveform visualization
   - Speak clearly into your microphone
   - The waveform shows audio levels

3. **Stop Recording**:
   - Press the hotkey again (Toggle mode) or release it (Hold mode)
   - Or press **Enter** in the overlay
   - Or click **Stop** in the overlay

4. **Text Injection**:
   - The transcribed text automatically appears in the focused text field
   - No clipboard involved - direct injection via Accessibility API

### Recording Modes

#### Toggle Mode

- Press hotkey to start recording
- Press hotkey again to stop
- Good for longer dictation sessions
- Can pause and resume

#### Hold-to-Talk Mode

- Hold hotkey while speaking
- Release to stop and transcribe
- Good for quick voice commands
- Hands-free operation

### Canceling Recording

- Press **Esc** in the overlay window
- Or click **Cancel** in the overlay
- Recording is discarded, no transcription

### Menu Bar Options

- **Backend Connection Status**: Shows if backend is connected
- **Start/Stop Backend Server**: Control backend server from menu
- **Start/Stop Recording**: Manual recording control
- **Preferences**: Configure hotkey, mode, and server settings
- **Model Manager**: Download and switch models
- **About**: App information
- **Quit**: Exit application

## Preferences

### Global Hotkey

Configure the keyboard shortcut to trigger recording:

- Click **"Listen for Shortcut"**
- Press your desired key combination
- Common choices: `Cmd+Shift+Space`, `Cmd+Ctrl+Space`
- Avoid system shortcuts (check for conflicts)

### Recording Mode

- **Toggle**: Press to start/stop
- **Hold-to-Talk**: Hold while speaking

### Backend Server

- **Auto-start backend server**: Automatically start backend when app launches
- **Project Directory**: Path to LocalFlow project (auto-detected if left empty)

## Model Management

### Available Models

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| tiny | ~39M | Fastest | Lowest | Quick testing |
| base | ~74M | Fast | Low | Quick dictation |
| small | ~244M | Medium | Good | General use |
| medium | ~769M | Slower | High | Quality dictation |
| large | ~1550M | Slow | Very High | Professional use |
| large-turbo | ~1550M | Medium | Very High | **Recommended (M4 Pro)** |

### Downloading Models

1. Open **Model Manager** from menu bar
2. Select a model variant
3. Click **Download**
4. Wait for completion (progress shown in notifications)
5. Models are cached in `~/.cache/local_whisper`

### Switching Models

1. Open **Model Manager**
2. Select a downloaded model
3. Click **Switch**
4. Model loads (takes a few seconds)
5. Configuration is automatically updated

### Model Storage

- **Location**: `~/.cache/local_whisper`
- **Size**: 3-5GB for large models
- **Persistence**: Models persist across app restarts
- **Cleanup**: Manually delete from cache directory if needed

## System Audio Capture

### Why System Audio?

System audio capture allows you to transcribe:

- Audio from video calls
- System sounds
- Audio from other applications
- What you hear through headphones

### BlackHole Setup

1. **Download and Install**:
   - <https://github.com/ExistentialAudio/BlackHole>
   - Install the 2ch (stereo) version
   - Restart Mac if prompted

2. **Verify Installation**:
   - Open **Audio MIDI Setup**
   - You should see "BlackHole 2ch" in the device list

3. **Configure (Optional)**:
   - Create Multi-Output Device including BlackHole
   - Set as system output to route audio to BlackHole
   - LocalFlow will automatically detect and use it

4. **Usage**:
   - LocalFlow auto-detects BlackHole when recording starts
   - Microphone and system audio are mixed together
   - Both streams are transcribed

### Without BlackHole

- Only microphone audio is captured
- This is sufficient for most dictation use cases
- No additional setup required

## Troubleshooting

### Menu Bar Icon Not Visible

1. **Check menu bar visibility**:
   - System Settings > Dock & Menu Bar
   - Ensure menu bar icons aren't hidden

2. **Verify app is running**:
   - Check Activity Monitor for "LocalFlow" process
   - App runs as menu bar app (no dock icon)

3. **Restart the app**:
   - Quit LocalFlow completely
   - Reopen `build/LocalFlow.app`

### Backend Server Not Running

**Symptoms:**

- Menu shows "✗ Backend Disconnected"
- Recording doesn't start
- Model Manager doesn't work

**Solution:**

1. Start backend server:

   ```bash
   ./scripts/run-backend.sh
   ```

   Or use menu: **Start Backend Server**

2. Verify connection:
   - Menu should show "✓ Backend Connected"
   - Check terminal for "Uvicorn running on <http://127.0.0.1:8000>"

3. Auto-start option:
   - Enable "Auto-start backend server" in Preferences
   - Backend starts automatically when app launches

### Accessibility Permissions

**Symptoms:**

- Hotkey doesn't work
- Text injection doesn't work
- Permission prompts appear

**Solution:**

1. Open **System Settings > Privacy & Security > Accessibility**
2. Enable **LocalFlow**
3. Restart the app
4. Verify in menu: hotkey should work

**Note:** You may need to enable permissions for:

- LocalFlow.app
- Python (if running backend separately)
- Terminal app (if using CLI mode)

### Audio Issues

**No microphone detected:**

1. Check microphone is connected
2. Verify in System Settings > Sound
3. Check microphone permissions
4. Try restarting the app

**System audio not working:**

1. Verify BlackHole is installed
2. Check Audio MIDI Setup for BlackHole device
3. Ensure BlackHole is in Multi-Output Device (if configured)
4. Check backend logs for device detection messages

**Poor audio quality:**

1. Check microphone positioning
2. Reduce background noise
3. Speak clearly and at consistent volume
4. Try a different microphone

### Model Download Issues

**Download fails:**

1. Check internet connection
2. Verify sufficient disk space (~5GB for large models)
3. Check Hugging Face Hub accessibility
4. Try downloading a smaller model first

**Model won't load:**

1. Verify model is fully downloaded
2. Check disk space in `~/.cache/local_whisper`
3. Try re-downloading the model
4. Check backend logs for error messages

### Hotkey Conflicts

**Hotkey doesn't work:**

1. Check for conflicts with other apps
2. Try a different key combination
3. Verify Accessibility permissions
4. Restart LocalFlow after changing hotkey

**Common conflicts:**

- Spotlight (Cmd+Space)
- System shortcuts
- Other dictation apps
- Window management tools

### Text Injection Not Working

**Text doesn't appear:**

1. Verify Accessibility permissions
2. Ensure a text field is focused
3. Check if target app supports Accessibility API
4. Try a different application

**Text appears in wrong place:**

1. Ensure correct text field is focused before recording
2. Some apps may not support Accessibility API properly
3. Try clicking in the target field before recording

### Performance Issues

**Slow transcription:**

1. Use a smaller model (base, small)
2. Ensure Apple Silicon (M1/M2/M3/M4) for best performance
3. Close other resource-intensive apps
4. Check system activity in Activity Monitor

**High CPU usage:**

1. Normal during transcription (50-100% single core)
2. Use smaller model for lower CPU usage
3. Transcription is Metal-accelerated on Apple Silicon

**Memory usage:**

1. Large models use ~4GB RAM
2. Normal for MLX-Whisper models
3. Close other apps if memory constrained

## Tips and Best Practices

### For Best Accuracy

1. **Use large-turbo model** (recommended for M4 Pro)
2. **Speak clearly** at consistent volume
3. **Reduce background noise**
4. **Use good microphone** (built-in is fine, external is better)
5. **Enable VAD** to trim silence automatically

### For Best Performance

1. **Use smaller models** (base, small) for faster transcription
2. **Close other apps** during transcription
3. **Use Apple Silicon** (M1/M2/M3/M4) for Metal acceleration
4. **Disable system audio capture** if not needed

### Workflow Tips

1. **Use Toggle mode** for longer dictation sessions
2. **Use Hold-to-Talk** for quick voice commands
3. **Check transcription** before continuing (text is injected immediately)
4. **Use Cancel** (Esc) if you make a mistake
5. **Keep backend running** in background (enable auto-start)

### Integration Tips

1. **Works with any app** that supports text input
2. **No clipboard** - direct injection (more reliable)
3. **Focus target field** before recording
4. **Test with simple apps** first (TextEdit, Notes)
5. **Some apps** may have limited Accessibility API support

## Advanced Usage

### Custom Audio Devices

Edit `configs/config.json` to specify audio devices:

```json
{
  "audio": {
    "microphone_device": 0,
    "system_audio_device": 2,
    "mix_audio": true,
    "auto_detect_devices": false
  }
}
```

Find device indices using Python:

```python
import sounddevice as sd
print(sd.query_devices())
```

### VAD Configuration

Voice Activity Detection can be disabled:

```json
{
  "vad_enabled": false
}
```

**When to disable:**

- Very quiet audio
- Non-speech audio
- When you want full audio transcribed

### Cache Directory

Change model cache location:

```json
{
  "cache_dir": "/custom/path/to/cache"
}
```

Default: `~/.cache/local_whisper`

## Getting Help

- **Check logs**: Backend terminal shows detailed logs
- **Check menu status**: Connection and recording status
- **Review documentation**: See [Technical Details](technical-details.md) for deep dive
- **Check GitHub issues**: Report bugs or request features
