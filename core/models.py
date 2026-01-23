"""
Immutable data models for Blooper5.

All models are immutable dataclasses to support:
- Easy undo/redo via command pattern
- Thread-safe sharing between UI and audio processes
- Efficient state diffing
"""
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any, List


@dataclass(frozen=True)
class AutomationPoint:
    """
    Single automation point for automation curves.

    Attributes:
        tick: Absolute tick position (0 to song length)
        value: Normalized value (0.0 to 1.0 for CC, -1.0 to 1.0 for pitch bend)
        curve_type: Interpolation type ("linear", "stepped", "bezier")
    """
    tick: int
    value: float
    curve_type: str = "linear"

    def __post_init__(self):
        """Validate automation point."""
        if self.tick < 0:
            raise ValueError(f"Tick must be non-negative, got {self.tick}")
        if self.curve_type not in ("linear", "stepped", "bezier"):
            raise ValueError(f"Invalid curve_type: {self.curve_type}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tick": self.tick,
            "value": self.value,
            "curve_type": self.curve_type,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutomationPoint":
        """Create AutomationPoint from dictionary."""
        return cls(
            tick=data["tick"],
            value=data["value"],
            curve_type=data.get("curve_type", "linear"),
        )


@dataclass(frozen=True)
class CCAutomation:
    """
    CC (Continuous Controller) automation lane.

    Stores automation curve for a single MIDI CC number (0-127).

    Attributes:
        cc_number: MIDI CC number (0-127)
        points: Tuple of AutomationPoint objects (sorted by tick)
        display_name: Human-readable name (e.g., "Modulation", "Filter Cutoff")
    """
    cc_number: int
    points: Tuple[AutomationPoint, ...] = field(default_factory=tuple)
    display_name: str = ""

    def __post_init__(self):
        """Validate CC automation."""
        if not 0 <= self.cc_number <= 127:
            raise ValueError(f"CC number must be 0-127, got {self.cc_number}")

        # Verify points are sorted by tick
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                if self.points[i].tick >= self.points[i + 1].tick:
                    raise ValueError("Automation points must be sorted by tick")

    def get_value_at_tick(self, tick: int) -> float:
        """
        Get interpolated automation value at a specific tick.

        Args:
            tick: Tick position to query

        Returns:
            Interpolated value (0.0-1.0)
        """
        if not self.points:
            return 0.0

        # Before first point: use first value
        if tick <= self.points[0].tick:
            return self.points[0].value

        # After last point: use last value
        if tick >= self.points[-1].tick:
            return self.points[-1].value

        # Find surrounding points
        for i in range(len(self.points) - 1):
            p1, p2 = self.points[i], self.points[i + 1]

            if p1.tick <= tick <= p2.tick:
                if p1.curve_type == "stepped":
                    return p1.value
                elif p1.curve_type == "linear":
                    # Linear interpolation
                    t = (tick - p1.tick) / (p2.tick - p1.tick)
                    return p1.value + t * (p2.value - p1.value)
                # Bezier curves handled later
                return p1.value

        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "cc_number": self.cc_number,
            "points": [p.to_dict() for p in self.points],
            "display_name": self.display_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CCAutomation":
        """Create CCAutomation from dictionary."""
        points = tuple(AutomationPoint.from_dict(p) for p in data.get("points", []))
        return cls(
            cc_number=data["cc_number"],
            points=points,
            display_name=data.get("display_name", ""),
        )


@dataclass(frozen=True)
class PitchBendAutomation:
    """
    Pitch bend automation lane.

    MIDI pitch bend is 14-bit (-8192 to +8191 for ±2 semitones by default).

    Attributes:
        points: Tuple of AutomationPoint objects (value range: -1.0 to +1.0)
        range_semitones: Pitch bend range in semitones (default 2)
    """
    points: Tuple[AutomationPoint, ...] = field(default_factory=tuple)
    range_semitones: int = 2

    def __post_init__(self):
        """Validate pitch bend automation."""
        # Verify points are sorted by tick
        if len(self.points) > 1:
            for i in range(len(self.points) - 1):
                if self.points[i].tick >= self.points[i + 1].tick:
                    raise ValueError("Automation points must be sorted by tick")

        # Verify values are in range -1.0 to +1.0
        for point in self.points:
            if not -1.0 <= point.value <= 1.0:
                raise ValueError(f"Pitch bend value must be -1.0 to +1.0, got {point.value}")

    def get_value_at_tick(self, tick: int) -> int:
        """
        Get interpolated pitch bend value at a specific tick.

        Args:
            tick: Tick position to query

        Returns:
            Pitch bend value (-8192 to +8191)
        """
        if not self.points:
            return 0

        # Before first point: use first value
        if tick <= self.points[0].tick:
            return int(self.points[0].value * 8192)

        # After last point: use last value
        if tick >= self.points[-1].tick:
            return int(self.points[-1].value * 8192)

        # Find surrounding points
        for i in range(len(self.points) - 1):
            p1, p2 = self.points[i], self.points[i + 1]

            if p1.tick <= tick <= p2.tick:
                if p1.curve_type == "stepped":
                    return int(p1.value * 8192)
                elif p1.curve_type == "linear":
                    # Linear interpolation
                    t = (tick - p1.tick) / (p2.tick - p1.tick)
                    value = p1.value + t * (p2.value - p1.value)
                    return int(value * 8192)
                return int(p1.value * 8192)

        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "points": [p.to_dict() for p in self.points],
            "range_semitones": self.range_semitones,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PitchBendAutomation":
        """Create PitchBendAutomation from dictionary."""
        points = tuple(AutomationPoint.from_dict(p) for p in data.get("points", []))
        return cls(
            points=points,
            range_semitones=data.get("range_semitones", 2),
        )


@dataclass(frozen=True)
class Marker:
    """
    Timeline marker for song navigation.

    Attributes:
        tick: Absolute tick position
        name: Marker name/label
        color: RGB color tuple (0-255 per channel)
    """
    tick: int
    name: str
    color: Tuple[int, int, int] = (255, 255, 0)

    def __post_init__(self):
        """Validate marker."""
        if self.tick < 0:
            raise ValueError(f"Tick must be non-negative, got {self.tick}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tick": self.tick,
            "name": self.name,
            "color": list(self.color),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Marker":
        """Create Marker from dictionary."""
        return cls(
            tick=data["tick"],
            name=data["name"],
            color=tuple(data.get("color", [255, 255, 0])),
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
class Note:
    """
    MIDI note event with full MIDI compliance.

    Attributes:
        note: MIDI note number (0-127)
        start: Start time in beats
        duration: Duration in beats
        velocity: Note-on velocity (1-127)
        selected: Whether note is selected in UI
        release_velocity: Note-off velocity (0-127, default 64)
        aftertouch_curve: Optional polyphonic aftertouch automation
    """
    note: int
    start: float
    duration: float
    velocity: int = 100
    selected: bool = False
    release_velocity: int = 64
    aftertouch_curve: Optional[Tuple[AutomationPoint, ...]] = None

    def __post_init__(self):
        """Validate note values."""
        if not 0 <= self.note <= 127:
            raise ValueError(f"Note must be 0-127, got {self.note}")
        if self.duration <= 0:
            raise ValueError(f"Duration must be positive, got {self.duration}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"Velocity must be 0-127, got {self.velocity}")
        if not 0 <= self.release_velocity <= 127:
            raise ValueError(f"Release velocity must be 0-127, got {self.release_velocity}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "note": self.note,
            "start": self.start,
            "duration": self.duration,
            "velocity": self.velocity,
            "selected": self.selected,
            "release_velocity": self.release_velocity,
        }
        if self.aftertouch_curve:
            result["aftertouch_curve"] = [p.to_dict() for p in self.aftertouch_curve]
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Note":
        """Create Note from dictionary."""
        aftertouch_curve = None
        if "aftertouch_curve" in data and data["aftertouch_curve"]:
            aftertouch_curve = tuple(AutomationPoint.from_dict(p) for p in data["aftertouch_curve"])

        return cls(
            note=data["note"],
            start=data["start"],
            duration=data["duration"],
            velocity=data.get("velocity", 100),
            selected=data.get("selected", False),
            release_velocity=data.get("release_velocity", 64),
            aftertouch_curve=aftertouch_curve,
        )


@dataclass(frozen=True)
class MIDIControlMapping:
    """
    Maps a MIDI message to a DAW control function.

    Supports multiple MIDI message types:
    - CC (Control Change): most common for buttons/knobs
    - Note: some controllers send note on/off for buttons
    - MMC (MIDI Machine Control): industry standard transport
    - Program Change: less common for transport

    Attributes:
        function: Function to trigger ("play", "stop", "record", "forward", "backward")
        message_type: Type of MIDI message ("cc", "note", "mmc", "program_change")
        channel: MIDI channel (0-15, None = omni/any channel)
        cc_number: Controller number for CC messages (0-127)
        note_number: Note number for Note messages (0-127)
        mmc_command: MMC command code (1=Stop, 2=Play, 6=Record, etc.)
        program_number: Program number for Program Change messages (0-127)
        trigger_threshold: Value threshold for triggering (default 64)
        is_toggle: Toggle vs Momentary behavior (default True)
    """
    function: str
    message_type: str  # "cc", "note", "mmc", "program_change"
    channel: Optional[int] = None
    cc_number: Optional[int] = None
    note_number: Optional[int] = None
    mmc_command: Optional[int] = None
    program_number: Optional[int] = None
    trigger_threshold: int = 64
    is_toggle: bool = True

    def matches_message(self, parsed_message: dict) -> bool:
        """Check if a parsed MIDI message matches this mapping."""
        if parsed_message.get('type') != self.message_type:
            return False

        # Check channel (if specified)
        if self.channel is not None:
            if parsed_message.get('channel') != self.channel:
                return False

        # Check message-specific fields
        if self.message_type == 'cc':
            return parsed_message.get('controller') == self.cc_number
        elif self.message_type == 'note':
            # Match both note_on and note_off
            return parsed_message.get('note') == self.note_number
        elif self.message_type == 'mmc':
            return parsed_message.get('mmc_command') == self.mmc_command
        elif self.message_type == 'program_change':
            return parsed_message.get('program') == self.program_number

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'function': self.function,
            'message_type': self.message_type,
            'channel': self.channel,
            'cc_number': self.cc_number,
            'note_number': self.note_number,
            'mmc_command': self.mmc_command,
            'program_number': self.program_number,
            'trigger_threshold': self.trigger_threshold,
            'is_toggle': self.is_toggle
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MIDIControlMapping':
        """Deserialize from dictionary."""
        return cls(
            function=data['function'],
            message_type=data['message_type'],
            channel=data.get('channel'),
            cc_number=data.get('cc_number'),
            note_number=data.get('note_number'),
            mmc_command=data.get('mmc_command'),
            program_number=data.get('program_number'),
            trigger_threshold=data.get('trigger_threshold', 64),
            is_toggle=data.get('is_toggle', True)
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

    # MIDI compliance fields
    midi_channel: int = 0  # 0-15 (displayed as 1-16 in UI)
    program_number: int = 0  # 0-127 (MIDI program/patch number)
    bank_msb: int = 0  # CC0 (bank select MSB)
    bank_lsb: int = 0  # CC32 (bank select LSB)
    cc_automation: Tuple[CCAutomation, ...] = field(default_factory=tuple)
    pitch_bend: Optional[PitchBendAutomation] = None
    channel_pressure: Tuple[AutomationPoint, ...] = field(default_factory=tuple)

    # MIDI input routing fields
    receive_midi_input: bool = False  # Enable MIDI input on this track
    midi_note_min: int = 0  # Minimum note number to accept (0-127)
    midi_note_max: int = 127  # Maximum note number to accept (0-127)

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
        result = {
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
            "midi_channel": self.midi_channel,
            "program_number": self.program_number,
            "bank_msb": self.bank_msb,
            "bank_lsb": self.bank_lsb,
            "cc_automation": [cc.to_dict() for cc in self.cc_automation],
            "channel_pressure": [p.to_dict() for p in self.channel_pressure],
            "receive_midi_input": self.receive_midi_input,
            "midi_note_min": self.midi_note_min,
            "midi_note_max": self.midi_note_max,
        }
        if self.pitch_bend:
            result["pitch_bend"] = self.pitch_bend.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Track":
        """Create Track from dictionary."""
        # Convert sampler_map keys back to int
        sampler_map = {}
        if "sampler_map" in data:
            sampler_map = {int(k): v for k, v in data["sampler_map"].items()}

        # Convert notes
        notes = tuple(Note.from_dict(n) for n in data.get("notes", []))

        # Convert CC automation
        cc_automation = tuple(CCAutomation.from_dict(cc) for cc in data.get("cc_automation", []))

        # Convert pitch bend
        pitch_bend = None
        if "pitch_bend" in data and data["pitch_bend"]:
            pitch_bend = PitchBendAutomation.from_dict(data["pitch_bend"])

        # Convert channel pressure
        channel_pressure = tuple(AutomationPoint.from_dict(p) for p in data.get("channel_pressure", []))

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
            midi_channel=data.get("midi_channel", 0),
            program_number=data.get("program_number", 0),
            bank_msb=data.get("bank_msb", 0),
            bank_lsb=data.get("bank_lsb", 0),
            cc_automation=cc_automation,
            pitch_bend=pitch_bend,
            channel_pressure=channel_pressure,
            receive_midi_input=data.get("receive_midi_input", False),
            midi_note_min=data.get("midi_note_min", 0),
            midi_note_max=data.get("midi_note_max", 127),
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

    # MIDI compliance fields
    key_signature: Tuple[int, int] = (0, 0)  # (sharps/flats [-7 to +7], major/minor [0=major, 1=minor])
    markers: Tuple[Marker, ...] = field(default_factory=tuple)
    send_midi_clock: bool = False
    receive_midi_clock: bool = False

    # Loop marker fields
    loop_start_tick: int = 0
    loop_end_tick: Optional[int] = None  # None = use full track length
    loop_enabled: bool = False

    # MIDI controller mappings
    midi_control_mappings: Tuple['MIDIControlMapping', ...] = field(default_factory=tuple)

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
            "key_signature": list(self.key_signature),
            "markers": [m.to_dict() for m in self.markers],
            "send_midi_clock": self.send_midi_clock,
            "receive_midi_clock": self.receive_midi_clock,
            "loop_start_tick": self.loop_start_tick,
            "loop_end_tick": self.loop_end_tick,
            "loop_enabled": self.loop_enabled,
            "midi_control_mappings": [m.to_dict() for m in self.midi_control_mappings],
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

        # Parse markers
        markers = tuple(Marker.from_dict(m) for m in data.get("markers", []))

        # Parse MIDI control mappings
        midi_control_mappings = tuple(
            MIDIControlMapping.from_dict(m) for m in data.get("midi_control_mappings", [])
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
            key_signature=tuple(data.get("key_signature", (0, 0))),
            markers=markers,
            send_midi_clock=data.get("send_midi_clock", False),
            receive_midi_clock=data.get("receive_midi_clock", False),
            loop_start_tick=data.get("loop_start_tick", 0),
            loop_end_tick=data.get("loop_end_tick", None),
            loop_enabled=data.get("loop_enabled", False),
            midi_control_mappings=midi_control_mappings,
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
        # Don't automatically reset dirty flag - preserve current state
        # Dirty flag should only be cleared via explicit mark_clean() calls

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
