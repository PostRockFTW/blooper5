"""
Drum Roll - Grid-based trigger editor for sampler/drum tracks in Blooper5.

Similar to Piano Roll but optimized for drum patterns:
- Taller rows for better visibility
- Alternating row colors
- Single-tick triggers (no sustained notes)
- Velocity editing per hit
- Pattern-based editing
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
    duration: float    # Duration in beats (usually very short for drums)
    velocity: int      # Velocity (0-127)
    selected: bool = False


# Constants
TPQN = 480  # Ticks per quarter note
DRUM_ROW_HEIGHT = 18  # Taller rows than piano roll
DRUM_NOTE_WIDTH = 12  # Fixed width for drum hits
SAMPLER_DEFAULT_START = 33  # Default MIDI note to center view on


class DrumRoll:
    """Drum Roll editor for sampler/drum pattern editing."""

    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height

        # Viewport/scrolling
        self.scroll_x = 0
        # Start scrolled to typical drum range (MIDI notes 33-60)
        self.scroll_y = (127 - (SAMPLER_DEFAULT_START + 15)) * DRUM_ROW_HEIGHT
        self.zoom_x = 0.537      # Horizontal zoom (pixels per tick)

        # Editing state
        self.is_dragging = False
        self.drag_start_pos: Optional[Tuple[int, int]] = None
        self.current_note: Optional[MockNote] = None
        self.ghost_notes: List[Dict[str, Any]] = []
        self.selected_notes: List[MockNote] = []
        self.tool = "pencil"  # pencil, select, erase

        # Playback
        self.current_tick = 0
        self.is_playing = False

        # Grid settings
        self.show_triplet_grid = True
        self.snap_to_grid = True
        self.quantize_value = TPQN  # 1/4 note by default

        # Mock song data
        self.song_length_ticks = TPQN * 4 * 8  # 8 measures
        self.notes: List[MockNote] = self._create_mock_drum_pattern()

        # Pad names (common drum kit mapping)
        self.pad_names = {
            36: "Bass Drum",
            38: "Snare",
            42: "Closed HH",
            46: "Open HH",
            49: "Crash",
            51: "Ride",
            40: "Snare Rim",
            45: "Low Tom",
            48: "Mid Tom",
            50: "High Tom",
        }

        # DearPyGui IDs
        self.window_id = None
        self.canvas_id = None
        self.drawlist_id = None

    def _create_mock_drum_pattern(self) -> List[MockNote]:
        """Create a simple 4/4 drum pattern for testing."""
        pattern = []
        # Kick on 1 and 3
        pattern.append(MockNote(note=36, start=0.0, duration=0.1, velocity=110))
        pattern.append(MockNote(note=36, start=2.0, duration=0.1, velocity=100))

        # Snare on 2 and 4
        pattern.append(MockNote(note=38, start=1.0, duration=0.1, velocity=100))
        pattern.append(MockNote(note=38, start=3.0, duration=0.1, velocity=95))

        # Hi-hats on 8th notes
        for beat in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
            vel = 90 if beat % 1.0 == 0 else 70  # Accented on beats
            pattern.append(MockNote(note=42, start=beat, duration=0.05, velocity=vel))

        return pattern

    def get_coords(self, tick: float, pitch: int) -> Tuple[float, float]:
        """Convert tick/pitch to screen coordinates."""
        x = (tick - self.scroll_x) * self.zoom_x
        y = (127 - pitch) * DRUM_ROW_HEIGHT - self.scroll_y
        return x, y

    def get_pitch_at(self, y: float) -> int:
        """Convert screen Y coordinate to MIDI pitch."""
        relative_y = y + self.scroll_y
        pitch = 127 - int(relative_y / DRUM_ROW_HEIGHT)
        return max(0, min(127, pitch))

    def get_tick_at(self, x: float) -> float:
        """Convert screen X coordinate to tick position."""
        tick = x / self.zoom_x + self.scroll_x
        return max(0.0, tick)

    def _get_grid_spacing(self) -> Tuple[int, int]:
        """Calculate grid spacing based on zoom level."""
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
        """Main draw function."""
        if not self.drawlist_id:
            return

        dpg.draw_rectangle(
            (0, 0), (self.width, self.height),
            color=(0, 0, 0, 0),
            fill=(15, 15, 20, 255),
            parent=self.drawlist_id
        )

        self._draw_pad_rows()
        self._draw_grid_lines()
        self._draw_drum_hits()
        self._draw_ghost_notes()
        self._draw_playhead()

    def _draw_pad_rows(self):
        """Draw alternating pad rows with labels."""
        for pitch in range(128):
            x, y = self.get_coords(0, pitch)

            # Only draw visible rows
            if -DRUM_ROW_HEIGHT <= y <= self.height:
                # Alternating colors for better visibility
                bg_color = (20, 20, 25, 255) if pitch % 2 == 0 else (15, 15, 18, 255)

                dpg.draw_rectangle(
                    (0, y), (self.width, y + DRUM_ROW_HEIGHT),
                    fill=bg_color,
                    parent=self.drawlist_id
                )

                # Row divider line
                dpg.draw_line(
                    (0, y), (self.width, y),
                    color=(30, 30, 35, 255),
                    thickness=1,
                    parent=self.drawlist_id
                )

                # Draw pad name label if it has one
                if pitch in self.pad_names:
                    label = f"{pitch}: {self.pad_names[pitch]}"
                    # Note: DearPyGui drawlist doesn't have text rendering
                    # This would need a separate text overlay or texture rendering
                    # For now, we skip labels in the drawlist

    def _draw_grid_lines(self):
        """Draw vertical grid lines."""
        grid_spacing, triplet_spacing = self._get_grid_spacing()
        measure_spacing = TPQN * 4

        # Triplet lines (faint)
        if self.show_triplet_grid:
            for t in range(0, self.song_length_ticks, triplet_spacing):
                if t % grid_spacing == 0 or t % measure_spacing == 0:
                    continue

                x, _ = self.get_coords(t, 0)
                if 0 <= x <= self.width:
                    dpg.draw_line(
                        (x, 0), (x, self.height),
                        color=(25, 25, 30, 255),
                        thickness=1,
                        parent=self.drawlist_id
                    )

        # Binary grid lines
        for t in range(0, self.song_length_ticks, grid_spacing):
            if t % measure_spacing == 0:
                continue

            x, _ = self.get_coords(t, 0)
            if 0 <= x <= self.width:
                dpg.draw_line(
                    (x, 0), (x, self.height),
                    color=(35, 35, 40, 255),
                    thickness=1,
                    parent=self.drawlist_id
                )

        # Measure lines (bright)
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

    def _draw_drum_hits(self):
        """Draw drum hits as fixed-width markers."""
        for note in self.notes:
            if note.start * TPQN >= self.song_length_ticks:
                continue

            nx, ny = self.get_coords(note.start * TPQN, note.note)

            # Only draw if visible
            if 0 <= nx <= self.width and -DRUM_ROW_HEIGHT <= ny <= self.height:
                # Drum hits are circles/diamonds instead of rectangles
                center_x = nx + DRUM_NOTE_WIDTH / 2
                center_y = ny + DRUM_ROW_HEIGHT / 2

                # Velocity affects size and brightness
                vel_factor = note.velocity / 127.0
                size = DRUM_NOTE_WIDTH * 0.3 * (0.5 + vel_factor * 0.5)
                brightness = int(150 + vel_factor * 105)

                # Color based on selection
                if note.selected:
                    color = (255, 180, 80, 255)  # Orange for selected
                else:
                    color = (brightness, brightness, brightness, 255)

                # Draw as a circle
                dpg.draw_circle(
                    (center_x, center_y),
                    size,
                    fill=color,
                    color=color,
                    parent=self.drawlist_id
                )

                # Velocity indicator (ring around circle)
                if vel_factor > 0.8:  # High velocity
                    dpg.draw_circle(
                        (center_x, center_y),
                        size + 2,
                        color=(255, 255, 100, 200),
                        thickness=1,
                        parent=self.drawlist_id
                    )

    def _draw_ghost_notes(self):
        """Draw preview hits during drag operations."""
        if not self.ghost_notes:
            return

        for ghost in self.ghost_notes:
            if ghost['tick'] >= self.song_length_ticks:
                continue

            gx, gy = self.get_coords(ghost['tick'], ghost['pitch'])

            if 0 <= gx <= self.width:
                center_x = gx + DRUM_NOTE_WIDTH / 2
                center_y = gy + DRUM_ROW_HEIGHT / 2

                dpg.draw_circle(
                    (center_x, center_y),
                    DRUM_NOTE_WIDTH * 0.3,
                    fill=(100, 100, 100, 128),
                    color=(150, 150, 150, 128),
                    parent=self.drawlist_id
                )

    def _draw_playhead(self):
        """Draw playback position."""
        if self.current_tick > 0:
            px, _ = self.get_coords(self.current_tick, 0)
            if 0 <= px <= self.width:
                dpg.draw_line(
                    (px, 0), (px, self.height),
                    color=(255, 80, 80, 255),
                    thickness=2,
                    parent=self.drawlist_id
                )

    def zoom_in(self):
        """Zoom in horizontally."""
        self.zoom_x = min(self.zoom_x * 1.2, 10.0)

    def zoom_out(self):
        """Zoom out horizontally."""
        self.zoom_x = max(self.zoom_x / 1.2, 0.1)

    def create_window(self, tag: str = "drum_roll_window"):
        """Create the DearPyGui window."""
        with dpg.window(label="Drum Roll", tag=tag, width=self.width + 20, height=self.height + 100):
            # Toolbar
            with dpg.group(horizontal=True):
                dpg.add_button(label="Pencil", callback=lambda: setattr(self, 'tool', 'pencil'))
                dpg.add_button(label="Select", callback=lambda: setattr(self, 'tool', 'select'))
                dpg.add_button(label="Erase", callback=lambda: setattr(self, 'tool', 'erase'))
                dpg.add_spacer(width=20)
                dpg.add_button(label="Zoom In", callback=self.zoom_in)
                dpg.add_button(label="Zoom Out", callback=self.zoom_out)
                dpg.add_spacer(width=20)
                dpg.add_text("Drum Pattern Editor")

            # Canvas
            self.canvas_id = dpg.add_drawlist(width=self.width, height=self.height)
            self.drawlist_id = self.canvas_id

            with dpg.handler_registry():
                dpg.add_mouse_wheel_handler(callback=self._handle_scroll)

        self.window_id = tag
        self.draw()

    def _handle_scroll(self, sender, app_data):
        """Handle mouse wheel for zooming."""
        if app_data > 0:
            self.zoom_in()
        else:
            self.zoom_out()
        self.draw()

    def update(self, current_tick: int):
        """Update playhead and redraw."""
        self.current_tick = current_tick
        if self.drawlist_id:
            dpg.delete_item(self.drawlist_id, children_only=True)
            self.draw()


def create_drum_roll_demo():
    """Demo function to test the drum roll."""
    dpg.create_context()

    drum_roll = DrumRoll(width=1200, height=600)
    drum_roll.create_window()

    dpg.create_viewport(title="Drum Roll Demo", width=1280, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    create_drum_roll_demo()
