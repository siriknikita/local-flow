# Configuration Reference

## Overview

LocalFlow configuration is stored in `configs/config.json` as a JSON file. The configuration is loaded on backend startup and can be updated via the API or by editing the file directly.

## Configuration File Location

```javascript
configs/config.json
```

The file is created automatically with default values if it doesn't exist.

## Configuration Structure

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

## Configuration Fields

### `hotkey`

Global hotkey configuration for triggering recording.

**Type:** `object | null`

**Structure:**

```json
{
  "modifiers": ["cmd", "shift"],
  "key": "space"
}
```

**Fields:**

- `modifiers` (array of strings): Modifier keys
  - Valid values: `"cmd"`, `"ctrl"`, `"alt"`, `"shift"`
  - Can include multiple modifiers
  - Order doesn't matter
- `key` (string): Main key
  - Valid values: `"space"`, `"enter"`, `"tab"`, or any single character
  - For special keys, use key names (see below)

**Examples:**

```json
// Cmd+Shift+Space (default)
{
  "modifiers": ["cmd", "shift"],
  "key": "space"
}

// Ctrl+Alt+S
{
  "modifiers": ["ctrl", "alt"],
  "key": "s"
}

// Cmd+Option+Return
{
  "modifiers": ["cmd", "alt"],
  "key": "enter"
}
```

**Special Keys:**

- `"space"`: Spacebar
- `"enter"`: Enter/Return
- `"tab"`: Tab
- `"esc"`: Escape
- `"backspace"`: Backspace
- `"delete"`: Delete
- `"up"`, `"down"`, `"left"`, `"right"`: Arrow keys
- `"f1"` through `"f12"`: Function keys
- Any single character: `"a"`, `"1"`, `"!"`, etc.

**Default:** `null` (no hotkey configured)

**Notes:**

- Hotkey changes may require app restart (in legacy CLI mode)
- Avoid conflicts with system shortcuts
- Accessibility permissions required for hotkey monitoring

---

### `model`

Whisper model to use for transcription.

**Type:** `string`

**Format:** Hugging Face repository ID

**Valid Values:**

- `"mlx-community/whisper-tiny"`
- `"mlx-community/whisper-base"`
- `"mlx-community/whisper-small"`
- `"mlx-community/whisper-medium"`
- `"mlx-community/whisper-large-v3"`
- `"mlx-community/whisper-large-v3-turbo"` (default)

**Default:** `"mlx-community/whisper-large-v3-turbo"`

**Notes:**

- Model must be downloaded before use
- Configuration is automatically updated when switching models via API
- Large models provide better accuracy but are slower

---

### `mode`

Recording mode for hotkey behavior.

**Type:** `string`

**Valid Values:**

- `"toggle"`: Press to start, press again to stop
- `"hold"`: Hold while speaking, release to stop

**Default:** `"toggle"`

**Usage:**

- **Toggle mode**: Good for longer dictation sessions, can pause and resume
- **Hold mode**: Good for quick voice commands, hands-free operation

---

### `cache_dir`

Directory for caching downloaded Whisper models.

**Type:** `string`

**Format:** Path (supports `~` expansion)

**Default:** `"~/.cache/local_whisper"`

**Examples:**

```json
// Default (home directory)
"cache_dir": "~/.cache/local_whisper"

// Custom path
"cache_dir": "/Users/username/models/whisper"

// Absolute path
"cache_dir": "/Volumes/External/models"
```

**Notes:**

- Directory is created automatically if it doesn't exist
- Models are cached here after download
- Changing this doesn't move existing models
- Ensure sufficient disk space (3-5GB for large models)

---

### `vad_enabled`

Enable Voice Activity Detection (VAD) for automatic silence trimming.

**Type:** `boolean`

**Default:** `true`

**When Enabled:**

- Silero VAD automatically detects speech boundaries
- Trims silence from beginning and end of recordings
- Adds padding (100ms default) around speech segments
- Improves transcription accuracy by removing noise

**When Disabled:**

- Full audio is transcribed without trimming
- Useful for non-speech audio or very quiet recordings

**Notes:**

- VAD requires Silero VAD ONNX model (loaded automatically)
- VAD processing adds minimal overhead
- Recommended to keep enabled for most use cases

---

### `audio`

Audio device configuration.

**Type:** `object`

**Structure:**

```json
{
  "microphone_device": null,
  "system_audio_device": null,
  "mix_audio": true,
  "auto_detect_devices": true
}
```

#### `microphone_device`

Microphone input device index.

**Type:** `integer | null`

**Default:** `null` (auto-detect default input device)

**Examples:**

```json
// Auto-detect (default)
"microphone_device": null

// Specific device index
"microphone_device": 0
```

**Finding Device Index:**

```python
import sounddevice as sd
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f"{i}: {device['name']}")
```

**Notes:**

- `null` uses system default input device
- Device index may change if devices are connected/disconnected
- Use `auto_detect_devices: true` for automatic detection

---

#### `system_audio_device`

System audio/loopback device index (for BlackHole).

**Type:** `integer | null`

**Default:** `null` (auto-detect BlackHole device)

**Examples:**

```json
// Auto-detect BlackHole (default)
"system_audio_device": null

// Specific device index
"system_audio_device": 2

// Disable system audio capture
"system_audio_device": null
// And set mix_audio: false
```

**Notes:**

- `null` attempts to auto-detect BlackHole device
- Requires BlackHole virtual audio driver for system audio capture
- Falls back to microphone-only if not found
- Use `auto_detect_devices: true` for automatic detection

---

