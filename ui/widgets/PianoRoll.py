"""
Piano Roll - Grid-based MIDI note editor for Blooper5 (Redesigned)

Improvements based on user feedback:
- Color customization sidebar for live theme adjustment
- Thinner, more muted grid lines
- Smart note drawing (width = 2-4x height based on grid snap)
- Draw/Select tools (left-click draw, right-click select)
- Movable toolbar with note length, velocity, note mode
- Blooper4-inspired appearance
"""

import dearpygui.dearpygui as dpg
from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass, field, replace
from core.models import Note


@dataclass
class PianoRollTheme:
    """Customizable theme colors for Piano Roll"""
    bg_color: List[int] = field(default_factory=lambda: [15, 15, 18])
    bg_color_black_key: List[int] = field(default_factory=lambda: [12, 12, 15])
    grid_line_color: List[int] = field(default_factory=lambda: [25, 25, 28])  # Muted
    triplet_line_color: List[int] = field(default_factory=lambda: [18, 18, 21])  # Very muted
    measure_line_color: List[int] = field(default_factory=lambda: [60, 60, 70])  # Brighter but not too much
    row_divider_color: List[int] = field(default_factory=lambda: [20, 20, 23])  # Muted
    note_colors: List[List[int]] = field(default_factory=lambda: [
        [140, 70, 70],    # C0-B0: Dark red
        [150, 90, 60],    # C1-B1: Orange-brown
        [160, 140, 60],   # C2-B2: Yellow-brown
        [90, 160, 90],    # C3-B3: Green
        [60, 140, 180],   # C4-B4: Cyan
        [90, 90, 180],    # C5-B5: Blue
        [140, 90, 160],   # C6-B6: Purple
        [180, 90, 120],   # C7-B7: Pink
    ])
    selected_note_brightness: int = 50  # How much brighter selected notes are
    playhead_color: List[int] = field(default_factory=lambda: [255, 80, 80])
    grid_line_thickness: int = 1  # Thin lines


# Constants
TPQN = 480  # Ticks per quarter note
GRID_HEIGHT = 12  # Pixel height per MIDI note row


