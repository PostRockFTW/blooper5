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
from core.models import Note, Song


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

    def __init__(self, width: int = 1000, height: int = 600, on_notes_changed: Optional[Callable] = None,
                 song: Optional[Song] = None):
        self.width = width
        self.height = height
        self.on_notes_changed = on_notes_changed  # Callback for undo/redo snapshots
        self.song = song  # Song reference for accessing time signature and measure metadata

        # Theme (customizable)
        self.theme = PianoRollTheme()

        # Viewport/scrolling
        self.scroll_x = 0
        self.scroll_y = 60 * GRID_HEIGHT
        self.zoom_x = 0.5  # Default zoom shows quarter notes + triplets (quarter note = ~240px)
        self.zoom_y = 1.0  # Vertical zoom scale (0.5 to 3.0)

        # Tool state (controlled by external NoteDrawToolbar)
        self.tool = "draw"  # "draw" or "select"
        self.note_mode = "held"  # "held" or "repeat"

        # Note drawing parameters (controlled by external NoteDrawToolbar)
        self.current_velocity = 100  # 1-127
        self.current_release_velocity = 64  # 0-127
        self.grid_snap = TPQN  # Current snap value (1/4 note by default)
        self.selected_quantization = TPQN  # Selected quantization from toolbar
        self.snap_enabled = True  # Grid snapping on/off
        self.note_length_beats = 1.0  # Default note length in beats

        # Editing state
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.ghost_note: Optional[Dict[str, Any]] = None
        self.selected_notes: List[Note] = []

        # Auto-resize tracking
        self._last_container_size = (0, 0)

        # Drawing drag state
        self.is_drawing_drag = False
        self.draw_drag_start_tick: Optional[int] = None
        self.draw_drag_start_pitch: Optional[int] = None
        self.draw_drag_notes: List[Note] = []  # Notes created during current drag

        # Erasing drag state
        self.is_erasing_drag = False
        self.erased_notes: set = set()  # Track note indices already erased

        # Bar selection state (for BarEditToolbar)
        self.bar_selection_mode = False
        self.selected_bar_start = None  # Bar index (0-based)
        self.selected_bar_end = None    # Bar index (inclusive, 0-based)
        self.on_bar_selection_changed = None  # Callback to notify toolbar

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

    def update_toolbar_state(self, toolbar_state: dict):
        """
        Update Piano Roll state from external NoteDrawToolbar.

        Args:
            toolbar_state: Dictionary with keys:
                - tool: 'draw', 'select', or 'erase'
                - note_mode: 'held' or 'repeat'
                - velocity: 1-127
                - snap_enabled: bool
                - quantize: '1/4', '1/8', etc.
        """
        self.tool = toolbar_state.get('tool', self.tool)
        self.note_mode = toolbar_state.get('note_mode', self.note_mode)
        self.current_velocity = toolbar_state.get('velocity', self.current_velocity)
        self.current_release_velocity = toolbar_state.get('release_velocity', self.current_release_velocity)
        self.snap_enabled = toolbar_state.get('snap_enabled', self.snap_enabled)

        # Store selected quantization from toolbar
        quantize = toolbar_state.get('quantize', '1/4')
        quant_map = {
            # Straight notes
            '1/4': TPQN,  # Quarter note
            '1/8': TPQN // 2,  # Eighth note
            '1/16': TPQN // 4,  # Sixteenth note
            '1/32': TPQN // 8,  # 32nd note
            '1/64': TPQN // 16,  # 64th note
            '1/128': TPQN // 32,  # 128th note
            # Triplets
            '1/4T': TPQN * 2 // 3,  # Quarter note triplet (320 ticks)
            '1/8T': TPQN // 3,  # Eighth note triplet (160 ticks)
            '1/16T': TPQN // 6,  # Sixteenth note triplet (80 ticks)
            '1/32T': TPQN // 12,  # 32nd note triplet (40 ticks)
            '1/64T': TPQN // 24,  # 64th note triplet (20 ticks)
            '1/128T': TPQN // 48,  # 128th note triplet (10 ticks)
        }
        self.selected_quantization = quant_map.get(quantize, TPQN)

        # Update grid_snap using smart snap logic
        visual_grid = self._get_visual_grid_for_zoom()
        self.grid_snap = min(visual_grid, self.selected_quantization)

    def update_bar_edit_state(self, toolbar_state: dict):
        """
        Update Piano Roll state from external BarEditToolbar.

        Args:
            toolbar_state: Dictionary with keys:
                - selection_mode_enabled: bool
                - selected_bar_start: int or None
                - selected_bar_end: int or None
        """
        self.bar_selection_mode = toolbar_state.get('selection_mode_enabled', False)
        self.selected_bar_start = toolbar_state.get('selected_bar_start')
        self.selected_bar_end = toolbar_state.get('selected_bar_end')
        self.draw()  # Redraw to show selection highlight

    def _get_bar_at_tick(self, tick: float) -> int:
        """
        Get bar/measure index at tick position.

        Args:
            tick: Tick position

        Returns:
            Bar index (0-based)
        """
        if not self.song or not self.song.measure_metadata:
            # Fallback: use global time signature
            time_signature = self.song.time_signature if self.song else (4, 4)
            measure_spacing = self._get_measure_spacing(time_signature)
            return int(tick / measure_spacing)

        # Use measure_metadata for accurate bar boundaries
        for i, measure in enumerate(self.song.measure_metadata):
            if measure.start_tick <= tick < measure.start_tick + measure.length_ticks:
                return i

        # If tick is beyond last measure, return last measure index
        if self.song.measure_metadata:
            return len(self.song.measure_metadata) - 1
        return 0

    def _get_bar_tick_range(self, bar_index: int) -> Tuple[int, int]:
        """
        Get start and end ticks for a bar.

        Args:
            bar_index: Bar index (0-based)

        Returns:
            Tuple of (start_tick, end_tick)
        """
        if not self.song or not self.song.measure_metadata:
            # Fallback: use global time signature
            time_signature = self.song.time_signature if self.song else (4, 4)
            measure_spacing = self._get_measure_spacing(time_signature)
            start_tick = bar_index * measure_spacing
            end_tick = (bar_index + 1) * measure_spacing
            return start_tick, end_tick

        if 0 <= bar_index < len(self.song.measure_metadata):
            measure = self.song.measure_metadata[bar_index]
            return measure.start_tick, measure.start_tick + measure.length_ticks

        return 0, 0

    def _handle_bar_selection_click(self, mouse_x: float, mouse_y: float):
        """
        Handle click in bar selection mode.

        Args:
            mouse_x: Mouse X position (canvas-relative)
            mouse_y: Mouse Y position (canvas-relative)
        """
        tick = self.get_tick_at(mouse_x)
        clicked_bar = self._get_bar_at_tick(tick)

        # Update selection
        self.selected_bar_start = clicked_bar
        self.selected_bar_end = clicked_bar

        # Notify toolbar via callback
        if self.on_bar_selection_changed:
            self.on_bar_selection_changed(clicked_bar, clicked_bar)

        self.draw()

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
                         all_tracks_data: List[dict] = None,
                         song: Optional[Song] = None):
        """
        Load notes for selected track or arrangement view.

        Args:
            track_index: 0-15 for single track, 16 for master/arrangement
            notes: Notes for single track mode
            track_color: RGBA color for single track
            all_tracks_data: List of {notes, color} for arrangement view
            song: Song reference for accessing time signature and measure metadata
        """
        self.current_track_index = track_index
        self.is_arrangement_view = (track_index == 16)

        # Update song reference if provided
        if song is not None:
            self.song = song
            # FIX: Update song length to match the actual song
            self.song_length_ticks = song.length_ticks

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

    def set_playhead_tick(self, tick: float):
        """
        Update playhead position directly from tick value (tempo-aware).

        Args:
            tick: Current playback position in ticks
        """
        new_tick = int(tick)

        # Only redraw if playhead moved significantly (reduce CPU usage)
        # Update every 20 ticks (~40ms at 120 BPM) for smooth but efficient playback
        if not hasattr(self, '_last_playhead_tick'):
            self._last_playhead_tick = -1

        if abs(new_tick - self._last_playhead_tick) >= 20:
            self.current_tick = new_tick
            self._last_playhead_tick = new_tick
            if self.drawlist_id:
                self.draw()

    def set_playhead_time(self, time_seconds: float, bpm: float):
        """
        Update playhead position (legacy method - use set_playhead_tick for tempo changes).

        Args:
            time_seconds: Current playback time in seconds
            bpm: Current tempo in BPM
        """
        # Convert seconds to ticks (assuming constant tempo - not accurate with tempo changes)
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

    def update(self):
        """Update piano roll (called every frame by DAWView)."""
        # Check if container size changed and redraw if needed
        current_size = self._get_canvas_size()
        if current_size != self._last_container_size:
            self._last_container_size = current_size
            self.draw()

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
        """Snap tick value to current grid (snaps to left grid line)."""
        import math
        return math.floor(tick / self.grid_snap) * self.grid_snap

    def _get_visual_grid_for_zoom(self) -> int:
        """Calculate visual grid spacing based on zoom level."""
        if self.zoom_x < 0.25:
            return TPQN * 4
        elif self.zoom_x < 0.4:
            return TPQN * 2
        elif self.zoom_x < 0.7:
            return TPQN
        elif self.zoom_x < 1.2:
            return TPQN // 2
        elif self.zoom_x < 2.0:
            return TPQN // 4
        elif self.zoom_x < 3.5:
            return TPQN // 8
        else:
            return TPQN // 16

    def _get_grid_spacing(self) -> Tuple[int, int]:
        """Calculate grid spacing based on zoom level."""
        visual_grid = self._get_visual_grid_for_zoom()
        triplet_spacing = visual_grid // 3

        # Smart snap: use finer of visual grid or selected quantization
        self.grid_snap = min(visual_grid, self.selected_quantization)

        return visual_grid, triplet_spacing

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

    def _get_canvas_size(self) -> Tuple[int, int]:
        """Get current canvas size from container (for auto-resize support)."""
        if hasattr(self, '_canvas_container') and dpg.does_item_exist(self._canvas_container):
            rect = dpg.get_item_rect_size(self._canvas_container)
            if rect[0] > 0 and rect[1] > 0:  # Valid size
                return int(rect[0]), int(rect[1])
        return self.width, self.height

    def draw(self):
        """Main draw function."""
        if not self.drawlist_id:
            return

        # Get current canvas size from container (for auto-resize support)
        new_width, new_height = self._get_canvas_size()

        # Resize canvas if container size changed
        if new_width != self.width or new_height != self.height:
            self.width = new_width
            self.height = new_height
            if dpg.does_item_exist(self.canvas_id):
                dpg.configure_item(self.canvas_id, width=self.width, height=self.height)

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
        self._draw_bar_selection_highlight()  # Draw bar selection highlight
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

    def _get_measure_spacing(self, time_signature: Tuple[int, int]) -> int:
        """Calculate measure spacing in ticks based on time signature."""
        numerator, denominator = time_signature
        ticks_per_denominator_note = TPQN * (4 / denominator)
        measure_ticks = int(numerator * ticks_per_denominator_note)
        return measure_ticks

    def _get_measure_at_tick(self, tick: float):
        """Get the measure metadata for a given tick position."""
        if not self.song or not self.song.measure_metadata:
            return None

        for measure in self.song.measure_metadata:
            if measure.start_tick <= tick < measure.start_tick + measure.length_ticks:
                return measure

        return None

    def _get_time_signature_at_tick(self, tick: float) -> Tuple[int, int]:
        """Get time signature at a specific tick position."""
        measure = self._get_measure_at_tick(tick)
        if measure:
            return measure.time_signature

        # Fallback to global
        return self.song.time_signature if self.song else (4, 4)

    def _draw_grid_lines(self):
        """Draw vertical grid lines with per-measure time-signature-aware progressive simplification."""
        grid_spacing, triplet_spacing = self._get_grid_spacing()

        # Use per-measure metadata if available, otherwise fall back to global
        if self.song and self.song.measure_metadata:
            self._draw_grid_lines_per_measure(grid_spacing, triplet_spacing)
        else:
            self._draw_grid_lines_global(grid_spacing, triplet_spacing)

    def _draw_grid_lines_global(self, grid_spacing: int, triplet_spacing: int):
        """Draw grid lines using global time signature (legacy/fallback mode)."""
        time_signature = self.song.time_signature if self.song else (4, 4)
        measure_spacing = self._get_measure_spacing(time_signature)

        # Calculate denominator-adjusted visibility thresholds
        denominator = time_signature[1]
        denominator_scale = 4.0 / denominator

        SHOW_TRIPLETS_THRESHOLD = 0.25 * denominator_scale
        SHOW_GRID_THRESHOLD = 0.15 * denominator_scale

        # Triplet lines (very faint)
        if self.zoom_x >= SHOW_TRIPLETS_THRESHOLD:
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

        # Grid lines (muted)
        if self.zoom_x >= SHOW_GRID_THRESHOLD:
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

        # Measure lines (brighter)
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

    def _draw_grid_lines_per_measure(self, grid_spacing: int, triplet_spacing: int):
        """Draw grid lines with per-measure time signature awareness."""

        # Draw measure lines and grid/triplet lines for each measure
        for measure in self.song.measure_metadata:
            measure_start = measure.start_tick
            measure_end = measure.start_tick + measure.length_ticks

            # Draw measure line at start
            x, _ = self.get_coords(measure_start, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=tuple(self.theme.measure_line_color + [255]),
                    thickness=2,
                    parent=self.drawlist_id
                )

            # Calculate thresholds for this measure's denominator
            denominator = measure.time_signature[1]
            denominator_scale = 4.0 / denominator

            SHOW_TRIPLETS_THRESHOLD = 0.25 * denominator_scale
            SHOW_GRID_THRESHOLD = 0.15 * denominator_scale

            # Draw triplet lines within this measure
            if self.zoom_x >= SHOW_TRIPLETS_THRESHOLD:
                t = measure_start
                while t < measure_end:
                    if t % grid_spacing != 0 and t != measure_start:
                        x, _ = self.get_coords(t, 0)
                        if 0 <= x <= self.width:
                            dpg.draw_line(
                                (x, 0), (x, self.height),
                                color=tuple(self.theme.triplet_line_color + [255]),
                                thickness=self.theme.grid_line_thickness,
                                parent=self.drawlist_id
                            )
                    t += triplet_spacing

            # Draw grid lines within this measure
            if self.zoom_x >= SHOW_GRID_THRESHOLD:
                t = measure_start
                while t < measure_end:
                    if t != measure_start:  # Don't overlap measure line
                        x, _ = self.get_coords(t, 0)
                        if 0 <= x <= self.width:
                            dpg.draw_line(
                                (x, 0), (x, self.height),
                                color=tuple(self.theme.grid_line_color + [255]),
                                thickness=self.theme.grid_line_thickness,
                                parent=self.drawlist_id
                            )
                    t += grid_spacing

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

            # Calculate visible portion of note
            visible_x = max(0, nx)
            if nx < 0:
                # Note extends past left edge - adjust width to show only visible portion
                visible_width = min(nw + nx, self.width)  # nw + nx because nx is negative
            else:
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

            # Initial velocity indicator (vertical bar on LEFT side)
            vel_bar_width = 4  # Pixels wide
            vel_ratio = note.velocity / 127.0  # 0.0 to 1.0
            vel_bar_height = row_h * vel_ratio  # Height based on velocity

            # Position on LEFT side of note
            vel_x_left = visible_x + 1
            vel_y_bottom = ny + row_h - 2  # Bottom of note
            vel_y_top = vel_y_bottom - vel_bar_height  # Top of velocity bar

            # Color: brighter version of note color
            vel_color = tuple([min(c + 60, 255) for c in note_color] + [220])

            # Draw left (initial) velocity bar
            if vel_bar_width > 0 and vel_bar_height > 1:
                dpg.draw_rectangle(
                    (vel_x_left, vel_y_top),
                    (vel_x_left + vel_bar_width, vel_y_bottom),
                    fill=vel_color,
                    color=vel_color,
                    parent=self.drawlist_id
                )

            # Release velocity indicator (vertical bar on RIGHT side)
            rel_vel_ratio = note.release_velocity / 127.0
            rel_vel_bar_height = row_h * rel_vel_ratio

            # Position on RIGHT side of note
            rel_vel_x_right = visible_x + visible_width - vel_bar_width - 1
            rel_vel_y_bottom = ny + row_h - 2
            rel_vel_y_top = rel_vel_y_bottom - rel_vel_bar_height

            # Use same color scheme for consistency
            rel_vel_color = tuple([min(c + 60, 255) for c in note_color] + [220])

            # Draw right (release) velocity bar
            if vel_bar_width > 0 and rel_vel_bar_height > 1:
                dpg.draw_rectangle(
                    (rel_vel_x_right, rel_vel_y_top),
                    (rel_vel_x_right + vel_bar_width, rel_vel_y_bottom),
                    fill=rel_vel_color,
                    color=rel_vel_color,
                    parent=self.drawlist_id
                )

            notes_drawn += 1

    def _draw_bar_selection_highlight(self):
        """Draw semi-transparent highlight over selected bars."""
        if self.selected_bar_start is None:
            return

        start_bar = self.selected_bar_start
        end_bar = self.selected_bar_end if self.selected_bar_end is not None else start_bar

        # Draw highlight for each bar in selection
        for bar_index in range(start_bar, end_bar + 1):
            start_tick, end_tick = self._get_bar_tick_range(bar_index)

            x_start, _ = self.get_coords(start_tick, 0)
            x_end, _ = self.get_coords(end_tick, 0)

            # Clip to viewport
            visible_x_start = max(0, x_start)
            visible_x_end = min(self.width, x_end)

            if visible_x_start < visible_x_end:
                # Draw semi-transparent overlay
                dpg.draw_rectangle(
                    (visible_x_start, 0),
                    (visible_x_end, self.height),
                    fill=(100, 150, 255, 50),  # Light blue, semi-transparent
                    color=(100, 150, 255, 150),  # Border
                    thickness=2,
                    parent=self.drawlist_id
                )

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
        """Route left-click to appropriate handler based on current tool."""
        # Check for bar selection mode first (takes priority over other tools)
        if self.bar_selection_mode:
            # Get mouse position
            mouse_pos = dpg.get_mouse_pos(local=False)
            canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
            mouse_x = mouse_pos[0] - canvas_rect_min[0]
            mouse_y = mouse_pos[1] - canvas_rect_min[1]

            self._handle_bar_selection_click(mouse_x, mouse_y)
            return

        # Normal tool routing
        if self.tool == "draw":
            self._handle_draw_click(sender, app_data)
        elif self.tool == "erase":
            self._handle_erase_click(sender, app_data)
        elif self.tool == "select":
            self._handle_select_click(sender, app_data)

    def _handle_draw_click(self, sender, app_data):
        """Handle left-click in draw mode - Blooper4-style toggle (delete if exists, create if not)."""
        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Convert to pitch and tick
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)
        # Only snap if snap is enabled
        snapped_tick = self.snap_to_grid(tick) if self.snap_enabled else tick

        # Check if a note already exists at this position (Blooper4-style toggle)
        for i, note in enumerate(self.notes):
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and
                note_start_tick <= tick <= note_end_tick):
                # Note exists - START ERASE DRAG (allows dragging to delete multiple notes)
                self.is_erasing_drag = True
                self.erased_notes = set()

                # Delete the clicked note
                self._erase_note_at_position(mouse_x, mouse_y)
                return

        # No note at this position - START DRAWING DRAG
        # Start drawing drag
        self.is_drawing_drag = True
        self.draw_drag_start_tick = int(snapped_tick)
        self.draw_drag_start_pitch = pitch
        self.draw_drag_notes = []

        # Create initial note (in case user doesn't drag)
        duration_ticks = self.selected_quantization

        new_note = Note(
            note=pitch,
            start=snapped_tick / TPQN,
            duration=duration_ticks / TPQN,  # Convert ticks to beats
            velocity=self.current_velocity,
            release_velocity=self.current_release_velocity,
            selected=False
        )

        self.draw_drag_notes.append(new_note)
        self.notes.append(new_note)
        self.draw()

    def _handle_erase_click(self, sender, app_data):
        """Handle left-click in erase mode - start erase drag."""
        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_rect_min[0]
        mouse_y = mouse_pos[1] - canvas_rect_min[1]

        # Start erase drag
        self.is_erasing_drag = True
        self.erased_notes = set()

        # Take snapshot before modifying (for undo)
        if self.on_notes_changed:
            self.on_notes_changed()

        # Erase note at click position
        self._erase_note_at_position(mouse_x, mouse_y)

    def _handle_select_click(self, sender, app_data):
        """Handle left-click in select mode: box selection (placeholder for future)."""
        # Placeholder for future box selection implementation
        # For now, do nothing (right-click still works for selection)
        pass

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

    def _handle_mouse_move(self, sender, app_data):
        """Handle mouse move - update drawing or erasing drag if active."""
        if self.is_drawing_drag:
            # Check if left mouse button is still held
            if not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
                self._finish_drawing_drag()
                return

            # Get current mouse position
            mouse_pos = dpg.get_mouse_pos(local=False)
            canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
            mouse_x = mouse_pos[0] - canvas_rect_min[0]
            mouse_y = mouse_pos[1] - canvas_rect_min[1]

            # Convert to musical coordinates
            current_pitch = self.get_pitch_at(mouse_y)
            current_tick = self.get_tick_at(mouse_x)

            # Only snap if snap is enabled
            if self.snap_enabled:
                snapped_tick = self.snap_to_grid(current_tick)
            else:
                snapped_tick = current_tick

            # Get note mode from toolbar
            if self.note_mode == "held":
                # HELD NOTE MODE: Stretch existing note
                self._update_held_note_drag(int(snapped_tick), current_pitch)
            else:
                # REPEAT NOTE MODE: Create multiple notes
                self._update_repeat_note_drag(int(snapped_tick), current_pitch)

            self.draw()

        elif self.is_erasing_drag:
            # Check if left mouse button is still held
            if not dpg.is_mouse_button_down(dpg.mvMouseButton_Left):
                self._finish_erasing_drag()
                return

            # Get current mouse position
            mouse_pos = dpg.get_mouse_pos(local=False)
            canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
            mouse_x = mouse_pos[0] - canvas_rect_min[0]
            mouse_y = mouse_pos[1] - canvas_rect_min[1]

            # Erase note at current position
            self._erase_note_at_position(mouse_x, mouse_y)
            self.draw()

    def _update_held_note_drag(self, current_tick: int, current_pitch: int):
        """Update held note during drag (single note stretches)."""
        if not self.draw_drag_notes:
            return

        # Update the single note's duration
        first_note = self.draw_drag_notes[0]
        start_tick = int(first_note.start * TPQN)

        # Calculate new duration
        if current_tick > start_tick:
            new_duration_ticks = current_tick - start_tick

            # Snap duration to quantization only if snap is enabled
            if self.snap_enabled:
                snapped_duration_ticks = int(self.snap_to_grid(new_duration_ticks))
            else:
                snapped_duration_ticks = int(new_duration_ticks)

            snapped_duration_beats = snapped_duration_ticks / TPQN

            # Ensure minimum duration (one quantization unit)
            min_duration = self.selected_quantization / TPQN
            snapped_duration_beats = max(snapped_duration_beats, min_duration)

            # Update note in list
            updated_note = replace(
                first_note,
                note=current_pitch,  # Also update pitch if dragging vertically
                duration=snapped_duration_beats
            )

            # Replace in both drag list and main list
            self.draw_drag_notes[0] = updated_note

            # Find and replace in main notes list
            for i, note in enumerate(self.notes):
                if note is first_note:
                    self.notes[i] = updated_note
                    break

    def _update_repeat_note_drag(self, current_tick: int, current_pitch: int):
        """Update repeat notes during drag (multiple notes created)."""
        start_tick = self.draw_drag_start_tick

        # Calculate how many quantized notes fit in the drag distance
        if current_tick <= start_tick:
            return

        distance_ticks = current_tick - start_tick
        num_notes = int(distance_ticks / self.selected_quantization) + 1

        # Remove old drag notes from main list
        for old_note in self.draw_drag_notes:
            if old_note in self.notes:
                self.notes.remove(old_note)

        # Create new notes at quantized intervals
        self.draw_drag_notes = []
        for i in range(num_notes):
            note_tick = start_tick + (i * self.selected_quantization)

            new_note = Note(
                note=current_pitch,  # Use current pitch
                start=note_tick / TPQN,
                duration=self.selected_quantization / TPQN,
                velocity=self.current_velocity,
                release_velocity=self.current_release_velocity,
                selected=False
            )

            # Check if note already exists (avoid duplicates)
            exists = False
            for existing in self.notes:
                if (existing.note == new_note.note and
                    abs(existing.start - new_note.start) < 0.01):
                    exists = True
                    break

            if not exists:
                self.draw_drag_notes.append(new_note)
                self.notes.append(new_note)

    def _finish_drawing_drag(self):
        """Finalize drawing drag operation."""
        self.is_drawing_drag = False
        self.draw_drag_start_tick = None
        self.draw_drag_start_pitch = None
        self.draw_drag_notes = []

        # Notify that notes have changed (saves to song and updates playback)
        if self.on_notes_changed:
            self.on_notes_changed()

        self.draw()

    def _erase_note_at_position(self, mouse_x: float, mouse_y: float):
        """Erase note at given mouse position (if exists)."""
        # Convert to musical coordinates
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)

        # Find note at this position
        for i, note in enumerate(self.notes):
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and
                note_start_tick <= tick <= note_end_tick):
                # Create unique identifier for this note
                note_id = (note.note, note.start)

                # Skip if already erased in this drag
                if note_id in self.erased_notes:
                    continue

                # Mark as erased (using pitch and start time as identifier)
                self.erased_notes.add(note_id)
                # Remove from list
                self.notes.pop(i)
                # Only delete one per position, then break
                break

    def _finish_erasing_drag(self):
        """Finalize erasing drag operation."""
        self.is_erasing_drag = False
        self.erased_notes = set()

        # Notify that notes have changed (saves to song and updates playback)
        if self.on_notes_changed:
            self.on_notes_changed()

        self.draw()

    def _handle_mouse_release(self, sender, app_data):
        """Handle mouse release - finish any active drag."""
        if self.is_drawing_drag:
            self._finish_drawing_drag()
        elif self.is_erasing_drag:
            self._finish_erasing_drag()

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

    def zoom_in(self, mouse_x: Optional[float] = None):
        """Zoom in horizontally (optionally mouse-centered)."""
        old_zoom = self.zoom_x
        self.zoom_x = min(self.zoom_x * 1.1, 10.0)  # FIXED: factor 1.1, max 10.0

        # Mouse-centered zoom adjustment
        if mouse_x is not None:
            tick_under_mouse = (mouse_x / old_zoom) + self.scroll_x
            self.scroll_x = tick_under_mouse - (mouse_x / self.zoom_x)
            self.scroll_x = max(0, self.scroll_x)

        self.draw()

    def zoom_out(self, mouse_x: Optional[float] = None):
        """Zoom out horizontally (optionally mouse-centered)."""
        old_zoom = self.zoom_x
        self.zoom_x = max(self.zoom_x / 1.1, 0.1)  # FIXED: factor 1.1, min 0.1

        # Mouse-centered zoom adjustment
        if mouse_x is not None:
            tick_under_mouse = (mouse_x / old_zoom) + self.scroll_x
            self.scroll_x = tick_under_mouse - (mouse_x / self.zoom_x)
            self.scroll_x = max(0, self.scroll_x)

        self.draw()

    def zoom_in_vertical(self, mouse_y: Optional[float] = None):
        """Zoom in vertically (taller notes)."""
        old_zoom = self.zoom_y
        self.zoom_y = min(self.zoom_y * 1.2, 3.0)  # Max: 36px per note

        # Adjust scroll to keep cursor position stable
        if mouse_y is not None:
            zoom_factor = self.zoom_y / old_zoom
            # Calculate pitch at cursor before zoom
            pitch_at_cursor = self.get_pitch_at(mouse_y)
            # Adjust scroll_y to keep the same pitch at the cursor position after zoom
            self.scroll_y = (self.scroll_y + mouse_y) * zoom_factor - mouse_y
            # Clamp scroll_y
            max_scroll = max(0, (128 * GRID_HEIGHT * self.zoom_y) - self.height)
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

        self.draw()

    def zoom_out_vertical(self, mouse_y: Optional[float] = None):
        """Zoom out vertically (shorter notes)."""
        old_zoom = self.zoom_y
        self.zoom_y = max(self.zoom_y / 1.2, 0.5)  # Min: 6px per note

        # Adjust scroll to keep cursor position stable
        if mouse_y is not None:
            zoom_factor = self.zoom_y / old_zoom
            # Calculate pitch at cursor before zoom
            pitch_at_cursor = self.get_pitch_at(mouse_y)
            # Adjust scroll_y to keep the same pitch at the cursor position after zoom
            self.scroll_y = (self.scroll_y + mouse_y) * zoom_factor - mouse_y
            # Clamp scroll_y
            max_scroll = max(0, (128 * GRID_HEIGHT * self.zoom_y) - self.height)
            self.scroll_y = max(0, min(self.scroll_y, max_scroll))

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

        # Get mouse position relative to canvas
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_rect_min = dpg.get_item_rect_min(self.canvas_id)
        mouse_x = mouse_pos[0] - canvas_rect_min[0]  # Relative X position
        mouse_y = mouse_pos[1] - canvas_rect_min[1]  # Relative Y position

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
                self.zoom_in_vertical(mouse_y=mouse_y)  # Pass mouse position
            else:
                self.zoom_out_vertical(mouse_y=mouse_y)  # Pass mouse position

        elif self._check_modifier(settings["horizontal_zoom_modifier"],
                                 shift_held, ctrl_held, alt_held):
            if scroll_delta > 0:
                self.zoom_in(mouse_x=mouse_x)  # Pass mouse position
            else:
                self.zoom_out(mouse_x=mouse_x)  # Pass mouse position

        elif self._check_modifier(settings["horizontal_scroll_modifier"],
                                 shift_held, ctrl_held, alt_held):
            self.scroll_x -= scroll_delta * 50
            self.scroll_x = max(0, self.scroll_x)
            self.draw()

        elif self._check_modifier(settings["vertical_scroll_modifier"],
                                 shift_held, ctrl_held, alt_held):
            scroll_speed = int(GRID_HEIGHT * self.zoom_y * 3)
            self.scroll_y -= scroll_delta * scroll_speed
            # Prevent scrolling past the lowest note (note 0)
            # Max scroll should stop when note 0 is at the bottom of the viewport
            max_scroll = max(0, (128 * GRID_HEIGHT * self.zoom_y) - self.height)
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

    # Toolbar methods removed - use external NoteDrawToolbar widget instead

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

        # Canvas for drawing notes - wrap in child_window for auto-resize
        with dpg.child_window(border=False, tag=f"piano_roll_canvas_container_{id(self)}") as canvas_container:
            self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
            self.drawlist_id = self.canvas_id
            self._canvas_container = canvas_container

        # Mouse handlers for canvas
        with dpg.item_handler_registry() as handler:
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self._handle_canvas_click)
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self._handle_canvas_right_click)

        dpg.bind_item_handler_registry(self.canvas_id, handler)

        # Mouse wheel, move, and release handlers (window-level)
        with dpg.handler_registry():
            dpg.add_mouse_wheel_handler(callback=self._handle_mouse_wheel)
            dpg.add_mouse_move_handler(callback=self._handle_mouse_move)
            dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=self._handle_mouse_release)

        # Item resize handler for auto-resize
        with dpg.item_handler_registry() as resize_handler:
            dpg.add_item_resize_handler(callback=lambda: self.draw())
        if hasattr(self, '_canvas_container'):
            dpg.bind_item_handler_registry(self._canvas_container, resize_handler)

        # Initial draw
        self.draw()

    def create_dockable(self, tag: str = "piano_roll_window", toolbar_tag: str = "piano_roll_toolbar", parent_docking_space=None):
        """
        DEPRECATED: Use create_inline() instead. Toolbar is now a separate NoteDrawToolbar widget.

        Create dockable Piano Roll window.

        Args:
            tag: Tag for Piano Roll window
            toolbar_tag: (DEPRECATED - toolbar is now separate widget)
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

            # Canvas for drawing notes - wrap in child_window for auto-resize
            with dpg.child_window(border=False, tag=f"piano_roll_canvas_container_dockable_{id(self)}") as canvas_container:
                self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
                self.drawlist_id = self.canvas_id
                self._canvas_container = canvas_container

            # Mouse handlers for canvas
            with dpg.item_handler_registry() as handler:
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self._handle_canvas_click)
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self._handle_canvas_right_click)

            dpg.bind_item_handler_registry(self.canvas_id, handler)

            # Mouse wheel, move, and release handlers (window-level)
            with dpg.handler_registry():
                dpg.add_mouse_wheel_handler(callback=self._handle_mouse_wheel)
                dpg.add_mouse_move_handler(callback=self._handle_mouse_move)
                dpg.add_mouse_release_handler(button=dpg.mvMouseButton_Left, callback=self._handle_mouse_release)

            # Item resize handler for auto-resize
            with dpg.item_handler_registry() as resize_handler:
                dpg.add_item_resize_handler(callback=lambda: self.draw())
            if hasattr(self, '_canvas_container'):
                dpg.bind_item_handler_registry(self._canvas_container, resize_handler)

        self.window_id = tag

        # NOTE: Toolbar is now a separate NoteDrawToolbar widget created by DAWView

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
