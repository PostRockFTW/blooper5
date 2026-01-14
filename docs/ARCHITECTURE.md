# Blooper5 Architecture

## Design Principles

1. **Separation of Concerns**: UI / Audio / State completely decoupled
2. **Immutability**: All state changes through Commands (undo/redo)
3. **Testability**: Pure functions, dependency injection, no globals
4. **Modularity**: Small files (~300 lines max), single responsibility
5. **Extensibility**: Plugin system for sources/effects, future WAV/MP3 support

## Component Architecture

### Core Layer (Pure Domain Logic)

- `core/models.py` - Immutable dataclasses (Note, Track, Song, AppState)
- `core/state.py` - Command pattern (AddNote, SetParameter, etc.)
- `core/constants.py` - Audio constants only (SAMPLE_RATE, TPQN)

### Audio Layer (Separate Process)

- `audio/engine.py` - Main audio loop in multiprocessing.Process
- `audio/mixer.py` - Track mixing, master output
- `audio/dsp/` - NumPy/Numba oscillators, filters, effects

### Plugin Layer

- `plugins/base.py` - AudioProcessor ABC, PluginMetadata, ParameterSpec
- `plugins/sources/` - Synth plugins (dual_osc.py, wavetable.py, etc.)
- `plugins/effects/` - FX plugins (reverb.py, eq.py, delay.py)
- `plugins/registry.py` - Plugin discovery and loading

### UI Layer (DearPyGui IMGUI)

- `ui/widgets/` - Reusable widgets (Button.py, Slider.py, Knob.py, etc.)
- `ui/views/` - Major views (LandingPage.py, MIDIEditor.py, SoundDesigner.py)
- `ui/theme.py` - Color palette, fonts, spacing constants
- `ui/commands/` - UI event → Command bridge

### Data Flow

```
User Click → UI Event → Command → AppState Update → Re-render UI
                                ↓
                        Audio Process Queue → Parameter Update
```

## File Organization Rules

- **Max 300 lines per file** (hard limit: 1000)
- **One widget per file** (Button.py, Slider.py, NOT widgets.py)
- **One plugin per file** (dual_osc.py = Processor + metadata)
- **No circular imports** (use dependency injection)

## Critical Design Decisions

1. **DearPyGui over Pygame**: Eliminates manual positioning, scales properly
2. **Pure Python audio**: Maintainable, debuggable, 90% of C++ speed with NumPy
3. **Multiprocess audio**: Prevents UI blocking, clean separation
4. **MessagePack serialization**: 50% smaller files, faster load times
5. **Command pattern**: Built-in undo/redo, testable state changes

## Future Extensibility Hooks

- `plugins/importers/` - WAV/MP3 file loading (planned)
- `core/automation.py` - Automation lane system (implemented)
- `core/markers.py` - Arrangement markers (implemented)
- `plugins/exporters/` - Audio export formats (planned)
- `plugins/vst/` - VST host integration (planned)

## VST Compatibility Architecture (Planned)

### Design Goals

1. **Bidirectional compatibility**: Load VST plugins into Blooper5 AND export Blooper5 plugins as VST
2. **Minimal code changes**: Existing native plugins work unchanged
3. **Parameter mapping**: Automatic translation between ParameterSpec and VST parameters
4. **UI flexibility**: Support both native UI and VST editor windows

### VST Host Integration

**Wrapper Layer:**
```
Blooper5 AudioProcessor (Native)
         ↕
VSTPluginWrapper (Adapter)
         ↕
VST 2.4 / VST3 Plugin
```

**Key Components:**
- `plugins/vst/host.py` - VST discovery and loading (using python-vst or pyvst)
- `plugins/vst/wrapper.py` - Wraps VST as AudioProcessor
- `plugins/vst/parameter_mapper.py` - Maps VST params to ParameterSpec
- `plugins/vst/ui_bridge.py` - Embeds VST editor in DearPyGui window

**Parameter Mapping:**
```python
# VST parameter (0.0-1.0 normalized) → ParameterSpec
vst_param = vst_plugin.get_parameter(0)  # 0.0-1.0
blooper_param = param_spec.denormalize(vst_param)  # e.g., 20-20000 Hz

# Reverse for automation
vst_plugin.set_parameter(0, param_spec.normalize(blooper_param))
```

**Audio Buffer Conversion:**
- VST expects interleaved or planar float32 buffers
- Blooper5 uses NumPy arrays (mono per note)
- Wrapper handles format conversion automatically

**Challenges to Address:**
1. **Thread safety**: VST audio processing must stay in audio process
2. **UI thread**: VST editors need main thread (DearPyGui also on main thread)
3. **State save/restore**: VST state blobs vs Blooper5 JSON params
4. **Latency reporting**: VST delay compensation in audio pipeline
5. **MIDI routing**: VST instruments need MIDI input

**Implementation Priority:**
- Phase 1 (MVP): Load VST effects only, auto-generate UI from parameters
- Phase 2: VST instruments with MIDI routing
- Phase 3: Embed native VST editor windows
- Phase 4: Export Blooper5 plugins as VST (advanced)

**Research Required:**
- Python VST host libraries (steinberg-vst3, pyvst, python-vst)
- VST3 vs VST 2.4 support (licensing, API differences)
- Cross-platform VST loading (Windows .dll, macOS .vst, Linux .so)
