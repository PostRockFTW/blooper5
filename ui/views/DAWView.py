"""
Main DAW (Digital Audio Workstation) View for Blooper5.

This is the primary workspace where users create music:
- Piano Roll (left) for MIDI editing
- Sound Designer (right) for synth/sampler/FX
- Transport controls (top) for playback
- 17-channel mixer strip (bottom) with rainbow colors
"""
import dearpygui.dearpygui as dpg
from typing import Optional, Callable
import colorsys
from ui.widgets.MixerStrip import MixerStrip


class DAWView:
    """
    Main DAW interface with dockable panels and mixer.

    Layout:
    - Top Bar: Menus + Transport controls (Play, Stop, Record, BPM, Time)
    - Center: Dockable Piano Roll + Sound Designer
    - Bottom: Collapsible 17-channel mixer (16 rainbow + 1 white master)
    """

    def __init__(self,
                 on_return_to_landing: Callable,
                 on_save_project: Optional[Callable] = None,
                 on_load_project: Optional[Callable] = None):
        """
        Args:
            on_return_to_landing: Callback to return to landing page
            on_save_project: Callback to save current project
            on_load_project: Callback to load a project
        """
        self.on_return_to_landing = on_return_to_landing
        self.on_save_project = on_save_project
        self.on_load_project = on_load_project

        # Window tags
        self._window_tag = "daw_main_window"
        self._docking_space_tag = "daw_docking_space"

        # Playback state
        self.current_track = 0  # 0-15 for tracks, 16 for master
        self.is_playing = False
        self.is_recording = False
        self.is_looping = False
        self.metronome_enabled = False
        self.bpm = 120
        self.current_time = 0.0  # Current playback position in seconds

        # Mixer state
        self.mixer_visible = True

        # Rainbow colors for 16 tracks + white for master
        self.track_colors = self._generate_rainbow_colors()

        # Sub-widgets (will be initialized in create())
        self.piano_roll = None
        self.sound_designer = None
        self.mixer_strips = []  # 17 MixerStrip instances

    def _generate_rainbow_colors(self) -> list:
        """
        Generate 16 rainbow colors + white for master channel.

        Uses HSV color space for smooth rainbow gradient.
        Colors are slightly desaturated and dimmed for VS Code dark theme.

        Returns:
            List of 17 RGBA tuples
        """
        colors = []
        for i in range(16):
            hue = i / 16.0  # 0.0 to 1.0
            saturation = 0.85  # Slightly desaturated for readability
            value = 0.90  # Slightly dimmed for dark theme
            rgb = colorsys.hsv_to_rgb(hue, saturation, value)
            rgba = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255), 255)
            colors.append(rgba)

        # Master channel: white
        colors.append((255, 255, 255, 255))

        return colors

    def create(self) -> str:
        """
        Create main DAW window with all panels.

        Returns:
            Window tag
        """
        with dpg.window(label="Blooper5 - DAW",
                       tag=self._window_tag,
                       no_scrollbar=True,
                       no_resize=False,
                       no_move=False,
                       no_close=True):

            # Top Bar: Hamburger + Transport Controls
            with dpg.group(horizontal=True):
                # Hamburger button (left side)
                dpg.add_button(
                    label="Menu",
                    callback=lambda: self.on_return_to_landing(),
                    width=60,
                    height=40
                )

                dpg.add_spacer(width=20)

                # Transport Controls (right side)
                self._create_transport_controls()

            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=5)

            # Center: Dockable Panels (Piano Roll + Sound Designer)
            # TODO: Implement docking space in Phase 5
            # Use child window to fill remaining space above mixer
            with dpg.child_window(tag=self._docking_space_tag,
                                 border=False,
                                 autosize_x=True,
                                 height=-240):  # Reserve space for mixer at bottom
                dpg.add_text("Piano Roll and Sound Designer will appear here")
                dpg.add_text("(Docking implementation coming in Phase 5)")

            dpg.add_spacer(height=5)
            dpg.add_separator()

            # Bottom: 17-Channel Mixer Strip (fixed at bottom)
            self._create_bottom_mixer()

        return self._window_tag

    def _create_transport_controls(self):
        """Create play, stop, record, BPM, time position controls."""
        with dpg.group(horizontal=True):
            # Play/Pause button
            dpg.add_button(
                label="Play",
                tag="daw_play_button",
                callback=self._on_play,
                width=50, height=40
            )

            # Stop button
            dpg.add_button(
                label="Stop",
                callback=self._on_stop,
                width=50, height=40
            )

            # Record button
            dpg.add_button(
                label="Rec",
                tag="daw_record_button",
                callback=self._on_record,
                width=50, height=40
            )

            dpg.add_spacer(width=20)

            # BPM input
            dpg.add_text("BPM:")
            dpg.add_input_int(
                tag="daw_bpm_input",
                default_value=self.bpm,
                min_value=30,
                max_value=300,
                width=60,
                callback=self._on_bpm_change
            )

            dpg.add_spacer(width=20)

            # Time position display (read-only)
            dpg.add_text("00:00:000", tag="daw_time_position_display")

            dpg.add_spacer(width=20)

            # Loop toggle
            dpg.add_checkbox(
                label="Loop",
                tag="daw_loop_toggle",
                default_value=self.is_looping,
                callback=self._on_loop_toggle
            )

            # Metronome toggle
            dpg.add_checkbox(
                label="Metro",
                tag="daw_metronome_toggle",
                default_value=self.metronome_enabled,
                callback=self._on_metronome_toggle
            )

    def _create_bottom_mixer(self):
        """Create collapsible 17-channel mixer strip."""
        with dpg.group(tag="daw_mixer_container"):
            # Toggle button
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Hide Mixer ▼",
                    callback=self._toggle_mixer_visibility,
                    tag="daw_mixer_toggle_button"
                )
                dpg.add_spacer(width=10)
                dpg.add_text("17-Channel Mixer (16 Rainbow + Master)", color=(150, 150, 150, 255))

            dpg.add_spacer(height=5)

            # Mixer strip container (can be hidden)
            with dpg.group(tag="daw_mixer_strips_group", horizontal=True):
                # Create 17 mixer strips (16 tracks + 1 master)
                for i in range(17):
                    is_master = (i == 16)
                    channel_num = i + 1 if not is_master else 17
                    color = self.track_colors[i]

                    # Create MixerStrip widget
                    mixer_strip = MixerStrip(
                        channel_number=channel_num,
                        channel_color=color,
                        is_master=is_master,
                        on_select=self._on_track_selected,
                        on_value_change=lambda param, value, idx=i: self._on_mixer_value_change(idx, param, value)
                    )
                    mixer_strip.create(parent="daw_mixer_strips_group")
                    self.mixer_strips.append(mixer_strip)

    # Transport Control Callbacks

    def _on_play(self):
        """Start/pause playback."""
        self.is_playing = not self.is_playing

        if self.is_playing:
            print(f"[PLAY] Playback started at {self.bpm} BPM")
            dpg.set_item_label("daw_play_button", "Pause")
        else:
            print("[PAUSE] Playback paused")
            dpg.set_item_label("daw_play_button", "Play")

    def _on_stop(self):
        """Stop playback and reset position."""
        self.is_playing = False
        self.current_time = 0.0
        print("[STOP] Playback stopped")
        dpg.set_item_label("daw_play_button", "Play")
        self._update_time_display()

    def _on_record(self):
        """Toggle recording."""
        self.is_recording = not self.is_recording
        print(f"[REC] Recording: {'ON' if self.is_recording else 'OFF'}")

    def _on_bpm_change(self, sender, bpm):
        """Handle BPM change."""
        self.bpm = max(30, min(300, bpm))  # Clamp to range
        print(f"BPM changed to {self.bpm}")

    def _on_loop_toggle(self, sender, value):
        """Toggle loop mode."""
        self.is_looping = value
        print(f"Loop: {'ON' if self.is_looping else 'OFF'}")

    def _on_metronome_toggle(self, sender, value):
        """Toggle metronome."""
        self.metronome_enabled = value
        print(f"Metronome: {'ON' if self.metronome_enabled else 'OFF'}")

    def _update_time_display(self):
        """Update time position display. Format: MM:SS:mmm"""
        minutes = int(self.current_time // 60)
        seconds = int(self.current_time % 60)
        millis = int((self.current_time % 1) * 1000)
        time_str = f"{minutes:02d}:{seconds:02d}:{millis:03d}"

        if dpg.does_item_exist("daw_time_position_display"):
            dpg.set_value("daw_time_position_display", time_str)

    # Mixer Callbacks

    def _toggle_mixer_visibility(self):
        """Show/hide mixer strips to save screen space."""
        self.mixer_visible = not self.mixer_visible

        if dpg.does_item_exist("daw_mixer_strips_group"):
            if self.mixer_visible:
                dpg.show_item("daw_mixer_strips_group")
                dpg.set_item_label("daw_mixer_toggle_button", "Hide Mixer ▼")
                print("Mixer shown")
            else:
                dpg.hide_item("daw_mixer_strips_group")
                dpg.set_item_label("daw_mixer_toggle_button", "Show Mixer ▲")
                print("Mixer hidden")

    def _on_track_selected(self, track_index: int):
        """
        Handle track selection (update Piano Roll view).

        Args:
            track_index: 0-15 for tracks, 16 for master
        """
        # Update previous selection highlight
        if hasattr(self, 'current_track') and 0 <= self.current_track < len(self.mixer_strips):
            self.mixer_strips[self.current_track].set_selected(False)

        self.current_track = track_index

        # Highlight new selection
        if 0 <= track_index < len(self.mixer_strips):
            self.mixer_strips[track_index].set_selected(True)

        if track_index == 16:
            print(f"Selected Master channel (Arrangement View)")
        else:
            print(f"Selected Track {track_index + 1}")

        # TODO: Update Piano Roll to show selected track in Phase 3

    def _on_mixer_value_change(self, channel_index: int, param_name: str, value):
        """
        Handle mixer value changes (volume, pan, mute, solo, fx_enabled).

        Args:
            channel_index: 0-15 for tracks, 16 for master
            param_name: "volume", "pan", "mute", "solo", or "fx_enabled"
            value: New value (float for volume/pan, bool for mute/solo/fx_enabled)
        """
        channel_name = "Master" if channel_index == 16 else f"Track {channel_index + 1}"
        print(f"{channel_name} {param_name} changed to {value}")

        # TODO: Apply changes to audio engine in future phase

    # Window Management

    def show(self):
        """Show the DAW window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.show_item(self._window_tag)

    def hide(self):
        """Hide the DAW window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.hide_item(self._window_tag)

    def destroy(self):
        """Destroy the DAW window."""
        if dpg.does_item_exist(self._window_tag):
            dpg.delete_item(self._window_tag)
