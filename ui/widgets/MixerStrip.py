"""
Individual Mixer Channel Strip Widget for Blooper5.

Each mixer strip represents one audio channel:
- 16 track channels (rainbow colors)
- 1 master channel (white)

Controls per strip:
- Pan slider (horizontal, above fader)
- Volume fader (vertical)
- Level meter (animated overlay on fader)
- Mute/Solo buttons (side-by-side)
- FX enable/disable toggle
"""
import dearpygui.dearpygui as dpg
from typing import Optional, Callable


class MixerStrip:
    """
    Individual mixer channel strip.

    Layout (vertical):
    ┌────────┐
    │   1    │  ← Channel number (colored background)
    ├────────┤
    │ ◄──●──►│  ← Pan slider (horizontal)
    ├────────┤
    │   ▓    │  ← Fader (vertical) with level meter overlay
    │   █    │
    │   █    │
    │   █    │
    ├────────┤
    │  M│S   │  ← Mute/Solo buttons
    ├────────┤
    │  FX    │  ← FX enable/disable toggle
    └────────┘
    """

    def __init__(self,
                 channel_number: int,
                 channel_color: tuple,
                 is_master: bool = False,
                 on_select: Optional[Callable] = None,
                 on_value_change: Optional[Callable] = None):
        """
        Args:
            channel_number: 1-16 for tracks, 17 for master (or "M" display)
            channel_color: RGBA tuple for this channel's color
            is_master: True if this is the master channel
            on_select: Callback when channel is selected: (channel_index: int) -> None
            on_value_change: Callback when value changes: (param_name: str, value: float) -> None
        """
        self.channel = channel_number
        self.color = channel_color
        self.is_master = is_master

        # Callbacks
        self.on_select = on_select
        self.on_value_change = on_value_change

        # State
        self.volume = 0.75  # 0.0 (silent) to 1.0 (max)
        self.pan = 0.5      # 0.0 (left) to 1.0 (right), 0.5 = center
        self.muted = False
        self.solo = False
        self.fx_enabled = True
        self.level = 0.0    # Current audio level for meter (0.0 to 1.0)

        # UI tags
        self._group_tag = f"mixer_strip_{channel_number}"
        self._fader_tag = f"mixer_fader_{channel_number}"
        self._pan_tag = f"mixer_pan_{channel_number}"
        self._level_meter_tag = f"mixer_level_{channel_number}"
        self._mute_button_tag = f"mixer_mute_{channel_number}"
        self._solo_button_tag = f"mixer_solo_{channel_number}"
        self._fx_button_tag = f"mixer_fx_{channel_number}"
        self._channel_label_tag = f"mixer_label_{channel_number}"

    def create(self, parent: Optional[str] = None) -> str:
        """
        Create mixer strip UI.

        Args:
            parent: Parent container tag (optional)

        Returns:
            Group tag for this mixer strip
        """
        # Display label (1-16 or "M" for master)
        display_label = "M" if self.is_master else str(self.channel)

        with dpg.group(tag=self._group_tag, parent=parent, horizontal=False):
            # Channel number label with colored background
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label=display_label,
                    tag=self._channel_label_tag,
                    width=60,
                    height=30,
                    callback=self._on_channel_select
                )
                # Apply channel color as theme
                with dpg.theme() as channel_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            self.color,
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._channel_label_tag, channel_theme)

            dpg.add_spacer(height=2)

            # Pan slider (horizontal)
            dpg.add_slider_float(
                tag=self._pan_tag,
                default_value=self.pan,
                min_value=0.0,
                max_value=1.0,
                width=60,
                height=15,
                callback=self._on_pan_change,
                format="%.2f"
            )

            dpg.add_spacer(height=2)

            # Volume fader (vertical) with level meter
            with dpg.group():
                # Fader slider (vertical)
                dpg.add_slider_float(
                    tag=self._fader_tag,
                    default_value=self.volume,
                    min_value=0.0,
                    max_value=1.0,
                    width=60,
                    height=150,
                    vertical=True,
                    callback=self._on_fader_change,
                    format="%.2f"
                )

                # Level meter (placeholder - will be drawn over fader in future)
                # For now, just show current level as text
                dpg.add_text(
                    f"L:{int(self.level * 100)}%",
                    tag=self._level_meter_tag,
                    color=(100, 200, 100, 255)
                )

            dpg.add_spacer(height=2)

            # Mute/Solo buttons (side-by-side)
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="M",
                    tag=self._mute_button_tag,
                    width=28,
                    height=25,
                    callback=self._toggle_mute
                )
                dpg.add_button(
                    label="S",
                    tag=self._solo_button_tag,
                    width=28,
                    height=25,
                    callback=self._toggle_solo
                )

            dpg.add_spacer(height=2)

            # FX enable/disable toggle
            dpg.add_button(
                label="FX",
                tag=self._fx_button_tag,
                width=60,
                height=25,
                callback=self._toggle_fx
            )

            # Apply initial button states
            self._update_mute_button()
            self._update_solo_button()
            self._update_fx_button()

        return self._group_tag

    # Callbacks

    def _on_channel_select(self):
        """Handle channel selection (clicking channel label)."""
        if self.on_select:
            # Pass channel index (0-15 for tracks, 16 for master)
            channel_index = 16 if self.is_master else (self.channel - 1)
            self.on_select(channel_index)

    def _on_fader_change(self, sender, value):
        """Handle volume fader change."""
        self.volume = value
        if self.on_value_change:
            self.on_value_change("volume", value)

    def _on_pan_change(self, sender, value):
        """Handle pan slider change."""
        self.pan = value
        if self.on_value_change:
            self.on_value_change("pan", value)

    def _toggle_mute(self):
        """Toggle mute state."""
        self.muted = not self.muted
        self._update_mute_button()

        if self.on_value_change:
            self.on_value_change("mute", self.muted)

    def _toggle_solo(self):
        """Toggle solo state."""
        self.solo = not self.solo
        self._update_solo_button()

        if self.on_value_change:
            self.on_value_change("solo", self.solo)

    def _toggle_fx(self):
        """Toggle FX enabled state."""
        self.fx_enabled = not self.fx_enabled
        self._update_fx_button()

        if self.on_value_change:
            self.on_value_change("fx_enabled", self.fx_enabled)

    # UI Update Methods

    def _update_mute_button(self):
        """Update mute button appearance based on state."""
        if dpg.does_item_exist(self._mute_button_tag):
            if self.muted:
                # Muted: Red background
                with dpg.theme() as mute_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            (200, 50, 50, 255),
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._mute_button_tag, mute_theme)
            else:
                # Not muted: Default theme
                dpg.bind_item_theme(self._mute_button_tag, 0)  # Unbind theme

    def _update_solo_button(self):
        """Update solo button appearance based on state."""
        if dpg.does_item_exist(self._solo_button_tag):
            if self.solo:
                # Solo: Yellow background
                with dpg.theme() as solo_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            (200, 200, 50, 255),
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._solo_button_tag, solo_theme)
            else:
                # Not solo: Default theme
                dpg.bind_item_theme(self._solo_button_tag, 0)  # Unbind theme

    def _update_fx_button(self):
        """Update FX button appearance based on state."""
        if dpg.does_item_exist(self._fx_button_tag):
            if self.fx_enabled:
                # FX enabled: Green background
                with dpg.theme() as fx_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            (50, 150, 50, 255),
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._fx_button_tag, fx_theme)
            else:
                # FX disabled: Default theme
                dpg.bind_item_theme(self._fx_button_tag, 0)  # Unbind theme

    # Public Methods for External Control

    def update_level(self, level: float):
        """
        Update real-time level meter.

        Called from audio callback to show current audio level.

        Args:
            level: Audio level (0.0 to 1.0)
        """
        self.level = max(0.0, min(1.0, level))  # Clamp to range

        # Update level meter display
        if dpg.does_item_exist(self._level_meter_tag):
            dpg.set_value(self._level_meter_tag, f"L:{int(self.level * 100)}%")

            # Color-code level (green → yellow → red)
            if self.level < 0.7:
                color = (100, 200, 100, 255)  # Green
            elif self.level < 0.9:
                color = (200, 200, 100, 255)  # Yellow
            else:
                color = (200, 100, 100, 255)  # Red (clipping warning)

            dpg.configure_item(self._level_meter_tag, color=color)

    def set_volume(self, volume: float):
        """
        Set volume programmatically.

        Args:
            volume: Volume level (0.0 to 1.0)
        """
        self.volume = max(0.0, min(1.0, volume))
        if dpg.does_item_exist(self._fader_tag):
            dpg.set_value(self._fader_tag, self.volume)

    def set_pan(self, pan: float):
        """
        Set pan programmatically.

        Args:
            pan: Pan position (0.0 = left, 0.5 = center, 1.0 = right)
        """
        self.pan = max(0.0, min(1.0, pan))
        if dpg.does_item_exist(self._pan_tag):
            dpg.set_value(self._pan_tag, self.pan)

    def set_selected(self, selected: bool):
        """
        Highlight this channel as selected.

        Args:
            selected: True to highlight, False to unhighlight
        """
        if dpg.does_item_exist(self._channel_label_tag):
            if selected:
                # Add border or glow effect (simplified: just brighten background)
                brightened_color = tuple(min(255, int(c * 1.3)) for c in self.color[:3]) + (255,)
                with dpg.theme() as selected_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            brightened_color,
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._channel_label_tag, selected_theme)
            else:
                # Restore normal color
                with dpg.theme() as normal_theme:
                    with dpg.theme_component(dpg.mvButton):
                        dpg.add_theme_color(
                            dpg.mvThemeCol_Button,
                            self.color,
                            category=dpg.mvThemeCat_Core
                        )
                dpg.bind_item_theme(self._channel_label_tag, normal_theme)

    def destroy(self):
        """Destroy this mixer strip and all its UI elements."""
        if dpg.does_item_exist(self._group_tag):
            dpg.delete_item(self._group_tag)