class PianoRoll:
    """Piano Roll editor with improved UX based on user feedback."""

    def __init__(self, width: int = 1000, height: int = 600, on_notes_changed: Optional[Callable] = None):
        self.width = width
        self.height = height
        self.on_notes_changed = on_notes_changed  # Callback for undo/redo snapshots

        # Theme (customizable)
        self.theme = PianoRollTheme()

        # Viewport/scrolling
        self.scroll_x = 0
        self.scroll_y = 60 * GRID_HEIGHT
        self.zoom_x = 0.5  # Default zoom shows quarter notes + triplets (quarter note = ~240px)
        self.zoom_y = 1.0  # Vertical zoom scale (0.5 to 3.0)

        # Tool state
        self.tool = "draw"  # "draw" or "select"
        self.note_mode = "held"  # "held" or "repeat"

        # Note drawing parameters
        self.current_velocity = 100  # Controlled by velocity slider
        self.grid_snap = TPQN  # Current snap value (1/4 note by default)
        self.note_length_beats = 1.0  # Default note length in beats

        # Editing state
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.ghost_note: Optional[Dict[str, Any]] = None
        self.selected_notes: List[Note] = []

        # Playback
        self.current_tick = 0

        # Mock song data
        self.song_length_ticks = TPQN * 4 * 1  # 1 bar (4 beats)
        self.notes: List[Note] = []  # Empty by default (populated when track loads)

        # Track-aware display
        self.current_track_index = 0  # 0-15 for single track, 16 for master
        self.is_arrangement_view = False
        self.all_tracks_data = []  # List of {notes, color} dicts

        # DearPyGui IDs
        self.window_id = None
        self.canvas_id = None
        self.drawlist_id = None
        self.toolbar_window_id = None
        self.color_sidebar_id = None

    def load_notes(self, notes: List[Note]):
        """
        Load notes from Song model.

        Args:
            notes: List of Note objects to load
        """
        self.notes = list(notes)  # Make a copy
        if self.drawlist_id:
            self.draw()

    def get_notes(self) -> List[Note]:
        """
        Get current notes for saving to Song model.

        Returns:
            List of Note objects (deselected for saving)
        """
        # Deselect all notes before saving
        return [replace(note, selected=False) for note in self.notes]

    def clear_notes(self):
        """Clear all notes (used for new project)."""
        self.notes = []
        if self.drawlist_id:
            self.draw()

    def load_track_notes(self,
                         track_index: int,
                         notes: List[Note] = None,
                         track_color: Tuple[int, int, int, int] = None,
                         all_tracks_data: List[dict] = None):
        """
        Load notes for selected track or arrangement view.

        Args:
            track_index: 0-15 for single track, 16 for master/arrangement
            notes: Notes for single track mode
            track_color: RGBA color for single track
            all_tracks_data: List of {notes, color} for arrangement view
        """
        self.current_track_index = track_index
        self.is_arrangement_view = (track_index == 16)

        if self.is_arrangement_view:
            self.all_tracks_data = all_tracks_data or []
            self.notes = []  # Clear single track notes
            self._current_track_color = None
        else:
            self.notes = notes or []
            self.all_tracks_data = []
            self._current_track_color = track_color  # Store for drawing

        if self.drawlist_id:
            self.draw()

    def set_playhead_time(self, time_seconds: float, bpm: float):
        """
        Update playhead position (throttled for performance).

        Args:
            time_seconds: Current playback time in seconds
            bpm: Current tempo in BPM
        """
        # Convert seconds to ticks (assuming 4/4 time signature)
        beats = (time_seconds / 60.0) * bpm
        new_tick = int(beats * TPQN)

        # Only redraw if playhead moved significantly (reduce CPU usage)
        # Update every 20 ticks (~40ms at 120 BPM) for smooth but efficient playback
        if not hasattr(self, '_last_playhead_tick'):
            self._last_playhead_tick = -1

        if abs(new_tick - self._last_playhead_tick) >= 20:
            self.current_tick = new_tick
            self._last_playhead_tick = new_tick
            if self.drawlist_id:
                self._draw_playhead_only()

    def get_coords(self, tick: float, pitch: int) -> Tuple[float, float]:
        """Convert tick/pitch to screen coordinates."""
        x = (tick - self.scroll_x) * self.zoom_x
        y = (127 - pitch) * GRID_HEIGHT * self.zoom_y - self.scroll_y
        return x, y

    def get_pitch_at(self, y: float) -> int:
        """Convert screen Y coordinate to MIDI pitch."""
        relative_y = y + self.scroll_y
        pitch = 127 - int(relative_y / (GRID_HEIGHT * self.zoom_y))
        return max(0, min(127, pitch))

    def get_tick_at(self, x: float) -> float:
        """Convert screen X coordinate to tick position."""
        tick = x / self.zoom_x + self.scroll_x
        return max(0.0, tick)

    def snap_to_grid(self, tick: float) -> float:
        """Snap tick value to current grid."""
        return round(tick / self.grid_snap) * self.grid_snap

    def _get_grid_spacing(self) -> Tuple[int, int]:
        """Calculate grid spacing based on zoom level."""
        if self.zoom_x < 0.25:
            grid_spacing = TPQN * 4
        elif self.zoom_x < 0.4:
            grid_spacing = TPQN * 2
        elif self.zoom_x < 0.7:
            grid_spacing = TPQN
        elif self.zoom_x < 1.2:
            grid_spacing = TPQN // 2
        elif self.zoom_x < 2.0:
            grid_spacing = TPQN // 4
        elif self.zoom_x < 3.5:
            grid_spacing = TPQN // 8
        else:
            grid_spacing = TPQN // 16

        self.grid_snap = grid_spacing  # Update snap value
        triplet_spacing = grid_spacing // 3
        return grid_spacing, triplet_spacing

    def _calculate_note_width(self) -> float:
        """Calculate default note width: 2-4x note height based on current grid.

        At any grid scale, a note matching that grid duration will be ~3x height.
        """
        # Note height in pixels
        note_height = GRID_HEIGHT

        # Target: 3x height for notes matching current grid snap
        target_width_pixels = note_height * 3

        # What duration (in ticks) gives us that width?
        # width_pixels = duration_ticks * zoom_x
        # So: duration_ticks = width_pixels / zoom_x
        duration_ticks = target_width_pixels / self.zoom_x

        # Convert to beats
        self.note_length_beats = duration_ticks / TPQN

        return duration_ticks

    def draw(self):
        """Main draw function."""
        if not self.drawlist_id:
            return

        dpg.delete_item(self.drawlist_id, children_only=True)

        # Background
        dpg.draw_rectangle(
            (0, 0), (self.width, self.height),
            fill=tuple(self.theme.bg_color + [255]),
            parent=self.drawlist_id
        )

        self._draw_background_grid()
        self._draw_grid_lines()
        self._draw_row_dividers()
        self._draw_notes()
        self._draw_ghost_note()
        self._draw_playhead()

    def _draw_background_grid(self):
        """Draw alternating row backgrounds."""
        row_h = GRID_HEIGHT * self.zoom_y

        for pitch in range(128):
            x, y = self.get_coords(0, pitch)

            if -row_h <= y <= self.height:
                is_black_key = (pitch % 12) in [1, 3, 6, 8, 10]
                bg = self.theme.bg_color_black_key if is_black_key else self.theme.bg_color

                dpg.draw_rectangle(
                    (0, y), (self.width, y + row_h),
                    fill=tuple(bg + [255]),
                    color=tuple(bg + [255]),  # Match border to fill (invisible border)
                    parent=self.drawlist_id
                )

    def _draw_grid_lines(self):
        """Draw vertical grid lines (thin and muted)."""
        grid_spacing, triplet_spacing = self._get_grid_spacing()
        measure_spacing = TPQN * 4

        # Triplet lines (very faint)
        for t in range(0, self.song_length_ticks, triplet_spacing):
            if t % grid_spacing == 0 or t % measure_spacing == 0:
                continue
            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=tuple(self.theme.triplet_line_color + [255]),
                    thickness=self.theme.grid_line_thickness,
                    parent=self.drawlist_id
                )

        # Binary grid lines (muted)
        for t in range(0, self.song_length_ticks, grid_spacing):
            if t % measure_spacing == 0:
                continue
            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=tuple(self.theme.grid_line_color + [255]),
                    thickness=self.theme.grid_line_thickness,
                    parent=self.drawlist_id
                )

        # Measure lines (brighter, slightly thicker)
        for bar in range(0, self.song_length_ticks // measure_spacing + 1):
            t = bar * measure_spacing
            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=tuple(self.theme.measure_line_color + [255]),
                    thickness=2,
                    parent=self.drawlist_id
                )

    def _draw_row_dividers(self):
        """Draw horizontal row dividers (drawn AFTER vertical lines to appear on top)."""
        row_h = GRID_HEIGHT * self.zoom_y

        for pitch in range(128):
            x, y = self.get_coords(0, pitch)

            if -row_h <= y <= self.height:
                # Draw horizontal line at the top of each row
                dpg.draw_line(
                    (0, y), (self.width, y),
                    color=tuple(self.theme.row_divider_color + [255]),
                    thickness=1,
                    parent=self.drawlist_id
                )

    def _draw_notes(self):
        """Draw all notes (single track or arrangement view)."""
        if self.is_arrangement_view:
            # Arrangement view: draw all tracks with channel colors
            for track_data in self.all_tracks_data:
                self._draw_track_notes(
                    track_data['notes'],
                    track_data['color'],
                    alpha=220  # Slight transparency
                )
        else:
            # Single track: use channel color with octave brightness
            # Get track color from load_track_notes (stored during load)
            track_color = getattr(self, '_current_track_color', None)
            if track_color:
                self._draw_track_notes(self.notes, color=track_color, alpha=255)
            else:
                # Fallback to octave colors if no track color set
                self._draw_track_notes(self.notes, use_octave_colors=True)

    def _draw_track_notes(self, notes: List[Note],
                          color: Tuple[int, int, int, int] = None,
                          use_octave_colors: bool = False,
                          alpha: int = 255):
        """
        Draw notes for a single track.

        Args:
            notes: List of Note objects
            color: RGBA color (used if use_octave_colors=False)
            use_octave_colors: Use theme octave colors instead of channel color
            alpha: Transparency (0-255)
        """
        row_h = GRID_HEIGHT * self.zoom_y

        notes_drawn = 0
        for note in notes:
            if note.start * TPQN >= self.song_length_ticks:
                continue

            nx, ny = self.get_coords(note.start * TPQN, note.note)
            nw = note.duration * TPQN * self.zoom_x

            # Viewport culling
            if nx + nw < 0 or nx > self.width:
                continue
            if ny + row_h < 0 or ny > self.height:
                continue

            visible_x = max(0, nx)
            visible_width = min(nw, self.width - visible_x)

            # Determine color
            if use_octave_colors:
                octave = min(note.note // 12, len(self.theme.note_colors) - 1)
                note_color = self.theme.note_colors[octave]
                if note.selected:
                    note_color = [min(c + self.theme.selected_note_brightness, 255)
                                for c in note_color]
            else:
                # Use channel color with octave-based lightness
                # Octave 0 (lowest) = almost black, Octave 10 (highest) = almost white
                import colorsys
                octave = min(note.note // 12, 10)

                # Convert channel color to HSV
                r, g, b = color[0] / 255.0, color[1] / 255.0, color[2] / 255.0
                h, s, v = colorsys.rgb_to_hsv(r, g, b)

                # Map octave to value (brightness): 0 -> 0.15, 10 -> 0.95
                v = 0.15 + (octave / 10.0) * 0.80

                # Keep saturation but slightly reduce for very dark/light notes
                if v < 0.3:
                    s = s * 0.7  # Desaturate dark notes
                elif v > 0.85:
                    s = s * 0.6  # Desaturate bright notes

                # Convert back to RGB
                r, g, b = colorsys.hsv_to_rgb(h, s, v)
                note_color = [int(r * 255), int(g * 255), int(b * 255)]

                if note.selected:
                    note_color = [min(c + 50, 255) for c in note_color]

            # Apply alpha
            note_color_with_alpha = tuple(note_color + [alpha])

            # Draw note rectangle
            dpg.draw_rectangle(
                (visible_x, ny + 1),
                (visible_x + visible_width - 1, ny + row_h - 2),
                fill=note_color_with_alpha,
                color=note_color_with_alpha,
                thickness=1,
                parent=self.drawlist_id
            )

            # Draw outline for clarity (especially in arrangement view)
            if not use_octave_colors:
                outline_color = tuple([min(c + 40, 255) for c in note_color] + [255])
                dpg.draw_rectangle(
                    (visible_x, ny + 1),
                    (visible_x + visible_width - 1, ny + row_h - 2),
                    color=outline_color,
                    thickness=1,
                    parent=self.drawlist_id
                )

            # Velocity indicator (vertical bar on right side)
            # Height of bar represents velocity (0-127 mapped to note height)
            vel_bar_width = 4  # Pixels wide
            vel_ratio = note.velocity / 127.0  # 0.0 to 1.0
            vel_bar_height = row_h * vel_ratio  # Height based on velocity

            # Position on right side of note
            vel_x_right = visible_x + visible_width - vel_bar_width - 1
            vel_y_bottom = ny + row_h - 2  # Bottom of note
            vel_y_top = vel_y_bottom - vel_bar_height  # Top of velocity bar

            # Color: brighter version of note color
            vel_color = tuple([min(c + 60, 255) for c in note_color] + [220])

            # Only draw if bar is visible and has width
            if vel_bar_width > 0 and vel_bar_height > 1:
                dpg.draw_rectangle(
                    (vel_x_right, vel_y_top),
                    (vel_x_right + vel_bar_width, vel_y_bottom),
                    fill=vel_color,
                    color=vel_color,
                    parent=self.drawlist_id
                )

            notes_drawn += 1

    def _draw_ghost_note(self):
        """Draw preview note during drawing."""
        if not self.ghost_note:
            return

        row_h = GRID_HEIGHT * self.zoom_y
        gx, gy = self.get_coords(self.ghost_note['tick'], self.ghost_note['pitch'])
        gw = self.ghost_note['duration'] * self.zoom_x

        if 0 <= gx <= self.width:
            dpg.draw_rectangle(
                (gx, gy + 1),
                (gx + gw - 1, gy + row_h - 2),
                fill=(100, 100, 100, 100),
                color=(150, 150, 150, 150),
                thickness=1,
                parent=self.drawlist_id
            )

    def _draw_playhead(self):
        """Draw playback position on main canvas."""
        if self.current_tick > 0:
            px, _ = self.get_coords(self.current_tick, 0)
            if 0 <= px <= self.width:
                # Store playhead item tag for efficient updates
                playhead_tag = f"playhead_line_{id(self)}"
                dpg.draw_line(
                    (px, 0), (px, self.height),
                    color=tuple(self.theme.playhead_color + [255]),
                    thickness=2,
                    parent=self.drawlist_id,
                    tag=playhead_tag
                )

    def _draw_playhead_only(self):
        """Redraw just the playhead (optimized for playback)."""
        if not self.drawlist_id:
            return

        # Delete previous playhead if it exists
        playhead_tag = f"playhead_line_{id(self)}"
        if dpg.does_item_exist(playhead_tag):
            dpg.delete_item(playhead_tag)

        # Draw new playhead
        if self.current_tick > 0:
            px, _ = self.get_coords(self.current_tick, 0)
            if 0 <= px <= self.width:
                dpg.draw_line(
                    (px, 0), (px, self.height),
                    color=tuple(self.theme.playhead_color + [255]),
                    thickness=2,
                    parent=self.drawlist_id,
                    tag=playhead_tag
                )

    def _handle_canvas_click(self, sender, app_data):
        """Handle left-click on canvas (draw mode): delete if note exists, otherwise draw new note."""
        if self.tool != "draw":
            return

        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Convert to pitch and tick
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)
        snapped_tick = self.snap_to_grid(tick)

        # Check if a note already exists at this position
        for i, note in enumerate(self.notes):
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and
                note_start_tick <= tick <= note_end_tick):
                # Note exists at this position - DELETE IT
                # Take snapshot before modifying (for undo)
                if self.on_notes_changed:
                    self.on_notes_changed()

                self.notes.pop(i)
                self.draw()
                return

        # No note at this position - CREATE NEW NOTE
        # Calculate note duration based on current grid
        duration_ticks = self._calculate_note_width()

        new_note = Note(
            note=pitch,
            start=snapped_tick / TPQN,
            duration=self.note_length_beats,
            velocity=self.current_velocity,
            selected=False
        )

        # Take snapshot before modifying (for undo)
        if self.on_notes_changed:
            self.on_notes_changed()

        self.notes.append(new_note)
        self.draw()

    def _handle_canvas_right_click(self, sender, app_data):
        """Handle right-click on canvas (select mode)."""
        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Find note under cursor
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)

        # Check if we clicked on a note
        for i, note in enumerate(self.notes):
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and
                note_start_tick <= tick <= note_end_tick):
                # Replace note with toggled selection (Note is immutable)
                self.notes[i] = replace(note, selected=not note.selected)
                self.draw()
                return

    def _handle_drag_start(self, sender, app_data):
        """Called when user starts dragging."""
        # Get mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Find note under cursor
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)

        for i, note in enumerate(self.notes):
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and note_start_tick <= tick <= note_end_tick):
                # Take snapshot before modifying (for undo)
                if self.on_notes_changed:
                    self.on_notes_changed()

                self.is_dragging = True
                self.drag_start_pos = (tick, pitch)
                # Store index instead of note object (Note is immutable)
                self.ghost_note = {"index": i, "orig_start": note.start, "orig_pitch": note.note}
                # Select the note being dragged
                self.notes[i] = replace(note, selected=True)
                break

    def _handle_drag(self, sender, app_data):
        """Called while dragging."""
        if not self.is_dragging or self.ghost_note is None:
            return

        # Get current mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Convert to pitch and tick
        new_pitch = self.get_pitch_at(mouse_y)
        new_tick = self.get_tick_at(mouse_x)
        snapped_tick = self.snap_to_grid(new_tick)

        # Update note position (Note is immutable, so create new one)
        note_index = self.ghost_note["index"]
        old_note = self.notes[note_index]
        self.notes[note_index] = replace(old_note, note=new_pitch, start=snapped_tick / TPQN)

        # Redraw
        self.draw()

    def _handle_drag_end(self, sender, app_data):
        """Called when drag ends."""
        if self.is_dragging:
            self.is_dragging = False
            self.drag_start_pos = None
            self.ghost_note = None
            self.draw()

    def zoom_in(self):
        """Zoom in horizontally."""
        self.zoom_x = min(self.zoom_x * 1.2, 0.5)  # Max: ~240px per quarter note
        self.draw()

    def zoom_out(self):
        """Zoom out horizontally."""
        self.zoom_x = max(self.zoom_x / 1.2, 0.01)  # Min: ~5px per quarter note
        self.draw()

    def zoom_in_vertical(self):
        """Zoom in vertically (taller notes)."""
        self.zoom_y = min(self.zoom_y * 1.2, 3.0)  # Max: 36px per note
        self.draw()

    def zoom_out_vertical(self):
        """Zoom out vertically (shorter notes)."""
        self.zoom_y = max(self.zoom_y / 1.2, 0.5)  # Min: 6px per note
        self.draw()

    def _check_modifier(self, required: str, shift: bool, ctrl: bool, alt: bool) -> bool:
        """Check if the required modifier matches current key states."""
        if required == "none":
            return not (shift or ctrl or alt)
        if required == "shift":
            return shift and not ctrl and not alt
        if required == "ctrl":
            return ctrl and not shift and not alt
        if required == "alt":
            return alt and not shift and not ctrl
        if required == "ctrl+shift":
            return ctrl and shift and not alt
        if required == "ctrl+alt":
            return ctrl and alt and not shift
        if required == "shift+alt":
            return shift and alt and not ctrl
        return False

    def _load_wheel_settings(self) -> dict:
        """Load mouse wheel modifier settings from settings file."""
        import json
        from pathlib import Path

        settings_path = Path.home() / ".blooper5" / "settings.json"
        if settings_path.exists():
            try:
                with open(settings_path, 'r') as f:
                    settings = json.load(f)
                    return settings.get("piano_roll", {
                        "vertical_scroll_modifier": "none",
                        "horizontal_scroll_modifier": "shift",
                        "horizontal_zoom_modifier": "ctrl",
                        "vertical_zoom_modifier": "alt"
                    })
            except (json.JSONDecodeError, IOError):
                pass
        # Return defaults
        return {
            "vertical_scroll_modifier": "none",
            "horizontal_scroll_modifier": "shift",
            "horizontal_zoom_modifier": "ctrl",
            "vertical_zoom_modifier": "ctrl+shift"
        }

    def _handle_mouse_wheel(self, sender, app_data):
        """Handle mouse wheel with configurable modifiers."""
        scroll_delta = app_data  # Positive = scroll up, negative = scroll down

        # Get current modifier states
        shift_held = dpg.is_key_down(dpg.mvKey_Shift)
        ctrl_held = dpg.is_key_down(dpg.mvKey_Control)
        alt_held = dpg.is_key_down(dpg.mvKey_Alt)

        # Load settings
        settings = self._load_wheel_settings()

        # Determine action based on modifiers (check in priority order)
        if self._check_modifier(settings["vertical_zoom_modifier"],
                               shift_held, ctrl_held, alt_held):
            if scroll_delta > 0:
                self.zoom_in_vertical()
            else:
                self.zoom_out_vertical()

        elif self._check_modifier(settings["horizontal_zoom_modifier"],
                                 shift_held, ctrl_held, alt_held):
            if scroll_delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()

        elif self._check_modifier(settings["horizontal_scroll_modifier"],
                                 shift_held, ctrl_held, alt_held):
            self.scroll_x -= scroll_delta * 50
            self.scroll_x = max(0, self.scroll_x)
            self.draw()

        elif self._check_modifier(settings["vertical_scroll_modifier"],
                                 shift_held, ctrl_held, alt_held):
            scroll_speed = int(GRID_HEIGHT * self.zoom_y * 3)
            self.scroll_y -= scroll_delta * scroll_speed
            max_scroll = 128 * GRID_HEIGHT * self.zoom_y
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))
            self.draw()

    def _create_color_sidebar_inline(self):
        """Create inline color customization sidebar."""
        dpg.add_text("Color Customization", color=(255, 255, 100))
        dpg.add_separator()

        # Debug display
        self.debug_text = dpg.add_text("Last update: None", color=(200, 200, 200))
        dpg.add_separator()

        # Background colors
        dpg.add_text("Background Colors:")
        dpg.add_color_edit(
            label="BG Color",
            default_value=self.theme.bg_color + [255],
            callback=lambda s, v: self._update_theme_color('bg_color', v[:3]),
            no_alpha=True
        )
        dpg.add_color_edit(
            label="Black Key BG",
            default_value=self.theme.bg_color_black_key + [255],
            callback=lambda s, v: self._update_theme_color('bg_color_black_key', v[:3]),
            no_alpha=True
        )

        dpg.add_separator()
        dpg.add_text("Vertical Grid Lines:")
        dpg.add_color_edit(
            label="Grid Lines",
            default_value=self.theme.grid_line_color + [255],
            callback=lambda s, v: self._update_theme_color('grid_line_color', v),
            no_alpha=True
        )
        dpg.add_color_edit(
            label="Triplet Lines",
            default_value=self.theme.triplet_line_color + [255],
            callback=lambda s, v: self._update_theme_color('triplet_line_color', v),
            no_alpha=True
        )
        dpg.add_color_edit(
            label="Measure Lines",
            default_value=self.theme.measure_line_color + [255],
            callback=lambda s, v: self._update_theme_color('measure_line_color', v),
            no_alpha=True
        )

        dpg.add_separator()
        dpg.add_text("Horizontal Row Lines:")
        dpg.add_color_edit(
            label="Row Dividers",
            default_value=self.theme.row_divider_color + [255],
            callback=lambda s, v: self._update_theme_color('row_divider_color', v),
            no_alpha=True
        )

        dpg.add_separator()
        dpg.add_text("Other:")
        dpg.add_color_edit(
            label="Playhead",
            default_value=self.theme.playhead_color + [255],
            callback=lambda s, v: self._update_theme_color('playhead_color', v),
            no_alpha=True
        )

        dpg.add_separator()
        dpg.add_button(label="Reset to Blooper4 Theme", callback=self._reset_theme)

    def _create_color_sidebar(self):
        """DEPRECATED: Use _create_color_sidebar_inline() instead."""
        pass

    def _update_theme_color(self, attr: str, color: List[int]):
        """Update theme color and redraw."""
        # DearPyGui color pickers return floats in 0.0-1.0 range
        # Convert to integers in 0-255 range
        rgb_color = [int(c * 255) for c in color[:3]]
        setattr(self.theme, attr, rgb_color)

        # Update debug display
        if hasattr(self, 'debug_text') and dpg.does_item_exist(self.debug_text):
            dpg.set_value(self.debug_text, f"Last update: {attr} = {rgb_color}")

        self.draw()

    def _reset_theme(self):
        """Reset to default Blooper4-inspired theme."""
        self.theme = PianoRollTheme()
        self.draw()

    def _create_toolbar_inline(self):
        """Create inline toolbar with note controls."""
        with dpg.child_window(height=120, border=True):
            with dpg.group(horizontal=True):
                # Tool selection
                dpg.add_text("Tool:")
                dpg.add_radio_button(
                    items=["Draw (Left-click)", "Select (Right-click always selects)"],
                    default_value="Draw (Left-click)",
                    callback=lambda s, v: setattr(self, 'tool', 'draw' if 'Draw' in v else 'select'),
                    horizontal=True
                )

            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Note mode
                dpg.add_text("Note Mode:")
                dpg.add_radio_button(
                    items=["Held Note", "Note Repeat"],
                    default_value="Held Note",
                    callback=lambda s, v: setattr(self, 'note_mode', 'held' if 'Held' in v else 'repeat'),
                    horizontal=True
                )

            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Velocity control
                dpg.add_text("Velocity:")
                dpg.add_slider_int(
                    default_value=self.current_velocity,
                    min_value=1,
                    max_value=127,
                    callback=lambda s, v: setattr(self, 'current_velocity', v),
                    width=200
                )
                dpg.add_text("100", tag="velocity_display")

            with dpg.group(horizontal=True):
                # Note length info
                dpg.add_text("Note Length:")
                dpg.add_spacer(width=10)
                dpg.add_text("Auto (follows grid)", tag="note_length_display", color=(150, 255, 150))

    def _create_toolbar(self):
        """DEPRECATED: Use _create_toolbar_inline() instead."""
        pass

    def _create_toolbar_window(self, tag: str = "piano_roll_toolbar"):
        """Create separate dockable toolbar window for note controls."""
        with dpg.window(label="Note Controls", tag=tag,
                       no_close=True,
                       no_collapse=True,
                       width=800,
                       height=140):

            with dpg.group(horizontal=True):
                # Tool selection
                dpg.add_text("Tool:")
                dpg.add_radio_button(
                    items=["Draw (Left-click)", "Select (Right-click always selects)"],
                    default_value="Draw (Left-click)",
                    callback=lambda s, v: setattr(self, 'tool', 'draw' if 'Draw' in v else 'select'),
                    horizontal=True
                )

            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Note mode
                dpg.add_text("Note Mode:")
                dpg.add_radio_button(
                    items=["Held Note", "Note Repeat"],
                    default_value="Held Note",
                    callback=lambda s, v: setattr(self, 'note_mode', 'held' if 'Held' in v else 'repeat'),
                    horizontal=True
                )

            dpg.add_separator()

            with dpg.group(horizontal=True):
                # Velocity control
                dpg.add_text("Velocity:")
                dpg.add_slider_int(
                    default_value=self.current_velocity,
                    min_value=1,
                    max_value=127,
                    callback=lambda s, v: setattr(self, 'current_velocity', v),
                    width=200
                )
                dpg.add_text("100", tag="velocity_display")

            with dpg.group(horizontal=True):
                # Note length info
                dpg.add_text("Note Length:")
                dpg.add_spacer(width=10)
                dpg.add_text("Auto (follows grid)", tag="note_length_display", color=(150, 255, 150))

        self.toolbar_window_id = tag

    def create_inline(self, parent=None):
        """
        Create Piano Roll inline (embedded in current container).

        Args:
            parent: Parent container tag (optional)
        """
        # Tool info at top
        with dpg.group(horizontal=True):
            dpg.add_spacer(width=10)
            dpg.add_text("Left-click: Draw | Right-click: Select | Mouse wheel: Scroll/Zoom", color=(150, 150, 150))

        dpg.add_spacer(height=5)

        # Canvas for drawing notes
        self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
        self.drawlist_id = self.canvas_id

        # Mouse handlers for canvas
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self._handle_canvas_click)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self._handle_canvas_right_click)

        dpg.bind_item_handler_registry(self.canvas_id, handler)

        # Mouse wheel handler (window-level)
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self._handle_mouse_wheel)

        # Initial draw
        self.draw()

    def create_dockable(self, tag: str = "piano_roll_window", toolbar_tag: str = "piano_roll_toolbar", parent_docking_space=None):
        """
        Create dockable Piano Roll window (no theme controls - see Settings).

        Args:
            tag: Tag for Piano Roll window
            toolbar_tag: Tag for separate toolbar window
            parent_docking_space: Parent docking space (optional)
        """
        # Create main Piano Roll window
        with dpg.window(label="Piano Roll", tag=tag,
                       no_close=True,  # Prevent accidental close
                       no_collapse=True):  # Always show content

            # Tool info at top
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=10)
                dpg.add_text("Left-click: Draw | Right-click: Select | Mouse wheel: Scroll/Zoom", color=(150, 150, 150))

            dpg.add_spacer(height=5)

            # Canvas for drawing notes
            self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
            self.drawlist_id = self.canvas_id

            # Mouse handlers for canvas
            with dpg.item_handler_registry() as handler:
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self._handle_canvas_click)
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self._handle_canvas_right_click)

            dpg.bind_item_handler_registry(self.canvas_id, handler)

            # Mouse wheel handler (window-level)
            with dpg.handler_registry():
                dpg.add_mouse_wheel_handler(callback=self._handle_mouse_wheel)

        self.window_id = tag

        # Create separate dockable toolbar window
        self._create_toolbar_window(toolbar_tag)

        # Initial draw
        self.draw()

        # Note: DearPyGui windows are dockable by default
        # User can drag window tabs to dock/undock


def create_piano_roll_demo():
    """Demo function."""
    dpg.create_context()

    piano_roll = PianoRoll(width=1000, height=600)
    piano_roll.create_window()

    dpg.create_viewport(title="Blooper5 - Piano Roll (Redesigned)", width=1350, height=850)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    create_piano_roll_demo()
