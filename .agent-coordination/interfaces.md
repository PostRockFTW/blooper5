# Shared Interface Contracts

**Last Updated**: 2026-01-15 08:30 AM
**Version**: 1.0

## Critical Interfaces Between Agents

### 1. Core → Audio: Note Playback
**Defined by**: Agent-Core (core/models.py)
**Used by**: Agent-Audio (audio/engine.py)
**Status**: ⏳ Pending implementation

```python
@dataclass(frozen=True)
class Note:
    """MIDI note event."""
    note: int          # MIDI note (0-127)
    start: float       # Start time in beats
    duration: float    # Duration in beats
    velocity: int      # Velocity (0-127)
    selected: bool     # UI selection state
```

**Contract**: Audio engine receives Note objects and must play them at correct timing.

---

### 2. Audio → Plugins: Audio Processing
**Defined by**: Agent-Plugins (plugins/base.py)
**Used by**: Agent-Audio (audio/engine.py)
**Status**: ⏳ Pending implementation

```python
class AudioProcessor(ABC):
    @abstractmethod
    def process(self, input_buffer: np.ndarray, sample_rate: int) -> np.ndarray:
        """Process audio buffer."""
```

**Contract**: All plugins implement process() with (frames, 2) stereo numpy arrays.

---

### 3. Core → Plugins: Plugin Metadata
**Defined by**: Agent-Plugins (plugins/base.py)
**Used by**: Agent-Core (for persistence)
**Status**: ⏳ Pending implementation

```python
class PluginMetadata:
    name: str
    version: str
    category: str  # "source" or "effect"
    parameters: List[ParameterDefinition]
```

**Contract**: All plugins expose metadata for UI generation and save/load.

---

### 4. Core → Audio: Playback State
**Defined by**: Agent-Core (core/models.py - AppState)
**Used by**: Agent-Audio (audio/engine.py)
**Status**: ⏳ Pending implementation

```python
class AppState:
    def get_current_song(self) -> Optional[Song]: ...
    def get_playback_position(self) -> float: ...
    def is_playing(self) -> bool: ...
```

**Contract**: Audio engine reads state without modifying it directly.

---

## Breaking Change Protocol

If you need to change a shared interface:
1. Document the change here with reason
2. Add migration note (old → new)
3. Update your status file with "🚨 INTERFACE CHANGE" marker
4. Update timestamp at top of this file
5. Other agents must acknowledge before proceeding

### Example:
```markdown
## 🚨 CHANGE 2026-01-15 09:00 AM: Note.velocity type
- **Old**: velocity: int (0-127)
- **New**: velocity: float (0.0-1.0)
- **Reason**: More precise velocity control
- **Agent**: agent-core
- **Acknowledged by**: [ ] agent-audio, [ ] agent-plugins
```

---

## Change Log

- 2026-01-15 08:30 AM - Initial interface definitions created
