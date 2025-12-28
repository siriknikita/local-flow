# LocalFlow API Reference

## Overview

LocalFlow provides a REST API for controlling the application and a WebSocket API for real-time updates. The API is served by the Python backend at `http://127.0.0.1:8000` by default.

## Base URL

```javascript
http://127.0.0.1:8000
```

## Authentication

No authentication is required. The API is only accessible from localhost for security.

## REST API Endpoints

### Get Application Status

Get the current status of the application.

**Endpoint:** `GET /api/status`

**Response:**

```json
{
  "is_recording": false,
  "model_loaded": "large-turbo",
  "vad_enabled": true
}
```

**Fields:**

- `is_recording` (boolean): Whether audio recording is currently active
- `model_loaded` (string|null): Currently loaded Whisper model variant
- `vad_enabled` (boolean): Whether Voice Activity Detection is enabled

---

### Start Recording

Start recording audio from the configured audio devices.

**Endpoint:** `POST /api/recording/start`

**Request Body:** None

**Response:**

```json
{
  "success": true
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "Already recording"
}
```

**Possible Errors:**

- `"Already recording"`: Recording is already in progress
- `"No microphone device available"`: No microphone found or configured
- Device-specific errors if audio initialization fails

**Notes:**

- Automatically detects and uses configured audio devices
- Starts waveform data streaming via WebSocket
- Recording continues until `POST /api/recording/stop` is called

---

### Stop Recording

Stop recording and process the captured audio.

**Endpoint:** `POST /api/recording/stop`

**Request Body:** None

**Response:**

```json
{
  "success": true
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "Not recording"
}
```

**Processing Flow:**

1. Stops audio capture
2. Applies VAD trimming (if enabled)
3. Transcribes audio using loaded Whisper model
4. Injects transcribed text into focused application
5. Sends transcription result via WebSocket

**WebSocket Events:**

- `transcription`: Sent when transcription completes
- `error`: Sent if transcription fails

---

### Get Configuration

Retrieve the current application configuration.

**Endpoint:** `GET /api/config`

**Response:**

```json
{
  "hotkey": {
    "modifiers": ["cmd", "shift"],
    "key": "space"
  },
  "model": "mlx-community/whisper-large-v3-turbo",
  "mode": "toggle",
  "vad_enabled": true,
  "cache_dir": "~/.cache/local_whisper",
  "audio": {
    "microphone_device": null,
    "system_audio_device": null,
    "mix_audio": true,
    "auto_detect_devices": true
  }
}
```

See [Configuration Reference](configuration.md) for detailed field descriptions.

---

### Update Configuration

Update application configuration. Only provided fields are updated.

**Endpoint:** `PUT /api/config`

**Request Body:**

```json
{
  "hotkey": {
    "modifiers": ["cmd", "shift"],
    "key": "space"
  },
  "mode": "toggle",
  "model": "mlx-community/whisper-large-v3-turbo",
  "vad_enabled": true,
  "audio": {
    "microphone_device": 0,
    "system_audio_device": 2,
    "mix_audio": true,
    "auto_detect_devices": false
  }
}
```

**Response:**

```json
{
  "success": true,
  "config": {
    // Full updated configuration
  }
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "Failed to save config"
}
```

**Notes:**

- Configuration is saved to `configs/config.json`
- Changes take effect immediately for most settings
- Hotkey changes may require app restart (in legacy CLI mode)

---

### List Models

Get information about available Whisper models and their download status.

**Endpoint:** `GET /api/models`

**Response:**

```json
{
  "success": true,
  "models": {
    "tiny": {
      "repo_id": "mlx-community/whisper-tiny",
      "downloaded": false,
      "path": null,
      "active": false
    },
    "base": {
      "repo_id": "mlx-community/whisper-base",
      "downloaded": true,
      "path": "/Users/username/.cache/local_whisper/mlx-community_whisper-base",
      "active": false
    },
    "large-turbo": {
      "repo_id": "mlx-community/whisper-large-v3-turbo",
      "downloaded": true,
      "path": "/Users/username/.cache/local_whisper/mlx-community_whisper-large-v3-turbo",
      "active": true
    }
  },
  "active_model": "mlx-community/whisper-large-v3-turbo"
}
```

**Fields:**

- `models` (object): Map of model variants to their information
  - `repo_id` (string): Hugging Face repository ID
  - `downloaded` (boolean): Whether model is downloaded locally
  - `path` (string|null): Local path to model files
  - `active` (boolean): Whether this model is currently loaded
- `active_model` (string): Full repository ID of currently active model

---

### Download Model

Download a Whisper model from Hugging Face Hub.

**Endpoint:** `POST /api/models/download`

**Request Body:**

```json
{
  "variant": "large-turbo"
}
```

**Response:**

```json
{
  "success": true,
  "variant": "large-turbo"
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "Download failed"
}
```

**WebSocket Events:**

- `model_download_progress`: Progress updates (0.0 to 1.0)

  ```json
  {
    "type": "model_download_progress",
    "variant": "large-turbo",
    "progress": 0.45
  }
  ```

**Notes:**

