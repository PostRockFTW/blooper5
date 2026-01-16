"""
Piano Roll - Grid-based MIDI note editor for Blooper5.

Features:
- Grid rendering with beat/measure lines
- Note creation (click to add)
- Note editing (drag to move, resize handles for duration)
- Multi-select functionality (click+drag selection box)
- Velocity editing (visual indicator + controls)
- Quantize controls (snap to grid)
- Zoom in/out (horizontal: time, vertical: pitch)
- Playhead visualization
- Ghost notes during drag operations
"""

import dearpygui.dearpygui as dpg
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


# Mock Note class (will be replaced with core.models.Note)
@dataclass
class MockNote:
    """Temporary note class until backend agents complete core.models.py"""
    note: int          # MIDI note number (0-127)
    start: float       # Start time in beats
    duration: float    # Duration in beats
    velocity: int      # Velocity (0-127)
    selected: bool = False


# Constants
TPQN = 480  # Ticks per quarter note (will come from core.constants)
GRID_HEIGHT = 12  # Pixel height per MIDI note row
OCTAVE_COLORS = [
    (140, 70, 70),    # C0-B0: Dark red
    (150, 90, 60),    # C1-B1: Orange-brown
    (160, 140, 60),   # C2-B2: Yellow-brown
    (90, 160, 90),    # C3-B3: Green
    (60, 140, 180),   # C4-B4: Cyan
    (90, 90, 180),    # C5-B5: Blue
    (140, 90, 160),   # C6-B6: Purple
    (180, 90, 120),   # C7-B7: Pink
    (200, 120, 120),  # C8-B8: Light red
    (220, 150, 150),  # C9-B9: Very light red
    (240, 180, 180),  # C10-B10: Pale pink
]


