"""Configuration management for LocalFlow."""
import json
import os
from pathlib import Path
from typing import Any, Dict


def get_config_path() -> Path:
    """Return the path to the config.json file."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    return script_dir / "config.json"


def load_config() -> Dict[str, Any]:
    """Load configuration from config.json."""
    config_path = get_config_path()
    
    if not config_path.exists():
        # Return default config if file doesn't exist
        return {
            "hotkey": None,
            "model": "mlx-community/whisper-large-v3-turbo",
            "mode": "toggle",
            "cache_dir": "~/.cache/local_whisper",
            "vad_enabled": True
        }
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except (json.JSONDecodeError, IOError) as e:
        # If there's an error reading, return default config
        print(f"Error loading config: {e}. Using defaults.")
        return {
            "hotkey": None,
            "model": "mlx-community/whisper-large-v3-turbo",
            "mode": "toggle",
            "cache_dir": "~/.cache/local_whisper",
            "vad_enabled": True
        }


def save_config(config: Dict[str, Any]) -> bool:
    """Save configuration to config.json."""
    config_path = get_config_path()
    
    try:
        # Ensure directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write config with pretty formatting
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error saving config: {e}")
        return False


def expand_cache_dir(cache_dir: str) -> str:
    """Expand ~ in cache directory path."""
    return os.path.expanduser(cache_dir)