- Models are cached in `~/.cache/local_whisper`
- Download progress is streamed via WebSocket
- Large models (large, large-turbo) can be 3-5GB
- Download may take several minutes depending on connection speed

---

### Switch Model

Switch to a different Whisper model variant.

**Endpoint:** `POST /api/models/switch`

**Request Body:**

```json
{
  "variant": "base"
}
```

**Response:**

```json
{
  "success": true,
  "variant": "base"
}
```

**Error Response:**

```json
{
  "success": false,
  "error": "Failed to load model"
}
```

**Notes:**

- Model must be downloaded first (use `/api/models/download`)
- Configuration is automatically updated with new model
- Previous model remains in memory until garbage collected
- Switching models may take a few seconds

**Available Variants:**

- `tiny`: Fastest, least accurate (~39M parameters)
- `base`: Good balance (~74M parameters)
- `small`: Better accuracy (~244M parameters)
- `medium`: High accuracy (~769M parameters)
- `large`: Very high accuracy (~1550M parameters)
- `large-turbo`: Best accuracy, optimized for Apple Silicon (~1550M parameters)

## WebSocket API

### Connection

**Endpoint:** `ws://127.0.0.1:8000/ws`

**Protocol:** WebSocket (RFC 6455)

**Message Format:** JSON

### Message Types

#### Waveform Data

Real-time audio amplitude data for visualization.

**Type:** `waveform`

**Message:**

```json
{
  "type": "waveform",
  "data": [0.1, 0.15, 0.2, 0.18, 0.12, ...]
}
```

**Fields:**

- `data` (array of floats): Amplitude values (0.0 to 1.0)
- Sent at ~20 FPS during recording
- Used for oscilloscope-style waveform visualization

**When Sent:**

- Continuously while recording is active
- Stops when recording ends

---

#### Transcription Result

Completed transcription text.

**Type:** `transcription`

**Message:**

```json
{
  "type": "transcription",
  "text": "Hello, this is the transcribed text."
}
```

**Fields:**

- `text` (string): Transcribed text from audio

**When Sent:**

- After `POST /api/recording/stop` completes transcription
- Text is also automatically injected into focused application

---

#### Model Download Progress

Progress updates during model download.

**Type:** `model_download_progress`

**Message:**

```json
{
  "type": "model_download_progress",
  "variant": "large-turbo",
  "progress": 0.65
}
```

**Fields:**

- `variant` (string): Model variant being downloaded
- `progress` (float): Download progress from 0.0 to 1.0
  - `0.0`: Download started
  - `1.0`: Download complete
  - `-1.0`: Download failed

**When Sent:**

- During model download initiated via `POST /api/models/download`
- Progress updates are approximate (Hugging Face Hub doesn't provide exact progress)

---

#### Error Message

Error notifications.

**Type:** `error`

**Message:**

```json
{
  "type": "error",
  "message": "Transcription failed: Model not loaded"
}
```

**Fields:**

- `message` (string): Error description

**When Sent:**

- When errors occur during recording, transcription, or model operations

---

#### Pong Response

Echo response for connection testing.

**Type:** `pong`

**Message:**

```json
{
  "type": "pong",
  "data": "<original message>"
}
```

**When Sent:**

- In response to any client message (for connection testing)

## Error Handling

### HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request format
- `500 Internal Server Error`: Server error

### Error Response Format

All error responses follow this format:

```json
{
  "success": false,
  "error": "Error message description"
}
```

### Common Errors

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `"Already recording"` | Recording already in progress | Stop current recording first |
| `"Not recording"` | No active recording | Start recording first |
| `"No microphone device available"` | No microphone found | Check audio device configuration |
| `"Transcriber not initialized"` | Backend not fully started | Wait for backend initialization |
| `"Model not loaded"` | No model loaded | Download and load a model first |
| `"Failed to save config"` | File system error | Check file permissions |

## Rate Limiting

No rate limiting is implemented. The API is designed for single-user localhost access.

## CORS

CORS is enabled for all origins (`*`) to allow the SwiftUI app to connect. In production, this should be restricted to specific origins.

## Examples

### Complete Recording Workflow

```bash
# 1. Check status
curl http://127.0.0.1:8000/api/status

# 2. Start recording
curl -X POST http://127.0.0.1:8000/api/recording/start

# 3. (Recording happens, waveform data streams via WebSocket)

# 4. Stop recording
curl -X POST http://127.0.0.1:8000/api/recording/stop

# 5. Transcription result arrives via WebSocket
```

### Model Management

```bash
# 1. List available models
curl http://127.0.0.1:8000/api/models

# 2. Download a model
curl -X POST http://127.0.0.1:8000/api/models/download \
  -H "Content-Type: application/json" \
  -d '{"variant": "base"}'

# 3. Switch to downloaded model
curl -X POST http://127.0.0.1:8000/api/models/switch \
  -H "Content-Type: application/json" \
  -d '{"variant": "base"}'
```

### Configuration Update

```bash
# Update hotkey and mode
curl -X PUT http://127.0.0.1:8000/api/config \
  -H "Content-Type: application/json" \
  -d '{
    "hotkey": {
      "modifiers": ["cmd", "ctrl"],
      "key": "space"
    },
    "mode": "hold"
  }'
```
