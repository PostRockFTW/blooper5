"""
Bar Edit Toolbar Widget

Provides controls for selecting and editing bars/measures in the Piano Roll:
- Bar selection mode toggle
- Clear bar (remove all notes)
- Remove bar (delete measure entirely)
- Copy/paste bars
- Add bars before/after selection
"""

from typing import Optional, Callable
import dearpygui.dearpygui as dpg


class BarEditToolbar:
    """Toolbar for bar/measure editing operations."""

    def __init__(
        self,
        width: int = 800,
        height: int = 40,
        on_state_changed: Optional[Callable] = None
    ):
        """
        Initialize the Bar Edit Toolbar.

        Args:
            width: Width of the toolbar
            height: Height of the toolbar (default 40px, single row)
            on_state_changed: Callback when toolbar state changes.
                             Receives state dict as parameter.
        """
        self.width = width
        self.height = height
        self.on_state_changed = on_state_changed

        # State
        self.selection_mode_enabled = False
        self.selected_bar_start = None  # Bar index (0-based)
        self.selected_bar_end = None    # Bar index (inclusive)
        self.copied_notes = []  # Notes from copied bar(s)
        self.copied_bar_length = 0  # Length of copied bar in ticks

        # UI element tags
        self._container_id = None
        self._selected_bars_text = None
        self._clear_button = None
        self._remove_button = None
        self._copy_button = None
        self._paste_button = None
        self._add_before_button = None
        self._add_after_button = None

    def create_inline(self, parent):
        """
        Create the toolbar inline within a parent container.

        Args:
            parent: Parent DPG container tag
        """
        # Create tight spacing theme for bar toolbar
        with dpg.theme() as toolbar_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 5, 2)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 6, 3)

        with dpg.group(parent=parent, horizontal=False) as self._container_id:
            dpg.bind_item_theme(self._container_id, toolbar_theme)
            # Single row with all buttons
            with dpg.group(horizontal=True):
                self._clear_button = dpg.add_button(
                    label="Clear Bar",
                    callback=self._on_clear_clicked,
                    width=90,
                    enabled=False
                )
                dpg.add_spacer(width=5)
                self._remove_button = dpg.add_button(
                    label="Remove Bar",
                    callback=self._on_remove_clicked,
                    width=100,
                    enabled=False
                )
                dpg.add_spacer(width=5)
                self._copy_button = dpg.add_button(
                    label="Copy Bar",
                    callback=self._on_copy_clicked,
                    width=90,
                    enabled=False
                )
                dpg.add_spacer(width=5)
                self._paste_button = dpg.add_button(
                    label="Paste Bar",
                    callback=self._on_paste_clicked,
                    width=90,
                    enabled=False
                )
                dpg.add_spacer(width=10)
                self._add_before_button = dpg.add_button(
                    label="Add Bar Before",
                    callback=self._on_add_before_clicked,
                    width=115,
                    enabled=False
                )
                dpg.add_spacer(width=5)
                self._add_after_button = dpg.add_button(
                    label="Add Bar After",
                    callback=self._on_add_after_clicked,
                    width=110,
                    enabled=False
                )
                dpg.add_spacer(width=10)
                dpg.add_text("Selected:")
                self._selected_bars_text = dpg.add_text(
                    "None",
                    color=(150, 150, 150)
                )

    def get_state(self) -> dict:
        """
        Get current toolbar state.

        Returns:
            State dictionary with current settings
        """
        return {
            'selection_mode_enabled': self.selection_mode_enabled,
            'selected_bar_start': self.selected_bar_start,
            'selected_bar_end': self.selected_bar_end,
            'copied_notes': self.copied_notes,
            'copied_bar_length': self.copied_bar_length,
        }

    def enable_selection_mode(self, enabled: bool):
        """
        Enable or disable bar selection mode.

        Args:
            enabled: True to enable, False to disable
        """
        self.selection_mode_enabled = enabled
        if not enabled:
            # Clear selection when disabling selection mode
            self.clear_selection(notify=True)  # Notify PianoRoll to clear visual highlight
        else:
            # Notify PianoRoll that selection mode is now enabled
            self._notify_change()
        self._update_button_states()

    def set_selected_bars(self, start: int, end: int, notify: bool = False):
        """
        Update the selected bar range.

        Args:
            start: Starting bar index (0-based)
            end: Ending bar index (inclusive, 0-based)
            notify: If True, notify parent via on_state_changed callback
        """
        self.selected_bar_start = start
        self.selected_bar_end = end
        self._update_selection_display()
        self._update_button_states()
        if notify:
            self._notify_change()

    def clear_selection(self, notify: bool = False):
        """
        Clear bar selection.

        Args:
            notify: If True, notify parent via on_state_changed callback
        """
        self.selected_bar_start = None
        self.selected_bar_end = None
        self._update_selection_display()
        self._update_button_states()
        if notify:
            self._notify_change()

    def set_copied_notes(self, notes: list, bar_length: int):
        """
        Set the copied notes from a copy operation.

        Args:
            notes: List of notes that were copied
            bar_length: Length of the copied bar(s) in ticks
        """
        self.copied_notes = notes
        self.copied_bar_length = bar_length
        self._update_button_states()

    def _update_selection_display(self):
        """Update the selected bars text display."""
        if self._selected_bars_text is None:
            return

        if self.selected_bar_start is None:
            dpg.set_value(self._selected_bars_text, "None")
            dpg.configure_item(self._selected_bars_text, color=(150, 150, 150))
        else:
            # Convert 0-based index to 1-based display
            start_display = self.selected_bar_start + 1
            end_display = (self.selected_bar_end if self.selected_bar_end is not None
                          else self.selected_bar_start) + 1

            if start_display == end_display:
                text = f"Bar {start_display}"
            else:
                text = f"Bars {start_display}-{end_display}"

            dpg.set_value(self._selected_bars_text, text)
            dpg.configure_item(self._selected_bars_text, color=(255, 255, 255))

    def _update_button_states(self):
        """Update enabled/disabled state of all buttons based on current state."""
        has_selection = self.selected_bar_start is not None
        has_copied_notes = len(self.copied_notes) > 0

        if self._clear_button:
            dpg.configure_item(self._clear_button, enabled=has_selection)
        if self._remove_button:
            dpg.configure_item(self._remove_button, enabled=has_selection)
        if self._copy_button:
            dpg.configure_item(self._copy_button, enabled=has_selection)
        if self._paste_button:
            dpg.configure_item(self._paste_button, enabled=has_selection and has_copied_notes)
        if self._add_before_button:
            dpg.configure_item(self._add_before_button, enabled=has_selection)
        if self._add_after_button:
            dpg.configure_item(self._add_after_button, enabled=has_selection)

    def _notify_change(self, action: Optional[str] = None):
        """
        Notify parent of state change via callback.

        Args:
            action: Optional action that triggered the change
        """
        if self.on_state_changed:
            state = self.get_state()
            if action:
                state['action'] = action
            self.on_state_changed(state)

    # Event handlers
    def _on_clear_clicked(self):
        """Handle clear bar button click."""
        self._notify_change(action='clear_bar')

    def _on_remove_clicked(self):
        """Handle remove bar button click."""
        self._notify_change(action='remove_bar')

    def _on_copy_clicked(self):
        """Handle copy bar button click."""
        self._notify_change(action='copy_bar')

    def _on_paste_clicked(self):
        """Handle paste bar button click."""
        self._notify_change(action='paste_bar')

    def _on_add_before_clicked(self):
        """Handle add bar before button click."""
        self._notify_change(action='add_bar_before')

    def _on_add_after_clicked(self):
        """Handle add bar after button click."""
        self._notify_change(action='add_bar_after')
