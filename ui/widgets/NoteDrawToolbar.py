"""
Note Drawing Toolbar widget for Piano Roll.

Provides controls for note editing:
- Tool selection (Draw/Select/Erase)
- Quantization/Snap settings
- Note mode (Held/Repeat)
- Velocity control
- Grid snapping
"""
import dearpygui.dearpygui as dpg
from typing import Optional, Callable


class NoteDrawToolbar:
    """
    Toolbar with note drawing controls.

    Combines blooper4's quantization controls with blooper5's tool selection.
    """

    def __init__(self,
                 width: int = 800,
                 height: int = 150,
                 on_state_changed: Optional[Callable] = None):
        """
        Initialize note drawing toolbar.

        Args:
            width: Toolbar width
            height: Toolbar height
            on_state_changed: Callback when any control changes (receives state dict)
        """
        self.width = width
        self.height = height
        self.on_state_changed = on_state_changed

        # Toolbar state
        self.tool = 'draw'  # 'draw', 'select', 'erase'
        self.note_mode = 'held'  # 'held', 'repeat'
        self.velocity = 100  # 1-127
        self.snap_enabled = True  # Grid snapping on/off
        self.quantize = '1/4'  # Quantization value ('1/4', '1/8', '1/16', '1/32')

        # DearPyGui tags
        self._container_id = None

    def create_inline(self, parent: Optional[str] = None):
        """
        Create inline toolbar (embedded in parent container).

        Args:
            parent: Parent container tag (None for top-level)
        """
        with dpg.child_window(height=self.height, border=True, parent=parent) as self._container_id:
            # Row 1: Tool selection and Quantization
            with dpg.group(horizontal=True):
                dpg.add_text("Tool:")
                dpg.add_radio_button(
                    items=["Draw", "Select", "Erase"],
                    default_value="Draw",
                    callback=self._on_tool_changed,
                    horizontal=True,
                    tag="note_toolbar_tool"
                )

                dpg.add_spacer(width=20)

                dpg.add_text("Quantize:")
                dpg.add_radio_button(
                    items=["1/4", "1/8", "1/16", "1/32", "1/64"],
                    default_value="1/4",
                    callback=self._on_quantize_changed,
                    horizontal=True,
                    tag="note_toolbar_quantize"
                )

            dpg.add_separator()

            # Row 2: Note mode and Snap toggle
            with dpg.group(horizontal=True):
                dpg.add_text("Note Mode:")
                dpg.add_radio_button(
                    items=["Held Note", "Note Repeat"],
                    default_value="Held Note",
                    callback=self._on_note_mode_changed,
                    horizontal=True,
                    tag="note_toolbar_mode"
                )

                dpg.add_spacer(width=20)

                dpg.add_checkbox(
                    label="Snap to Grid",
                    default_value=True,
                    callback=self._on_snap_changed,
                    tag="note_toolbar_snap"
                )

            dpg.add_separator()

            # Row 3: Velocity control
            with dpg.group(horizontal=True):
                dpg.add_text("Velocity:")
                dpg.add_slider_int(
                    default_value=self.velocity,
                    min_value=1,
                    max_value=127,
                    callback=self._on_velocity_changed,
                    width=300,
                    tag="note_toolbar_velocity"
                )
                dpg.add_text(str(self.velocity), tag="note_toolbar_velocity_display")

    def create_window(self, tag: str = "note_draw_toolbar"):
        """
        Create separate dockable window.

        Args:
            tag: Window tag
        """
        with dpg.window(
            label="Note Drawing Toolbar",
            tag=tag,
            no_close=True,
            no_collapse=True,
            width=self.width,
            height=self.height
        ) as self._container_id:
            self.create_inline()

    def get_state(self) -> dict:
        """
        Get current toolbar state.

        Returns:
            Dictionary with current values:
            - tool: 'draw', 'select', or 'erase'
            - note_mode: 'held' or 'repeat'
            - velocity: 1-127
            - snap_enabled: bool
            - quantize: '1/4', '1/8', etc.
        """
        return {
            'tool': self.tool,
            'note_mode': self.note_mode,
            'velocity': self.velocity,
            'snap_enabled': self.snap_enabled,
            'quantize': self.quantize
        }

    # Callback handlers

    def _on_tool_changed(self, sender, value):
        """Handle tool selection change."""
        self.tool = value.lower()
        self._notify_change()

    def _on_note_mode_changed(self, sender, value):
        """Handle note mode change."""
        self.note_mode = 'held' if 'Held' in value else 'repeat'
        self._notify_change()

    def _on_velocity_changed(self, sender, value):
        """Handle velocity slider change."""
        self.velocity = value
        if dpg.does_item_exist("note_toolbar_velocity_display"):
            dpg.set_value("note_toolbar_velocity_display", str(value))
        self._notify_change()

    def _on_snap_changed(self, sender, value):
        """Handle snap toggle change."""
        self.snap_enabled = value
        self._notify_change()

    def _on_quantize_changed(self, sender, value):
        """Handle quantization change."""
        self.quantize = value
        self._notify_change()

    def _notify_change(self):
        """Notify parent of state change."""
        if self.on_state_changed:
            self.on_state_changed(self.get_state())

    def show(self):
        """Show toolbar."""
        if self._container_id:
            dpg.show_item(self._container_id)

    def hide(self):
        """Hide toolbar."""
        if self._container_id:
            dpg.hide_item(self._container_id)

    def destroy(self):
        """Clean up toolbar."""
        if self._container_id and dpg.does_item_exist(self._container_id):
            dpg.delete_item(self._container_id)
