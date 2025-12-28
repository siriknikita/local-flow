"""Text injection via macOS Accessibility API."""
import logging
import time
from typing import Optional

try:
    import AppKit
    import Quartz
    from Foundation import NSDictionary
except ImportError:
    logging.warning("PyObjC frameworks not available")
    AppKit = None
    Quartz = None

logger = logging.getLogger(__name__)


class TextInjector:
    """Text injector using macOS Accessibility API (no clipboard)."""
    
    def __init__(self):
        """Initialize text injector."""
        logger.info("Initializing TextInjector")
        self._check_permissions()
        logger.info("TextInjector initialized")
    
    def _check_permissions(self) -> bool:
        """Check if Accessibility permissions are granted.
        
        Returns:
            True if permissions granted, False otherwise
        """
        logger.info("Step 1: Checking Accessibility permissions")
        
        if not Quartz:
            logger.warning("Step 1: PyObjC Quartz not available, cannot check permissions")
            return False
        
        try:
            # Check accessibility permissions
            # Try to use AXIsProcessTrustedWithOptions with kAXTrustedCheckOptionPrompt
            trusted = False
            try:
                # First, try to get the constant value
                prompt_key = Quartz.kAXTrustedCheckOptionPrompt
                options = NSDictionary.dictionaryWithObject_forKey_(True, prompt_key)
                trusted = Quartz.AXIsProcessTrustedWithOptions(options)
                logger.debug("Step 1: Permission check completed using AXIsProcessTrustedWithOptions")
            except (AttributeError, KeyError) as opt_error:
                # kAXTrustedCheckOptionPrompt might not be available or accessible
                logger.debug(f"Step 1: Could not use kAXTrustedCheckOptionPrompt: {opt_error}")
                # Try with an empty options dict or None
                try:
                    # Some versions accept None or empty dict
                    trusted = Quartz.AXIsProcessTrustedWithOptions(None)
                    logger.debug("Step 1: Permission check completed using AXIsProcessTrustedWithOptions(None)")
                except Exception:
                    # If that doesn't work, we can't check permissions programmatically
                    # But we'll still allow the app to run - permissions will be checked when actually trying to inject
                    logger.warning("Step 1: Cannot check permissions programmatically, will check at injection time")
                    return True  # Allow app to continue, will fail gracefully at injection time
            
            if not trusted:
                logger.warning("Step 1: Accessibility permissions not granted")
                logger.info("Please enable Accessibility permissions in System Settings > Privacy & Security > Accessibility")
                logger.info("The app will continue to run, but text injection may not work until permissions are granted")
                return False
            
            logger.info("Step 1: Accessibility permissions granted")
            return True
        except Exception as e:
            # Handle any other errors gracefully
            error_str = str(e)
            if "kAXTrustedCheckOptionPrompt" in error_str or "AXIsProcessTrusted" in error_str:
                logger.warning(f"Step 1: Permission check API not available (non-fatal): {e}")
                logger.info("The app will continue to run, but text injection may not work until permissions are granted")
                return True  # Allow app to continue
            else:
                logger.warning(f"Step 1: Error checking permissions (non-fatal): {e}")
                logger.info("The app will continue to run, but text injection may not work until permissions are granted")
                return True  # Allow app to continue
    
    def get_focused_element(self):
        """Get the currently focused UI element.
        
        Returns:
            Focused accessibility element or None if not found
        """
        if not Quartz:
            return None
        
        try:
            # Get the system-wide accessibility element
            system_wide = Quartz.AXUIElementCreateSystemWide()
            
            # Get the focused application
            from AppKit import NoneObj
            focused_app_ref = Quartz.AXUIElementCopyAttributeValue(
                system_wide,
                Quartz.kAXFocusedApplicationAttribute,
                NoneObj
            )
            
            if focused_app_ref[0] != Quartz.kAXErrorSuccess:
                return None
            
            focused_app = focused_app_ref[1]
            
            # Get the focused UI element
            focused_element_ref = Quartz.AXUIElementCopyAttributeValue(
                focused_app,
                Quartz.kAXFocusedUIElementAttribute,
                NoneObj
            )
            
            if focused_element_ref[0] != Quartz.kAXErrorSuccess:
                return None
            
            return focused_element_ref[1]
            
        except Exception as e:
            logger.error(f"Error getting focused element: {e}", exc_info=True)
            return None
    
    def set_text_value(self, element, text: str) -> bool:
        """Set text value directly via Accessibility API.
        
        Args:
            element: Accessibility element
            text: Text to set
            
        Returns:
            True if successful, False otherwise
        """
        if not AppKit or not Quartz:
            return False
        
        try:
            # Try to set the value attribute directly
            text_value = AppKit.NSString.stringWithString_(text)
            
            error = Quartz.AXUIElementSetAttributeValue(
                element,
                Quartz.kAXValueAttribute,
                text_value
            )
            
            if error == Quartz.kAXErrorSuccess:
                return True
            
            # Try alternative: set selected text range and insert
            return self._set_text_via_selection(element, text)
            
        except Exception as e:
            logger.error(f"Error setting text value: {e}", exc_info=True)
            return False
    
    def _set_text_via_selection(self, element, text: str) -> bool:
        """Set text by selecting and replacing.
        
        Args:
            element: Accessibility element
            text: Text to set
            
        Returns:
            True if successful, False otherwise
        """
        if not Quartz:
            return False
        
        try:
            from AppKit import NoneObj
            # Get current selected text range
            selected_range_ref = Quartz.AXUIElementCopyAttributeValue(
                element,
                Quartz.kAXSelectedTextRangeAttribute,
                NoneObj
            )
            
            if selected_range_ref[0] != Quartz.kAXErrorSuccess:
                return False
            
            # Try to insert text at selection
            text_value = AppKit.NSString.stringWithString_(text)
            error = Quartz.AXUIElementSetAttributeValue(
                element,
                Quartz.kAXSelectedTextAttribute,
                text_value
            )
            
            return error == Quartz.kAXErrorSuccess
            
        except Exception as e:
            logger.error(f"Error setting text via selection: {e}", exc_info=True)
            return False
    
    def simulate_typing(self, element, text: str) -> bool:
        """Simulate typing character by character.
        
        Args:
            element: Accessibility element
            text: Text to type
            
        Returns:
            True if successful, False otherwise
        """
        if not Quartz:
            return False
        
        try:
            from AppKit import NoneObj
            # Use CGEvent to simulate keyboard input
            # First, we need to get the application PID
            pid_ref = Quartz.AXUIElementGetPid(element, NoneObj)
            if pid_ref[0] != Quartz.kAXErrorSuccess:
                return False
            
            pid = pid_ref[1]
            
            # Create keyboard events for each character
            for char in text:
                # Get key code for character
                key_code = self._char_to_keycode(char)
                
                if key_code is None:
                    # For special characters, use Unicode
                    self._type_unicode_char(char)
                else:
                    # Simulate key down and up
                    from AppKit import NoneObj as QuartzNone
                    key_down = Quartz.CGEventCreateKeyboardEvent(QuartzNone, key_code, True)
                    key_up = Quartz.CGEventCreateKeyboardEvent(QuartzNone, key_code, False)
                    
                    # Post events
                    Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_down)
                    time.sleep(0.01)  # Small delay between key down and up
                    Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_up)
                    time.sleep(0.01)  # Small delay between characters
                
                time.sleep(0.005)  # Typing speed delay
            
            return True
            
        except Exception as e:
            logger.error(f"Error simulating typing: {e}", exc_info=True)
            return False
    
    def _char_to_keycode(self, char: str) -> Optional[int]:
        """Convert character to key code.
        
        Args:
            char: Single character
            
        Returns:
            Key code or None if not mappable
        """
        # Simple mapping for common characters
        # This is a simplified version - full implementation would need
        # comprehensive key code mapping
        char_lower = char.lower()
        
        if char_lower.isalpha():
            # A-Z: key codes 0-25
            return ord(char_lower) - ord('a')
        elif char_lower.isdigit():
            # 0-9: key codes 29-38
            return ord(char_lower) - ord('0') + 29
        elif char == ' ':
            return 49  # Space
        elif char == '\n':
            return 36  # Return/Enter
        
        return None
    
    def _type_unicode_char(self, char: str):
        """Type a Unicode character using CGEvent.
        
        Args:
            char: Unicode character
        """
        if not Quartz:
            return
        
        try:
            from AppKit import NoneObj as QuartzNone
            # Create Unicode keyboard event
            key_down = Quartz.CGEventCreateKeyboardEvent(QuartzNone, 0, True)
            Quartz.CGEventKeyboardSetUnicodeString(key_down, len(char), char)
            
            key_up = Quartz.CGEventCreateKeyboardEvent(QuartzNone, 0, False)
            Quartz.CGEventKeyboardSetUnicodeString(key_up, len(char), char)
            
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_down)
            time.sleep(0.01)
            Quartz.CGEventPost(Quartz.kCGSessionEventTap, key_up)
            
        except Exception as e:
            logger.error(f"Error typing Unicode char: {e}", exc_info=True)
    
    def inject_text(self, text: str, simulate_typing: bool = False) -> bool:
        """Inject text into focused element.
        
        Args:
            text: Text to inject
            simulate_typing: If True, use character-by-character typing
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Step 1: Attempting to inject text (length: {len(text)} chars)")
        
        if not text:
            logger.warning("Step 1: No text provided for injection")
            return False
        
        logger.debug("Step 2: Getting focused element")
        element = self.get_focused_element()
        if element is None:
            logger.warning("Step 2: No focused element found")
            return False
        
        logger.debug("Step 2: Focused element found")
        
        # Try direct injection first (faster)
        if not simulate_typing:
            logger.info("Step 3: Attempting direct text injection")
            if self.set_text_value(element, text):
                logger.info("Step 4: Text injection successful (direct method)")
                return True
            logger.debug("Step 3: Direct injection failed, trying fallback")
        
        # Fallback to simulated typing
        logger.info("Step 3: Attempting simulated typing")
        result = self.simulate_typing(element, text)
        if result:
            logger.info("Step 4: Text injection successful (simulated typing)")
        else:
            logger.error("Step 4: Text injection failed (all methods)")
        return result
