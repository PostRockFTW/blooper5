# Blooper5 Coding Conventions

## Python Style

- **PEP 8 compliant** with exceptions below
- **Line length**: 100 characters (not 79)
- **Imports**: stdlib → third-party → local, alphabetized
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for all classes and public methods

## File Length Guidelines

- **Target**: 200-300 lines per file
- **Hard limit**: 1000 lines (never exceed)
- **If file grows beyond 300 lines**: Refactor into smaller modules
- **Example**: ui_components.py (1040 lines) → Button.py, Slider.py, Knob.py, etc.

## Naming Conventions

- **Classes**: PascalCase (AudioProcessor, PluginMetadata)
- **Functions/Variables**: snake_case (get_plugin, track_idx)
- **Constants**: UPPER_SNAKE (SAMPLE_RATE, TPQN)
- **Private**: _leading_underscore (_internal_method)
- **Files**: snake_case.py (dual_osc.py, not DualOsc.py)

## Widget File Structure

Each widget gets its own file in `ui/widgets/`:

```python
# ui/widgets/button.py
"""
Button widget for Blooper5 UI.
Provides clickable buttons with accent color support.
"""
import dearpygui.dearpygui as dpg
from typing import Callable, Optional

class Button:
    """A clickable button widget."""

    def __init__(self, label: str, callback: Callable, accent: bool = False):
        """
        Args:
            label: Text displayed on button
            callback: Function called on click
            accent: If True, uses accent color theme
        """
        self.label = label
        self.callback = callback
        self.accent = accent
        self._tag = None

    def create(self, parent: str) -> str:
        """Creates the button in DearPyGui and returns its tag."""
        self._tag = dpg.add_button(
            label=self.label,
            callback=self.callback,
            parent=parent
        )
        if self.accent:
            dpg.bind_item_theme(self._tag, "accent_theme")
        return self._tag

    def set_enabled(self, enabled: bool):
        """Enable or disable the button."""
        dpg.configure_item(self._tag, enabled=enabled)
```

## Plugin File Structure

Plugins stay in single files (~150 lines):

```python
# plugins/sources/dual_osc.py
"""
Dual Oscillator synthesizer plugin.
Combines two waveforms with adjustable mix.
"""
from plugins.base import AudioProcessor, PluginMetadata, ParameterSpec, ParameterType
import numpy as np

class DualOscillator(AudioProcessor):
    """Two-oscillator subtractive synth."""

    def get_metadata(self) -> PluginMetadata:
        """Define plugin parameters and UI."""
        return PluginMetadata(
            id="DUAL_OSC",
            name="Dual Oscillator",
            category=PluginCategory.SOURCE,
            parameters=[
                ParameterSpec("osc1_type", ParameterType.ENUM,
                             default="SAW", enum_values=["SINE", "SAW", "SQUARE", "TRI"]),
                ParameterSpec("osc_mix", ParameterType.FLOAT,
                             default=0.5, min_val=0.0, max_val=1.0)
            ]
        )

    def process(self, input_buffer, params, note, context):
        """Generate audio output."""
        # Audio processing logic here (~50-80 lines)
        pass
```

## Documentation Standards

**Class Docstrings:**
```python
class MIDIEditor:
    """
    Piano roll editor for MIDI notes.

    Allows users to create, edit, and delete notes in a track.
    Supports drag-to-move, resize, and velocity editing.

    Attributes:
        track_idx: Index of currently edited track (0-15)
        viewport: Visible tick range (start, end)
        selected_notes: Set of selected note IDs
    """
```

**Function Docstrings:**
```python
def quantize_note(note: Note, grid_size: int) -> Note:
    """
    Quantize note to nearest grid position.

    Args:
        note: The note to quantize
        grid_size: Grid resolution in ticks (e.g., 120 for 1/16th notes)

    Returns:
        New note with quantized tick position

    Raises:
        ValueError: If grid_size is zero or negative
    """
```

## Testing Conventions

**Test File Naming:**
- `test_<module>.py` mirrors module structure
- `tests/unit/test_models.py` tests `blooper5/core/models.py`

**Test Function Naming:**
- `test_<what>_<condition>_<expected>`
- Example: `test_add_note_command_empty_track_adds_note()`

**Test Structure (Arrange-Act-Assert):**
```python
def test_add_note_command():
    # Arrange
    state = AppState(song=Song(...))
    note = Note(tick=0, pitch=60, duration=480, velocity=100)
    cmd = AddNoteCommand(track_idx=0, note=note)

    # Act
    new_state = cmd.execute(state)

    # Assert
    assert len(new_state.song.tracks[0].notes) == 1
    assert new_state.song.tracks[0].notes[0] == note
```

## Git Commit Conventions

**Format:**
```
<type>(<scope>): <subject>

<body>

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring (no behavior change)
- `test`: Add or update tests
- `docs`: Documentation only
- `style`: Formatting, whitespace (no logic change)

**Examples:**
```
feat(ui): add Slider widget with logarithmic mode

Implements vertical and horizontal sliders with optional
logarithmic scaling for frequency controls.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

```
fix(audio): prevent buffer underrun in reverb tail

Increased delay buffer size from 2s to 4s to accommodate
long reverb tails at low BPM.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

## Code Review Checklist

Before merging any PR:
- [ ] All files under 1000 lines (ideally under 300)
- [ ] Type hints on all public functions
- [ ] Docstrings on all classes and public methods
- [ ] No commented-out code (delete or move to TODOs)
- [ ] Tests pass (`pytest tests/`)
- [ ] No new linter warnings (`pylint blooper5/`)
- [ ] Imports organized (stdlib → third-party → local)
- [ ] No hardcoded values (use constants.py)

## Common Pitfalls to Avoid

1. **Don't mutate state directly** - Use Commands
2. **Don't import UI in audio layer** - Breaks multiprocess
3. **Don't use globals** - Pass dependencies explicitly
4. **Don't mix tabs and spaces** - Use 4 spaces
5. **Don't skip tests** - TDD is mandatory
