"""Main application entry point for LocalFlow."""
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional

# Configure Tk library paths BEFORE importing Tkinter/CustomTkinter
# This fixes compatibility issues with newer macOS versions
def _configure_tk_library():
    """Configure Tk library paths to use Homebrew's Python-Tk if available.
    
    This fixes the NSInvalidArgumentException crash on newer macOS versions
    where the system's Tk library is incompatible.
    """
    # Common Homebrew paths for Python-Tk
    homebrew_prefixes = [
        "/opt/homebrew",  # Apple Silicon
        "/usr/local",     # Intel Mac
    ]
    
    for prefix in homebrew_prefixes:
        tk_lib = Path(prefix) / "lib" / "tk8.6"
        tcl_lib = Path(prefix) / "lib" / "tcl8.6"
        
        # Check if Homebrew Tk is available
        if tk_lib.exists() and tcl_lib.exists():
            os.environ["TK_LIBRARY"] = str(tk_lib)
            os.environ["TCL_LIBRARY"] = str(tcl_lib)
            # Log will be configured later, just set env vars for now
            return True
    
    # If Homebrew Tk not found, continue anyway
    # The error will be caught later with a helpful message
    return False

def _test_tkinter_compatibility():
    """Test if Tkinter can be safely initialized without crashing.
    
    Uses a subprocess to test, so if it crashes, it won't kill the main process.
    
    Returns:
        True if Tkinter is compatible, False otherwise
    """
    import subprocess
    
    # Test script that tries to create a Tkinter root window
    test_script = """
import sys
import os
try:
    import customtkinter as ctk
    root = ctk.CTk()
    root.withdraw()
    root.destroy()
    print("SUCCESS")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
"""
    
    try:
        # Run test in subprocess with timeout
        # Use the same environment variables (including TK_LIBRARY, TCL_LIBRARY)
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=5,
            env=os.environ.copy()
        )
        
        if result.returncode == 0 and "SUCCESS" in result.stdout:
            return True
        else:
            # Log the error for debugging
            if result.stderr:
                print(f"Tkinter compatibility test failed: {result.stderr}", file=sys.stderr)
            if result.stdout and "ERROR" in result.stdout:
                print(f"Tkinter compatibility test error: {result.stdout}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        # Subprocess timed out - likely crashed
        print("Tkinter compatibility test timed out (likely crashed)", file=sys.stderr)
        return False
    except (subprocess.SubprocessError, Exception) as e:
        # If subprocess crashes or times out, Tkinter is not compatible
        print(f"Tkinter compatibility test failed: {e}", file=sys.stderr)
        return False

# Configure Tk before any imports
_configure_tk_library()

# Test Tkinter compatibility before importing
# This prevents crashes in the main process
TKINTER_AVAILABLE = _test_tkinter_compatibility()

# Only import CustomTkinter if it's compatible
if TKINTER_AVAILABLE:
    import customtkinter as ctk
else:
    ctk = None  # Will be checked before use

import rumps
from pynput import keyboard

try:
    import Quartz
    from Foundation import NSDictionary
except ImportError:
    Quartz = None
    NSDictionary = None

import config
from engine.audio import AudioRecorder
from engine.injector import TextInjector
from engine.transcriber import WhisperTranscriber
from engine.vad import SileroVAD
from ui.overlay import RecordingOverlay
from ui.settings import ModelManagerWindow, PreferencesWindow

try:
    import sounddevice as sd
except ImportError:
    sd = None

# Configure logging with unbuffered output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
    force=True  # Force reconfiguration if already configured
)
# Ensure unbuffered output for immediate log visibility
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(line_buffering=True)
except (AttributeError, OSError):
    # Fallback: ensure stdout is flushed
    sys.stdout.flush()

logger = logging.getLogger(__name__)


