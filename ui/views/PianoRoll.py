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
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field


@dataclass
class MockNote:
    """Temporary note class until backend agents complete core.models.py"""
    note: int          # MIDI note number (0-127)
    start: float       # Start time in beats
    duration: float    # Duration in beats
    velocity: int      # Velocity (0-127)
    selected: bool = False


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

    def __init__(self, width: int = 1000, height: int = 600):
        self.width = width
        self.height = height

        # Theme (customizable)
        self.theme = PianoRollTheme()

        # Viewport/scrolling
        self.scroll_x = 0
        self.scroll_y = 60 * GRID_HEIGHT
        self.zoom_x = 0.537

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
        self.selected_notes: List[MockNote] = []

        # Playback
        self.current_tick = 0

        # Mock song data
        self.song_length_ticks = TPQN * 4 * 8  # 8 measures
        self.notes: List[MockNote] = self._create_mock_notes()

        # DearPyGui IDs
        self.window_id = None
        self.canvas_id = None
        self.drawlist_id = None
        self.toolbar_window_id = None
        self.color_sidebar_id = None

    def _create_mock_notes(self) -> List[MockNote]:
        """Create some mock notes for testing UI."""
        return [
            MockNote(note=60, start=0.0, duration=1.0, velocity=100),
            MockNote(note=64, start=1.0, duration=1.0, velocity=90),
            MockNote(note=67, start=2.0, duration=1.0, velocity=85),
            MockNote(note=72, start=3.0, duration=2.0, velocity=95),
        ]

    def get_coords(self, tick: float, pitch: int) -> Tuple[float, float]:
        """Convert tick/pitch to screen coordinates."""
        x = (tick - self.scroll_x) * self.zoom_x
        y = (127 - pitch) * GRID_HEIGHT - self.scroll_y
        return x, y

    def get_pitch_at(self, y: float) -> int:
        """Convert screen Y coordinate to MIDI pitch."""
        relative_y = y + self.scroll_y
        pitch = 127 - int(relative_y / GRID_HEIGHT)
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
        self._draw_notes()
        self._draw_ghost_note()
        self._draw_playhead()

    def _draw_background_grid(self):
        """Draw alternating row backgrounds."""
        row_h = GRID_HEIGHT

        for pitch in range(128):
            x, y = self.get_coords(0, pitch)

            if -row_h <= y <= self.height:
                is_black_key = (pitch % 12) in [1, 3, 6, 8, 10]
                bg = self.theme.bg_color_black_key if is_black_key else self.theme.bg_color

                dpg.draw_rectangle(
                    (0, y), (self.width, y + row_h),
                    fill=tuple(bg + [255]),
                    parent=self.drawlist_id
                )

                # Muted row divider
                dpg.draw_line(
                    (0, y), (self.width, y),
                    color=tuple(self.theme.row_divider_color + [255]),
                    thickness=1,
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

    def _draw_notes(self):
        """Draw all notes."""
        row_h = GRID_HEIGHT

        for note in self.notes:
            if note.start * TPQN >= self.song_length_ticks:
                continue

            nx, ny = self.get_coords(note.start * TPQN, note.note)
            nw = note.duration * TPQN * self.zoom_x

            if nx + nw >= 0 and nx <= self.width:
                visible_x = max(0, nx)
                visible_width = min(nw, self.width - visible_x)

                # Color by octave
                octave = min(note.note // 12, len(self.theme.note_colors) - 1)
                color = self.theme.note_colors[octave]

                # Brighten if selected
                if note.selected:
                    color = [min(c + self.theme.selected_note_brightness, 255) for c in color]

                # Draw note
                dpg.draw_rectangle(
                    (visible_x, ny + 1),
                    (visible_x + visible_width - 1, ny + row_h - 2),
                    fill=tuple(color + [255]),
                    color=tuple([min(c + 20, 255) for c in color] + [255]),
                    thickness=1,
                    parent=self.drawlist_id
                )

                # Velocity indicator (thin bar on left)
                vel_width = 3
                vel_brightness = int(note.velocity / 127.0 * 120)
                dpg.draw_rectangle(
                    (visible_x, ny + 1),
                    (visible_x + vel_width, ny + row_h - 2),
                    fill=(vel_brightness, vel_brightness, vel_brightness, 200),
                    parent=self.drawlist_id
                )

    def _draw_ghost_note(self):
        """Draw preview note during drawing."""
        if not self.ghost_note:
            return

        row_h = GRID_HEIGHT
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
        """Draw playback position."""
        if self.current_tick > 0:
            px, _ = self.get_coords(self.current_tick, 0)
            if 0 <= px <= self.width:
                dpg.draw_line(
                    (px, 0), (px, self.height),
                    color=tuple(self.theme.playhead_color + [255]),
                    thickness=2,
                    parent=self.drawlist_id
                )

    def _handle_canvas_click(self, sender, app_data):
        """Handle left-click on canvas (draw mode)."""
        if self.tool != "draw":
            return

        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_pos = dpg.get_item_pos(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_pos[0]
        mouse_y = mouse_pos[1] - canvas_pos[1]

        # Convert to pitch and tick
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)
        snapped_tick = self.snap_to_grid(tick)

        # Calculate note duration based on current grid
        duration_ticks = self._calculate_note_width()

        # Create new note
        new_note = MockNote(
            note=pitch,
            start=snapped_tick / TPQN,
            duration=self.note_length_beats,
            velocity=self.current_velocity,
            selected=False
        )
        self.notes.append(new_note)
        self.draw()

    def _handle_canvas_right_click(self, sender, app_data):
        """Handle right-click on canvas (select mode)."""
        # Get mouse position from DearPyGui
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_pos = dpg.get_item_pos(self.canvas_id)

        mouse_x = mouse_pos[0] - canvas_pos[0]
        mouse_y = mouse_pos[1] - canvas_pos[1]

        # Find note under cursor
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)

        # Check if we clicked on a note
        for note in self.notes:
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and
                note_start_tick <= tick <= note_end_tick):
                note.selected = not note.selected
                self.draw()
                return

    def _handle_drag_start(self, sender, app_data):
        """Called when user starts dragging."""
        # Get mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_pos = dpg.get_item_pos(self.canvas_id)
        mouse_x = mouse_pos[0] - canvas_pos[0]
        mouse_y = mouse_pos[1] - canvas_pos[1]

        # Find note under cursor
        pitch = self.get_pitch_at(mouse_y)
        tick = self.get_tick_at(mouse_x)

        for note in self.notes:
            note_start_tick = note.start * TPQN
            note_end_tick = note_start_tick + (note.duration * TPQN)

            if (note.note == pitch and note_start_tick <= tick <= note_end_tick):
                self.is_dragging = True
                self.drag_start_pos = (tick, pitch)
                self.ghost_note = {"note": note, "orig_start": note.start, "orig_pitch": note.note}
                # Select the note being dragged
                note.selected = True
                break

    def _handle_drag(self, sender, app_data):
        """Called while dragging."""
        if not self.is_dragging or self.ghost_note is None:
            return

        # Get current mouse position
        mouse_pos = dpg.get_mouse_pos(local=False)
        canvas_pos = dpg.get_item_pos(self.canvas_id)
        mouse_x = mouse_pos[0] - canvas_pos[0]
        mouse_y = mouse_pos[1] - canvas_pos[1]

        # Convert to pitch and tick
        new_pitch = self.get_pitch_at(mouse_y)
        new_tick = self.get_tick_at(mouse_x)
        snapped_tick = self.snap_to_grid(new_tick)

        # Update note position
        note = self.ghost_note["note"]
        note.note = new_pitch
        note.start = snapped_tick / TPQN

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
        self.zoom_x = min(self.zoom_x * 1.2, 10.0)
        self.draw()

    def zoom_out(self):
        """Zoom out horizontally."""
        self.zoom_x = max(self.zoom_x / 1.2, 0.1)
        self.draw()

    def _create_color_sidebar(self):
        """Create color customization sidebar."""
        with dpg.window(label="Theme Customizer", pos=(self.width + 30, 10),
                       width=300, height=600, tag="theme_sidebar"):
            dpg.add_text("Color Customization", color=(255, 255, 100))
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

    def _update_theme_color(self, attr: str, color: List[int]):
        """Update theme color and redraw."""
        # Convert from RGBA to RGB (color pickers return 4 values)
        rgb_color = list(color[:3])
        setattr(self.theme, attr, rgb_color)
        self.draw()

    def _reset_theme(self):
        """Reset to default Blooper4-inspired theme."""
        self.theme = PianoRollTheme()
        self.draw()

    def _create_toolbar(self):
        """Create movable toolbar with note controls."""
        with dpg.window(label="Note Controls", pos=(10, self.height + 80),
                       width=600, height=150, tag="note_toolbar"):
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

    def create_window(self, tag: str = "piano_roll_window"):
        """Create the DearPyGui window."""
        with dpg.window(label="Piano Roll (Redesigned)", tag=tag,
                       width=self.width + 20, height=self.height + 60, pos=(10, 10)):
            # Zoom controls
            with dpg.group(horizontal=True):
                dpg.add_button(label="Zoom In", callback=self.zoom_in)
                dpg.add_button(label="Zoom Out", callback=self.zoom_out)
                dpg.add_text("Left-click: Draw | Right-click: Select | Scroll: Zoom", color=(150, 150, 150))

            # Canvas
            self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
            self.drawlist_id = self.canvas_id

            # Mouse handlers
            with dpg.item_handler_registry() as handler:
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self._handle_canvas_click)
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self._handle_canvas_right_click)

            dpg.bind_item_handler_registry(self.canvas_id, handler)

        # Keyboard handlers (window-level)
        with dpg.handler_registry():
            dpg.add_key_press_handler(dpg.mvKey_Delete, callback=self._delete_selected_notes)
            dpg.add_key_press_handler(dpg.mvKey_Escape, callback=self._deselect_all_notes)
            dpg.add_key_press_handler(dpg.mvKey_Spacebar, callback=self._toggle_playback)
            # Ctrl+A for select all (using key_down to detect Ctrl)
            dpg.add_key_press_handler(dpg.mvKey_A, callback=self._handle_key_a)

        self.window_id = tag

        # Create sidebar and toolbar
        self._create_color_sidebar()
        self._create_toolbar()

        # Initial draw
        self.draw()


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