#### `mix_audio`

Enable mixing of microphone and system audio.

**Type:** `boolean`

**Default:** `true`

**When Enabled:**

- Microphone and system audio are mixed together
- Both streams are captured and transcribed
- Useful for transcribing video calls or system audio

**When Disabled:**

- Only microphone audio is captured
- System audio is ignored even if device is configured
- Reduces processing overhead

**Notes:**

- Requires both devices to be configured
- Mixing happens in real-time during recording
- Audio levels are added (may need normalization for some use cases)

---

#### `auto_detect_devices`

Automatically detect and use suitable audio devices.

**Type:** `boolean`

**Default:** `true`

**When Enabled:**

- Automatically finds default microphone
- Automatically finds BlackHole device (if installed)
- Overrides `microphone_device` and `system_audio_device` if they are `null`
- Device detection happens on each recording start

**When Disabled:**

- Uses explicitly configured device indices
- Fails if configured devices are not available
- More control but requires manual configuration

**Notes:**

- Recommended to keep enabled for most users
- Disable only if you need specific device control
- Device indices may change, so auto-detection is more reliable

---

## Default Configuration

Complete default configuration:

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

## Configuration Examples

### Minimal Configuration

Only essential settings:

```json
{
  "model": "mlx-community/whisper-base",
  "mode": "toggle"
}
```

All other settings use defaults.

---

### Custom Hotkey

Custom hotkey configuration:

```json
{
  "hotkey": {
    "modifiers": ["cmd", "ctrl"],
    "key": "d"
  },
  "mode": "hold"
}
```

---

### Microphone Only

Disable system audio capture:

```json
{
  "audio": {
    "microphone_device": null,
    "system_audio_device": null,
    "mix_audio": false,
    "auto_detect_devices": true
  }
}
```

---

### Specific Audio Devices

Use specific device indices:

```json
{
  "audio": {
    "microphone_device": 1,
    "system_audio_device": 3,
    "mix_audio": true,
    "auto_detect_devices": false
  }
}
```

---

### Fast Transcription

Optimize for speed over accuracy:

```json
{
  "model": "mlx-community/whisper-base",
  "vad_enabled": true,
  "audio": {
    "mix_audio": false,
    "auto_detect_devices": true
  }
}
```

---

### High Accuracy

Optimize for accuracy over speed:

```json
{
  "model": "mlx-community/whisper-large-v3-turbo",
  "vad_enabled": true,
  "audio": {
    "mix_audio": true,
    "auto_detect_devices": true
  }
}
```

---

### Custom Cache Location

Use custom model cache directory:

```json
{
  "cache_dir": "/Volumes/External/models/whisper",
  "model": "mlx-community/whisper-large-v3-turbo"
}
```

---

### No VAD

Disable voice activity detection:

```json
{
  "vad_enabled": false,
  "model": "mlx-community/whisper-large-v3-turbo"
}
```

Useful for:

- Non-speech audio
- Very quiet recordings
- When you want full audio transcribed

## Updating Configuration

### Via API

Update configuration via REST API:

```bash
curl -X PUT http://127.0.0.1:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "hold",
    "vad_enabled": false
  }'
```

Only provided fields are updated. See [API Reference](api-reference.md) for details.

### Via File Edit

Edit `configs/config.json` directly:

1. Stop the backend server (if running)
2. Edit the JSON file
3. Restart the backend server
4. Changes take effect on next startup

**Note:** File edits are not automatically reloaded. Restart required.

### Via SwiftUI App

Use the Preferences window:

1. Click LocalFlow menu bar icon
2. Select **Preferences**
3. Make changes
4. Click **Save Preferences**

Changes are saved to `configs/config.json` and take effect immediately.

## Configuration Validation

The backend validates configuration on load:

- **Invalid JSON**: Falls back to defaults
- **Missing fields**: Uses default values
- **Invalid values**: Logs warning and uses defaults
- **Invalid device indices**: Falls back to auto-detection

## Environment-Specific Settings

### Development

```json
{
  "model": "mlx-community/whisper-base",
  "cache_dir": "~/.cache/local_whisper-dev",
  "vad_enabled": true
}
```

### Production

```json
{
  "model": "mlx-community/whisper-large-v3-turbo",
  "cache_dir": "~/.cache/local_whisper",
  "vad_enabled": true,
  "audio": {
    "auto_detect_devices": true,
    "mix_audio": true
  }
}
```

## Troubleshooting Configuration

### Configuration Not Loading

1. Check file exists: `configs/config.json`
2. Verify JSON syntax (use a JSON validator)
3. Check file permissions
4. Review backend logs for errors

### Hotkey Not Working

1. Verify `hotkey` field is properly formatted
2. Check for conflicts with system shortcuts
3. Ensure Accessibility permissions are granted
4. Try a different key combination

### Audio Devices Not Found

1. Set `auto_detect_devices: true`
2. Verify devices are connected
3. Check device indices with `sounddevice.query_devices()`
4. Review backend logs for device detection messages

### Model Not Loading

1. Verify `model` field matches a valid repository ID
2. Ensure model is downloaded
3. Check `cache_dir` is accessible
4. Review backend logs for model loading errors

## Best Practices

1. **Use auto-detection**: Set `auto_detect_devices: true` for reliability
2. **Keep VAD enabled**: Improves accuracy by trimming silence
3. **Use appropriate model**: Balance speed vs accuracy for your use case
4. **Test hotkey**: Ensure no conflicts before relying on it
5. **Backup config**: Save working configuration for reference
6. **Document custom settings**: Note any non-default values for your setup
