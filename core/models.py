"""
Immutable data models for Blooper5.

All models are immutable dataclasses to support:
- Easy undo/redo via command pattern
- Thread-safe sharing between UI and audio processes
- Efficient state diffing
"""
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any


@dataclass(frozen=True)
class Note:
    """
    MIDI note event.

    Attributes:
        note: MIDI note number (0-127)
        start: Start time in beats
        duration: Duration in beats
        velocity: Note velocity (0-127)
        selected: Whether note is selected in UI
    """
    note: int
    start: float
    duration: float
    velocity: int = 100
    selected: bool = False

    def __post_init__(self):
        """Validate note values."""
        if not 0 <= self.note <= 127:
            raise ValueError(f"Note must be 0-127, got {self.note}")
        if self.duration <= 0:
            raise ValueError(f"Duration must be positive, got {self.duration}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "note": self.note,
            "start": self.start,
            "duration": self.duration,
            "velocity": self.velocity,
            "selected": self.selected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create Note from dictionary."""
        return cls(
            note=data["note"],
            start=data["start"],
            duration=data["duration"],
            velocity=data.get("velocity", 100),
            selected=data.get("selected", False),
        )


@dataclass(frozen=True)
class MeasureMetadata:
    """
    Metadata for a single measure.

    Stores time signature and tempo information for a specific measure.
    Designed to map cleanly to MIDI meta events (SetTempo 0xFF 0x51, TimeSignature 0xFF 0x58).

    Attributes:
        measure_index: Index of this measure (0-based)
        start_tick: Absolute tick position where measure starts
        time_signature: (numerator, denominator) for this measure
        bpm: Tempo for this measure
        length_ticks: Duration of this measure in ticks
    """
    measure_index: int
    start_tick: int
    time_signature: Tuple[int, int]
    bpm: float
    length_ticks: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "measure_index": self.measure_index,
            "start_tick": self.start_tick,
            "time_signature": list(self.time_signature),
            "bpm": self.bpm,
            "length_ticks": self.length_ticks,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MeasureMetadata':
        """Create MeasureMetadata from dictionary."""
        return MeasureMetadata(
            measure_index=data["measure_index"],
            start_tick=data["start_tick"],
            time_signature=tuple(data["time_signature"]),
            bpm=data["bpm"],
            length_ticks=data["length_ticks"],
        )


@dataclass(frozen=True)
class Track:
    """
    Single track containing notes and settings (Blooper 4.1 schema).

    Operating Modes:
    - SYNTH: Single source engine plays all notes
    - SAMPLER: Each MIDI pitch has independent engine (drum machine/workstation)

    Attributes:
        name: Track name
        mode: Operating mode ("SYNTH" or "SAMPLER")
        is_drum: Legacy field for backward compatibility

        # SYNTH mode data
        source_type: Plugin ID for synth mode
        last_synth_source: Memory of last synth used
        source_params: Parameters for synth plugin
        piano_roll_scale: "CHROMATIC", "MODAL", or "MICROTONAL"

        # SAMPLER mode data
        sampler_map: Dict[int, dict] - Per-note engine config (0-127)
        sampler_base_note: Base note for sampler UI
        active_pad: Currently selected pad in sampler

        # Mixer parameters (always used)
        volume: Track volume (0.0-1.0)
        pan: Stereo panning (0.0-1.0, 0.5=center)
        muted: Whether track is muted
        solo: Whether track is soloed

        # Effects and notes
        effects: Tuple of effect configurations
        notes: Tuple of Note objects
    """
    name: str
    mode: str = "SYNTH"  # "SYNTH" or "SAMPLER"
    is_drum: bool = False  # Legacy compatibility

    # SYNTH mode
    source_type: str = "DUAL_OSC"
    last_synth_source: str = "DUAL_OSC"
    source_params: Dict[str, Any] = field(default_factory=lambda: {
        "osc1_type": "|/",
        "osc2_type": "~",
        "osc_mix": 0.5,
        "osc2_interval": 0,
        "osc2_detune": 15,
        "filter_cutoff": 5000,
        "transpose": 0,
        "gain": 1.0,
        "attack": 0.01,
        "length": 0.5,
        "root_note": 60
    })
    piano_roll_scale: str = "CHROMATIC"

    # SAMPLER mode
    sampler_map: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    sampler_base_note: int = 33
    active_pad: int = 33

    # Mixer
    volume: float = 0.8
    pan: float = 0.5
    muted: bool = False
    solo: bool = False

    # Effects and notes
    effects: Tuple[Dict[str, Any], ...] = field(default_factory=tuple)
    notes: Tuple[Note, ...] = field(default_factory=tuple)

    def __post_init__(self):
        """Validate track data and initialize sampler map if empty."""
        # Initialize sampler_map if not provided
        if not self.sampler_map:
            sampler_map = {}
            for p in range(0, 128):
                sampler_map[p] = {
                    "engine": "NOISE_DRUM",
                    "params": {
                        "pitch_hpf": 60,
                        "length": 0.3,
                        "type": "DRUM",
                        "gain": 1.0,
                        "transpose": 0,
                        "color": "WHITE",
                        "root_note": p
                    },
                    "label": ""
                }
            # Use object.__setattr__ to modify frozen dataclass during init
            object.__setattr__(self, 'sampler_map', sampler_map)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "mode": self.mode,
            "is_drum": self.is_drum,
            "source_type": self.source_type,
            "last_synth_source": self.last_synth_source,
            "source_params": self.source_params,
            "piano_roll_scale": self.piano_roll_scale,
            "sampler_map": {str(k): v for k, v in self.sampler_map.items()},
            "sampler_base_note": self.sampler_base_note,
            "active_pad": self.active_pad,
            "volume": self.volume,
            "pan": self.pan,
            "muted": self.muted,
            "solo": self.solo,
            "effects": list(self.effects),
            "notes": [n.to_dict() for n in self.notes],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Track":
        """Create Track from dictionary."""
        # Convert sampler_map keys back to int
        sampler_map = {}
        if "sampler_map" in data:
            sampler_map = {int(k): v for k, v in data["sampler_map"].items()}

        # Convert notes
        notes = tuple(Note.from_dict(n) for n in data.get("notes", []))

        return cls(
            name=data.get("name", "Track"),
            mode=data.get("mode", "SYNTH"),
            is_drum=data.get("is_drum", False),
            source_type=data.get("source_type", "DUAL_OSC"),
            last_synth_source=data.get("last_synth_source", "DUAL_OSC"),
            source_params=data.get("source_params", {}),
            piano_roll_scale=data.get("piano_roll_scale", "CHROMATIC"),
            sampler_map=sampler_map,
            sampler_base_note=data.get("sampler_base_note", 33),
            active_pad=data.get("active_pad", 33),
            volume=data.get("volume", 0.8),
            pan=data.get("pan", 0.5),
            muted=data.get("muted", False),
            solo=data.get("solo", False),
            effects=tuple(data.get("effects", [])),
            notes=notes,
        )


@dataclass(frozen=True)
class Song:
    """
    Complete song/project containing all tracks and metadata.

    Attributes:
        name: Song name
        bpm: Tempo in beats per minute (default/global, used if no measure_metadata)
        time_signature: (numerator, denominator) (default/global, used if no measure_metadata)
        tpqn: Ticks per quarter note (timing resolution)
        tracks: Tuple of Track objects (up to 16)
        length_ticks: Song length in ticks
        file_path: Path to saved file (None if unsaved)
        measure_metadata: Optional tuple of per-measure tempo/time signature data
    """
    name: str
    bpm: float
    time_signature: Tuple[int, int]
    tpqn: int
    tracks: Tuple[Track, ...]
    length_ticks: int = 1920  # 1 bar (4 beats) at 480 TPQN in 4/4 time
    file_path: Optional[str] = None
    measure_metadata: Optional[Tuple[MeasureMetadata, ...]] = None

    def __post_init__(self):
        """Validate song structure."""
        if self.bpm <= 0:
            raise ValueError(f"BPM must be positive, got {self.bpm}")
        if self.tpqn <= 0:
            raise ValueError(f"TPQN must be positive, got {self.tpqn}")
        if len(self.tracks) > 16:
            raise ValueError(f"Maximum 16 tracks allowed, got {len(self.tracks)}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "version": "5.0.0",
            "name": self.name,
            "bpm": self.bpm,
            "time_signature": self.time_signature,
            "tpqn": self.tpqn,
            "length_ticks": self.length_ticks,
            "tracks": [t.to_dict() for t in self.tracks],
            "file_path": self.file_path,
        }
        # Add measure_metadata if present
        if self.measure_metadata:
            result["measure_metadata"] = [m.to_dict() for m in self.measure_metadata]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Song":
        """Create Song from dictionary."""
        tracks = tuple(Track.from_dict(t) for t in data.get("tracks", []))

        # Parse measure_metadata if present
        measure_metadata = None
        if "measure_metadata" in data:
            measure_metadata = tuple(
                MeasureMetadata.from_dict(m) for m in data["measure_metadata"]
            )

        return cls(
            name=data.get("name", "Untitled"),
            bpm=float(data.get("bpm", 120.0)),
            time_signature=tuple(data.get("time_signature", (4, 4))),
            tpqn=data.get("tpqn", 480),
            tracks=tracks,
            length_ticks=data.get("length_ticks", 1920),
            file_path=data.get("file_path"),
            measure_metadata=measure_metadata,
        )


class AppState:
    """
    Global application state (singleton).

    Manages:
    - Current song/project
    - Playback state (playing, position, etc.)
    - UI state (selected track, view mode, etc.)
    """

    def __init__(self):
        """Initialize empty state."""
        self._current_song: Optional[Song] = None
        self._playback_position: float = 0.0  # In beats
        self._is_playing: bool = False
        self._selected_track: Optional[int] = None
        self._is_dirty: bool = False

    def get_current_song(self) -> Optional[Song]:
        """Get currently loaded song."""
        return self._current_song

    def set_current_song(self, song: Song):
        """Set current song."""
        self._current_song = song
        self._is_dirty = False

    def get_playback_position(self) -> float:
        """Get current playback position in beats."""
        return self._playback_position

    def set_playback_position(self, position: float):
        """Set current playback position in beats."""
        self._playback_position = max(0.0, position)

    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self._is_playing

    def set_playing(self, playing: bool):
        """Set playback state."""
        self._is_playing = playing

    def get_selected_track(self) -> Optional[int]:
        """Get index of currently selected track."""
        return self._selected_track

    def set_selected_track(self, track_index: Optional[int]):
        """Set selected track index."""
        self._selected_track = track_index

    def is_dirty(self) -> bool:
        """Check if song has unsaved changes."""
        return self._is_dirty

    def mark_dirty(self):
        """Mark song as having unsaved changes."""
        self._is_dirty = True

    def mark_clean(self):
        """Mark song as saved."""
        self._is_dirty = False
