# Blooper5 Development Guide

This document covers development setup, coding standards, project structure, and common development tasks.

## Development Environment Setup

### Prerequisites

- Python 3.10 or higher
- Git
- Virtual environment tool (venv, virtualenv, or conda)

### Initial Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/PostRockFTW/blooper5.git
   cd blooper5
   ```

2. **Create and activate virtual environment**:
   ```bash
   # Using venv (recommended)
   python -m venv venv

   # Activate on Windows
   venv\Scripts\activate

   # Activate on macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation**:
   ```bash
   python main.py
   ```

### Development Dependencies

The `requirements.txt` includes development tools:

- **black**: Code formatter
- **pylint**: Code linter
- **pytest**: Testing framework
- **pytest-cov**: Test coverage reporting

## Project Structure

```
blooper5/
├── main.py                 # Application entry point
├── core/                   # Core domain logic (no UI dependencies)
│   ├── models.py          # Data models (AppState, Song, Track, Note)
│   ├── commands.py        # Command pattern for undo/redo
│   ├── persistence.py     # Project file I/O
│   └── constants.py       # Musical constants
├── ui/                     # User interface layer
│   ├── views/             # Full-page application contexts
│   │   ├── DAWView.py     # Main workspace
│   │   ├── LandingPage.py # Project launcher
│   │   └── SettingsPage.py # Settings
│   ├── widgets/           # Reusable UI components
│   │   ├── PianoRoll.py   # Piano roll editor
│   │   ├── DrumRoll.py    # Drum sequencer (WIP)
│   │   ├── PluginRack.py  # Plugin UI container
│   │   ├── MixerStrip.py  # Mixer channel strip
│   │   └── KeyBindingCapture.py # Keybinding widget
│   └── theme.py           # Theming and styling
├── audio/                  # Audio processing
│   ├── engine.py          # Audio engine (legacy, unused)
│   ├── dsp.py             # DSP utilities
│   └── scheduler.py       # Tick-based scheduler
├── plugins/               # Plugin system
│   ├── base.py            # Base classes (AudioProcessor, etc.)
│   ├── sources/           # Synth plugins
│   ├── effects/           # Effect plugins
│   └── registry.py        # Plugin discovery
├── midi/                  # MIDI handling
├── tests/                 # Test suite
└── docs/                  # Documentation
```

## Coding Standards

### Code Style

Blooper5 follows Python best practices:

1. **PEP 8 Compliance**: Use `black` for automatic formatting
   ```bash
   black .
   ```

2. **Type Hints**: Use type hints for function signatures
   ```python
   def add_note(track: Track, note: Note) -> Track:
       """Add a note to a track."""
       ...
   ```

3. **Docstrings**: Use Google-style docstrings
   ```python
   def process_audio(buffer: np.ndarray, sample_rate: int) -> np.ndarray:
       """Process audio buffer.

       Args:
           buffer: Input audio samples
           sample_rate: Sample rate in Hz

       Returns:
           Processed audio samples
       """
       ...
   ```

4. **File Length**: Target 300 lines per file, hard limit 1000 lines

### Architecture Principles

1. **Separation of Concerns**:
   - Core layer has no UI dependencies
   - UI layer handles only presentation
   - Audio layer isolated in separate modules

2. **Immutability**:
   - All state changes create new objects
   - Use dataclasses with `frozen=True` for models
   - Never mutate existing state

3. **Command Pattern**:
   - All state mutations go through Command objects
   - Commands implement `execute()` and `undo()`
   - Enables undo/redo functionality

4. **Dependency Injection**:
   - Pass dependencies as constructor parameters
   - Avoid global state
   - Makes testing easier

### Naming Conventions

