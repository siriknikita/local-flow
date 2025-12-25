"""Recording overlay window with oscilloscope waveform visualization."""
import threading
import tkinter as tk
from typing import Callable, Optional

import customtkinter as ctk


class RecordingOverlay:
    """Recording overlay with oscilloscope-style waveform display."""
    
    WINDOW_WIDTH = 400
    WINDOW_HEIGHT = 200
    
    def __init__(self, waveform_callback: Optional[Callable[[], list[float]]] = None):
        """Initialize recording overlay.
        
        Args:
            waveform_callback: Callback function that returns current waveform data
        """
        self.waveform_callback = waveform_callback
        self.window: Optional[ctk.CTkToplevel] = None
        self.canvas: Optional[tk.Canvas] = None
        self.status_label: Optional[ctk.CTkLabel] = None
        self.is_visible = False
        self.cancel_callback: Optional[Callable[[], None]] = None
        self.stop_callback: Optional[Callable[[], None]] = None
        self._update_id = None
        self._waveform_data = []
        
        # Setup CustomTkinter
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
    
    def show(self, cancel_callback: Optional[Callable[[], None]] = None,
             stop_callback: Optional[Callable[[], None]] = None):
        """Show the recording overlay.
        
        Args:
            cancel_callback: Callback when cancel button is clicked
            stop_callback: Callback when stop button is clicked
        """
        if self.is_visible:
            return
        
        self.cancel_callback = cancel_callback
        self.stop_callback = stop_callback
        
        try:
            # Create overlay window
            self.window = ctk.CTkToplevel()
            self.window.title("Recording...")
            self.window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}")
            
            # Center window on screen
            self._center_window()
            
            # Make window always on top and semi-transparent
            self.window.attributes("-topmost", True)
            self.window.attributes("-alpha", 0.9)
            
            # Remove window decorations for clean look
            self.window.overrideredirect(True)
            
            # Create main frame
            main_frame = ctk.CTkFrame(self.window, corner_radius=15)
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Status label
            self.status_label = ctk.CTkLabel(
                main_frame,
                text="Recording...",
                font=ctk.CTkFont(size=16, weight="bold")
            )
            self.status_label.pack(pady=(15, 10))
            
            # Canvas for oscilloscope waveform
            canvas_frame = ctk.CTkFrame(main_frame)
            canvas_frame.pack(fill="both", expand=True, padx=20, pady=10)
            
            self.canvas = tk.Canvas(
                canvas_frame,
                bg="#1a1a1a",
                highlightthickness=0,
                width=self.WINDOW_WIDTH - 60,
                height=80
            )
            self.canvas.pack(fill="both", expand=True, padx=5, pady=5)
            
            # Button frame
            button_frame = ctk.CTkFrame(main_frame)
            button_frame.pack(pady=(10, 15))
            
            # Cancel button
            cancel_btn = ctk.CTkButton(
                button_frame,
                text="Cancel (Esc)",
                command=self._on_cancel,
                fg_color="#d32f2f",
                hover_color="#b71c1c",
                width=100
            )
            cancel_btn.pack(side="left", padx=10)
            
            # Stop button
            stop_btn = ctk.CTkButton(
                button_frame,
                text="Stop (Enter)",
                command=self._on_stop,
                fg_color="#388e3c",
                hover_color="#2e7d32",
                width=100
            )
            stop_btn.pack(side="left", padx=10)
            
            # Bind keyboard shortcuts
            self.window.bind("<Escape>", lambda e: self._on_cancel())
            self.window.bind("<Return>", lambda e: self._on_stop())
            self.window.bind("<KP_Enter>", lambda e: self._on_stop())
            
            # Focus window to receive keyboard events
            self.window.focus_set()
            
            self.is_visible = True
            
            # Start waveform update loop
            self._update_waveform()
        except Exception as e:
            # If Tkinter fails, log the error but don't crash
            # Recording can continue without the overlay
            error_msg = str(e)
            is_tk_error = (
                "NSInvalidArgumentException" in error_msg or
                "macOSVersion" in error_msg or
                "unrecognized selector" in error_msg.lower() or
                "TclError" in str(type(e).__name__)
            )
            
            if is_tk_error:
                print(f"Overlay window cannot be shown due to Tkinter compatibility issue: {e}")
                print("Recording will continue without the visual overlay.")
            else:
                print(f"Failed to show overlay window: {e}")
            
            # Mark as not visible since window creation failed
            self.is_visible = False
            self.window = None
    
    def _center_window(self):
        """Center the window on screen."""
        if not self.window:
            return
        
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        
        x = (screen_width - self.WINDOW_WIDTH) // 2
        y = (screen_height - self.WINDOW_HEIGHT) // 2
        
        self.window.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")
    
    def _update_waveform(self):
        """Update oscilloscope waveform display."""
        if not self.is_visible or not self.canvas:
            return
        
        # Get waveform data from callback
        if self.waveform_callback:
            try:
                self._waveform_data = self.waveform_callback()
            except Exception as e:
                print(f"Error getting waveform data: {e}")
                self._waveform_data = []
        
        # Clear canvas
        self.canvas.delete("all")
        
        if not self._waveform_data:
            # Draw empty state
            self.canvas.create_text(
                self.canvas.winfo_width() // 2,
                self.canvas.winfo_height() // 2,
                text="Waiting for audio...",
                fill="#666666",
                font=("Arial", 10)
            )
        else:
            # Draw oscilloscope waveform
            self._draw_oscilloscope()
        
        # Schedule next update (every ~50ms for smooth animation)
        self._update_id = self.window.after(50, self._update_waveform)
    
    def _draw_oscilloscope(self):
        """Draw oscilloscope-style waveform on canvas."""
        if not self.canvas or not self._waveform_data:
            return
        
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        if width <= 1 or height <= 1:
            return
        
        # Normalize amplitude data to fit canvas
        if not self._waveform_data:
            return
        
        max_amplitude = max(self._waveform_data) if self._waveform_data else 1.0
        if max_amplitude == 0:
            max_amplitude = 1.0
        
        # Draw grid lines (optional, for oscilloscope look)
        grid_color = "#333333"
        center_y = height // 2
        
        # Horizontal center line
        self.canvas.create_line(0, center_y, width, center_y, fill=grid_color, width=1)
        
        # Draw waveform as continuous line
        points = []
        data_len = len(self._waveform_data)
        
        for i, amplitude in enumerate(self._waveform_data):
            x = int((i / max(data_len - 1, 1)) * width)
            # Normalize amplitude to [-1, 1] range and scale to canvas
            normalized = (amplitude / max_amplitude) * 2 - 1  # Center around 0
            y = int(center_y - (normalized * (height // 2 - 10)))  # Leave some margin
            points.append((x, y))
        
        if len(points) > 1:
            # Draw continuous line
            for i in range(len(points) - 1):
                self.canvas.create_line(
                    points[i][0], points[i][1],
                    points[i + 1][0], points[i + 1][1],
                    fill="#4CAF50",
                    width=2,
                    smooth=True
                )
        
        # Draw current amplitude indicator
        if self._waveform_data:
            current_amp = self._waveform_data[-1]
            normalized = (current_amp / max_amplitude) * 2 - 1
            current_y = int(center_y - (normalized * (height // 2 - 10)))
            self.canvas.create_oval(
                width - 15, current_y - 3,
                width - 5, current_y + 3,
                fill="#FFC107",
                outline=""
            )
    
    def update_status(self, status: str):
        """Update status text.
        
        Args:
            status: Status message to display
        """
        if self.status_label:
            self.status_label.configure(text=status)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        if self.cancel_callback:
            self.cancel_callback()
        self.hide()
    
    def _on_stop(self):
        """Handle stop button click."""
        if self.stop_callback:
            self.stop_callback()
        # Don't hide immediately - let the callback handle it
    
    def hide(self):
        """Hide the overlay window."""
        if not self.is_visible:
            return
        
        self.is_visible = False
        
        if self._update_id:
            if self.window:
                self.window.after_cancel(self._update_id)
            self._update_id = None
        
        if self.window:
            self.window.destroy()
            self.window = None
        
        self.canvas = None
        self.status_label = None
        self._waveform_data = []

