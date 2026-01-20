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
                 height: int = 100,
                 on_state_changed: Optional[Callable] = None):
        """
        Initialize note drawing toolbar.

        Args:
            width: Toolbar width
            height: Toolbar height (default 100px, compressed layout)
            on_state_changed: Callback when any control changes (receives state dict)
        """
        self.width = width
        self.height = height
        self.on_state_changed = on_state_changed

        # Toolbar state
        self.tool = 'draw'  # 'draw', 'select', 'erase'
        self.note_mode = 'held'  # 'held', 'repeat'
        self.velocity = 100  # 1-127
        self.release_velocity = 64  # 0-127
        self.snap_enabled = True  # Grid snapping on/off
        self.quantize = '1/4'  # Quantization value ('1/4', '1/8', '1/16', '1/32', '1/4T', '1/8T', etc.)
        self.is_triplet = False  # Whether current quantization is triplet
        self.bar_selection_mode = False  # Bar selection mode toggle

        # DearPyGui tags
        self._container_id = None

    def create_inline(self, parent: Optional[str] = None):
        """
        Create inline toolbar (embedded in parent container).

        Args:
            parent: Parent container tag (None for top-level)
        """
        # Create tight spacing theme for this toolbar
        with dpg.theme() as toolbar_theme:
            with dpg.theme_component(dpg.mvAll):
                # Reduce vertical spacing between rows (default 4px → 1px)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 1)
                # Reduce frame padding (default 6px → 3px)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 8, 3)
                # Reduce window padding (default 12px → 2px vertical, 4px horizontal)
                dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 4, 2)

        with dpg.child_window(height=self.height, border=False, parent=parent) as self._container_id:
            dpg.bind_item_theme(self._container_id, toolbar_theme)

            # Row 1: Combined Quantization (straight and triplets)
            with dpg.group(horizontal=True):
                dpg.add_text("Quantize:")
                dpg.add_radio_button(
                    items=["1/4", "1/8", "1/16", "1/32", "1/64", "1/128",
                           "1/4T", "1/8T", "1/16T", "1/32T", "1/64T", "1/128T"],
                    default_value="1/4",
                    callback=self._on_quantize_changed,
                    horizontal=True,
                    tag="note_toolbar_quantize"
                )

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

            # Row 3: Velocity and Release Velocity controls (combined on one line)
            with dpg.group(horizontal=True):
                dpg.add_text("Velocity:")
                dpg.add_slider_int(
                    default_value=self.velocity,
                    min_value=1,
                    max_value=127,
                    callback=self._on_velocity_changed,
                    width=200,
                    tag="note_toolbar_velocity"
                )
                dpg.add_text(str(self.velocity), tag="note_toolbar_velocity_display")

                dpg.add_spacer(width=20)

                dpg.add_text("Release:")
                dpg.add_slider_int(
                    default_value=self.release_velocity,
                    min_value=0,
                    max_value=127,
                    callback=self._on_release_velocity_changed,
                    width=200,
                    tag="note_toolbar_release_velocity"
                )
                dpg.add_text(str(self.release_velocity), tag="note_toolbar_release_velocity_display")

                dpg.add_spacer(width=20)

                dpg.add_checkbox(
                    label="Bar Selection Mode",
                    default_value=False,
                    callback=self._on_bar_selection_mode_changed,
                    tag="note_toolbar_bar_selection_mode"
                )

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
            - release_velocity: 0-127
            - snap_enabled: bool
            - quantize: '1/4', '1/8', etc.
        """
        return {
            'tool': self.tool,
            'note_mode': self.note_mode,
            'velocity': self.velocity,
            'release_velocity': self.release_velocity,
            'snap_enabled': self.snap_enabled,
            'quantize': self.quantize,
            'bar_selection_mode': self.bar_selection_mode
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

    def _on_release_velocity_changed(self, sender, value):
        """Handle release velocity slider change."""
        self.release_velocity = value
        if dpg.does_item_exist("note_toolbar_release_velocity_display"):
            dpg.set_value("note_toolbar_release_velocity_display", str(value))
        self._notify_change()

    def _on_snap_changed(self, sender, value):
        """Handle snap toggle change."""
        self.snap_enabled = value
        self._notify_change()

    def _on_quantize_changed(self, sender, value):
        """Handle quantization change (combined straight and triplets)."""
        self.quantize = value
        self.is_triplet = 'T' in value
        self._notify_change()

    def _on_bar_selection_mode_changed(self, sender, value):
        """Handle bar selection mode toggle."""
        self.bar_selection_mode = value
        self._notify_change()

    def _notify_change(self):
        """Notify parent of state change."""
        if self.on_state_changed:
            self.on_state_changed(self.get_state())

    def _notify_change_with_action(self, action: str):
        """Notify parent of state change with specific action."""
        if self.on_state_changed:
            state = self.get_state()
            state['action'] = action
            self.on_state_changed(state)

    def set_tool(self, tool: str):
        """
        Set tool programmatically (for keyboard shortcuts).

        Args:
            tool: 'draw', 'select', or 'erase'
        """
        self.tool = tool.lower()

        # Update radio button to match
        if dpg.does_item_exist("note_toolbar_tool"):
            display_value = tool.capitalize()
            dpg.set_value("note_toolbar_tool", display_value)

        self._notify_change()

    def set_quantize(self, quantize: str):
        """
        Set quantization programmatically (for keyboard shortcuts).

        Args:
            quantize: '1/4', '1/8', '1/16', '1/32', '1/4T', '1/8T', etc.
        """
        self.quantize = quantize
        self.is_triplet = 'T' in quantize

        # Update combined radio button
        if dpg.does_item_exist("note_toolbar_quantize"):
            dpg.set_value("note_toolbar_quantize", quantize)

        self._notify_change()

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
