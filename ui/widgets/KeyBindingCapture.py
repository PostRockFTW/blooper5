"""
KeyBindingCapture widget for Blooper5.

Reusable widget for capturing keyboard input for key binding assignment.
"""
import dearpygui.dearpygui as dpg
from typing import Callable, Optional


class KeyBindingCapture:
    """
    Captures keyboard input for key binding assignment.

    Handles:
    - All letter keys (A-Z)
    - Number keys (0-9)
    - Function keys (F1-F12)
    - Special keys (Space, Enter, Tab, Escape, Arrow keys, etc.)
    - Punctuation (using Windows VK codes)
    - Modifier combinations (Ctrl+, Shift+, Alt+)
    """

    def __init__(self):
        """Initialize key capture widget."""
        self.binding_in_progress = False
        self.binding_target = None
        self.on_binding_captured = None  # Callback(binding_str)
        self.on_binding_cancelled = None  # Callback()

    def start_capture(self, target_name: str,
                     on_captured: Callable[[str], None],
                     on_cancelled: Callable[[], None]):
        """
        Start capturing keystrokes for a binding.

        Args:
            target_name: Name of the binding target
            on_captured: Callback when key is captured, receives binding string
            on_cancelled: Callback when capture is cancelled
        """
        self.binding_in_progress = True
        self.binding_target = target_name
        self.on_binding_captured = on_captured
        self.on_binding_cancelled = on_cancelled

    def stop_capture(self):
        """Stop capturing keystrokes."""
        self.binding_in_progress = False
        self.binding_target = None
        self.on_binding_captured = None
        self.on_binding_cancelled = None

    def update(self):
        """
        Called every frame in main loop to detect key presses.

        Detects:
        - Modifier keys (Ctrl, Shift, Alt) via VK codes 16, 17, 18
        - Letter keys (A-Z) via DearPyGui constants
        - Number keys (0-9) via DearPyGui constants
        - Special keys (Space=32, Enter=13, Tab=9, Escape=27)
        - Punctuation via Windows VK codes (189=-, 187==, 186=;, etc.)
        - Function keys (F1-F12)
        - Arrow keys, Home, End, PageUp, PageDown
        """
        if not self.binding_in_progress:
            return

        # Check for ESC to cancel
        if hasattr(dpg, "mvKey_Escape") and dpg.is_key_pressed(dpg.mvKey_Escape):
            self._cancel_capture()
            return

        # Build modifier prefix
        modifiers = []

        # Check Control key - try both constants and common key codes
        ctrl_detected = False
        if hasattr(dpg, "mvKey_LControl"):
            ctrl_detected = ctrl_detected or dpg.is_key_down(dpg.mvKey_LControl)
        if hasattr(dpg, "mvKey_RControl"):
            ctrl_detected = ctrl_detected or dpg.is_key_down(dpg.mvKey_RControl)
        # Also try common Ctrl key codes (17 = Ctrl on Windows)
        if not ctrl_detected:
            ctrl_detected = dpg.is_key_down(17)
        if ctrl_detected:
            modifiers.append("Ctrl")

        # Check Shift key - try both constants and common key codes
        shift_detected = False
        if hasattr(dpg, "mvKey_LShift"):
            shift_detected = shift_detected or dpg.is_key_down(dpg.mvKey_LShift)
        if hasattr(dpg, "mvKey_RShift"):
            shift_detected = shift_detected or dpg.is_key_down(dpg.mvKey_RShift)
        # Also try common Shift key codes (16 = Shift on Windows)
        if not shift_detected:
            shift_detected = dpg.is_key_down(16)
        if shift_detected:
            modifiers.append("Shift")

        # Check Alt key - try both constants and common key codes
        alt_detected = False
        if hasattr(dpg, "mvKey_LAlt"):
            try:
                alt_detected = alt_detected or dpg.is_key_down(dpg.mvKey_LAlt)
            except AttributeError:
                pass
        if hasattr(dpg, "mvKey_RAlt"):
            try:
                alt_detected = alt_detected or dpg.is_key_down(dpg.mvKey_RAlt)
            except AttributeError:
                pass
        # Also try common Alt key codes (18 = Alt on Windows)
        if not alt_detected:
            alt_detected = dpg.is_key_down(18)
        if alt_detected:
            modifiers.append("Alt")

        # Build key_map dynamically
        key_map = self._build_key_map()

        # Check for any key press - use is_key_down() to catch keys
        for key_code, key_name in key_map.items():
            # Try both is_key_pressed and is_key_down for better compatibility
            if dpg.is_key_pressed(key_code) or dpg.is_key_down(key_code):
                # Use a debounce flag to prevent repeated captures
                debounce_key = f"_debounce_{key_code}"
                if hasattr(self, debounce_key):
                    continue  # Already processed this key down event
                setattr(self, debounce_key, True)

                # Don't allow modifier-only bindings
                if key_name in ["Ctrl", "Shift", "Alt"]:
                    continue

                modifier_str = "+".join(modifiers) + "+" if modifiers else ""
                binding_str = modifier_str + key_name
                self._finalize_capture(binding_str)
                return
            else:
                # Clear debounce flag when key is released
                debounce_key = f"_debounce_{key_code}"
                if hasattr(self, debounce_key):
                    delattr(self, debounce_key)

    def _build_key_map(self) -> dict:
        """
        Build mapping of key codes to key names.

        Returns dict with:
        - DearPyGui constants (if available via hasattr)
        - Windows VK codes for punctuation (186-222 range)
        - Common special keys (8, 9, 13, 27, 32)
        """
        key_map = {}

        # Special keys (only add if they exist)
        special_keys = {
            "mvKey_Space": "Space",
            "mvKey_Return": "Enter",
            "mvKey_Tab": "Tab",
            "mvKey_Backspace": "Backspace",
            "mvKey_Delete": "Delete",
            "mvKey_Home": "Home",
            "mvKey_End": "End",
            "mvKey_PageUp": "PageUp",
            "mvKey_PageDown": "PageDown",
            "mvKey_UpArrow": "Up",
            "mvKey_DownArrow": "Down",
            "mvKey_LeftArrow": "Left",
            "mvKey_RightArrow": "Right",
        }

        for key_attr, key_name in special_keys.items():
            if hasattr(dpg, key_attr):
                key_map[getattr(dpg, key_attr)] = key_name

        # Add F1-F12
        for i in range(1, 13):
            key_attr = f"mvKey_F{i}"
            if hasattr(dpg, key_attr):
                key_map[getattr(dpg, key_attr)] = f"F{i}"

        # Add A-Z (only if mvKey_A exists)
        if hasattr(dpg, "mvKey_A"):
            for i in range(26):
                key_map[dpg.mvKey_A + i] = chr(65 + i)

        # Add 0-9 (only if mvKey_0 exists)
        if hasattr(dpg, "mvKey_0"):
            for i in range(10):
                key_map[dpg.mvKey_0 + i] = str(i)

        # Manually add common keys by Windows VK codes
        common_keys = {
            # Special control keys
            32: "Space",
            8: "Backspace",
            27: "Escape",
            13: "Enter",
            9: "Tab",

            # Punctuation and symbols (using Windows Virtual Key codes)
            192: "`",       # Backtick/Grave (VK_OEM_3)
            189: "-",       # Minus/Hyphen (VK_OEM_MINUS)
            187: "=",       # Equals (VK_OEM_PLUS)
            219: "[",       # Left bracket (VK_OEM_4)
            221: "]",       # Right bracket (VK_OEM_6)
            220: "\\",      # Backslash (VK_OEM_5)
            186: ";",       # Semicolon (VK_OEM_1)
            222: "'",       # Apostrophe/Quote (VK_OEM_7)
            188: ",",       # Comma (VK_OEM_COMMA)
            190: ".",       # Period (VK_OEM_PERIOD)
            191: "/",       # Slash (VK_OEM_2)
        }
        for code, name in common_keys.items():
            if code not in key_map:
                key_map[code] = name

        return key_map

    def _finalize_capture(self, binding_str: str):
        """
        Finalize key capture with the detected binding string.

        Args:
            binding_str: The captured key binding (e.g., "Ctrl+S", "Space")
        """
        if self.on_binding_captured:
            self.on_binding_captured(binding_str)
        self.stop_capture()

    def _cancel_capture(self):
        """Cancel key capture without assigning a binding."""
        if self.on_binding_cancelled:
            self.on_binding_cancelled()
        self.stop_capture()