class PianoRoll:
    """Piano Roll editor with grid-based MIDI note editing."""

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height

        # Viewport/scrolling
        self.scroll_x = 0        # Horizontal scroll in ticks
        self.scroll_y = 60 * GRID_HEIGHT  # Vertical scroll (start at middle C)
        self.zoom_x = 0.537      # Horizontal zoom (pixels per tick)
        self.zoom_y = 1.0        # Vertical zoom (row height multiplier)

        # Editing state
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.current_note: Optional[MockNote] = None
        self.ghost_notes: List[Dict[str, Any]] = []  # Preview notes during drag
        self.selected_notes: List[MockNote] = []
        self.tool = "pencil"  # pencil, select, erase

        # Playback
        self.current_tick = 0
        self.is_playing = False

        # Grid settings
        self.show_triplet_grid = True
        self.snap_to_grid = True
        self.quantize_value = TPQN  # 1/4 note by default

        # Mock song data (until backend is ready)
        self.song_length_ticks = TPQN * 4 * 8  # 8 measures
        self.notes: List[MockNote] = self._create_mock_notes()

        # DearPyGui window/drawlist IDs
        self.window_id = None
        self.canvas_id = None
        self.drawlist_id = None

    def _create_mock_notes(self) -> List[MockNote]:
        """Create some mock notes for testing UI."""
        return [
            MockNote(note=60, start=0.0, duration=1.0, velocity=100),     # C4
            MockNote(note=64, start=1.0, duration=1.0, velocity=90),      # E4
            MockNote(note=67, start=2.0, duration=1.0, velocity=85),      # G4
            MockNote(note=72, start=3.0, duration=2.0, velocity=95),      # C5
            MockNote(note=60, start=4.0, duration=0.5, velocity=80),      # C4
            MockNote(note=64, start=4.5, duration=0.5, velocity=75),      # E4
            MockNote(note=67, start=5.0, duration=0.5, velocity=70),      # G4
            MockNote(note=72, start=5.5, duration=0.5, velocity=85),      # C5
        ]

    def get_coords(self, tick: float, pitch: int) -> Tuple[float, float]:
        """Convert tick/pitch to screen coordinates."""
        x = (tick - self.scroll_x) * self.zoom_x
        y = (127 - pitch) * GRID_HEIGHT * self.zoom_y - self.scroll_y
        return x, y

    def get_pitch_at(self, y: float) -> int:
        """Convert screen Y coordinate to MIDI pitch."""
        relative_y = y + self.scroll_y
        pitch = 127 - int(relative_y / (GRID_HEIGHT * self.zoom_y))
        return max(0, min(127, pitch))  # Clamp to valid range

    def get_tick_at(self, x: float) -> float:
        """Convert screen X coordinate to tick position."""
        tick = x / self.zoom_x + self.scroll_x
        return max(0.0, tick)

    def _get_grid_spacing(self) -> Tuple[int, int]:
        """Calculate grid spacing based on zoom level (binary and triplet)."""
        # Binary grid spacing (powers of 2)
        if self.zoom_x < 0.25:
            grid_spacing = TPQN * 4  # Whole notes
        elif self.zoom_x < 0.4:
            grid_spacing = TPQN * 2  # Half notes
        elif self.zoom_x < 0.7:
            grid_spacing = TPQN      # Quarter notes
        elif self.zoom_x < 1.2:
            grid_spacing = TPQN // 2  # 8th notes
        elif self.zoom_x < 2.0:
            grid_spacing = TPQN // 4  # 16th notes
        elif self.zoom_x < 3.5:
            grid_spacing = TPQN // 8  # 32nd notes
        else:
            grid_spacing = TPQN // 16  # 64th notes

        triplet_spacing = grid_spacing // 3 if self.show_triplet_grid else grid_spacing
        return grid_spacing, triplet_spacing

    def draw(self):
        """Main draw function - renders the piano roll."""
        if not self.drawlist_id:
            return

        dpg.draw_rectangle(
            (0, 0), (self.width, self.height),
            color=(0, 0, 0, 0),
            fill=(15, 15, 20, 255),
            parent=self.drawlist_id
        )

        # Draw in layers
        self._draw_background_grid()
        self._draw_grid_lines()
        self._draw_notes()
        self._draw_ghost_notes()
        self._draw_playhead()
        self._draw_selection_box()

    def _draw_background_grid(self):
        """Draw alternating row backgrounds (black keys darker)."""
        row_h = GRID_HEIGHT * self.zoom_y

        for pitch in range(128):
            x, y = self.get_coords(0, pitch)

            # Only draw visible rows
            if -row_h <= y <= self.height:
                # Black keys get darker background
                is_black_key = (pitch % 12) in [1, 3, 6, 8, 10]
                bg_color = (15, 15, 18, 255) if is_black_key else (20, 20, 25, 255)

                dpg.draw_rectangle(
                    (0, y), (self.width, y + row_h),
                    fill=bg_color,
                    parent=self.drawlist_id
                )

                # Horizontal divider line
                dpg.draw_line(
                    (0, y), (self.width, y),
                    color=(30, 30, 35, 255),
                    thickness=1,
                    parent=self.drawlist_id
                )

    def _draw_grid_lines(self):
        """Draw vertical grid lines (beats, measures, triplets)."""
        grid_spacing, triplet_spacing = self._get_grid_spacing()
        measure_spacing = TPQN * 4  # 4 beats per measure

        # Pass 1: Draw triplet subdivision lines (faintest)
        if self.show_triplet_grid:
            for t in range(0, self.song_length_ticks, triplet_spacing):
                if t % grid_spacing == 0 or t % measure_spacing == 0:
                    continue  # Skip positions that overlap with primary grid

                x, _ = self.get_coords(t, 0)
                if 0 <= x <= self.width:
                    dpg.draw_line(
                        (x, 0), (x, self.height),
                        color=(25, 25, 30, 255),
                        thickness=1,
                        parent=self.drawlist_id
                    )

        # Pass 2: Draw binary grid lines (medium brightness)
        for t in range(0, self.song_length_ticks, grid_spacing):
            if t % measure_spacing == 0:
                continue  # Skip measure lines

            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=(35, 35, 40, 255),
                    thickness=1,
                    parent=self.drawlist_id
                )

        # Pass 3: Draw measure lines (brightest and thicker)
        for bar in range(0, self.song_length_ticks // measure_spacing + 1):
            t = bar * measure_spacing
            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=(90, 90, 100, 255),
                    thickness=2,
                    parent=self.drawlist_id
                )

    def _draw_notes(self):
        """Draw all MIDI notes."""
        row_h = GRID_HEIGHT * self.zoom_y

        for note in self.notes:
            # Skip notes beyond song length
            if note.start * TPQN >= self.song_length_ticks:
                continue

            nx, ny = self.get_coords(note.start * TPQN, note.note)
            nw = note.duration * TPQN * self.zoom_x

            # Only draw if visible
            if nx + nw >= 0 and nx <= self.width:
                # Clamp to visible area
                visible_x = max(0, nx)
                visible_width = min(nw, self.width - visible_x)

                # Color by octave
                octave = min(note.note // 12, len(OCTAVE_COLORS) - 1)
                color = OCTAVE_COLORS[octave]

                # Highlight selected notes
                if note.selected:
                    color = tuple(min(c + 50, 255) for c in color)

                # Draw note rectangle
                dpg.draw_rectangle(
                    (visible_x, ny + 1),
                    (visible_x + visible_width - 1, ny + row_h - 2),
                    fill=(*color, 255),
                    color=(*color, 255),
                    parent=self.drawlist_id
                )

                # Velocity indicator (brightness bar on left edge)
                vel_width = 4
                vel_brightness = int(note.velocity / 127.0 * 100)
                dpg.draw_rectangle(
                    (visible_x, ny + 1),
                    (visible_x + vel_width, ny + row_h - 2),
                    fill=(vel_brightness, vel_brightness, vel_brightness, 200),
                    parent=self.drawlist_id
                )

    def _draw_ghost_notes(self):
        """Draw semi-transparent preview notes during drag operations."""
        if not self.ghost_notes:
            return

        row_h = GRID_HEIGHT * self.zoom_y

        for ghost in self.ghost_notes:
            if ghost['tick'] >= self.song_length_ticks:
                continue

            gx, gy = self.get_coords(ghost['tick'], ghost['pitch'])
            gw = ghost['duration'] * self.zoom_x

            if gx + gw >= 0 and gx <= self.width:
                visible_x = max(0, gx)
                visible_width = min(gw, self.width - visible_x)

                dpg.draw_rectangle(
                    (visible_x, gy + 1),
                    (visible_x + visible_width - 1, gy + row_h - 2),
                    fill=(100, 100, 100, 128),
                    color=(150, 150, 150, 128),
                    parent=self.drawlist_id
                )

    def _draw_playhead(self):
        """Draw the playback position indicator."""
        if self.current_tick > 0:
            px, _ = self.get_coords(self.current_tick, 0)
            if 0 <= px <= self.width:
                dpg.draw_line(
                    (px, 0), (px, self.height),
                    color=(255, 80, 80, 255),
                    thickness=2,
                    parent=self.drawlist_id
                )

    def _draw_selection_box(self):
        """Draw selection rectangle during multi-select."""
        if self.is_dragging and self.drag_start_pos and self.tool == "select":
            # This would be implemented with mouse tracking
            pass

    def zoom_in(self):
        """Zoom in horizontally."""
        self.zoom_x = min(self.zoom_x * 1.2, 10.0)

    def zoom_out(self):
        """Zoom out horizontally."""
        self.zoom_x = max(self.zoom_x / 1.2, 0.1)

    def quantize_notes(self):
        """Snap all selected notes to grid."""
        for note in self.selected_notes:
            # Quantize start time
            tick = note.start * TPQN
            quantized_tick = round(tick / self.quantize_value) * self.quantize_value
            note.start = quantized_tick / TPQN

            # Optionally quantize duration
            duration_ticks = note.duration * TPQN
            quantized_duration = round(duration_ticks / self.quantize_value) * self.quantize_value
            note.duration = max(quantized_duration / TPQN, self.quantize_value / TPQN)

    def create_window(self, tag: str = "piano_roll_window"):
        """Create the DearPyGui window for the piano roll."""
        with dpg.window(label="Piano Roll", tag=tag, width=self.width + 20, height=self.height + 100):
            # Toolbar
            with dpg.group(horizontal=True):
                dpg.add_button(label="Pencil", callback=lambda: setattr(self, 'tool', 'pencil'))
                dpg.add_button(label="Select", callback=lambda: setattr(self, 'tool', 'select'))
                dpg.add_button(label="Erase", callback=lambda: setattr(self, 'tool', 'erase'))
                dpg.add_spacer(width=20)
                dpg.add_button(label="Zoom In", callback=self.zoom_in)
                dpg.add_button(label="Zoom Out", callback=self.zoom_out)
                dpg.add_spacer(width=20)
                dpg.add_button(label="Quantize", callback=self.quantize_notes)

            # Canvas for drawing
            self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
            self.drawlist_id = self.canvas_id

            # Register handler for drawing updates
            with dpg.handler_registry():
                dpg.add_mouse_wheel_handler(callback=self._handle_scroll)

        self.window_id = tag

        # Initial draw
        self.draw()

    def _handle_scroll(self, sender, app_data):
        """Handle mouse wheel for zooming."""
        if app_data > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        self.draw()

    def update(self, current_tick: int):
        """Update playhead position and redraw."""
        self.current_tick = current_tick
        if self.drawlist_id:
            dpg.delete_item(self.drawlist_id, children_only=True)
            self.draw()


def create_piano_roll_demo():
    """Demo function to test the piano roll."""
    dpg.create_context()

    piano_roll = PianoRoll(width=1200, height=600)
    piano_roll.create_window()

    dpg.create_viewport(title="Piano Roll Demo", width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    create_piano_roll_demo()