- **Files**: snake_case (e.g., `piano_roll.py`)
- **Classes**: PascalCase (e.g., `PianoRoll`, `AddNoteCommand`)
- **Functions/Variables**: snake_case (e.g., `add_note`, `current_track`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_BPM`, `TICKS_PER_BEAT`)
- **Private members**: Leading underscore (e.g., `_internal_method`)

## Common Development Tasks

### Running the Application

```bash
python main.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run specific test
pytest tests/test_models.py::test_note_creation
```

### Code Quality Checks

```bash
# Format code
black .

# Lint code
pylint core/ ui/ plugins/

# Type checking (if using mypy)
mypy .
```

### Adding a New Plugin

See [PLUGIN_PROTOCOL.md](PLUGIN_PROTOCOL.md) for detailed plugin development guide.

Quick example:

1. Create plugin file in `plugins/sources/` or `plugins/effects/`:
   ```python
   from plugins.base import AudioProcessor, PluginMetadata, ParameterSpec

   class MyPlugin(AudioProcessor):
       """My custom plugin."""

       @staticmethod
       def get_metadata() -> PluginMetadata:
           return PluginMetadata(
               name="My Plugin",
               category="source",  # or "effect"
               parameters=[
                   ParameterSpec("volume", 0.0, 1.0, 0.5),
               ]
           )

       def process(self, input_buffer, params, note, context):
           # Generate or process audio
           return output_buffer
   ```

2. Plugin is auto-discovered by registry

### Adding a New UI View

1. Create file in `ui/views/`:
   ```python
   import dearpygui.dearpygui as dpg

   class MyView:
       """My custom view."""

       def __init__(self, app_state, on_close=None):
           self.app_state = app_state
           self.on_close = on_close
           self._window = None

       def create_window(self):
           """Create the DearPyGui window."""
           with dpg.window(label="My View", tag="my_view") as self._window:
               # Build UI here
               pass

       def show(self):
           """Show the view."""
           dpg.show_item(self._window)

       def hide(self):
           """Hide the view."""
           dpg.hide_item(self._window)
   ```

2. Integrate in `main.py` or parent view

### Adding a New Command

1. Create command class in `core/commands.py`:
   ```python
   from dataclasses import dataclass
   from core.models import AppState

   @dataclass
   class MyCommand:
       """Description of what this command does."""

       # Command parameters
       param1: str
       param2: int

       def execute(self, state: AppState) -> AppState:
           """Execute the command."""
           # Create and return new state
           return new_state

       def undo(self, state: AppState) -> AppState:
           """Undo the command."""
           # Restore previous state
           return previous_state
   ```

2. Use in UI event handlers:
   ```python
   command = MyCommand(param1="value", param2=42)
   new_state = command.execute(self.app_state)
   self.app_state = new_state
   ```

### Working with Project Files

Project files use `.bloom5` extension with MessagePack serialization:

```python
from core.persistence import ProjectFile

# Save project
project_file = ProjectFile(file_path="my_project.bloom5")
project_file.save(app_state)

# Load project
loaded_state = project_file.load()
```

### Debugging Tips

1. **DearPyGui Debug Window**:
   - Add `dpg.show_debug()` to see DearPyGui internals
   - Shows widget hierarchy, metrics, style editor

2. **Audio Debugging**:
   - Print statements in audio callback can cause glitches
   - Use logging to file instead
   - Visualize audio buffers with matplotlib

3. **State Debugging**:
   - AppState is immutable - print before/after command execution
   - Use dataclass `__repr__` for readable output

## Git Workflow

### Branch Strategy

- `main` - Production-ready code
- `dev` - Development integration branch
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches

### Commit Messages

Follow conventional commit format:

```
<type>: <description>

[optional body]

[optional footer]
```

Types:
- `feat:` - New feature
- `fix:` - Bug fix
- `refactor:` - Code refactoring
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `style:` - Code style changes (formatting)
- `perf:` - Performance improvements

Example:
```
feat: Add note velocity editing in Piano Roll

Implement velocity slider that appears when notes are selected.
Updates are applied through SetNoteVelocityCommand for undo/redo.

Closes #42
```

### Creating Pull Requests

1. Create feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/my-feature
   ```

2. Make changes and commit:
   ```bash
   git add .
   git commit -m "feat: Add my feature"
   ```

3. Push and create PR:
   ```bash
   git push origin feature/my-feature
   # Create PR on GitHub targeting dev branch
   ```

## Testing Guidelines

### Test Structure

- Place tests in `tests/` directory
- Mirror source structure (e.g., `tests/core/test_models.py`)
- Name test files `test_*.py`
- Name test functions `test_*`

### Writing Tests

```python
import pytest
from core.models import Note, Track

def test_note_creation():
    """Test basic note creation."""
    note = Note(start=0.0, pitch=60, duration=1.0, velocity=100)
    assert note.pitch == 60
    assert note.duration == 1.0

def test_track_add_note():
    """Test adding note to track."""
    track = Track(name="Track 1", notes=[])
    note = Note(start=0.0, pitch=60, duration=1.0, velocity=100)

    new_track = track.add_note(note)

    assert len(new_track.notes) == 1
    assert new_track.notes[0] == note
    assert len(track.notes) == 0  # Original unchanged (immutability)
```

### Test Coverage

Aim for:
- 80%+ coverage for core logic
- 60%+ coverage for UI code (harder to test)
- 100% coverage for critical paths (save/load, command execution)

## Performance Considerations

1. **Audio Processing**:
   - Use NumPy for vectorized operations
   - Use Numba JIT for hot loops
   - Avoid allocations in audio callback

2. **UI Updates**:
   - Batch DearPyGui updates when possible
   - Avoid unnecessary re-renders
   - Use lazy loading for large datasets

3. **State Updates**:
   - Dataclass copy is efficient for small changes
   - Consider structural sharing for large state

## Known Issues and Gotchas

1. **DearPyGui Windows Line Endings**: Git may show CRLF warnings on Windows (harmless)

2. **Audio Callback Threading**: Audio callbacks run on separate thread - no UI calls allowed

3. **Immutability**: Remember to use returned state, not mutated input:
   ```python
   # Wrong
   command.execute(state)

   # Right
   state = command.execute(state)
   ```

4. **DearPyGui Tag Uniqueness**: All DearPyGui items need unique tags across entire application

## Resources

- [DearPyGui Documentation](https://dearpygui.readthedocs.io/)
- [NumPy Documentation](https://numpy.org/doc/)
- [Numba Documentation](https://numba.readthedocs.io/)
- [MessagePack Specification](https://msgpack.org/)
- [Python Type Hints](https://docs.python.org/3/library/typing.html)

## Getting Help

- Check existing issues on GitHub
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions
- Review [CONVENTIONS.md](CONVENTIONS.md) for code style
- Ask in discussions for general questions
