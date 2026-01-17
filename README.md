# Blooper5

A modern Digital Audio Workstation (DAW) built with Python, featuring a clean UI, plugin-based synthesis, and tick-based audio scheduling.

## Status

Blooper5 is in active development. Core functionality is implemented:
- Piano Roll note editor with mouse-based note editing
- Track management and mixing
- Plugin-based synthesis architecture (DualOscillator, FM Drum, Wavetable, etc.)
- Project file save/load (.bloom5 format)
- Theme customization and settings
- Tick-based audio scheduler for playback

## Features

### Implemented
- **Piano Roll Editor**: Visual note editing with drag-to-create, delete, resize, and move operations
- **DAW View**: Main workspace with integrated Piano Roll and mixer
- **Landing Page**: Project launcher with new project, open project, and recent projects
- **Settings Page**: Theme customization, keybindings, and application settings
- **Plugin System**: Modular architecture for synth and effect plugins
  - Sources: DualOscillator, Wavetable, FM Drum, Noise Drum, Square Cymbal, Periodic Noise
  - Effects: Reverb, Plate Reverb, Space Reverb, Delay, EQ
- **Audio Engine**: NoteScheduler with tick-based playback (Blooper4-style master clock)
- **Project Persistence**: Save/load projects in .bloom5 format (MessagePack serialization)
- **Unsaved Changes Protection**: Automatic warnings when loading/creating projects with unsaved changes
- **Command Pattern**: Undo/redo support for all state changes

### Planned
- Audio playback with real-time synthesis
- MIDI input/output
- Automation lanes
- VST plugin hosting
- Audio file import/export (WAV, MP3)
- DrumRoll editor (drum sequencer)

## Installation

### Requirements
- Python 3.10 or higher
- Windows, macOS, or Linux

### Setup

1. Clone the repository:
```bash
git clone https://github.com/PostRockFTW/blooper5.git
cd blooper5
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run Blooper5 from the project root:
```bash
python main.py
```

### Quick Start

1. **Create a new project**: Click "New Project" on the landing page
2. **Add notes**: In the Piano Roll, drag to create notes on the grid
3. **Edit notes**:
   - Delete: Select notes and press Delete or right-click → Delete
   - Move: Drag notes to new positions
   - Resize: Drag note edges to change duration
4. **Save project**: File menu → Save (saves to .bloom5 format)

### Project Files

Projects are saved with the `.bloom5` extension. The default save location is configurable in Settings.

## Project Structure

```
blooper5/
├── main.py                 # Entry point
├── core/                   # Domain models and business logic
│   ├── models.py          # AppState, Song, Track, Note
│   ├── commands.py        # Command pattern implementation
│   ├── persistence.py     # Project file I/O
│   └── constants.py       # Musical constants
├── ui/                     # User interface
│   ├── views/             # Full-page application contexts
│   │   ├── DAWView.py     # Main DAW workspace
│   │   ├── LandingPage.py # Project launcher
│   │   └── SettingsPage.py # Settings and preferences
│   ├── widgets/           # Reusable UI components
│   │   ├── PianoRoll.py   # Piano roll editor
│   │   ├── DrumRoll.py    # Drum sequencer
│   │   ├── PluginRack.py  # Plugin UI container
│   │   ├── MixerStrip.py  # Mixer channel strip
│   │   └── KeyBindingCapture.py # Keybinding widget
│   └── theme.py           # Visual styling
├── audio/                  # Audio processing
│   ├── engine.py          # Audio engine (legacy, unused)
│   ├── dsp.py             # DSP utilities
│   └── scheduler.py       # Tick-based note scheduler
├── plugins/               # Plugin system
│   ├── base.py            # Plugin base classes
│   ├── sources/           # Synth plugins
│   ├── effects/           # Effect plugins
│   └── registry.py        # Plugin discovery
├── midi/                  # MIDI handling
└── docs/                  # Documentation
    ├── ARCHITECTURE.md    # System architecture
    ├── DEVELOPMENT.md     # Development guide
    ├── PLUGIN_PROTOCOL.md # Plugin development
    └── CONVENTIONS.md     # Code conventions
```

## Development

See [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) for development setup, coding standards, and contribution guidelines.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for architectural overview and design decisions.

## Known Issues

1. **Audio buffering**: Audio playback needs pre-buffering to prevent glitches during real-time processing (see Claude_Questions.md Issue 1)
2. **Grid zoom**: Piano Roll grid zoom levels need implementation following Blooper4's beat subdivision pattern (see Claude_Questions.md Issue 2)
3. **Piano Roll first load**: Fixed in latest version - initial_load parameter prevents stale note data

## Technology Stack

- **UI Framework**: DearPyGui (immediate-mode GUI)
- **Audio Processing**: NumPy, SciPy, Numba (JIT compilation)
- **Audio I/O**: sounddevice
- **Serialization**: MessagePack (compact binary format)
- **Testing**: pytest

## License

[Add your license here]

## Credits

Developed by PostRockFTW

Based on Blooper4's tick-based master clock architecture.