class LocalFlowApp(rumps.App):
    """Main LocalFlow application with menubar integration."""
    
    def __init__(self):
        """Initialize LocalFlow application."""
        logger.info("=" * 60)
        logger.info("Initializing LocalFlow Application")
        logger.info("=" * 60)
        
        super(LocalFlowApp, self).__init__("LocalFlow", quit_button=None)
        
        # Load configuration
        logger.info("Step 1: Loading configuration")
        self.config = config.load_config()
        logger.info("Step 1: Configuration loaded successfully")
        
        # Initialize components
        logger.info("Step 2: Initializing audio recorder")
        self.audio_recorder = AudioRecorder()
        
        logger.info("Step 3: Initializing transcriber")
        self.transcriber = WhisperTranscriber(
            cache_dir=config.expand_cache_dir(self.config.get("cache_dir", "~/.cache/local_whisper"))
        )
        
        logger.info("Step 4: Initializing text injector")
        self.injector = TextInjector()
        
        self.vad: Optional[SileroVAD] = None
        
        # Initialize VAD if enabled
        if self.config.get("vad_enabled", True):
            logger.info("Step 5: Initializing VAD (Voice Activity Detection)")
            self.vad = SileroVAD()
            vad_success = self.vad.load_vad_model()
            if vad_success:
                logger.info("Step 5: VAD initialized successfully")
            else:
                logger.warning("Step 5: VAD initialization failed, continuing without VAD")
        else:
            logger.info("Step 5: VAD disabled in configuration")
        
        # Load default model
        logger.info("Step 6: Loading default Whisper model")
        model_name = self.config.get("model", "mlx-community/whisper-large-v3-turbo")
        # Extract variant from model name
        model_variant = self._extract_model_variant(model_name)
        if model_variant:
            model_success = self.transcriber.load_model(model_variant)
            if model_success:
                logger.info(f"Step 6: Default model '{model_variant}' loaded successfully")
            else:
                logger.error(f"Step 6: Failed to load default model '{model_variant}'")
        else:
            logger.warning(f"Step 6: Could not extract variant from model name '{model_name}'")
        
        # UI components
        logger.info("Step 7: Initializing UI components")
        self.overlay: Optional[RecordingOverlay] = None
        self.preferences_window: Optional[PreferencesWindow] = None
        self.model_manager_window: Optional[ModelManagerWindow] = None
        
        # State management
        self.is_recording = False
        self.hotkey_listener: Optional[keyboard.Listener] = None
        self.current_hotkey: Optional[dict] = None
        self._active_threads = []  # Track active threads for cleanup
        self._permission_checked = False  # Track if we've shown permission alert
        self._diagnostic_mode = False  # Track diagnostic mode for logging all key events
        
        # Setup menu
        logger.info("Step 8: Setting up menu")
        self._setup_menu()
        
        # Setup hotkey listener
        logger.info("Step 9: Setting up hotkey listener")
        self._setup_hotkey_listener()
        
        # Check permissions on startup
        logger.info("Step 11: Checking Accessibility permissions")
        self._check_startup_permissions()
        
        # Initialize CustomTkinter configuration (defer root window creation)
        logger.info("Step 10: Initializing UI framework")
        if not TKINTER_AVAILABLE:
            logger.warning("Step 10: Tkinter is not available (incompatible with macOS 26.1)")
            logger.warning("Step 10: UI windows will not be available")
            logger.warning("Step 10: To fix: brew install python-tk@3.12")
            self.root = False  # Mark as unavailable
            # Show alert after a delay
            threading.Timer(2.0, self._show_tkinter_unavailable_alert).start()
        else:
            try:
                logger.info("Step 10.1: Setting CustomTkinter appearance mode")
                if ctk:
                    ctk.set_appearance_mode("dark")
                    logger.info("Step 10.1: Appearance mode set successfully")
                    
                    # Defer root window creation until actually needed
                    # Creating it here conflicts with rumps' event loop on macOS
                    logger.info("Step 10.2: UI framework configured (root window will be created on demand)")
                    self.root = None  # Will be created lazily when first window is shown
                    logger.info("Step 10: UI framework initialized successfully")
                else:
                    logger.warning("Step 10: CustomTkinter not available")
                    self.root = False
            except Exception as e:
                logger.error(f"Step 10: Failed to initialize UI framework: {e}", exc_info=True)
                logger.error("Step 10: Application will continue but UI windows may not work properly")
                self.root = False
        
        logger.info("=" * 60)
        logger.info("LocalFlow started successfully. Check the menu bar for options.")
        logger.info("=" * 60)
        sys.stdout.flush()  # Ensure logs are flushed
    
    def _ensure_ctk_root(self):
        """Ensure CustomTkinter root window exists (lazy initialization).
        
        This is called when a window needs to be shown, avoiding conflicts
        with rumps' event loop during startup.
        
        Raises:
            RuntimeError: If Tkinter initialization fails due to macOS compatibility issues
        """
        # Check if Tkinter is available at all
        if not TKINTER_AVAILABLE or ctk is None:
            raise RuntimeError(
                "Tkinter is not compatible with macOS 26.1. "
                "Please install Homebrew Python-Tk: brew install python-tk@3.12"
            )
        
        # If root is False, it means initialization previously failed
        if self.root is False:
            raise RuntimeError("Tkinter initialization previously failed due to macOS compatibility issue")
        
        if self.root is None:
            try:
                logger.info("Creating CustomTkinter root window (lazy initialization)")
                # Create root window in a way that doesn't interfere with rumps
                # Use update_idletasks to initialize without blocking
                self.root = ctk.CTk()
                self.root.withdraw()  # Hide root window immediately
                self.root.update_idletasks()  # Process any pending events
                logger.info("CustomTkinter root window created successfully")
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                
                # Check for macOS Tkinter compatibility issues
                is_macos_tk_error = (
                    "NSInvalidArgumentException" in error_msg or
                    "macOSVersion" in error_msg or
                    "unrecognized selector" in error_msg.lower() or
                    error_type == "TclError"
                )
                
                logger.error(f"Failed to create CustomTkinter root window: {e}", exc_info=True)
                
                if is_macos_tk_error:
                    error_message = (
                        "Tkinter is not compatible with your macOS version.\n\n"
                        "This is a known issue with the system's Tk library.\n\n"
                        "To fix this, install Python-Tk via Homebrew:\n"
                        "  brew install python-tk@3.12\n\n"
                        "Then restart the application.\n\n"
                        "The app will continue running, but UI windows won't be available."
                    )
                    logger.error("Tkinter compatibility error detected")
                    logger.error("Solution: Install Homebrew Python-Tk: brew install python-tk@3.12")
                    
                    # Show user-friendly error using rumps (doesn't require Tkinter)
                    try:
                        rumps.alert(
                            title="UI Not Available",
                            message=error_message,
                            ok="OK"
                        )
                    except Exception:
                        # If rumps.alert also fails, just log it
                        logger.error("Could not show error dialog")
                    
                    # Set root to a sentinel value to prevent repeated attempts
                    self.root = False  # Use False instead of None to indicate failure
                    raise RuntimeError("Tkinter initialization failed due to macOS compatibility issue")
                else:
                    logger.error("This may be due to a conflict with rumps' event loop or another issue")
                    self.root = False  # Mark as failed
                    raise
    
    def _extract_model_variant(self, model_name: str) -> Optional[str]:
        """Extract model variant from full model name.
        
        Args:
            model_name: Full model name like "mlx-community/whisper-large-v3-turbo"
            
        Returns:
            Variant name like "large-turbo" or None
        """
        model_lower = model_name.lower()
        
        if "large-v3-turbo" in model_lower or "large-turbo" in model_lower:
            return "large-turbo"
        elif "large-v3" in model_lower or "large" in model_lower:
            return "large"
        elif "medium" in model_lower:
            return "medium"
        elif "small" in model_lower:
            return "small"
        elif "base" in model_lower:
            return "base"
        elif "tiny" in model_lower:
            return "tiny"
        
        return None
    
    def _setup_menu(self):
        """Setup menubar menu."""
        self.menu = [
            rumps.MenuItem("Start Recording", callback=self.menu_start_recording),
            None,  # Separator
            rumps.MenuItem("Test Hotkey", callback=self.test_hotkey),
            rumps.MenuItem("Toggle Diagnostic Mode", callback=self.toggle_diagnostic_mode),
            None,  # Separator
            rumps.MenuItem("Preferences", callback=self.show_preferences),
            rumps.MenuItem("Model Manager", callback=self.show_model_manager),
            None,  # Separator
            rumps.MenuItem("Check Permissions", callback=self.check_permissions),
            rumps.MenuItem("About", callback=self.show_about),
            rumps.MenuItem("Quit", callback=self.quit_app)
        ]
    
    def _setup_hotkey_listener(self):
        """Setup global hotkey listener."""
        hotkey_config = self.config.get("hotkey")
        if not hotkey_config:
            logger.info("No hotkey configured, skipping hotkey listener setup")
            return
        
        self.current_hotkey = hotkey_config
        try:
            self._register_hotkey()
        except Exception as e:
            logger.error(f"Failed to setup hotkey listener: {e}", exc_info=True)
            # Check if it's a permission issue
            if not self._check_accessibility_permissions():
                logger.warning("Hotkey listener failed - Accessibility permissions may be missing")
                # Show alert in a thread-safe way
                threading.Timer(1.0, self._show_permission_alert).start()
            else:
                rumps.alert(
                    title="Hotkey Setup Failed",
                    message=f"Failed to setup hotkey listener: {e}\n\n"
                           "The app will continue to run, but hotkeys won't work.\n"
                           "You can still use 'Start Recording' from the menu.",
                    ok="OK"
                )
    
    def _register_hotkey(self):
        """Register global hotkey."""
        if not self.current_hotkey:
            return
        
        # Stop existing listener
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except Exception:
                pass
        
        modifiers = self.current_hotkey.get("modifiers", [])
        key_name = self.current_hotkey.get("key", "").lower()
        
        logger.info(f"Registering hotkey - modifiers: {modifiers}, key: {key_name}")
        
        # Map modifier names to keyboard.Key objects
        modifier_keys = []
        for mod in modifiers:
            if mod == "cmd":
                modifier_keys.append(keyboard.Key.cmd)
            elif mod == "ctrl":
                modifier_keys.append(keyboard.Key.ctrl)
            elif mod == "alt":
                modifier_keys.append(keyboard.Key.alt)
            elif mod == "shift":
                modifier_keys.append(keyboard.Key.shift)
        
        # Map main key name to keyboard.Key object
        if key_name == "space":
            main_key = keyboard.Key.space
        elif hasattr(keyboard.Key, key_name):
            main_key = getattr(keyboard.Key, key_name)
        else:
            # Try to use as character key
            main_key = key_name
        
        logger.info(f"Hotkey combination: {modifiers} + {key_name}")
        
        # Track pressed keys for hotkey detection
        pressed_keys = set()
        last_trigger_time = 0.0
        debounce_interval = 0.2  # 200ms debounce
        
        def check_hotkey_combination():
            """Check if the hotkey combination is currently pressed."""
            # Check if main key is pressed
            main_key_pressed = False
            if isinstance(main_key, keyboard.Key):
                main_key_pressed = main_key in pressed_keys
            else:
                # For character keys, check if any pressed key matches
                for key in pressed_keys:
                    if hasattr(key, 'char') and key.char == main_key:
                        main_key_pressed = True
                        break
            
            if not main_key_pressed:
                return False
            
            # Check if all modifiers are pressed
            for mod_key in modifier_keys:
                if mod_key not in pressed_keys:
                    return False
            
            return True
        
        def on_press(key):
            nonlocal last_trigger_time
            try:
                key_str = str(key)
                if self._diagnostic_mode:
                    logger.debug(f"[DIAGNOSTIC] Key pressed: {key_str}")
                
                pressed_keys.add(key)
                
                # Check if hotkey combination is triggered
                if check_hotkey_combination():
                    current_time = time.time()
                    # Debounce: only trigger if enough time has passed since last trigger
                    if current_time - last_trigger_time >= debounce_interval:
                        logger.info("=" * 60)
                        logger.info("HOTKEY COMBINATION DETECTED - Triggering callback!")
                        logger.info("=" * 60)
                        last_trigger_time = current_time
                        # Trigger in a separate thread to avoid blocking key events
                        threading.Thread(target=self._on_hotkey_triggered, daemon=True).start()
                    else:
                        logger.debug(f"Hotkey combination detected but debounced (last trigger: {current_time - last_trigger_time:.3f}s ago)")
            except Exception as e:
                logger.error(f"Error in hotkey press handler for key {key}: {e}", exc_info=True)
        
        def on_release(key):
            try:
                key_str = str(key)
                if self._diagnostic_mode:
                    logger.debug(f"[DIAGNOSTIC] Key released: {key_str}")
                
                pressed_keys.discard(key)
                
                # For hold mode, check if main key is released
                mode = self.config.get("mode", "toggle")
                if mode == "hold" and self.is_recording:
                    # Check if the main key is released
                    if isinstance(main_key, keyboard.Key):
                        if key == main_key:
                            logger.info("Main key released in hold mode, stopping recording")
                            self._stop_recording()
                    else:
                        # For character keys
                        if hasattr(key, 'char') and key.char == main_key:
                            logger.info("Main key released in hold mode, stopping recording")
                            self._stop_recording()
            except Exception as e:
                logger.error(f"Error in hotkey release handler for key {key}: {e}", exc_info=True)
        
        try:
            logger.info("Creating keyboard.Listener...")
            self.hotkey_listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            logger.info("Starting hotkey listener...")
            self.hotkey_listener.start()
            logger.info(f"Hotkey listener started successfully")
            logger.info(f"Registered hotkey: {self._format_hotkey_for_log(self.current_hotkey)}")
            logger.info("Hotkey listener is now active and monitoring for key events")
            
            # Verify listener is running
            if self.hotkey_listener.running:
                logger.info("Hotkey listener confirmed running (listener.running = True)")
            else:
                logger.warning("Hotkey listener started but 'running' flag is False - this may indicate a problem")
        except Exception as e:
            logger.error(f"Failed to start hotkey listener: {e}", exc_info=True)
            # Check if it's a permission issue
            error_str = str(e).lower()
            if "not trusted" in error_str or "accessibility" in error_str or "permission" in error_str:
                logger.error("Accessibility permissions are required for hotkey monitoring")
                raise PermissionError("Accessibility permissions required for hotkey monitoring")
            raise
    
    def _format_hotkey_for_log(self, hotkey_config: dict) -> str:
        """Format hotkey config for logging."""
        if not hotkey_config:
            return "None"
        modifiers = hotkey_config.get("modifiers", [])
        key = hotkey_config.get("key", "")
        return f"{'+'.join(modifiers)}+{key}" if modifiers else key
    
    def _on_hotkey_triggered(self):
        """Handle hotkey trigger."""
        logger.info("=" * 60)
        logger.info("HOTKEY TRIGGERED - Handler called successfully!")
        logger.info("=" * 60)
        mode = self.config.get("mode", "toggle")
        logger.info(f"Current mode: {mode}, is_recording: {self.is_recording}")
        
        if mode == "toggle":
            if self.is_recording:
                logger.info("Toggle mode: Stopping recording")
                self._stop_recording()
            else:
                logger.info("Toggle mode: Starting recording")
                self._start_recording()
        else:  # hold mode
            if not self.is_recording:
                logger.info("Hold mode: Starting recording")
                self._start_recording()
            else:
                logger.info("Hold mode: Already recording, ignoring trigger")
    
    def _detect_audio_devices(self):
        """Detect and return microphone and system audio device indices.
        
        Returns:
            Tuple of (microphone_device, system_audio_device) indices, or None if not found
        """
        audio_config = self.config.get("audio", {})
        auto_detect = audio_config.get("auto_detect_devices", True)
        
        # Get configured devices
        mic_device = audio_config.get("microphone_device")
        system_device = audio_config.get("system_audio_device")
        
        # Auto-detect if enabled and devices not configured
        if auto_detect:
            if mic_device is None:
                mic_device = self.audio_recorder.get_default_input_device()
                if mic_device is not None:
                    try:
                        mic_info = sd.query_devices(mic_device)
                        logger.info(f"Auto-detected microphone: {mic_info['name']} (index {mic_device})")
                    except Exception:
                        mic_device = None
            
            if system_device is None:
                system_device = self.audio_recorder.find_blackhole_device()
                if system_device is not None:
                    try:
                        system_info = sd.query_devices(system_device)
                        logger.info(f"Auto-detected system audio device: {system_info['name']} (index {system_device})")
                    except Exception:
                        system_device = None
                else:
                    logger.info("No BlackHole device found for system audio capture")
                    logger.info("To capture system audio, install BlackHole from: https://github.com/ExistentialAudio/BlackHole")
        
        return mic_device, system_device
    
    def _start_recording(self):
        """Start recording audio."""
        if self.is_recording:
            logger.warning("Recording already in progress, ignoring start request")
            return
        
        logger.info("=" * 60)
        logger.info("=== STARTING RECORDING ===")
        logger.info("=" * 60)
        self.is_recording = True
        
        # UI overlay code commented out - backend not working yet
        # # Ensure CustomTkinter root exists before showing overlay
        # try:
        #     self._ensure_ctk_root()
        # except Exception as e:
        #     logger.error(f"Failed to initialize UI for recording overlay: {e}", exc_info=True)
        #     logger.error("Recording will continue but overlay will not be shown")
        #     # Continue without overlay
        #     self.audio_recorder.start_recording()
        #     logger.info("Recording started without overlay")
        #     return
        # 
        # # Show overlay
        # logger.debug("Showing recording overlay")
        # self.overlay = RecordingOverlay(
        #     waveform_callback=self.audio_recorder.get_waveform_data
        # )
        # self.overlay.show(
        #     cancel_callback=self._cancel_recording,
        #     stop_callback=self._stop_recording
        # )
        
        # Detect audio devices
        try:
            mic_device, system_device = self._detect_audio_devices()
            
            if mic_device is None:
                error_msg = (
                    "No microphone device available.\n\n"
                    "Please check your audio settings and ensure a microphone is connected."
                )
                logger.error(error_msg)
                rumps.alert(
                    title="No Microphone Found",
                    message=error_msg,
                    ok="OK"
                )
                self.is_recording = False
                return
            
            # Get audio configuration
            audio_config = self.config.get("audio", {})
            mix_audio = audio_config.get("mix_audio", True)
            
            # Start audio recording
            logger.debug("Starting audio recorder")
            try:
                self.audio_recorder.start_recording(
                    microphone_device=mic_device,
                    system_audio_device=system_device,
                    mix_audio=mix_audio
                )
                logger.info("Recording started successfully")
            except RuntimeError as e:
                error_msg = str(e)
                logger.error(f"Failed to start recording: {error_msg}")
                
                # Provide helpful error messages
                if "microphone" in error_msg.lower() or "device" in error_msg.lower():
                    user_msg = (
                        f"Failed to start audio recording:\n{error_msg}\n\n"
                        "Please check:\n"
                        "• Microphone is connected and working\n"
                        "• Microphone permissions are granted\n"
                        "• Audio device settings in Preferences"
                    )
                elif system_device is not None and "system" in error_msg.lower():
                    user_msg = (
                        f"Failed to start system audio recording:\n{error_msg}\n\n"
                        "To capture system audio:\n"
                        "1. Install BlackHole from: https://github.com/ExistentialAudio/BlackHole\n"
                        "2. Configure BlackHole in Audio MIDI Setup\n"
                        "3. Or disable system audio capture in Preferences"
                    )
                else:
                    user_msg = f"Failed to start recording: {error_msg}"
                
                rumps.alert(
                    title="Recording Error",
                    message=user_msg,
                    ok="OK"
                )
                self.is_recording = False
        except Exception as e:
            logger.error(f"Unexpected error starting recording: {e}", exc_info=True)
            rumps.alert(
                title="Recording Error",
                message=f"An unexpected error occurred: {e}",
                ok="OK"
            )
            self.is_recording = False
    
    def _stop_recording(self):
        """Stop recording and process audio."""
        if not self.is_recording:
            logger.warning("Not recording, nothing to stop")
            return
        
        logger.info("Stopping recording session")
        self.is_recording = False
        
        # UI overlay code commented out - backend not working yet
        # # Update overlay status
        # if self.overlay:
        #     self.overlay.update_status("Processing...")
        
        # Stop audio recording
        logger.debug("Stopping audio recorder")
        audio_data = self.audio_recorder.stop_recording()
        
        if len(audio_data) == 0:
            logger.warning("No audio recorded, nothing to process")
            # UI overlay code commented out - backend not working yet
            # if self.overlay:
            #     self.overlay.hide()
            return
        
        audio_duration = len(audio_data) / self.audio_recorder.SAMPLE_RATE
        logger.info("=" * 60)
        logger.info("=== RECORDING FINISHED ===")
        logger.info(f"Audio captured: {len(audio_data)} samples ({audio_duration:.2f} seconds)")
        logger.info("=" * 60)
        
        # Trim silence using VAD if available
        audio_to_transcribe = audio_data
        if self.vad and self.vad.session is not None:
            try:
                logger.info("Using VAD to trim silence from audio")
                start_idx, end_idx = self.vad.find_speech_boundaries(audio_data, padding_ms=100)
                if start_idx < end_idx:
                    audio_to_transcribe = audio_data[start_idx:end_idx]
                    trimmed_duration = len(audio_to_transcribe) / self.audio_recorder.SAMPLE_RATE
                    logger.info(f"VAD trimming: {len(audio_data)} -> {len(audio_to_transcribe)} samples "
                              f"({audio_duration:.2f}s -> {trimmed_duration:.2f}s)")
                else:
                    logger.warning("VAD returned invalid boundaries, using full audio")
            except Exception as e:
                logger.warning(f"VAD trimming failed: {e}, using full audio", exc_info=True)
        else:
            logger.info("VAD not available, transcribing full audio")
        
        logger.info(f"Starting transcription...")
        
        # Process audio in background thread
        def process_audio():
            try:
                logger.info("Processing audio in background thread")
                # Transcribe audio
                def on_transcription_complete(text: str):
                    logger.info("=" * 60)
                    logger.info("=== TRANSCRIPTION RESULT ===")
                    if text:
                        logger.info(f"Transcribed text: {text}")
                        logger.info(f"Text length: {len(text)} characters")
                    else:
                        logger.warning("No transcription result (empty text)")
                    logger.info("=" * 60)
                    
                    # Text injection commented out - focus on detection quality testing
                    # logger.info("Step 4: Attempting to inject text")
                    # success = self.injector.inject_text(text)
                    # if success:
                    #     logger.info(f"Step 5: Text injection successful: '{text[:50]}...'")
                    # else:
                    #     logger.error("Step 5: Text injection failed")
                    
                    # UI overlay code commented out - backend not working yet
                    # # Hide overlay
                    # if self.overlay:
                    #     self.overlay.hide()
                    logger.info("Recording session completed")
                
                logger.info("Starting async transcription")
                self.transcriber.transcribe_async(audio_to_transcribe, on_transcription_complete)
                
            except Exception as e:
                logger.error(f"Error processing audio: {e}", exc_info=True)
                # UI overlay code commented out - backend not working yet
                # if self.overlay:
                #     self.overlay.hide()
        
        process_thread = threading.Thread(target=process_audio, daemon=True)
        process_thread.start()
        self._active_threads.append(process_thread)
        logger.debug("Audio processing thread started")
    
    def _cancel_recording(self):
        """Cancel recording."""
        if not self.is_recording:
            logger.warning("Not recording, nothing to cancel")
            return
        
        logger.info("Cancelling recording session")
        self.is_recording = False
        self.audio_recorder.stop_recording()
        
        # UI overlay code commented out - backend not working yet
        # if self.overlay:
        #     self.overlay.hide()
        
        logger.info("Recording cancelled successfully")
    
    def show_preferences(self, _=None):
        """Show preferences window."""
        try:
            self._ensure_ctk_root()
        except Exception as e:
            logger.error(f"Failed to initialize UI for preferences window: {e}", exc_info=True)
            rumps.alert(
                title="Error",
                message="Failed to open preferences window. Please check logs for details.",
                ok="OK"
            )
            return
        
        def on_save(updated_config):
            self.config = updated_config
            self._setup_hotkey_listener()
        
        self.preferences_window = PreferencesWindow(on_save=on_save)
        self.preferences_window.show()
    
    def show_model_manager(self, _=None):
        """Show model manager window."""
        try:
            self._ensure_ctk_root()
        except Exception as e:
            logger.error(f"Failed to initialize UI for model manager window: {e}", exc_info=True)
            rumps.alert(
                title="Error",
                message="Failed to open model manager window. Please check logs for details.",
                ok="OK"
            )
            return
        
        def on_model_switch(variant):
            self.config = config.load_config()
            print(f"Model switched to {variant}")
        
        self.model_manager_window = ModelManagerWindow(
            transcriber=self.transcriber,
            on_model_switch=on_model_switch
        )
        self.model_manager_window.show()
    
    def _check_accessibility_permissions(self) -> bool:
        """Check if Accessibility permissions are granted for keyboard monitoring.
        
        Returns:
            True if permissions granted, False otherwise
        """
        if not Quartz:
            logger.warning("Quartz framework not available - cannot check Accessibility permissions")
            return False
        
        try:
            import os
            current_pid = os.getpid()
            
            # Try to get process name if psutil is available
            try:
                import psutil
                current_process = psutil.Process(current_pid)
                process_name = current_process.name()
                logger.info(f"Checking Accessibility permissions for process: {process_name} (PID: {current_pid})")
            except ImportError:
                logger.info(f"Checking Accessibility permissions for current process (PID: {current_pid})")
            except Exception:
                logger.info(f"Checking Accessibility permissions for current process (PID: {current_pid})")
            
            trusted = False
            try:
                # Try with prompt option first
                prompt_key = Quartz.kAXTrustedCheckOptionPrompt
                options = NSDictionary.dictionaryWithObject_forKey_(True, prompt_key)
                trusted = Quartz.AXIsProcessTrustedWithOptions(options)
                logger.info(f"Permission check result (with prompt): {trusted}")
            except (AttributeError, KeyError) as e:
                logger.debug(f"kAXTrustedCheckOptionPrompt not available: {e}")
                # Fallback to None
                try:
                    trusted = Quartz.AXIsProcessTrustedWithOptions(None)
                    logger.info(f"Permission check result (without prompt): {trusted}")
                except Exception as e2:
                    logger.warning(f"Cannot check permissions programmatically: {e2}")
                    logger.info("Will assume permissions are OK and fail gracefully if not")
                    return True  # Assume OK, will fail gracefully
            
            if trusted:
                logger.info("✓ Accessibility permissions are granted")
            else:
                logger.warning("✗ Accessibility permissions are NOT granted")
                logger.warning("The Python process needs Accessibility permissions, not just Cursor.app")
                logger.warning("Please enable permissions for: Python, python3, or the terminal app you're using")
            
            return trusted
        except ImportError:
            logger.warning("psutil not available - cannot show process name in permission check")
            # Continue with basic check
            try:
                trusted = Quartz.AXIsProcessTrustedWithOptions(None)
                logger.info(f"Permission check result: {trusted}")
                return trusted
            except Exception as e:
                logger.warning(f"Error checking Accessibility permissions: {e}")
                return False
        except Exception as e:
            logger.warning(f"Error checking Accessibility permissions: {e}")
            return False
    
    def _check_startup_permissions(self):
        """Check permissions on startup and show alert if needed."""
        if self._permission_checked:
            return
        
        # Check both text injection and keyboard monitoring permissions
        has_permissions = self._check_accessibility_permissions()
        
        if not has_permissions:
            # Show alert after a short delay to avoid blocking startup
            threading.Timer(2.0, self._show_permission_alert).start()
        
        self._permission_checked = True
    
    def _show_permission_alert(self):
        """Show alert about missing Accessibility permissions."""
        rumps.alert(
            title="Accessibility Permissions Required",
            message="LocalFlow needs Accessibility permissions to work properly.\n\n"
                   "This allows:\n"
                   "• Global hotkey monitoring (Cmd+Shift+Space)\n"
                   "• Text injection into applications\n\n"
                   "To grant permissions:\n"
                   "1. Open System Settings\n"
                   "2. Go to Privacy & Security > Accessibility\n"
                   "3. Enable LocalFlow\n"
                   "4. Restart the application\n\n"
                   "You can still use 'Start Recording' from the menu without permissions.",
            ok="OK"
        )
    
    def _show_tkinter_unavailable_alert(self):
        """Show alert about Tkinter being unavailable."""
        rumps.alert(
            title="UI Not Available",
            message="Tkinter is not compatible with macOS 26.1.\n\n"
                   "This means UI windows (Preferences, Model Manager, Recording Overlay) "
                   "will not be available.\n\n"
                   "To fix this:\n"
                   "1. Install Homebrew Python-Tk:\n"
                   "   brew install python-tk@3.12\n"
                   "2. Restart the application\n\n"
                   "The app will continue running, but you'll need to use the menu bar "
                   "for all functions.",
            ok="OK"
        )
    
    def check_permissions(self, _=None):
        """Check and display permission status."""
        has_permissions = self._check_accessibility_permissions()
        
        if has_permissions:
            # Also check listener status
            listener_status = "running" if (self.hotkey_listener and self.hotkey_listener.running) else "not running"
            rumps.alert(
                title="Permissions Status",
                message="✓ Accessibility permissions are granted.\n\n"
                       f"Hotkey listener status: {listener_status}\n\n"
                       "Hotkey monitoring and text injection should work properly.",
                ok="OK"
            )
        else:
            self._show_permission_alert()
    
    def test_hotkey(self, _=None):
        """Manually test the hotkey handler."""
        logger.info("=" * 60)
        logger.info("MANUAL HOTKEY TEST - Triggering handler directly")
        logger.info("=" * 60)
        self._on_hotkey_triggered()
        rumps.notification(
            title="Hotkey Test",
            message="Hotkey handler was triggered manually",
            subtitle="Check logs to verify it worked"
        )
    
    def toggle_diagnostic_mode(self, sender=None):
        """Toggle diagnostic mode for logging all key events."""
        self._diagnostic_mode = not self._diagnostic_mode
        status = "enabled" if self._diagnostic_mode else "disabled"
        logger.info(f"Diagnostic mode {status} - all key events will be logged")
        
        rumps.notification(
            title="Diagnostic Mode",
            message=f"Diagnostic mode {status}",
            subtitle="All key events will now be logged" if self._diagnostic_mode else "Only hotkey-related events will be logged"
        )
    
    def menu_start_recording(self, _=None):
        """Start recording from menu item."""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()
    
    def show_about(self, _=None):
        """Show about dialog."""
        rumps.alert(
            title="About LocalFlow",
            message="LocalFlow - AI Dictation for macOS\n\n"
                   "A local-first dictation application using MLX-Whisper.\n"
                   "Optimized for Apple Silicon (M4 Pro).",
            ok="Close"
        )
    
    def quit_app(self, _=None):
        """Quit application."""
        logger.info("=" * 60)
        logger.info("Shutting down LocalFlow application")
        logger.info("=" * 60)
        
        # Stop hotkey listener
        logger.info("Step 1: Stopping hotkey listener")
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
                logger.info("Step 1: Hotkey listener stopped")
            except Exception as e:
                logger.error(f"Step 1: Error stopping hotkey listener: {e}", exc_info=True)
        
        # Stop recording if active
        if self.is_recording:
            logger.info("Step 2: Stopping active recording")
            self._cancel_recording()
        
        # Wait for active threads to complete (with timeout)
        logger.info("Step 3: Waiting for active threads to complete")
        for thread in self._active_threads:
            if thread.is_alive():
                logger.debug(f"Waiting for thread {thread.name} to complete")
                thread.join(timeout=2.0)
                if thread.is_alive():
                    logger.warning(f"Thread {thread.name} did not complete within timeout")
        
        # Clean up audio resources
        logger.info("Step 4: Cleaning up audio resources")
        if self.audio_recorder and self.audio_recorder.is_recording:
            try:
                self.audio_recorder.stop_recording()
                logger.info("Step 4: Audio resources cleaned up")
            except Exception as e:
                logger.error(f"Step 4: Error cleaning up audio resources: {e}", exc_info=True)
        
        # Clean up UI resources
        logger.info("Step 5: Cleaning up UI resources")
        if self.overlay:
            try:
                self.overlay.hide()
            except Exception:
                pass
        
        logger.info("Step 6: Application shutdown complete")
        logger.info("=" * 60)
        
        # Quit
        rumps.quit_application()


def main():
    """Main entry point."""
    try:
        logger.info("Starting LocalFlow application")
        sys.stdout.flush()
        
        logger.info("Creating LocalFlowApp instance...")
        app = LocalFlowApp()
        logger.info("LocalFlowApp instance created successfully")
        sys.stdout.flush()
        
        logger.info("Starting rumps application event loop...")
        sys.stdout.flush()
        app.run()
        logger.info("Rumps application event loop exited")
        sys.stdout.flush()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.stdout.flush()
    except Exception as e:
        logger.critical(f"Fatal error in application: {e}", exc_info=True)
        sys.stdout.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
