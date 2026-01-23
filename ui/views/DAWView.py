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
import queue
from ui.widgets.MixerStrip import MixerStrip
from ui.widgets.PianoRoll import PianoRoll
from ui.widgets.NoteDrawToolbar import NoteDrawToolbar
from plugins.sources.dual_osc import DualOscillator
from plugins.base import ProcessContext, ParameterType
from plugins.registry import get_global_registry
from core.models import Note, AppState
from audio.scheduler import NoteScheduler
from audio.voice_manager import VoiceManager
from midi.handler import MIDIHandler


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
        self.current_time = 0.0  # Current playback position in seconds (for time display)
        self.current_tick = 0.0  # Current playback position in ticks (for playhead visual)
        self.current_bpm = 120.0  # Current BPM at playhead (for tempo changes)

        # Audio playback engine
        self.audio_stream = None
        self.sample_rate = 44100

        # Per-track synth instances (no longer using single global dual_osc)
        self.plugin_registry = get_global_registry()
        self.track_synths = {}  # Cache: track_idx -> {'source_type': str, 'instance': AudioProcessor}

        self.playback_thread = None
        self.playback_lock = threading.Lock()

        # MIDI sync
        self.midi_handler = None  # Initialized when playback starts

        # Thread-safe queue for playhead position jumps during playback
        self.playhead_jump_queue = queue.Queue(maxsize=10)

        # Live MIDI input state
        # Key: (track_idx, note_number), Value: {'velocity': int, 'start_tick': int}
        self.active_live_notes = {}

        # Voice manager for live MIDI rendering (prevents retriggering)
        self.voice_manager = VoiceManager()

        # MIDI learn state
        self.midi_learn_active = False
        self.midi_learn_function = None  # Which function we're learning
        self.last_midi_message = None  # For learn mode feedback

        # CC button hold state tracking for continuous actions
        # Key: (function_name, cc_number), Value: {'pressed_time': float, 'last_action_time': float}
        self.held_transport_buttons = {}

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
        self.note_controls_height = 70  # Note Controls toolbar height (compact)
        self.mixer_height = 360  # Mixer strip height (increased to show all controls including FX buttons)

        # Splitter dragging state
        self.dragging_vertical_splitter = False  # Left/Right splitter
        self.dragging_horizontal_splitter = False  # Note Controls/Piano Roll splitter
        self.dragging_mixer_splitter = False  # Main content/Mixer splitter
        self.drag_start_pos = None

        # Sub-widgets (will be initialized in create())
        self.piano_roll = None
        self.note_draw_toolbar = None
        self.bar_edit_toolbar = None
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
                            on_notes_changed=self._on_piano_roll_notes_changed,
                            on_loop_markers_changed=self._on_loop_markers_changed
                        )
                        self.piano_roll.create_inline(parent="piano_roll_panel")

                        # Set up bar selection callback for BarEditToolbar
                        self.piano_roll.on_bar_selection_changed = self._on_bar_selection_changed

                # Vertical splitter (between Left and Right panels)
                with dpg.drawlist(width=4, height=-self.mixer_height-10, tag="vertical_splitter_visual"):
                    pass  # Will draw in post-create

                # Invisible button for vertical splitter drag
                dpg.add_button(label="", width=4, height=-self.mixer_height-10, tag="vertical_splitter_btn",
                             callback=lambda: None)  # Drag handled by mouse handlers

                # RIGHT PANEL: Sound Designer with Dynamic Synth Selection
                with dpg.child_window(width=-1, height=-self.mixer_height-10, border=False, tag="sound_designer_panel"):
                    self._create_sound_designer_ui()

            dpg.add_spacer(height=2)

            # Horizontal splitter (between main content and mixer)
            with dpg.drawlist(width=-1, height=4, tag="mixer_splitter_visual"):
                dpg.draw_rectangle((0, 0), (2000, 4),
                                 fill=(60, 60, 60, 255), color=(80, 80, 80, 255))

            # Invisible button for mixer splitter drag
            dpg.add_button(label="", width=-1, height=4, tag="mixer_splitter_btn",
                         callback=lambda: None)

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

        # Mixer splitter (Main content / Mixer)
        with dpg.item_handler_registry(tag="mixer_splitter_handler") as handler:
            dpg.add_item_hover_handler(callback=self._on_mixer_splitter_hover)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left,
                                        callback=self._on_mixer_splitter_click)

        dpg.bind_item_handler_registry("mixer_splitter_btn", "mixer_splitter_handler")

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

            # Tool switching (D/S/E)
            dpg.add_key_press_handler(dpg.mvKey_D, callback=self._on_key_tool_draw)
            dpg.add_key_press_handler(dpg.mvKey_S, callback=self._on_key_tool_select)
            dpg.add_key_press_handler(dpg.mvKey_E, callback=self._on_key_tool_erase)

            # Quantization shortcuts (1-5 for straight, Shift+1-4 for triplets)
            dpg.add_key_press_handler(dpg.mvKey_1, callback=self._on_key_quantize_1)
            dpg.add_key_press_handler(dpg.mvKey_2, callback=self._on_key_quantize_2)
            dpg.add_key_press_handler(dpg.mvKey_3, callback=self._on_key_quantize_3)
            dpg.add_key_press_handler(dpg.mvKey_4, callback=self._on_key_quantize_4)
            dpg.add_key_press_handler(dpg.mvKey_5, callback=self._on_key_quantize_5)

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

    # Tool switching keyboard handlers

    def _on_key_tool_draw(self):
        """Handle D key for Draw tool (unless Ctrl is held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                self.note_draw_toolbar.set_tool('draw')

    def _on_key_tool_select(self):
        """Handle S key for Select tool (unless Ctrl is held for Save)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                self.note_draw_toolbar.set_tool('select')

    def _on_key_tool_erase(self):
        """Handle E key for Erase tool (unless Ctrl is held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                self.note_draw_toolbar.set_tool('erase')

    # Quantization keyboard handlers

    def _on_key_quantize_1(self):
        """Handle 1 key for 1/4 note (or 1/4T if Shift held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                if dpg.is_key_down(dpg.mvKey_Shift):
                    self.note_draw_toolbar.set_quantize('1/4T')
                else:
                    self.note_draw_toolbar.set_quantize('1/4')

    def _on_key_quantize_2(self):
        """Handle 2 key for 1/8 note (or 1/8T if Shift held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                if dpg.is_key_down(dpg.mvKey_Shift):
                    self.note_draw_toolbar.set_quantize('1/8T')
                else:
                    self.note_draw_toolbar.set_quantize('1/8')

    def _on_key_quantize_3(self):
        """Handle 3 key for 1/16 note (or 1/16T if Shift held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                if dpg.is_key_down(dpg.mvKey_Shift):
                    self.note_draw_toolbar.set_quantize('1/16T')
                else:
                    self.note_draw_toolbar.set_quantize('1/16')

    def _on_key_quantize_4(self):
        """Handle 4 key for 1/32 note (or 1/32T if Shift held)."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                if dpg.is_key_down(dpg.mvKey_Shift):
                    self.note_draw_toolbar.set_quantize('1/32T')
                else:
                    self.note_draw_toolbar.set_quantize('1/32')

    def _on_key_quantize_5(self):
        """Handle 5 key for 1/64 note."""
        if not (dpg.is_key_down(dpg.mvKey_Control) or dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)):
            if self.note_draw_toolbar:
                self.note_draw_toolbar.set_quantize('1/64')

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

        # Update current_song_id to match the restored song object
        self.current_song_id = id(previous_song)

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

        # Update current_song_id to match the restored song object
        self.current_song_id = id(next_song)

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

    def _on_mixer_splitter_hover(self, sender, app_data):
        """Change cursor when hovering over mixer splitter."""
        pass  # Cursor change can be added later

    def _on_mixer_splitter_click(self, sender, app_data):
        """Handle mixer splitter drag."""
        if not self.dragging_mixer_splitter:
            self.dragging_mixer_splitter = True
            self.drag_start_pos = dpg.get_mouse_pos()

    def _create_sound_designer_ui(self):
        """Create Sound Designer panel with dynamic synth selection."""
        dpg.add_spacer(height=20)

        # Header
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("SOUND DESIGNER", color=(100, 150, 200, 255))

        dpg.add_spacer(height=15)

        # Synth Type Selector
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_text("Synth Type:", color=(200, 200, 200, 255))

        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            # Will be populated from registry when track is selected
            dpg.add_combo(
                items=["DUAL_OSC"],
                default_value="DUAL_OSC",
                callback=self._on_synth_type_changed,
                tag="synth_type_selector",
                width=200
            )

        dpg.add_spacer(height=15)
        dpg.add_separator()
        dpg.add_spacer(height=15)

        # Dynamic parameter container (child window for scrolling)
        with dpg.child_window(tag="synth_params_container", height=-60, width=-1, border=False):
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=20)
                dpg.add_text("Select a track to edit synth parameters", color=(150, 150, 150, 255))

        dpg.add_spacer(height=10)

        # Test Audio Button
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=20)
            dpg.add_button(
                label="Test Audio (Middle C)",
                callback=self._test_audio,
                width=200,
                height=40,
                tag="test_audio_button"
            )

    def _test_audio(self):
        """Test current track's synth with middle C."""
        if self.current_track >= 16:
            print("[TEST AUDIO] Master track has no synth")
            return

        print("[TEST AUDIO] Playing middle C...")

        try:
            # Get current track's synth
            track_synth = self._get_or_create_track_synth(self.current_track)
            if not track_synth:
                print("[TEST AUDIO] Failed to create synth")
                return

            song = self.app_state.get_current_song()
            if not song:
                print("[TEST AUDIO] No song loaded")
                return

            track = song.tracks[self.current_track]

            # Create a test note (middle C, velocity 100)
            test_note = Note(note=60, start=0.0, duration=1.0, velocity=100)

            # Create process context
            context = ProcessContext(
                sample_rate=self.sample_rate,
                bpm=120.0,
                tpqn=480,
                current_tick=0
            )

            # Generate audio using track's synth and parameters
            audio_buffer = track_synth.process(None, track.source_params, test_note, context)

            # Normalize to prevent clipping
            max_val = np.max(np.abs(audio_buffer))
            if max_val > 0:
                audio_buffer = audio_buffer / max_val * 0.8

            # Play audio
            print(f"[TEST AUDIO] Playing {len(audio_buffer)} samples with {track.source_type}...")
            sd.play(audio_buffer, samplerate=self.sample_rate)
            sd.wait()
            print("[TEST AUDIO] Done!")

        except Exception as e:
            print(f"[TEST AUDIO ERROR] {e}")
            import traceback
            traceback.print_exc()

    def _generate_synth_param_ui(self, track_idx: int):
        """Generate UI widgets from plugin metadata for the selected track."""
        song = self.app_state.get_current_song()
        if not song or track_idx >= len(song.tracks):
            return

        track = song.tracks[track_idx]

        # Get metadata from registry
        try:
            metadata = self.plugin_registry.get_plugin_metadata(track.source_type)
        except Exception as e:
            print(f"[UI ERROR] Failed to get metadata for {track.source_type}: {e}")
            return

        # Clear existing params
        if dpg.does_item_exist("synth_params_container"):
            dpg.delete_item("synth_params_container", children_only=True)

        # Generate widgets from metadata
        for param in metadata.parameters:
            tag = f"synth_param_{param.name}"

            # Delete old tag if it exists
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

            # Create horizontal group for label
            label_group = dpg.add_group(horizontal=True, parent="synth_params_container")
            dpg.add_spacer(width=20, parent=label_group)
            dpg.add_text(f"{param.display_name}:", color=(200, 200, 200, 255), parent=label_group)

            # Create horizontal group for widget
            widget_group = dpg.add_group(horizontal=True, parent="synth_params_container")
            dpg.add_spacer(width=20, parent=widget_group)

            if param.type == ParameterType.FLOAT:
                default_val = track.source_params.get(param.name, param.default)
                widget_id = dpg.add_slider_float(
                    min_value=param.min_val,
                    max_value=param.max_val,
                    default_value=default_val,
                    callback=self._create_param_callback(track_idx, param.name),
                    width=200,
                    format="%.3f",
                    parent=widget_group
                )
                dpg.set_item_alias(widget_id, tag)
                # Add unit if available
                if hasattr(param, 'unit') and param.unit:
                    dpg.add_text(param.unit, color=(150, 150, 150, 255), parent=widget_group)

            elif param.type == ParameterType.INT:
                widget_id = dpg.add_slider_int(
                    min_value=int(param.min_val),
                    max_value=int(param.max_val),
                    default_value=int(track.source_params.get(param.name, param.default)),
                    callback=self._create_param_callback(track_idx, param.name),
                    width=200,
                    parent=widget_group
                )
                dpg.set_item_alias(widget_id, tag)
                # Add unit if available
                if hasattr(param, 'unit') and param.unit:
                    dpg.add_text(param.unit, color=(150, 150, 150, 255), parent=widget_group)

            elif param.type == ParameterType.BOOL:
                widget_id = dpg.add_checkbox(
                    default_value=track.source_params.get(param.name, param.default),
                    callback=self._create_param_callback(track_idx, param.name),
                    parent=widget_group
                )
                dpg.set_item_alias(widget_id, tag)

            elif param.type == ParameterType.ENUM:
                default_val = track.source_params.get(param.name, param.default)
                widget_id = dpg.add_combo(
                    items=param.enum_values,
                    default_value=default_val,
                    callback=self._create_param_callback(track_idx, param.name),
                    width=200,
                    parent=widget_group
                )
                dpg.set_item_alias(widget_id, tag)

            # Add spacing between parameters
            dpg.add_spacer(height=10, parent="synth_params_container")

        print(f"[SYNTH UI] Generated {len(metadata.parameters)} parameters for {track.source_type}")

    def _on_synth_param_changed(self, track_idx: int, param_name: str, value):
        """Auto-save parameter change to track.source_params."""
        song = self.app_state.get_current_song()
        if not song or track_idx >= len(song.tracks):
            return

        track = song.tracks[track_idx]

        # Update source_params (immutable, create new track)
        new_params = track.source_params.copy()
        new_params[param_name] = value

        new_track = dataclasses.replace(track, source_params=new_params)
        new_tracks = list(song.tracks)
        new_tracks[track_idx] = new_track

        new_song = dataclasses.replace(song, tracks=tuple(new_tracks))
        self.app_state.set_current_song(new_song)
        self.app_state.mark_dirty()

        # Update current_song_id to match the new song object
        self.current_song_id = id(new_song)

        print(f"[SYNTH PARAM] Track {track_idx}: {param_name} = {value}")

    def _create_param_callback(self, track_idx: int, param_name: str):
        """Create a callback that captures track_idx and param_name correctly.

        DearPyGUI callbacks receive (sender, value) arguments.
        This wrapper captures track and parameter identifiers in the closure.
        """
        def callback(sender, value):
            self._on_synth_param_changed(track_idx, param_name, value)
        return callback

    def _refresh_sound_designer_ui(self, track_idx: int, track):
        """Refresh Sound Designer UI for selected track."""
        # Update synth type selector
        if dpg.does_item_exist("synth_type_selector"):
            source_ids = list(self.plugin_registry.SOURCE_PLUGINS.keys())
            dpg.configure_item("synth_type_selector", items=source_ids)
            dpg.set_value("synth_type_selector", track.source_type)

        # Regenerate parameter UI
        self._generate_synth_param_ui(track_idx)

        print(f"[SYNTH UI] Loaded {track.source_type} for Track {track_idx + 1}")

    def _on_synth_type_changed(self, sender, new_synth_id):
        """Handle synth type change for current track."""
        if self.current_track >= 16:
            return  # Master track doesn't have synth

        song = self.app_state.get_current_song()
        if not song:
            return

        track = song.tracks[self.current_track]

        # Don't process if already the same
        if track.source_type == new_synth_id:
            return

        # Get new synth metadata for parameter migration
        try:
            new_metadata = self.plugin_registry.get_plugin_metadata(new_synth_id)
        except Exception as e:
            print(f"[SYNTH ERROR] Failed to get metadata for {new_synth_id}: {e}")
            return

        # Migrate parameters (preserve common ones)
        new_params = {}
        for param_spec in new_metadata.parameters:
            # Use old value if param name exists, else default
            new_params[param_spec.name] = track.source_params.get(
                param_spec.name,
                param_spec.default
            )

        # Update track
        new_track = dataclasses.replace(
            track,
            source_type=new_synth_id,
            last_synth_source=track.source_type,
            source_params=new_params
        )

        new_tracks = list(song.tracks)
        new_tracks[self.current_track] = new_track
        new_song = dataclasses.replace(song, tracks=tuple(new_tracks))

        self.app_state.set_current_song(new_song)
        self.app_state.mark_dirty()

        # Clear cached synth for this track
        self._clear_track_synth_cache(self.current_track)

        # Refresh UI
        self._refresh_sound_designer_ui(self.current_track, new_track)

        print(f"[SYNTH CHANGE] Track {self.current_track + 1}: {track.source_type} -> {new_synth_id}")

    def _create_note_controls(self):
        """Create note drawing toolbar and bar edit toolbar."""
        # Note Draw Toolbar
        self.note_draw_toolbar = NoteDrawToolbar(
            width=self.left_panel_width - 20,
            height=70,  # Compact height
            on_state_changed=self._on_toolbar_state_changed
        )
        self.note_draw_toolbar.create_inline(parent="note_controls_panel")

        # Bar Edit Toolbar (inline, hidden by default)
        from ui.widgets.BarEditToolbar import BarEditToolbar
        self.bar_edit_toolbar = BarEditToolbar(
            width=self.left_panel_width - 20,
            height=40,  # Single row of buttons
            on_state_changed=self._on_bar_toolbar_state_changed
        )
        # Create container group (hidden by default)
        with dpg.group(show=False, tag="bar_edit_toolbar_container", parent="note_controls_panel"):
            self.bar_edit_toolbar.create_inline(parent="bar_edit_toolbar_container")

    def _on_toolbar_state_changed(self, toolbar_state: dict):
        """Handle toolbar state changes - update Piano Roll and handle bar actions."""
        if self.piano_roll:
            self.piano_roll.update_toolbar_state(toolbar_state)

        # Handle bar selection mode toggle - show/hide bar toolbar and expand panel
        bar_selection_mode = toolbar_state.get('bar_selection_mode', False)
        if dpg.does_item_exist("bar_edit_toolbar_container"):
            # Update bar toolbar's internal state
            if self.bar_edit_toolbar:
                self.bar_edit_toolbar.enable_selection_mode(bar_selection_mode)

            if bar_selection_mode:
                dpg.show_item("bar_edit_toolbar_container")
                # Expand note_controls_panel to fit both toolbars
                self.note_controls_height = 110  # 70 (note toolbar) + 40 (bar toolbar)
                dpg.configure_item("note_controls_panel", height=self.note_controls_height)
            else:
                dpg.hide_item("bar_edit_toolbar_container")
                # Shrink back to just note toolbar
                self.note_controls_height = 70  # Just note toolbar (tighter now)
                dpg.configure_item("note_controls_panel", height=self.note_controls_height)

        # Handle bar editing actions
        action = toolbar_state.get('action')
        if action == 'clear_bar':
            self._execute_clear_bar_from_piano_roll()
        elif action == 'remove_bar':
            self._execute_remove_bar_from_piano_roll()
        elif action == 'copy_bar':
            self._execute_copy_bar_from_piano_roll()
        elif action == 'paste_bar':
            self._execute_paste_bar_from_piano_roll()
        elif action == 'add_bar_before':
            self._execute_add_bar_before_from_piano_roll()
        elif action == 'add_bar_after':
            self._execute_add_bar_after_from_piano_roll()

    def _on_bar_selection_changed(self, bar_start: int, bar_end: int):
        """Handle bar selection changes from Piano Roll - update BarEditToolbar."""
        if self.bar_edit_toolbar:
            self.bar_edit_toolbar.set_selected_bars(bar_start, bar_end)

    def _on_bar_toolbar_state_changed(self, toolbar_state: dict):
        """Handle bar edit toolbar state changes."""
        # Update Piano Roll with bar edit state
        if self.piano_roll:
            self.piano_roll.update_bar_edit_state(toolbar_state)

        # Handle button actions
        action = toolbar_state.get('action')
        if action == 'clear_bar':
            self._execute_clear_bar(toolbar_state)
        elif action == 'remove_bar':
            self._execute_remove_bar(toolbar_state)
        elif action == 'copy_bar':
            self._execute_copy_bar(toolbar_state)
        elif action == 'paste_bar':
            self._execute_paste_bar(toolbar_state)
        elif action == 'add_bar_before':
            self._execute_add_bar_before(toolbar_state)
        elif action == 'add_bar_after':
            self._execute_add_bar_after(toolbar_state)

    # New methods that get bar selection from PianoRoll (for integrated toolbar)
    def _execute_clear_bar_from_piano_roll(self):
        """Execute clear bar command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_start = self.piano_roll.selected_bar_start
        bar_end = self.piano_roll.selected_bar_end if self.piano_roll.selected_bar_end is not None else bar_start

        if bar_start is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        track_index = self.current_track
        from core.commands import ClearBarCommand
        command = ClearBarCommand(track_index, bar_start, bar_end)
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_remove_bar_from_piano_roll(self):
        """Execute remove bar command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_start = self.piano_roll.selected_bar_start
        bar_end = self.piano_roll.selected_bar_end if self.piano_roll.selected_bar_end is not None else bar_start

        if bar_start is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        from core.commands import RemoveBarCommand
        command = RemoveBarCommand(bar_start, bar_end)
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Clear piano roll selection (bars are removed)
        self.piano_roll.selected_bar_start = None
        self.piano_roll.selected_bar_end = None

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_copy_bar_from_piano_roll(self):
        """Execute copy bar command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_start = self.piano_roll.selected_bar_start
        bar_end = self.piano_roll.selected_bar_end if self.piano_roll.selected_bar_end is not None else bar_start

        if bar_start is None:
            return  # No selection

        track_index = self.current_track
        from core.commands import CopyBarCommand
        command = CopyBarCommand(track_index, bar_start, bar_end)
        command.execute(self.app_state)  # Copy is read-only, no undo snapshot needed

        # Store copied notes for paste operation
        self.piano_roll.copied_notes = command.copied_notes
        self.piano_roll.copied_bar_length = command.copied_bar_length

    def _execute_paste_bar_from_piano_roll(self):
        """Execute paste bar command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_start = self.piano_roll.selected_bar_start
        bar_end = self.piano_roll.selected_bar_end if self.piano_roll.selected_bar_end is not None else bar_start
        copied_notes = getattr(self.piano_roll, 'copied_notes', [])
        copied_bar_length = getattr(self.piano_roll, 'copied_bar_length', 0)

        if bar_start is None or not copied_notes:
            return  # No selection or no copied notes

        # Take undo snapshot
        self.take_snapshot()

        track_index = self.current_track
        from core.commands import PasteBarCommand
        command = PasteBarCommand(track_index, bar_start, bar_end, copied_notes, copied_bar_length)
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_add_bar_before_from_piano_roll(self):
        """Execute add bar before command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_index = self.piano_roll.selected_bar_start

        if bar_index is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        # Get current time signature and BPM from song
        song = self.app_state.get_current_song()
        time_signature = song.time_signature if song else (4, 4)
        bpm = song.bpm if song else 120.0

        from core.commands import AddBarCommand
        command = AddBarCommand(
            bar_index, position="before",
            time_signature=time_signature, bpm=bpm
        )
        command.execute(self.app_state)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

    def _execute_add_bar_after_from_piano_roll(self):
        """Execute add bar after command using PianoRoll's bar selection."""
        if not self.piano_roll:
            return

        bar_index = self.piano_roll.selected_bar_start

        if bar_index is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        # Get current time signature and BPM from song
        song = self.app_state.get_current_song()
        time_signature = song.time_signature if song else (4, 4)
        bpm = song.bpm if song else 120.0

        from core.commands import AddBarCommand
        command = AddBarCommand(
            bar_index, position="after",
            time_signature=time_signature, bpm=bpm
        )
        command.execute(self.app_state)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

    # Original methods that get bar selection from toolbar_state (for old BarEditToolbar)
    def _execute_clear_bar(self, toolbar_state: dict):
        """Execute clear bar command."""
        bar_start = toolbar_state.get('selected_bar_start')
        bar_end = toolbar_state.get('selected_bar_end', bar_start)

        if bar_start is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        track_index = self.current_track
        from core.commands import ClearBarCommand
        command = ClearBarCommand(track_index, bar_start, bar_end)
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_remove_bar(self, toolbar_state: dict):
        """Execute remove bar command."""
        bar_start = toolbar_state.get('selected_bar_start')
        bar_end = toolbar_state.get('selected_bar_end', bar_start)

        if bar_start is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        from core.commands import RemoveBarCommand
        command = RemoveBarCommand(bar_start, bar_end)
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Clear toolbar selection (bars are removed)
        if self.bar_edit_toolbar:
            self.bar_edit_toolbar.clear_selection()

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_copy_bar(self, toolbar_state: dict):
        """Execute copy bar command."""
        bar_start = toolbar_state.get('selected_bar_start')
        bar_end = toolbar_state.get('selected_bar_end', bar_start)

        if bar_start is None:
            return  # No selection

        track_index = self.current_track
        from core.commands import CopyBarCommand
        command = CopyBarCommand(track_index, bar_start, bar_end)
        command.execute(self.app_state)  # Copy is read-only, no undo snapshot needed

        # Update toolbar with copied notes
        if self.bar_edit_toolbar:
            self.bar_edit_toolbar.set_copied_notes(
                command.copied_notes,
                command.copied_bar_length
            )

    def _execute_paste_bar(self, toolbar_state: dict):
        """Execute paste bar command."""
        bar_start = toolbar_state.get('selected_bar_start')
        bar_end = toolbar_state.get('selected_bar_end', bar_start)
        copied_notes = toolbar_state.get('copied_notes', [])
        copied_bar_length = toolbar_state.get('copied_bar_length', 0)

        if bar_start is None or not copied_notes:
            return  # No selection or no copied notes

        # Take undo snapshot
        self.take_snapshot()

        track_index = self.current_track
        from core.commands import PasteBarCommand
        command = PasteBarCommand(
            track_index, bar_start, bar_end,
            copied_notes, copied_bar_length
        )
        command.execute(self.app_state)

        # Update current_song_id to match the new song object
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

    def _execute_add_bar_before(self, toolbar_state: dict):
        """Execute add bar before command."""
        bar_index = toolbar_state.get('selected_bar_start')

        if bar_index is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        # Get current time signature and BPM from song
        song = self.app_state.get_current_song()
        time_signature = song.time_signature if song else (4, 4)
        bpm = song.bpm if song else 120.0

        from core.commands import AddBarCommand
        command = AddBarCommand(
            bar_index, position="before",
            time_signature=time_signature, bpm=bpm
        )
        command.execute(self.app_state)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

        # Update current_song_id to match the new song object (prevents cross-project note pollution)
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

    def _execute_add_bar_after(self, toolbar_state: dict):
        """Execute add bar after command."""
        bar_index = toolbar_state.get('selected_bar_start')

        if bar_index is None:
            return  # No selection

        # Take undo snapshot
        self.take_snapshot()

        # Get current time signature and BPM from song
        song = self.app_state.get_current_song()
        time_signature = song.time_signature if song else (4, 4)
        bpm = song.bpm if song else 120.0

        from core.commands import AddBarCommand
        command = AddBarCommand(
            bar_index, position="after",
            time_signature=time_signature, bpm=bpm
        )
        command.execute(self.app_state)

        # Refresh Piano Roll
        self._refresh_piano_roll_from_song()

        # Update current_song_id to match the new song object (prevents cross-project note pollution)
        new_song = self.app_state.get_current_song()
        if new_song:
            self.current_song_id = id(new_song)

    def _refresh_piano_roll_from_song(self):
        """Refresh Piano Roll display from current song."""
        if not self.piano_roll:
            return

        song = self.app_state.get_current_song()
        if not song:
            return

        # Reload current track
        if self.current_track < len(song.tracks):
            track = song.tracks[self.current_track]
            track_color = self.track_colors[self.current_track]
            self.piano_roll.load_track_notes(
                track_index=self.current_track,
                notes=list(track.notes),
                track_color=track_color,
                song=song
            )

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
            dpg.add_button(
                label="Learn",
                callback=lambda: self._start_midi_learn('play'),
                tag="learn_play_button",
                width=50, height=20
            )

            dpg.add_spacer(width=10)

            # Stop button
            dpg.add_button(
                label="Stop",
                callback=self._on_stop,
                width=50, height=40
            )
            dpg.add_button(
                label="Learn",
                callback=lambda: self._start_midi_learn('stop'),
                tag="learn_stop_button",
                width=50, height=20
            )

            dpg.add_spacer(width=10)

            # Record button
            dpg.add_button(
                label="Rec",
                tag="daw_record_button",
                callback=self._on_record,
                width=50, height=40
            )
            dpg.add_button(
                label="Learn",
                callback=lambda: self._start_midi_learn('record'),
                tag="learn_record_button",
                width=50, height=20
            )

            dpg.add_spacer(width=10)

            # Rewind button (mapped to "forward" for MPK25 compatibility)
            dpg.add_button(
                label="<<",
                callback=self._on_forward,
                width=40, height=40
            )
            dpg.add_button(
                label="Learn",
                callback=lambda: self._start_midi_learn('forward'),
                tag="learn_forward_button",
                width=40, height=20
            )

            dpg.add_spacer(width=10)

            # Fast-forward button (mapped to "backward" for MPK25 compatibility)
            dpg.add_button(
                label=">>",
                callback=self._on_backward,
                width=40, height=40
            )
            dpg.add_button(
                label="Learn",
                callback=lambda: self._start_midi_learn('backward'),
                tag="learn_backward_button",
                width=40, height=20
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

            dpg.add_spacer(width=20)

            # Test track button
            dpg.add_button(
                label="Load Test Track",
                callback=self._create_test_track_with_changing_measures,
                width=120,
                height=40
            )

    def _create_bottom_mixer(self):
        """Create collapsible 17-channel mixer strip."""
        # Wrap mixer in child_window with fixed height to ensure proper positioning
        with dpg.child_window(height=self.mixer_height, border=False, tag="daw_mixer_window"):
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

            # Update current_song_id to match the new song object
            self.current_song_id = id(updated_song)

    def _on_loop_markers_changed(self, start_tick: int, end_tick):
        """Called when loop markers are dragged in Piano Roll."""
        song = self.app_state.get_current_song()
        if not song:
            return

        # Update song with new loop positions
        loop_enabled = (end_tick is not None)
        updated_song = dataclasses.replace(
            song,
            loop_start_tick=start_tick,
            loop_end_tick=end_tick,
            loop_enabled=loop_enabled
        )

        self.app_state.set_current_song(updated_song)
        self.app_state._is_dirty = True

        # Update current_song_id to match the new song object
        self.current_song_id = id(updated_song)

        # Sync the is_looping flag and checkbox with the song state
        self.is_looping = loop_enabled
        if dpg.does_item_exist("daw_loop_toggle"):
            dpg.set_value("daw_loop_toggle", loop_enabled)

    def _on_play(self):
        """Start/pause playback."""
        self.is_playing = not self.is_playing

        if self.is_playing:
            # Save current piano roll notes to song before playback
            self._save_current_track_notes()

            # Initialize current_bpm (will be updated by scheduler during playback)
            self.current_bpm = self.bpm

            print(f"[PLAY] Playback started at {self.bpm} BPM")
            dpg.set_item_label("daw_play_button", "Pause")
            self._start_playback()

            # Send MIDI Start message
            song = self.app_state.get_current_song()
            if song and song.send_midi_clock and self.midi_handler and self.midi_handler.midi_out:
                self.midi_handler.send_start()
        else:
            print("[PAUSE] Playback paused")
            dpg.set_item_label("daw_play_button", "Play")

            # Send MIDI Stop message
            if self.midi_handler and self.midi_handler.midi_out:
                self.midi_handler.send_stop()

            self._stop_playback()

    def _on_stop(self):
        """Stop playback and reset position."""
        was_playing = self.is_playing
        self.is_playing = False
        self.current_time = 0.0
        self.current_tick = 0.0
        self.current_bpm = self.bpm  # Reset to global BPM
        print("[STOP] Playback stopped")

        # Reset BPM display
        if dpg.does_item_exist("daw_bpm_input"):
            dpg.set_value("daw_bpm_input", int(self.bpm))
        dpg.set_item_label("daw_play_button", "Play")
        if was_playing:
            # Send MIDI Stop message
            if self.midi_handler and self.midi_handler.midi_out:
                self.midi_handler.send_stop()

            self._stop_playback()

        # Clear all live MIDI voices
        self.voice_manager.clear_all()

        self._update_time_display()

        # Reset playhead to start
        if self.piano_roll:
            self.piano_roll.set_playhead_tick(0.0)

    def _on_record(self):
        """Toggle recording."""
        self.is_recording = not self.is_recording
        print(f"[REC] Recording: {'ON' if self.is_recording else 'OFF'}")

    def _find_measure_at_tick(self, tick: float, song) -> int:
        """Find which measure index contains the given tick."""
        if not song or not song.measure_metadata:
            # Fallback: use global time signature
            ticks_per_measure = song.tpqn * song.time_signature[0] * (4 / song.time_signature[1])
            return int(tick / ticks_per_measure)

        # Use measure_metadata for accurate boundaries
        for i, measure in enumerate(song.measure_metadata):
            if measure.start_tick <= tick < measure.start_tick + measure.length_ticks:
                return i

        # If beyond last measure, return last measure index
        if song.measure_metadata:
            return len(song.measure_metadata) - 1
        return 0

    def _get_measure_start_tick(self, measure_index: int, song) -> int:
        """Get the start tick of a measure."""
        if not song or not song.measure_metadata:
            # Fallback: use global time signature
            ticks_per_measure = song.tpqn * song.time_signature[0] * (4 / song.time_signature[1])
            return measure_index * ticks_per_measure

        # Use measure_metadata
        if 0 <= measure_index < len(song.measure_metadata):
            return song.measure_metadata[measure_index].start_tick

        return 0

    def _on_forward(self, first_press=False):
        """Skip backward to previous measure (MPK25 REW/CC115 mapped here).

        Args:
            first_press: True on initial button press, False for continuous hold actions
        """
        song = self.app_state.get_current_song()
        if not song:
            return

        # Find current measure
        current_measure_index = self._find_measure_at_tick(self.current_tick, song)
        current_measure_start = self._get_measure_start_tick(current_measure_index, song)

        if self.is_playing:
            # During playback: first press snaps to current measure, hold continues to previous
            if first_press:
                # First press: always snap to current measure start
                new_tick = current_measure_start
            else:
                # Continuous hold: go to previous measure
                if current_measure_index > 0:
                    new_tick = self._get_measure_start_tick(current_measure_index - 1, song)
                else:
                    new_tick = 0  # Already at first measure
        else:
            # When stopped: use snap threshold for smart behavior
            SNAP_THRESHOLD = 10

            # If we're significantly past the measure start, snap to current measure start
            if self.current_tick - current_measure_start > SNAP_THRESHOLD:
                new_tick = current_measure_start
            else:
                # We're at (or very close to) the measure start, go to previous measure
                if current_measure_index > 0:
                    new_tick = self._get_measure_start_tick(current_measure_index - 1, song)
                else:
                    new_tick = 0  # Already at first measure

        # Clamp to valid range
        new_tick = max(0, new_tick)
        self.current_tick = new_tick

        # Update piano roll playhead
        if self.piano_roll:
            self.piano_roll.set_playhead_tick(new_tick)

        # If playing, also jump the scheduler position
        if self.is_playing:
            try:
                self.playhead_jump_queue.put_nowait(new_tick)
            except queue.Full:
                print("[TRANSPORT] Warning: Jump queue full, ignoring request")

        print(f"[TRANSPORT] Backward to tick {int(new_tick)}")

    def _on_backward(self, first_press=False):
        """Skip forward to next measure (MPK25 FF/CC116 mapped here).

        Args:
            first_press: True on initial button press, False for continuous hold actions
        """
        song = self.app_state.get_current_song()
        if not song:
            return

        # Find current measure
        current_measure_index = self._find_measure_at_tick(self.current_tick, song)
        current_measure_start = self._get_measure_start_tick(current_measure_index, song)

        if self.is_playing:
            # During playback: always go to next measure (both tap and hold)
            if not song.measure_metadata:
                # Fallback: calculate using global time signature
                ticks_per_measure = song.tpqn * song.time_signature[0] * (4 / song.time_signature[1])
                total_measures = int((song.length_ticks + ticks_per_measure - 1) / ticks_per_measure)

                if current_measure_index + 1 < total_measures:
                    new_tick = self._get_measure_start_tick(current_measure_index + 1, song)
                else:
                    new_tick = song.length_ticks  # At end
            else:
                # Use measure_metadata
                if current_measure_index + 1 < len(song.measure_metadata):
                    new_tick = song.measure_metadata[current_measure_index + 1].start_tick
                else:
                    new_tick = song.length_ticks  # At end
        else:
            # When stopped: always go to next measure (existing behavior)
            if not song.measure_metadata:
                # Fallback: calculate using global time signature
                ticks_per_measure = song.tpqn * song.time_signature[0] * (4 / song.time_signature[1])
                total_measures = int((song.length_ticks + ticks_per_measure - 1) / ticks_per_measure)

                if current_measure_index + 1 < total_measures:
                    new_tick = self._get_measure_start_tick(current_measure_index + 1, song)
                else:
                    new_tick = song.length_ticks  # At end
            else:
                # Use measure_metadata
                if current_measure_index + 1 < len(song.measure_metadata):
                    new_tick = song.measure_metadata[current_measure_index + 1].start_tick
                else:
                    new_tick = song.length_ticks  # At end

        # Clamp to valid range
        new_tick = min(new_tick, song.length_ticks)
        self.current_tick = new_tick

        # Update piano roll playhead
        if self.piano_roll:
            self.piano_roll.set_playhead_tick(new_tick)

        # If playing, also jump the scheduler position
        if self.is_playing:
            try:
                self.playhead_jump_queue.put_nowait(new_tick)
            except queue.Full:
                print("[TRANSPORT] Warning: Jump queue full, ignoring request")

        print(f"[TRANSPORT] Forward to tick {int(new_tick)}")

    def _process_control_event(self, event: dict):
        """
        Process MIDI control event (CC, MMC, Note, etc.).

        Two modes:
        1. Learn Mode: Capture event and create mapping
        2. Normal Mode: Check mappings and trigger functions
        """
        song = self.app_state.get_current_song()
        if not song:
            return

        # Learn Mode: Capture this message
        if self.midi_learn_active:
            self._capture_midi_learn(event)
            return

        # Normal Mode: Check mappings
        from core.models import MIDIControlMapping
        import time

        for mapping in song.midi_control_mappings:
            if mapping.matches_message(event):
                value = self._get_event_value(event)

                # For transport controls (forward/backward), track hold state
                if mapping.function in ['forward', 'backward']:
                    cc_num = event.get('controller', -1)
                    key = (mapping.function, cc_num)

                    if value >= mapping.trigger_threshold:
                        current_time = time.time()
                        # Button pressed or still held (repeated messages)
                        if key not in self.held_transport_buttons:
                            # First press - record timestamp and trigger immediate action
                            self.held_transport_buttons[key] = {
                                'pressed_time': current_time,
                                'last_action_time': current_time,
                                'last_message_time': current_time
                            }
                            # Trigger immediate first action
                            self._trigger_transport_function(mapping.function, first_press=True)
                            print(f"[MIDI CTRL] {mapping.function.upper()} pressed (ch {event.get('channel', 'omni')})")
                        else:
                            # Button still held - update last message time
                            self.held_transport_buttons[key]['last_message_time'] = current_time
                    else:
                        # Button released - clear hold state
                        if key in self.held_transport_buttons:
                            del self.held_transport_buttons[key]
                            print(f"[MIDI CTRL] {mapping.function.upper()} released")
                else:
                    # Non-transport controls: immediate trigger as before
                    if value >= mapping.trigger_threshold:
                        self._trigger_function(mapping.function)
                        print(f"[MIDI CTRL] {mapping.function.upper()} triggered by {event['type']} "
                              f"(ch {event.get('channel', 'omni')})")

    def _get_event_value(self, event: dict) -> int:
        """Extract value from event (for threshold check)."""
        if event['type'] == 'cc':
            return event.get('value', 0)
        elif event['type'] == 'note_on':
            return event.get('velocity', 0)
        elif event['type'] == 'mmc':
            return 127  # MMC always triggers (no velocity)
        elif event['type'] == 'program_change':
            return 127  # Program change always triggers
        return 0

    def _trigger_function(self, function: str):
        """Trigger a DAW function (play, stop, record, etc.)."""
        if function == 'play':
            self._on_play()
        elif function == 'stop':
            self._on_stop()
        elif function == 'record':
            self._on_record()
        elif function == 'forward':
            self._on_forward()
        elif function == 'backward':
            self._on_backward()
        else:
            print(f"[MIDI CTRL] Unknown function: {function}")

    def _trigger_transport_function(self, function: str, first_press: bool = False):
        """Trigger a transport function with first_press awareness.

        Args:
            function: 'forward' or 'backward'
            first_press: True on initial button press, False for continuous hold actions
        """
        if function == 'forward':
            self._on_forward(first_press=first_press)
        elif function == 'backward':
            self._on_backward(first_press=first_press)

    def _capture_midi_learn(self, event: dict):
        """Capture MIDI event in learn mode and create mapping."""
        import dataclasses
        from core.models import MIDIControlMapping

        self.last_midi_message = event

        # Create mapping from captured event
        mapping = self._create_mapping_from_event(
            function=self.midi_learn_function,
            event=event
        )

        # Add to song
        song = self.app_state.get_current_song()
        updated_mappings = list(song.midi_control_mappings) + [mapping]

        updated_song = dataclasses.replace(
            song,
            midi_control_mappings=tuple(updated_mappings)
        )

        self.app_state.set_current_song(updated_song)
        self.app_state.mark_dirty()

        # Exit learn mode
        self.midi_learn_active = False
        self.midi_learn_function = None

        print(f"[MIDI LEARN] Mapped {event['type']} to {mapping.function}")

        # Update UI to show mapping learned
        self._update_midi_learn_ui()

    def _create_mapping_from_event(self, function: str, event: dict):
        """Create a MIDIControlMapping from a captured event."""
        from core.models import MIDIControlMapping

        mapping_args = {
            'function': function,
            'message_type': event['type'],
            'channel': event.get('channel'),  # None = omni
        }

        if event['type'] == 'cc':
            mapping_args['cc_number'] = event['controller']
        elif event['type'] == 'note_on':
            mapping_args['note_number'] = event['note']
            mapping_args['message_type'] = 'note'  # Normalize to 'note'
        elif event['type'] == 'mmc':
            mapping_args['mmc_command'] = event['mmc_command']
        elif event['type'] == 'program_change':
            mapping_args['program_number'] = event['program']

        return MIDIControlMapping(**mapping_args)

    def _start_midi_learn(self, function: str):
        """Start MIDI learn mode for a function, or clear existing mapping."""
        import dataclasses

        song = self.app_state.get_current_song()
        if not song:
            return

        # Check if mapping already exists
        existing_mapping = next(
            (m for m in song.midi_control_mappings if m.function == function),
            None
        )

        if existing_mapping:
            # Clear existing mapping
            updated_mappings = [m for m in song.midi_control_mappings if m.function != function]
            updated_song = dataclasses.replace(
                song,
                midi_control_mappings=tuple(updated_mappings)
            )
            self.app_state.set_current_song(updated_song)
            self.app_state.mark_dirty()

            print(f"[MIDI LEARN] Cleared mapping for {function.upper()}")

            # Update UI
            self._update_midi_learn_ui()
        else:
            # Start learn mode
            self.midi_learn_active = True
            self.midi_learn_function = function

            print(f"[MIDI LEARN] Press a button/knob on your MIDI controller to map to {function.upper()}")

            # Visual feedback - highlight the learn button
            if dpg.does_item_exist(f"learn_{function}_button"):
                dpg.configure_item(f"learn_{function}_button", label="Listening...")

    def _update_midi_learn_ui(self):
        """Update UI to show current MIDI mappings."""
        song = self.app_state.get_current_song()
        if not song:
            return

        # For each transport function, show what's mapped
        for function in ['play', 'stop', 'record', 'forward', 'backward']:
            # Find mapping for this function
            mapping = next(
                (m for m in song.midi_control_mappings if m.function == function),
                None
            )

            # Update learn button label
            button_tag = f"learn_{function}_button"
            if dpg.does_item_exist(button_tag):
                if mapping:
                    label = self._get_mapping_label(mapping)
                    dpg.configure_item(button_tag, label=label)
                else:
                    dpg.configure_item(button_tag, label="Learn")

    def _get_mapping_label(self, mapping) -> str:
        """Get short label describing a mapping."""
        if mapping.message_type == 'cc':
            return f"CC{mapping.cc_number}"
        elif mapping.message_type == 'note':
            return f"Note{mapping.note_number}"
        elif mapping.message_type == 'mmc':
            return "MMC"
        elif mapping.message_type == 'program_change':
            return f"Prog{mapping.program_number}"
        return "Mapped"

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

        # Update song's loop_enabled flag
        song = self.app_state.get_current_song()
        if song:
            updated_song = dataclasses.replace(song, loop_enabled=value)
            self.app_state.set_current_song(updated_song)
            self.app_state._is_dirty = True

            # Update current_song_id to match the new song object
            self.current_song_id = id(updated_song)

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
                all_tracks_data=all_tracks_data,
                song=song
            )
        else:
            # Single track view - use channel color
            track = song.tracks[track_index]
            self.piano_roll.load_track_notes(
                track_index=track_index,
                notes=list(track.notes),
                track_color=self.track_colors[track_index],
                song=song
            )

            # Load synth UI for selected track
            self._refresh_sound_designer_ui(track_index, track)

        # Mark Piano Roll notes as belonging to this project (prevents cross-project pollution)
        self.current_song_id = id(song)

        # Load loop markers from song
        if song and self.piano_roll:
            # If no loop_end_tick is set, default to full track length
            loop_end = song.loop_end_tick if song.loop_end_tick is not None else song.length_ticks

            self.piano_roll.loop_start_tick = song.loop_start_tick
            self.piano_roll.loop_end_tick = loop_end

            # Update loop toggle and sync is_looping state
            self.is_looping = song.loop_enabled
            if dpg.does_item_exist("daw_loop_toggle"):
                dpg.set_value("daw_loop_toggle", song.loop_enabled)

        # Update MIDI learn UI to show current mappings
        self._update_midi_learn_ui()

        # Initialize MIDI handler for MIDI Learn (if not already done)
        if initial_load:
            self._ensure_midi_handler_initialized()
            # Clear synth cache when loading new project
            self._clear_track_synth_cache()

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

    def _ensure_midi_handler_initialized(self):
        """
        Initialize MIDI handler if not already done.

        Called after song is loaded, ensuring MIDI Learn works without starting playback.
        Respects song settings (receive_midi_clock, send_midi_clock, track MIDI input).
        """
        song = self.app_state.get_current_song()
        if song and self.midi_handler is None:
            try:
                # Always initialize handler (gracefully handles missing devices)
                self.midi_handler = MIDIHandler()

                # Decide what to open based on song settings
                needs_midi_input = (
                    song.receive_midi_clock or
                    any(track.receive_midi_input for track in song.tracks) or
                    True  # Always open input for MIDI Learn
                )
                needs_midi_output = song.send_midi_clock

                if needs_midi_input:
                    # TODO: Make device configurable via settings
                    input_device = "Akai MPK25 0"
                    self.midi_handler.open_input(input_device)
                    if self.midi_handler.input_opened:
                        print(f"[MIDI INPUT] Opened for MIDI Learn and live notes: {input_device}")
                    else:
                        print(f"[MIDI INPUT] Failed to open: {input_device}")

                if needs_midi_output:
                    self.midi_handler.open_output()
                    if self.midi_handler.output_opened:
                        print("[MIDI OUTPUT] Opened for clock sync")

            except Exception as e:
                print(f"[MIDI] Failed to initialize: {e}")
                self.midi_handler = None

    def _start_playback(self):
        """Start audio playback thread."""
        # Ensure MIDI handler is initialized (safety check)
        self._ensure_midi_handler_initialized()

        if self.playback_thread is None or not self.playback_thread.is_alive():
            self.playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
            self.playback_thread.start()

    def _stop_playback(self):
        """Stop audio playback thread."""
        # Thread will exit when it sees is_playing is False
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=1.0)

        # Note: Keep MIDI handler open for MIDI Learn and transport control
        # It will be closed when the DAW closes (if needed)

    def _process_midi_event(self, event, current_tick, song):
        """
        Route MIDI events to appropriate tracks based on channel and note range.

        Args:
            event: MIDI event dictionary from note_event_queue
            current_tick: Current playback tick position
            song: Current song object
        """
        channel = event['channel']  # 0-15 (0-indexed)
        event_type = event['type']

        # Find tracks listening on this channel with MIDI input enabled
        for track_idx, track in enumerate(song.tracks):
            if not track.receive_midi_input:
                continue

            if track.midi_channel != channel:
                continue

            # Check note range filtering (for keyboard vs pads)
            if event_type in ['note_on', 'note_off']:
                note = event['note']
                if note < track.midi_note_min or note > track.midi_note_max:
                    continue

            # Process event based on type
            if event_type == 'note_on':
                velocity = event['velocity']
                if velocity > 0:
                    # Note On - add to active live notes
                    key = (track_idx, note)
                    self.active_live_notes[key] = {
                        'velocity': velocity,
                        'start_tick': current_tick
                    }
                    print(f"[MIDI IN] Ch {channel+1} | Note ON  {note} | Vel {velocity:3d} -> Track {track_idx}")

                    # Create voice in voice manager
                    track_synth = self._get_or_create_track_synth(track_idx)
                    if track_synth:
                        from plugins.base import ProcessContext
                        context = ProcessContext(
                            sample_rate=self.sample_rate,
                            bpm=self.current_bpm,
                            tpqn=480,
                            current_tick=int(current_tick)
                        )
                        self.voice_manager.note_on(
                            track_idx=track_idx,
                            note_num=note,
                            velocity=velocity,
                            synth=track_synth,
                            source_params=track.source_params,
                            context=context
                        )
                else:
                    # Note Off (velocity 0)
                    key = (track_idx, note)
                    if key in self.active_live_notes:
                        del self.active_live_notes[key]
                        print(f"[MIDI IN] Ch {channel+1} | Note OFF {note} -> Track {track_idx}")
                        # Trigger note_off in voice manager
                        self.voice_manager.note_off(track_idx, note)

            elif event_type == 'note_off':
                note = event['note']
                key = (track_idx, note)
                if key in self.active_live_notes:
                    del self.active_live_notes[key]
                    print(f"[MIDI IN] Ch {channel+1} | Note OFF {note} -> Track {track_idx}")
                    # Trigger note_off in voice manager
                    self.voice_manager.note_off(track_idx, note)

            elif event_type == 'channel_aftertouch':
                # Channel aftertouch - could modulate synth parameters
                pressure = event['pressure']
                print(f"[MIDI IN] Ch {channel+1} | Aftertouch {pressure:3d}")
                # TODO: Apply to all active notes on this track

            elif event_type == 'poly_aftertouch':
                # Polyphonic aftertouch - per-note pressure
                note = event['note']
                pressure = event['pressure']
                print(f"[MIDI IN] Ch {channel+1} | Poly AT Note {note} | Pressure {pressure:3d}")
                # TODO: Apply to specific note

            elif event_type == 'cc':
                cc_num = event['controller']
                cc_value = event['value']
                print(f"[MIDI IN] Ch {channel+1} | CC {cc_num:3d} = {cc_value:3d}")
                # TODO: Map to synth parameters

    def _playback_worker(self):
        """Worker thread with real-time note triggering (Blooper4-style)."""
        print("[PLAYBACK WORKER] Starting real-time playback...")

        try:
            # Get current song for tempo/measure metadata
            song = self.app_state.get_current_song()
            measure_metadata = song.measure_metadata if song else None

            # Create scheduler with per-measure tempo support
            scheduler = NoteScheduler(
                sample_rate=self.sample_rate,
                measure_metadata=measure_metadata,
                initial_tick=self.current_tick  # Start from UI playhead position
            )
            scheduler.bpm = self.bpm  # Fallback BPM if no measure_metadata
            print(f"[PLAYBACK] Starting from tick {int(self.current_tick)}")

            # Active voices (currently playing notes)
            active_voices = []

            def audio_callback(outdata, frames, time_info, status):
                """Called by sounddevice for each audio chunk (512 samples)."""
                nonlocal active_voices

                if not self.is_playing:
                    outdata[:] = 0
                    return

                # Check for incoming SPP messages
                song = self.app_state.get_current_song()
                if song and song.receive_midi_clock and self.midi_handler:
                    incoming_tick = self.midi_handler.get_spp_from_queue()
                    if incoming_tick is not None:
                        print(f"[MIDI SPP] Jumping to tick {incoming_tick}")

                        # Jump to received position
                        scheduler.current_tick = float(incoming_tick)

                        # Clear active voices to prevent audio bleeding
                        active_voices = []
                        self.voice_manager.clear_all()

                # Check for position jump requests from transport controls
                try:
                    jump_to_tick = self.playhead_jump_queue.get_nowait()
                    scheduler.current_tick = jump_to_tick
                    self.current_tick = jump_to_tick
                    print(f"[PLAYBACK] Jumped to tick {int(jump_to_tick)}")
                except queue.Empty:
                    pass

                # Process incoming MIDI note events
                if song and self.midi_handler and self.midi_handler.input_opened:
                    note_events = self.midi_handler.get_note_events()
                    for event in note_events:
                        self._process_midi_event(event, int(scheduler.current_tick), song)

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

                # === LOOP HANDLING ===
                looped_this_frame = False

                # Get effective loop end (default to song length if not set)
                loop_end_tick = song.loop_end_tick if song.loop_end_tick is not None else song.length_ticks

                # Debug: Print loop state every 100 frames to avoid spam
                if hasattr(self, '_loop_debug_counter'):
                    self._loop_debug_counter += 1
                else:
                    self._loop_debug_counter = 0

                if self._loop_debug_counter % 100 == 0:
                    print(f"[LOOP DEBUG] is_looping={self.is_looping}, song.loop_enabled={song.loop_enabled if song else None}, "
                          f"loop_start={song.loop_start_tick if song else None}, loop_end={song.loop_end_tick if song else None}, "
                          f"effective_loop_end={loop_end_tick}, curr_tick={int(curr_tick)}")

                if song and self.is_looping and song.loop_enabled and loop_end_tick:
                    if curr_tick >= loop_end_tick:
                        print(f"[LOOP] Looping back! curr_tick={int(curr_tick)} >= loop_end={loop_end_tick}")

                        # Calculate overshoot
                        overshoot_ticks = curr_tick - loop_end_tick

                        # Jump back to loop start
                        scheduler.current_tick = song.loop_start_tick + overshoot_ticks
                        curr_tick = scheduler.current_tick
                        looped_this_frame = True

                        # Clear active voices to prevent audio bleeding
                        active_voices = []
                        self.voice_manager.clear_all()

                        # Send MIDI SPP on loop jump
                        if song.send_midi_clock and self.midi_handler and self.midi_handler.midi_out:
                            try:
                                self.midi_handler.send_spp(int(scheduler.current_tick), scheduler.tpqn)
                            except Exception as e:
                                print(f"[MIDI] Error sending SPP: {e}")

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
                    should_trigger = False
                    if not looped_this_frame:
                        # Normal trigger check
                        if prev_tick <= note_tick < curr_tick:
                            should_trigger = True
                    else:
                        # If we looped, check segment from loop_start to curr_tick
                        loop_start = song.loop_start_tick
                        if loop_start <= note_tick < curr_tick:
                            should_trigger = True

                    if should_trigger:
                        # Generate full audio for this note using track's synth instance
                        track = song.tracks[track_idx]
                        track_synth = self._get_or_create_track_synth(track_idx)
                        if track_synth:
                            audio = track_synth.process(None, track.source_params, note, context)

                            triggered.append({
                                'audio': audio,
                                'position': 0,
                                'note': note,
                                'track_idx': track_idx,
                                'volume': mixer_strip.volume,
                                'pan': mixer_strip.pan
                            })
                        else:
                            # Skip if synth creation failed
                            continue

                active_voices.extend(triggered)

                # Initialize output buffers (stereo)
                output_left = np.zeros(frames, dtype=np.float32)
                output_right = np.zeros(frames, dtype=np.float32)

                # Render active live MIDI voices (from real-time input)
                live_left, live_right = self.voice_manager.render_frame(
                    frames=frames,
                    song=song,
                    mixer_strips=self.mixer_strips,
                    any_solo_active=any_solo_active
                )

                # Mix live voices into output buffers
                output_left[:] += live_left
                output_right[:] += live_right

                # Mix Piano Roll voices into output buffer (stereo)
                # (output buffers already initialized above with live notes mixed in)

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
                    # Use scheduler's actual elapsed time (tempo-aware) for time display
                    self.current_time = scheduler.elapsed_time
                    # Store tick position for accurate playhead visual positioning
                    self.current_tick = scheduler.current_tick
                    # Get current BPM at playhead position for display
                    self.current_bpm = scheduler.get_bpm_at_tick(scheduler.current_tick)

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

    def _get_or_create_track_synth(self, track_idx: int):
        """Get or create synth instance for track."""
        song = self.app_state.get_current_song()
        if not song or track_idx >= len(song.tracks):
            return None

        track = song.tracks[track_idx]

        # Check cache and validate source_type matches
        if track_idx in self.track_synths:
            cached = self.track_synths[track_idx]
            if cached['source_type'] == track.source_type:
                return cached['instance']
            else:
                # Source type changed, reset old instance
                cached['instance'].reset()

        # Create new instance from registry
        try:
            synth = self.plugin_registry.create_instance(track.source_type)
            self.track_synths[track_idx] = {
                'source_type': track.source_type,
                'instance': synth
            }
            return synth
        except Exception as e:
            print(f"[SYNTH ERROR] Failed to create {track.source_type}: {e}")
            # Fallback to DUAL_OSC
            synth = self.plugin_registry.create_instance("DUAL_OSC")
            self.track_synths[track_idx] = {
                'source_type': "DUAL_OSC",
                'instance': synth
            }
            return synth

    def _clear_track_synth_cache(self, track_idx=None):
        """Clear synth cache (all or specific track)."""
        if track_idx is not None:
            if track_idx in self.track_synths:
                self.track_synths[track_idx]['instance'].reset()
                del self.track_synths[track_idx]
        else:
            for cached in self.track_synths.values():
                cached['instance'].reset()
            self.track_synths.clear()

    def _get_synth_params(self):
        """
        DEPRECATED: Use track.source_params directly.

        This method reads global UI state and is no longer used.
        Kept for backward compatibility only.
        """
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
        # Process MIDI control events
        if self.midi_handler and self.midi_handler.input_opened:
            control_events = self.midi_handler.get_control_events()
            for event in control_events:
                self._process_control_event(event)

        # Handle held transport buttons for continuous actions
        import time
        current_time = time.time()

        # Timeout for auto-release if no messages received (handles controllers that don't send release)
        BUTTON_TIMEOUT = 0.2  # 200ms without messages = button released

        for key, state in list(self.held_transport_buttons.items()):
            function_name, cc_num = key
            time_since_last_message = current_time - state.get('last_message_time', state['pressed_time'])
            time_since_last_action = current_time - state['last_action_time']

            # Auto-release if no messages received for timeout period
            if time_since_last_message > BUTTON_TIMEOUT:
                del self.held_transport_buttons[key]
                print(f"[MIDI CTRL] {function_name.upper()} released (timeout)")
                continue

            # Only apply continuous action during playback
            if not self.is_playing:
                continue

            # Define timing thresholds
            HOLD_THRESHOLD = 0.25  # 250ms - button must be held this long before continuous actions start
            CONTINUOUS_INTERVAL = 0.05  # 50ms between jumps once continuous mode starts

            # Calculate time since initial button press
            time_since_press = current_time - state['pressed_time']

            # Only start continuous actions if button held longer than threshold
            if time_since_press >= HOLD_THRESHOLD:
                if time_since_last_action >= CONTINUOUS_INTERVAL:
                    # Trigger continuous action (not first press)
                    self._trigger_transport_function(function_name, first_press=False)
                    state['last_action_time'] = current_time

        # Update piano roll (for auto-resize)
        if self.piano_roll:
            self.piano_roll.update()

        # Update time display and playhead if playing
        if self.is_playing:
            self._update_time_display()

            # Update BPM display to show current tempo at playhead
            if dpg.does_item_exist("daw_bpm_input"):
                dpg.set_value("daw_bpm_input", int(self.current_bpm))

            # Update Piano Roll playhead (use tick position for accuracy with tempo changes)
            if self.piano_roll:
                self.piano_roll.set_playhead_tick(self.current_tick)

        # Check if mouse button is released to stop dragging
        if not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
            self.dragging_horizontal_splitter = False
            self.dragging_vertical_splitter = False
            self.dragging_mixer_splitter = False
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

        # Handle mixer splitter dragging (Main content / Mixer)
        if self.dragging_mixer_splitter and self.drag_start_pos:
            mouse_pos = dpg.get_mouse_pos()
            delta_y = mouse_pos[1] - self.drag_start_pos[1]

            # Update mixer height (drag DOWN = larger mixer, drag UP = smaller mixer)
            new_height = max(200, min(600, self.mixer_height - delta_y))
            if new_height != self.mixer_height:
                self.mixer_height = new_height

                # Update all elements that depend on mixer height
                dpg.configure_item("daw_mixer_window", height=self.mixer_height)
                dpg.configure_item("left_panel", height=-self.mixer_height-10)
                dpg.configure_item("vertical_splitter_visual", height=-self.mixer_height-10)
                dpg.configure_item("vertical_splitter_btn", height=-self.mixer_height-10)
                dpg.configure_item("sound_designer_panel", height=-self.mixer_height-10)

                self.drag_start_pos = mouse_pos

    def _create_test_track_with_changing_measures(self):
        """Create and load test track with changing time signatures and tempos."""
        from core.test_data import create_test_track_with_changing_measures

        test_song = create_test_track_with_changing_measures()
        self.app_state.set_current_song(test_song)

        # Update current_song_id to match the test song object
        self.current_song_id = id(test_song)

        # Update the view with the test song
        if self.current_track >= 0 and self.current_track < len(test_song.tracks):
            self._on_track_selected(self.current_track)
        else:
            # Default to first track
            self._on_track_selected(0)

        print("Test track loaded: 3/4@60bpm -> 4/4@120bpm -> 9/8@240bpm")

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
