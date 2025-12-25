"""Settings windows for Preferences and Model Manager."""
import threading
from typing import Callable, Optional

import customtkinter as ctk

import config


class PreferencesWindow:
    """Preferences window with hotkey recorder."""
    
    def __init__(self, on_save: Optional[Callable[[dict], None]] = None):
        """Initialize preferences window.
        
        Args:
            on_save: Callback when preferences are saved
        """
        self.on_save = on_save
        self.window: Optional[ctk.CTkToplevel] = None
        self.hotkey_label: Optional[ctk.CTkLabel] = None
        self.recording_hotkey = False
        self.captured_hotkey: Optional[dict] = None
        self.mode_var: Optional[ctk.StringVar] = None
        
        # Setup CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def show(self):
        """Show preferences window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return
        
        try:
            self.window = ctk.CTkToplevel()
            self.window.title("LocalFlow Preferences")
            self.window.geometry("500x400")
            
            # Load current config
            current_config = config.load_config()
            
            # Main frame
            main_frame = ctk.CTkFrame(self.window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            title_label = ctk.CTkLabel(
                main_frame,
                text="Preferences",
                font=ctk.CTkFont(size=24, weight="bold")
            )
            title_label.pack(pady=(20, 30))
            
            # Hotkey section
            hotkey_frame = ctk.CTkFrame(main_frame)
            hotkey_frame.pack(fill="x", padx=20, pady=10)
            
            hotkey_title = ctk.CTkLabel(
                hotkey_frame,
                text="Global Hotkey",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            hotkey_title.pack(pady=(15, 10))
            
            # Current hotkey display
            current_hotkey = current_config.get("hotkey")
            hotkey_text = self._format_hotkey(current_hotkey) if current_hotkey else "Not set"
            
            self.hotkey_label = ctk.CTkLabel(
                hotkey_frame,
                text=f"Current: {hotkey_text}",
                font=ctk.CTkFont(size=14)
            )
            self.hotkey_label.pack(pady=5)
            
            # Record hotkey button
            record_btn = ctk.CTkButton(
                hotkey_frame,
                text="Listen for Shortcut" if not self.recording_hotkey else "Press keys now...",
                command=self._start_recording_hotkey,
                width=200
            )
            record_btn.pack(pady=10)
            
            # Mode selection
            mode_frame = ctk.CTkFrame(main_frame)
            mode_frame.pack(fill="x", padx=20, pady=10)
            
            mode_title = ctk.CTkLabel(
                mode_frame,
                text="Recording Mode",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            mode_title.pack(pady=(15, 10))
            
            self.mode_var = ctk.StringVar(value=current_config.get("mode", "toggle"))
            
            toggle_radio = ctk.CTkRadioButton(
                mode_frame,
                text="Toggle (Press to start/stop)",
                variable=self.mode_var,
                value="toggle"
            )
            toggle_radio.pack(pady=5)
            
            hold_radio = ctk.CTkRadioButton(
                mode_frame,
                text="Hold-to-Talk (Hold while speaking)",
                variable=self.mode_var,
                value="hold"
            )
            hold_radio.pack(pady=5)
            
            # Save button
            save_btn = ctk.CTkButton(
                main_frame,
                text="Save Preferences",
                command=self._save_preferences,
                width=200,
                fg_color="#388e3c",
                hover_color="#2e7d32"
            )
            save_btn.pack(pady=20)
        except Exception as e:
            # If Tkinter fails, re-raise to be handled by caller
            error_msg = str(e)
            is_tk_error = (
                "NSInvalidArgumentException" in error_msg or
                "macOSVersion" in error_msg or
                "unrecognized selector" in error_msg.lower() or
                "TclError" in str(type(e).__name__)
            )
            
            if is_tk_error:
                raise RuntimeError(
                    "Preferences window cannot be shown due to Tkinter compatibility issue. "
                    "Please install Homebrew Python-Tk: brew install python-tk@3.12"
                ) from e
            else:
                raise
    
    def _format_hotkey(self, hotkey: dict) -> str:
        """Format hotkey dict to readable string.
        
        Args:
            hotkey: Hotkey dictionary with modifiers and key
            
        Returns:
            Formatted string like "Cmd+Shift+Space"
        """
        if not hotkey:
            return "Not set"
        
        modifiers = hotkey.get("modifiers", [])
        key = hotkey.get("key", "")
        
        mod_names = {
            "cmd": "Cmd",
            "ctrl": "Ctrl",
            "alt": "Opt",
            "shift": "Shift"
        }
        
        mod_str = "+".join([mod_names.get(m, m.title()) for m in modifiers])
        key_str = key.title() if key else ""
        
        if mod_str and key_str:
            return f"{mod_str}+{key_str}"
        elif key_str:
            return key_str
        else:
            return "Not set"
    
    def _start_recording_hotkey(self):
        """Start recording hotkey."""
        if self.recording_hotkey:
            return
        
        self.recording_hotkey = True
        self.captured_hotkey = None
        
        if self.hotkey_label:
            self.hotkey_label.configure(text="Press your hotkey combination now...")
        
        # Start listening for keys in background thread
        threading.Thread(target=self._capture_hotkey, daemon=True).start()
    
    def _capture_hotkey(self):
        """Capture hotkey combination."""
        from pynput import keyboard
        
        modifiers = set()
        key_pressed = None
        listener_stopped = False
        
        def on_press(key):
            nonlocal modifiers, key_pressed
            
            try:
                # Check for modifier keys
                if key == keyboard.Key.cmd:
                    modifiers.add("cmd")
                elif key == keyboard.Key.ctrl:
                    modifiers.add("ctrl")
                elif key == keyboard.Key.alt:
                    modifiers.add("alt")
                elif key == keyboard.Key.shift:
                    modifiers.add("shift")
                else:
                    # Regular key - stop listening
                    if hasattr(key, 'char') and key.char:
                        key_pressed = key.char
                    elif key == keyboard.Key.space:
                        key_pressed = "space"
                    else:
                        # Try to extract key name
                        key_str = str(key)
                        if key_str.startswith("Key."):
                            key_pressed = key_str.replace("Key.", "")
                        else:
                            key_pressed = key_str
                    
                    return False  # Stop listener
            except Exception as e:
                print(f"Error capturing key: {e}")
                return False
        
        def on_release(key):
            # Stop listener when any key is released (if we have a key pressed)
            if key_pressed:
                return False
            return True
        
        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        listener.join()
        
        # Store captured hotkey
        if modifiers and key_pressed:
            self.captured_hotkey = {
                "modifiers": list(modifiers),
                "key": key_pressed
            }
            
            if self.hotkey_label:
                formatted = self._format_hotkey(self.captured_hotkey)
                self.hotkey_label.configure(text=f"Captured: {formatted}")
        else:
            if self.hotkey_label:
                self.hotkey_label.configure(text="No hotkey captured. Try again.")
        
        self.recording_hotkey = False
    
    def _save_preferences(self):
        """Save preferences to config."""
        current_config = config.load_config()
        
        # Update hotkey if captured
        if self.captured_hotkey:
            current_config["hotkey"] = self.captured_hotkey
        
        # Update mode
        if self.mode_var:
            current_config["mode"] = self.mode_var.get()
        
        # Save config
        if config.save_config(current_config):
            if self.on_save:
                self.on_save(current_config)
            
            # Show success message
            success_label = ctk.CTkLabel(
                self.window,
                text="Preferences saved!",
                text_color="#4CAF50"
            )
            success_label.pack(pady=10)
            self.window.after(2000, success_label.destroy)


class ModelManagerWindow:
    """Model Manager window for downloading and switching models."""
    
    def __init__(self, transcriber, on_model_switch: Optional[Callable[[str], None]] = None):
        """Initialize model manager window.
        
        Args:
            transcriber: WhisperTranscriber instance
            on_model_switch: Callback when model is switched
        """
        self.transcriber = transcriber
        self.on_model_switch = on_model_switch
        self.window: Optional[ctk.CTkToplevel] = None
        self.model_buttons = {}
        
        # Setup CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def show(self):
        """Show model manager window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self._refresh_model_list()
            return
        
        try:
            self.window = ctk.CTkToplevel()
            self.window.title("Model Manager")
            self.window.geometry("600x500")
            
            # Main frame with scrollable area
            main_frame = ctk.CTkFrame(self.window)
            main_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Title
            title_label = ctk.CTkLabel(
                main_frame,
                text="Whisper Models",
                font=ctk.CTkFont(size=24, weight="bold")
            )
            title_label.pack(pady=(20, 20))
            
            # Scrollable frame for model list
            scrollable_frame = ctk.CTkScrollableFrame(main_frame)
            scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            self.scrollable_frame = scrollable_frame
            self._refresh_model_list()
        except Exception as e:
            # If Tkinter fails, re-raise to be handled by caller
            error_msg = str(e)
            is_tk_error = (
                "NSInvalidArgumentException" in error_msg or
                "macOSVersion" in error_msg or
                "unrecognized selector" in error_msg.lower() or
                "TclError" in str(type(e).__name__)
            )
            
            if is_tk_error:
                raise RuntimeError(
                    "Model Manager window cannot be shown due to Tkinter compatibility issue. "
                    "Please install Homebrew Python-Tk: brew install python-tk@3.12"
                ) from e
            else:
                raise
    
    def _refresh_model_list(self):
        """Refresh the model list display."""
        if not self.scrollable_frame:
            return
        
        # Clear existing widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.model_buttons = {}
        
        # Get model info
        models_info = self.transcriber.get_available_models()
        current_config = config.load_config()
        active_model = current_config.get("model", "").split("/")[-1].replace("whisper-", "").replace("-v3", "").replace("-turbo", "-turbo")
        
        # Display each model
        for variant, info in models_info.items():
            model_frame = ctk.CTkFrame(self.scrollable_frame)
            model_frame.pack(fill="x", padx=10, pady=5)
            
            # Model name and status
            status_text = "✓ Downloaded" if info["downloaded"] else "Not downloaded"
            status_color = "#4CAF50" if info["downloaded"] else "#666666"
            active_indicator = " (Active)" if variant == active_model or (variant == "large-turbo" and "large-v3-turbo" in active_model) else ""
            
            model_label = ctk.CTkLabel(
                model_frame,
                text=f"{variant.title()}: {status_text}{active_indicator}",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            model_label.pack(side="left", padx=15, pady=10)
            
            # Action buttons
            button_frame = ctk.CTkFrame(model_frame)
            button_frame.pack(side="right", padx=15, pady=10)
            
            if info["downloaded"]:
                # Switch button
                switch_btn = ctk.CTkButton(
                    button_frame,
                    text="Switch" if not active_indicator else "Active",
                    command=lambda v=variant: self._switch_model(v),
                    width=80,
                    state="disabled" if active_indicator else "normal"
                )
                switch_btn.pack(side="left", padx=5)
                self.model_buttons[variant] = switch_btn
            else:
                # Download button
                download_btn = ctk.CTkButton(
                    button_frame,
                    text="Download",
                    command=lambda v=variant: self._download_model(v),
                    width=80,
                    fg_color="#FF9800",
                    hover_color="#F57C00"
                )
                download_btn.pack(side="left", padx=5)
                self.model_buttons[variant] = download_btn
    
    def _download_model(self, variant: str):
        """Download a model.
        
        Args:
            variant: Model variant name
        """
        button = self.model_buttons.get(variant)
        if button:
            button.configure(text="Downloading...", state="disabled")
        
        def download_thread():
            def progress_callback(progress):
                if button and progress >= 0:
                    button.configure(text=f"Downloading... {int(progress * 100)}%")
            
            success = self.transcriber.download_model(variant, progress_callback)
            
            if button:
                if success:
                    button.configure(text="Downloaded", state="disabled")
                else:
                    button.configure(text="Download Failed", state="normal")
            
            # Refresh list
            self.window.after(100, self._refresh_model_list)
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def _switch_model(self, variant: str):
        """Switch to a different model.
        
        Args:
            variant: Model variant name
        """
        # Load model
        if self.transcriber.load_model(variant):
            # Update config
            current_config = config.load_config()
            repo_id = self.transcriber.MODEL_VARIANTS.get(variant)
            if repo_id:
                current_config["model"] = repo_id
                config.save_config(current_config)
            
            if self.on_model_switch:
                self.on_model_switch(variant)
            
            # Refresh list
            self._refresh_model_list()
            
            # Show success
            success_label = ctk.CTkLabel(
                self.window,
                text=f"Switched to {variant} model!",
                text_color="#4CAF50"
            )
            success_label.pack(pady=10)
            self.window.after(2000, success_label.destroy)

