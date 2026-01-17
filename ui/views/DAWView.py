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
import sounddevice as sd
import numpy as np
import threading
import time
import dataclasses
import math
from ui.widgets.MixerStrip import MixerStrip
from ui.widgets.PianoRoll import PianoRoll
from plugins.sources.dual_osc import DualOscillator
from plugins.base import ProcessContext
from core.models import Note, AppState
from audio.scheduler import NoteScheduler


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
                 app_state: AppState,
                 on_save_project: Optional[Callable] = None,
                 on_load_project: Optional[Callable] = None,
                 on_new_project: Optional[Callable] = None):
        """
        Args:
            on_return_to_landing: Callback to return to landing page
            app_state: Global application state
            on_save_project: Callback to save current project
            on_load_project: Callback to load a project
            on_new_project: Callback to create a new project
        """
        self.on_return_to_landing = on_return_to_landing
        self.app_state = app_state
        self.on_save_project = on_save_project
        self.on_load_project = on_load_project
        self.on_new_project = on_new_project

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

        # Audio playback engine
        self.audio_stream = None
        self.sample_rate = 44100
        self.dual_osc = DualOscillator()
        self.playback_thread = None
        self.playback_lock = threading.Lock()

        # Mixer state
        self.mixer_visible = True

        # Undo/Redo state
        self.undo_stack = []  # List of song snapshots
        self.redo_stack = []  # List of song snapshots
        self.max_undo_history = 50  # Maximum number of undo steps

        # Project state tracking (prevent cross-project note pollution)
        self.current_song_id = None  # ID of song that Piano Roll notes belong to

        # Rainbow colors for 16 tracks + white for master
        self.track_colors = self._generate_rainbow_colors()

        # Panel sizes (resizable via draggable splitters)
        self.left_panel_width = 900  # Left panel (Note Controls + Piano Roll)
        self.note_controls_height = 150  # Note Controls toolbar height
        self.mixer_height = 240  # Mixer strip height

        # Splitter dragging state
        self.dragging_vertical_splitter = False  # Left/Right splitter
        self.dragging_horizontal_splitter = False  # Note Controls/Piano Roll splitter
        self.drag_start_pos = None

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
                # Hamburger button (left side) - returns to landing page
                dpg.add_button(
                    label="Menu",
                    callback=lambda: self.on_return_to_landing(),
                    width=60,
                    height=40
                )

                dpg.add_spacer(width=20)

                # Transport Controls (right side)
                self._create_transport_controls()

            dpg.add_spacer(height=2)

            # Center: Split layout with draggable splitters
            with dpg.group(horizontal=True, tag="center_layout"):
                # LEFT PANEL: Note Controls + Piano Roll (stacked vertically)
                with dpg.child_window(width=self.left_panel_width, height=-self.mixer_height-10, border=False, tag="left_panel"):
                    # Note Controls Toolbar (top)
                    with dpg.child_window(height=self.note_controls_height, border=False, tag="note_controls_panel"):
                        self._create_note_controls()

                    # Horizontal splitter (between Note Controls and Piano Roll)
                    with dpg.drawlist(width=self.left_panel_width, height=4, tag="horizontal_splitter_visual"):
                        dpg.draw_rectangle((0, 0), (self.left_panel_width, 4),
                                         fill=(60, 60, 60, 255), color=(80, 80, 80, 255))

                    # Invisible button for horizontal splitter drag
                    dpg.add_button(label="", width=-1, height=4, tag="horizontal_splitter_btn",
                                 callback=lambda: None)  # Drag handled by mouse handlers

                    # Piano Roll (bottom, takes remaining space)
                    with dpg.child_window(height=-1, border=False, tag="piano_roll_panel"):
                        self.piano_roll = PianoRoll(
                            width=self.left_panel_width-10,
                            height=400,
                            on_notes_changed=self._on_piano_roll_notes_changed
                        )
                        self.piano_roll.create_inline(parent="piano_roll_panel")

                # Vertical splitter (between Left and Right panels)
                with dpg.drawlist(width=4, height=-self.mixer_height-10, tag="vertical_splitter_visual"):
                    pass  # Will draw in post-create

                # Invisible button for vertical splitter drag
                dpg.add_button(label="", width=4, height=-self.mixer_height-10, tag="vertical_splitter_btn",
                             callback=lambda: None)  # Drag handled by mouse handlers

                # RIGHT PANEL: Sound Designer with Dual Oscillator
                with dpg.child_window(width=-1, height=-self.mixer_height-10, border=False, tag="sound_designer_panel"):
                    self._create_dual_oscillator_ui()

            dpg.add_spacer(height=2)

            # Bottom: 17-Channel Mixer Strip (fixed at bottom)
            self._create_bottom_mixer()

        # Setup splitter drag handlers
        self._setup_splitter_handlers()

        # Setup keyboard handlers
        self._setup_keyboard_handlers()

        return self._window_tag

    def _setup_splitter_handlers(self):
        """Setup mouse handlers for draggable splitters."""
        # Horizontal splitter (Note Controls / Piano Roll)
        with dpg.item_handler_registry(tag="horizontal_splitter_handler") as handler:
            dpg.add_item_hover_handler(callback=self._on_horizontal_splitter_hover)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left,
                                        callback=self._on_horizontal_splitter_click)

        dpg.bind_item_handler_registry("horizontal_splitter_btn", "horizontal_splitter_handler")

        # Vertical splitter (Left / Right panels)
        with dpg.item_handler_registry(tag="vertical_splitter_handler") as handler:
            dpg.add_item_hover_handler(callback=self._on_vertical_splitter_hover)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left,
                                        callback=self._on_vertical_splitter_click)

        dpg.bind_item_handler_registry("vertical_splitter_btn", "vertical_splitter_handler")

    def _setup_keyboard_handlers(self):
        """Setup keyboard handlers for playback and other shortcuts."""
        # Window-level keyboard handlers
        with dpg.handler_registry():
            # Playback controls
            dpg.add_key_press_handler(dpg.mvKey_Spacebar, callback=self._on_play)
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self._on_stop)

            # Project management
            if self.on_save_project:
                dpg.add_key_press_handler(dpg.mvKey_S, callback=lambda: self._handle_ctrl_s())
            if self.on_new_project:
                dpg.add_key_press_handler(dpg.mvKey_N, callback=lambda: self._handle_ctrl_n())
            if self.on_load_project:
                dpg.add_key_press_handler(dpg.mvKey_O, callback=lambda: self._handle_ctrl_o())

            # Undo/Redo
            dpg.add_key_press_handler(dpg.mvKey_Z, callback=lambda: self._handle_ctrl_z())
            dpg.add_key_press_handler(dpg.mvKey_Y, callback=lambda: self._handle_ctrl_y())

    def _handle_ctrl_s(self):
        """Handle Ctrl+S for save (check if Ctrl is held)."""
        if dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            if self.on_save_project:
                self.on_save_project()

    def _handle_ctrl_n(self):
        """Handle Ctrl+N for new project (check if Ctrl is held)."""
        if dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._check_unsaved_and_new()

    def _handle_ctrl_o(self):
        """Handle Ctrl+O for open project (check if Ctrl is held)."""
        if dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self._check_unsaved_and_open()

    def _handle_ctrl_z(self):
        """Handle Ctrl+Z for undo (check if Ctrl is held)."""
        if dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self.undo()

    def _handle_ctrl_y(self):
        """Handle Ctrl+Y for redo (check if Ctrl is held)."""
        if dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
            self.redo()

    def _check_unsaved_and_new(self):
        """Check for unsaved changes before creating a new project."""
        if self.app_state._is_dirty:
            # Show confirmation dialog
            self._show_unsaved_dialog(action="new")
        else:
            # No unsaved changes, proceed with new project
            if self.on_new_project:
                self.on_new_project()

    def _check_unsaved_and_open(self):
        """Check for unsaved changes before opening a project."""
        if self.app_state._is_dirty:
            # Show confirmation dialog
            self._show_unsaved_dialog(action="open")
        else:
            # No unsaved changes, proceed with open dialog
            self._show_open_file_dialog()

    def _show_unsaved_dialog(self, action: str):
        """Show dialog asking to save unsaved changes."""
        dialog_tag = f"unsaved_dialog_{action}"

        if not dpg.does_item_exist(dialog_tag):
            with dpg.window(
                label="Unsaved Changes",
                modal=True,
                show=False,
                tag=dialog_tag,
                pos=[400, 300],
                width=400,
                height=150,
                no_resize=True
            ):
                dpg.add_text("You have unsaved changes. Do you want to save before continuing?")
                dpg.add_spacer(height=20)

                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Save",
                        width=100,
                        callback=lambda: self._handle_unsaved_save(action, dialog_tag)
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_button(
                        label="Don't Save",
                        width=100,
                        callback=lambda: self._handle_unsaved_dont_save(action, dialog_tag)
                    )
                    dpg.add_spacer(width=10)
                    dpg.add_button(
                        label="Cancel",
                        width=100,
                        callback=lambda: dpg.hide_item(dialog_tag)
                    )

        dpg.show_item(dialog_tag)

    def _handle_unsaved_save(self, action: str, dialog_tag: str):
        """Handle save button in unsaved changes dialog."""
        # Save the project first
        if self.on_save_project:
            self.on_save_project()

        # Hide dialog
        dpg.hide_item(dialog_tag)

        # Proceed with the action
        if action == "new" and self.on_new_project:
            self.on_new_project()
        elif action == "open":
            self._show_open_file_dialog()

    def _handle_unsaved_dont_save(self, action: str, dialog_tag: str):
        """Handle don't save button in unsaved changes dialog."""
        # Mark as not dirty (discarding changes)
        self.app_state._is_dirty = False

        # Hide dialog
        dpg.hide_item(dialog_tag)

        # Proceed with the action
        if action == "new" and self.on_new_project:
            self.on_new_project()
        elif action == "open":
            self._show_open_file_dialog()

    def _show_open_file_dialog(self):
        """Show file dialog to open a project."""
        from pathlib import Path

        # Create file dialog if it doesn't exist
        if not dpg.does_item_exist("daw_open_project_dialog"):
            with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self._open_file_dialog_callback,
                tag="daw_open_project_dialog",
                width=700,
                height=400,
                default_path=str(Path.home() / "Documents")
            ):
                dpg.add_file_extension(".bloom5", color=(0, 122, 204, 255))
                dpg.add_file_extension(".*")

        dpg.show_item("daw_open_project_dialog")

    def _open_file_dialog_callback(self, sender, app_data):
        """Handle file dialog selection."""
        selections = app_data.get('selections', {})
        if selections:
            file_path = list(selections.values())[0]
            if self.on_load_project:
                self.on_load_project(file_path)

    def take_snapshot(self):
        """
        Take a snapshot of the current song state for undo.
        Call this before making any changes to notes.
        """
        # Save current piano roll notes to song first
        self._save_current_track_notes()

        song = self.app_state.get_current_song()
        if song is None:
            return

        # Store a copy of the current song
        self.undo_stack.append(song)

        # Limit history size
        if len(self.undo_stack) > self.max_undo_history:
            self.undo_stack.pop(0)

        # Clear redo stack when new changes are made
        self.redo_stack.clear()

        print(f"[UNDO] Snapshot taken, undo stack size: {len(self.undo_stack)}")

    def undo(self):
        """Undo the last change."""
        if not self.undo_stack:
            print("[UNDO] Nothing to undo")
            return

        # Save current state to redo stack
        current_song = self.app_state.get_current_song()
        if current_song:
            self.redo_stack.append(current_song)

        # Pop the last snapshot
        previous_song = self.undo_stack.pop()

        # Restore the previous state
        self.app_state.set_current_song(previous_song)

        # Reload the current track in piano roll
        if self.piano_roll and hasattr(self, 'current_track'):
            self._on_track_selected(self.current_track)

        print(f"[UNDO] Restored previous state, undo stack size: {len(self.undo_stack)}")

    def redo(self):
        """Redo the last undone change."""
        if not self.redo_stack:
            print("[REDO] Nothing to redo")
            return

        # Save current state to undo stack
        current_song = self.app_state.get_current_song()
        if current_song:
            self.undo_stack.append(current_song)

        # Pop the last redo snapshot
        next_song = self.redo_stack.pop()

        # Restore the next state
        self.app_state.set_current_song(next_song)

        # Reload the current track in piano roll
        if self.piano_roll and hasattr(self, 'current_track'):
            self._on_track_selected(self.current_track)

        print(f"[REDO] Restored next state, redo stack size: {len(self.redo_stack)}")

    def _on_horizontal_splitter_hover(self, sender, app_data):
        """Change cursor when hovering over horizontal splitter."""
        # TODO: Set cursor to vertical resize arrow
        pass

    def _on_horizontal_splitter_click(self, sender, app_data):
        """Handle horizontal splitter drag."""
        if not self.dragging_horizontal_splitter:
            self.dragging_horizontal_splitter = True
            self.drag_start_pos = dpg.get_mouse_pos()

    def _on_vertical_splitter_hover(self, sender, app_data):
        """Change cursor when hovering over vertical splitter."""
        # TODO: Set cursor to horizontal resize arrow
        pass

    def _on_vertical_splitter_click(self, sender, app_data):
        """Handle vertical splitter drag."""
        if not self.dragging_vertical_splitter:
            self.dragging_vertical_splitter = True
            self.drag_start_pos = dpg.get_mouse_pos()

    def _create_dual_oscillator_ui(self):
        """Create dual oscillator synthesizer controls."""
        dpg.add_spacer(height=20)

        # Header
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("DUAL OSCILLATOR SYNTH", color=(100, 150, 200, 255))

        dpg.add_spacer(height=15)

        # Oscillator 1
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Osc 1:", color=(200, 200, 200, 255))
            dpg.add_combo(items=["SINE", "SQUARE", "SAW", "TRIANGLE", "NONE"],
                         default_value="SAW",
                         width=120,
                         tag="osc1_type")

        dpg.add_spacer(height=10)

        # Oscillator 2
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Osc 2:", color=(200, 200, 200, 255))
            dpg.add_combo(items=["SINE", "SQUARE", "SAW", "TRIANGLE", "NONE"],
                         default_value="SINE",
                         width=120,
                         tag="osc2_type")

        dpg.add_spacer(height=10)

        # Osc 2 Interval
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Interval:", color=(200, 200, 200, 255))
            dpg.add_slider_int(default_value=0, min_value=-24, max_value=24,
                             width=200, tag="osc2_interval")
            dpg.add_text("st")

        dpg.add_spacer(height=10)

        # Osc 2 Detune
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Detune:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=10.0, min_value=-50.0, max_value=50.0,
                               width=200, tag="osc2_detune", format="%.1f")
            dpg.add_text("cents")

        dpg.add_spacer(height=10)

        # Osc Mix
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Mix:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=0.5, min_value=0.0, max_value=1.0,
                               width=200, tag="osc_mix", format="%.2f")

        dpg.add_spacer(height=15)
        dpg.add_separator()
        dpg.add_spacer(height=15)

        # Filter
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Filter Cutoff:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=5000.0, min_value=50.0, max_value=12000.0,
                               width=200, tag="filter_cutoff", format="%.0f")
            dpg.add_text("Hz")

        dpg.add_spacer(height=15)
        dpg.add_separator()
        dpg.add_spacer(height=15)

        # Envelope
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Attack:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=0.01, min_value=0.001, max_value=2.0,
                               width=200, tag="attack", format="%.3f")
            dpg.add_text("s")

        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Length:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=0.5, min_value=0.01, max_value=5.0,
                               width=200, tag="length", format="%.2f")
            dpg.add_text("s")

        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Gain:", color=(200, 200, 200, 255))
            dpg.add_slider_float(default_value=0.7, min_value=0.0, max_value=1.0,
                               width=200, tag="gain", format="%.2f")

        dpg.add_spacer(height=20)

        # Test Audio Button
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_button(label="Test Audio (Middle C)", callback=self._test_audio, width=200, height=40)

    def _test_audio(self):
        """Test audio by playing middle C with current dual oscillator settings."""
        print("[TEST AUDIO] Playing middle C...")

        try:
            # Get current UI parameter values
            params = {
                "osc1_type": dpg.get_value("osc1_type"),
                "osc2_type": dpg.get_value("osc2_type"),
                "osc2_interval": dpg.get_value("osc2_interval"),
                "osc2_detune": dpg.get_value("osc2_detune"),
                "osc_mix": dpg.get_value("osc_mix"),
                "filter_cutoff": dpg.get_value("filter_cutoff"),
                "attack": dpg.get_value("attack"),
                "length": dpg.get_value("length"),
                "gain": dpg.get_value("gain"),
                "root_note": 60,  # Middle C
                "transpose": 0
            }

            # Create a test note (middle C, velocity 100)
            test_note = Note(note=60, start=0.0, duration=1.0, velocity=100)

            # Create dual oscillator instance
            dual_osc = DualOscillator()

            # Create process context
            context = ProcessContext(
                sample_rate=44100,
                bpm=120.0,
                tpqn=480,
                current_tick=0
            )

            # Generate audio
            audio_buffer = dual_osc.process(None, params, test_note, context)

            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio_buffer))
            if max_val > 0:
                audio_buffer = audio_buffer / max_val * 0.8

            # Play audio
            print(f"[TEST AUDIO] Playing {len(audio_buffer)} samples...")
            sd.play(audio_buffer, samplerate=44100)
            sd.wait()
            print("[TEST AUDIO] Done!")

        except Exception as e:
            print(f"[TEST AUDIO ERROR] {e}")
            import traceback
            traceback.print_exc()

    def _create_note_controls(self):
        """Create inline note controls toolbar."""
        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=10)
            # Tool selection
            dpg.add_text("Tool:")
            dpg.add_radio_button(
                items=["Draw", "Select"],
                default_value="Draw",
                horizontal=True,
                callback=self._on_tool_change,
                tag="tool_selector"
            )

        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=10)
            # Note mode
            dpg.add_text("Note Mode:")
            dpg.add_radio_button(
                items=["Held Note", "Note Repeat"],
                default_value="Held Note",
                horizontal=True,
                callback=self._on_note_mode_change,
                tag="note_mode_selector"
            )

        dpg.add_spacer(height=10)

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=10)
            # Velocity control
            dpg.add_text("Velocity:")
            dpg.add_slider_int(
                default_value=100,
                min_value=1,
                max_value=127,
                width=200,
                callback=self._on_velocity_change,
                tag="velocity_slider"
            )

    def _on_tool_change(self, sender, value):
        """Handle tool selection change."""
        if self.piano_roll:
            self.piano_roll.tool = 'draw' if value == 'Draw' else 'select'

    def _on_note_mode_change(self, sender, value):
        """Handle note mode change."""
        if self.piano_roll:
            self.piano_roll.note_mode = 'held' if 'Held' in value else 'repeat'

    def _on_velocity_change(self, sender, value):
        """Handle velocity slider change."""
        if self.piano_roll:
            self.piano_roll.current_velocity = value

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
                width=80,
                callback=self._on_bpm_change,
                on_enter=True,
                step=0
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

    def _on_piano_roll_notes_changed(self):
        """Called when notes are modified in Piano Roll - save to app_state and take snapshot."""
        # Take snapshot for undo/redo
        self.take_snapshot()

        # Save notes to app_state so playback can see the changes
        self._save_current_track_notes()

    def _save_current_track_notes(self):
        """Save current piano roll notes back to the song."""
        song = self.app_state.get_current_song()
        if not song or not self.piano_roll:
            return

        # Only save for single tracks (not arrangement view or master)
        if not hasattr(self, 'current_track') or not (0 <= self.current_track < 16):
            return

        # Prevent cross-project note pollution: only save if Piano Roll notes
        # belong to the current project (prevent stale notes from being saved)
        if self.current_song_id is not None and id(song) != self.current_song_id:
            print(f"[DEBUG] Skipping save: Piano Roll notes belong to different project")
            return

        # Get current notes from piano roll
        current_notes = tuple(self.piano_roll.notes)

        # Check if notes have changed
        old_track = song.tracks[self.current_track]
        if current_notes != old_track.notes:
            # Mark as dirty if notes changed
            self.app_state._is_dirty = True

            # Update the track with new notes
            updated_track = dataclasses.replace(old_track, notes=current_notes)

            # Replace track in song
            new_tracks = list(song.tracks)
            new_tracks[self.current_track] = updated_track
            updated_song = dataclasses.replace(song, tracks=tuple(new_tracks))

            # Update app state
            self.app_state.set_current_song(updated_song)

    def _on_play(self):
        """Start/pause playback."""
        self.is_playing = not self.is_playing

        if self.is_playing:
            # Save current piano roll notes to song before playback
            self._save_current_track_notes()

            print(f"[PLAY] Playback started at {self.bpm} BPM")
            dpg.set_item_label("daw_play_button", "Pause")
            self._start_playback()
        else:
            print("[PAUSE] Playback paused")
            dpg.set_item_label("daw_play_button", "Play")
            self._stop_playback()

    def _on_stop(self):
        """Stop playback and reset position."""
        was_playing = self.is_playing
        self.is_playing = False
        self.current_time = 0.0
        print("[STOP] Playback stopped")
        dpg.set_item_label("daw_play_button", "Play")
        if was_playing:
            self._stop_playback()
        self._update_time_display()

        # Reset playhead to start
        if self.piano_roll:
            self.piano_roll.set_playhead_time(0.0, self.bpm)

    def _on_record(self):
        """Toggle recording."""
        self.is_recording = not self.is_recording
        print(f"[REC] Recording: {'ON' if self.is_recording else 'OFF'}")

    def _on_bpm_change(self, sender, bpm):
        """Handle BPM change."""
        self.bpm = max(30, min(300, bpm))  # Clamp to range

        # Update UI to show clamped value
        if dpg.does_item_exist("daw_bpm_input"):
            dpg.set_value("daw_bpm_input", self.bpm)

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

    def _on_track_selected(self, track_index: int, initial_load: bool = False):
        """
        Handle track selection (update Piano Roll view).

        Args:
            track_index: 0-15 for tracks, 16 for master
            initial_load: If True, skip saving current notes (prevents overwriting freshly loaded data)
        """
        # Save current piano roll notes back to the previous track before switching
        # Skip on initial load to prevent overwriting freshly loaded notes with stale Piano Roll data
        if not initial_load:
            self._save_current_track_notes()

        # Get song from app state (might be updated by save above)
        song = self.app_state.get_current_song()
        if not song:
            print("[TRACK SELECT] ERROR: song is None")
            return

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

        # Update Piano Roll display
        if not self.piano_roll:
            return

        if track_index == 16:
            # Master channel: Arrangement View (all tracks)
            all_tracks_data = []
            for i, track in enumerate(song.tracks):
                all_tracks_data.append({
                    'notes': list(track.notes),
                    'color': self.track_colors[i]
                })
            self.piano_roll.load_track_notes(
                track_index=16,
                all_tracks_data=all_tracks_data
            )
        else:
            # Single track view - use channel color
            track = song.tracks[track_index]
            self.piano_roll.load_track_notes(
                track_index=track_index,
                notes=list(track.notes),
                track_color=self.track_colors[track_index]
            )

        # Mark Piano Roll notes as belonging to this project (prevents cross-project pollution)
        self.current_song_id = id(song)

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

    # Audio Playback Engine

    def _start_playback(self):
        """Start audio playback thread."""
        if self.playback_thread is None or not self.playback_thread.is_alive():
            self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.playback_thread.start()

    def _stop_playback(self):
        """Stop audio playback thread."""
        # Thread will exit when it sees is_playing is False
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)

    def _playback_worker(self):
        """Worker thread with real-time note triggering (Blooper4-style)."""
        print("[PLAYBACK WORKER] Starting real-time playback...")

        try:
            # Create scheduler and set BPM
            scheduler = NoteScheduler(sample_rate=self.sample_rate)
            scheduler.bpm = self.bpm

            # Get synth parameters (these apply to all triggered notes)
            synth_params = self._get_synth_params()

            # Active voices (currently playing notes)
            active_voices = []

            def audio_callback(outdata, frames, time_info, status):
                """Called by sounddevice for each audio chunk (512 samples)."""
                nonlocal active_voices

                if not self.is_playing:
                    outdata[:] = 0
                    return

                # Advance scheduler
                prev_tick = scheduler.current_tick
                scheduler.advance(frames)
                curr_tick = scheduler.current_tick

                # Fetch current notes from app_state (thread-safe read of immutable data)
                # This allows playback to reflect note edits made during playback
                song = self.app_state.get_current_song()
                if not song:
                    outdata[:] = 0
                    return

                # Collect ALL notes from all 16 tracks with track index
                all_notes_with_tracks = []
                for i, track in enumerate(song.tracks):
                    for note in track.notes:
                        all_notes_with_tracks.append((note, i))

                # Check for new note triggers with real-time mute/solo filtering
                # Check if any track has solo enabled (check in real-time)
                any_solo_active = any(strip.solo for strip in self.mixer_strips[:16])

                # Create process context for audio generation
                from plugins.base import ProcessContext
                context = ProcessContext(
                    sample_rate=self.sample_rate,
                    bpm=self.bpm,
                    tpqn=scheduler.tpqn,
                    current_tick=int(curr_tick)
                )

                triggered = []
                for note, track_idx in all_notes_with_tracks:
                    # Get mixer strip for this track
                    mixer_strip = self.mixer_strips[track_idx]

                    # Check mute/solo state in real-time
                    if mixer_strip.muted:
                        continue  # Skip muted tracks

                    if any_solo_active and not mixer_strip.solo:
                        continue  # Skip non-soloed tracks when any solo is active

                    # Convert note.start (beats) to ticks
                    note_tick = note.start * scheduler.tpqn

                    # Check if note triggers in this window
                    if prev_tick <= note_tick < curr_tick:
                        # Generate full audio for this note
                        audio = self.dual_osc.process(None, synth_params, note, context)

                        triggered.append({
                            'audio': audio,
                            'position': 0,
                            'note': note,
                            'track_idx': track_idx,
                            'volume': mixer_strip.volume,
                            'pan': mixer_strip.pan
                        })

                active_voices.extend(triggered)

                # Mix all active voices into output buffer (stereo)
                output_left = np.zeros(frames, dtype=np.float32)
                output_right = np.zeros(frames, dtype=np.float32)

                voices_to_remove = []
                for i, voice in enumerate(active_voices):
                    # Get volume and pan for this voice
                    volume = voice.get('volume', 0.75)
                    pan = voice.get('pan', 0.5)

                    # Check if this voice's track is now muted/not-soloed
                    if 'track_idx' in voice:
                        track_idx = voice['track_idx']
                        mixer_strip = self.mixer_strips[track_idx]

                        # Update volume/pan in real-time from mixer
                        volume = mixer_strip.volume
                        pan = mixer_strip.pan

                        # Stop voice if track is muted
                        if mixer_strip.muted:
                            voices_to_remove.append(i)
                            continue

                        # Stop voice if not soloed when solo is active
                        if any_solo_active and not mixer_strip.solo:
                            voices_to_remove.append(i)
                            continue

                    remaining = len(voice['audio']) - voice['position']

                    if remaining <= 0:
                        # Voice finished playing
                        voices_to_remove.append(i)
                        continue

                    # How many samples to copy from this voice
                    to_copy = min(remaining, frames)

                    # Get audio samples and apply volume
                    samples = voice['audio'][voice['position']:voice['position'] + to_copy] * volume

                    # Apply pan (0.0 = left, 0.5 = center, 1.0 = right)
                    # Use constant power panning for smooth stereo image
                    pan_angle = pan * (math.pi / 2)  # 0 to π/2
                    left_gain = math.cos(pan_angle)
                    right_gain = math.sin(pan_angle)

                    # Mix into stereo output
                    output_left[:to_copy] += samples * left_gain
                    output_right[:to_copy] += samples * right_gain

                    voice['position'] += to_copy

                # Remove finished/muted voices
                for i in reversed(voices_to_remove):
                    active_voices.pop(i)

                # Normalize to prevent clipping (check both channels)
                max_val = max(np.max(np.abs(output_left)), np.max(np.abs(output_right)))
                if max_val > 0.8:
                    output_left = output_left / max_val * 0.8
                    output_right = output_right / max_val * 0.8

                # Output to audio device (stereo)
                outdata[:, 0] = output_left   # Left channel
                outdata[:, 1] = output_right  # Right channel

                # Update playhead position (for UI, using lock for thread safety)
                with self.playback_lock:
                    # Convert ticks back to seconds for time display
                    beats = scheduler.current_tick / 480
                    self.current_time = (beats * 60.0) / self.bpm

            # Start audio streaming with callback (stereo output)
            with sd.OutputStream(samplerate=self.sample_rate, channels=2,
                               blocksize=512, dtype='float32',
                               latency='low',
                               callback=audio_callback):
                # Keep thread alive while playing
                while self.is_playing:
                    sd.sleep(100)  # Check every 100ms

            print("[PLAYBACK WORKER] Stopped")

        except Exception as e:
            print(f"[PLAYBACK WORKER ERROR] {e}")
            import traceback
            traceback.print_exc()
            self.is_playing = False

    def _get_synth_params(self):
        """Get current synthesizer parameters from UI."""
        params = {}

        # Try to get values from UI, use defaults if widgets don't exist
        try:
            params["osc1_type"] = dpg.get_value("osc1_type") if dpg.does_item_exist("osc1_type") else "SAW"
            params["osc2_type"] = dpg.get_value("osc2_type") if dpg.does_item_exist("osc2_type") else "SINE"
            params["osc2_interval"] = dpg.get_value("osc2_interval") if dpg.does_item_exist("osc2_interval") else 0
            params["osc2_detune"] = dpg.get_value("osc2_detune") if dpg.does_item_exist("osc2_detune") else 10.0
            params["osc_mix"] = dpg.get_value("osc_mix") if dpg.does_item_exist("osc_mix") else 0.5
            params["filter_cutoff"] = dpg.get_value("filter_cutoff") if dpg.does_item_exist("filter_cutoff") else 5000.0
            params["attack"] = dpg.get_value("attack") if dpg.does_item_exist("attack") else 0.01
            params["length"] = dpg.get_value("length") if dpg.does_item_exist("length") else 0.5
            params["gain"] = dpg.get_value("gain") if dpg.does_item_exist("gain") else 0.7
            params["root_note"] = 60
            params["transpose"] = 0
        except Exception as e:
            print(f"[GET SYNTH PARAMS ERROR] {e}")
            # Use defaults
            params = {
                "osc1_type": "SAW",
                "osc2_type": "SINE",
                "osc2_interval": 0,
                "osc2_detune": 10.0,
                "osc_mix": 0.5,
                "filter_cutoff": 5000.0,
                "attack": 0.01,
                "length": 0.5,
                "gain": 0.7,
                "root_note": 60,
                "transpose": 0
            }

        return params

    # Update Loop

    def update(self):
        """Update method called every frame to handle splitter dragging and time display."""
        # Update time display and playhead if playing
        if self.is_playing:
            self._update_time_display()

            # Update Piano Roll playhead
            if self.piano_roll:
                self.piano_roll.set_playhead_time(self.current_time, self.bpm)

        # Check if mouse button is released to stop dragging
        if not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self.dragging_horizontal_splitter = False
            self.dragging_vertical_splitter = False
            self.drag_start_pos = None
            return

        # Handle horizontal splitter dragging (Note Controls / Piano Roll)
        if self.dragging_horizontal_splitter and self.drag_start_pos:
            mouse_pos = dpg.get_mouse_pos()
            delta_y = mouse_pos[1] - self.drag_start_pos[1]

            # Update Note Controls height
            new_height = max(100, min(400, self.note_controls_height + delta_y))
            if new_height != self.note_controls_height:
                self.note_controls_height = new_height
                dpg.configure_item("note_controls_panel", height=self.note_controls_height)
                self.drag_start_pos = mouse_pos

        # Handle vertical splitter dragging (Left / Right panels)
        if self.dragging_vertical_splitter and self.drag_start_pos:
            mouse_pos = dpg.get_mouse_pos()
            delta_x = mouse_pos[0] - self.drag_start_pos[0]

            # Update left panel width
            new_width = max(400, min(1400, self.left_panel_width + delta_x))
            if new_width != self.left_panel_width:
                self.left_panel_width = new_width
                dpg.configure_item("left_panel", width=self.left_panel_width)
                self.drag_start_pos = mouse_pos

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
