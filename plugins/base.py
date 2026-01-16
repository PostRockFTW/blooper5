"""
Base classes for all audio plugins.

Blooper5 Plugin System:
- Unified AudioProcessor interface for sources and effects
- Declarative parameter metadata (ParameterSpec)
- Auto-generated UI from metadata
- Pure audio processing (no UI code in plugins)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional
import numpy as np


class ParameterType(Enum):
    """Types of plugin parameters."""
    FLOAT = "float"
    INT = "int"
    BOOL = "bool"
    ENUM = "enum"


class PluginCategory(Enum):
    """Plugin categories."""
    SOURCE = "source"  # Synthesizers, drum machines (generate audio)
    EFFECT = "effect"  # EQ, reverb, delay (process audio)


@dataclass
class ParameterSpec:
    """
    Declarative parameter specification.

    UI is auto-generated from this metadata.

    Attributes:
        name: Internal parameter name (snake_case)
        type: Parameter data type
        default: Default value
        min_val: Minimum value (for numeric types)
        max_val: Maximum value (for numeric types)
        display_name: UI label
        description: Tooltip text
        enum_values: List of choices (for ENUM type)
        unit: Display unit (e.g., "Hz", "dB", "%")
        logarithmic: Use logarithmic scale for slider (for FLOAT)
    """
    name: str
    type: ParameterType
    default: Any
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    display_name: Optional[str] = None
    description: Optional[str] = None
    enum_values: Optional[List[str]] = None
    unit: Optional[str] = None
    logarithmic: bool = False

    def __post_init__(self):
        """Validate parameter specification."""
        if not self.name:
            raise ValueError("Parameter name is required")

        if self.display_name is None:
            # Auto-generate display name from snake_case
            self.display_name = self.name.replace('_', ' ').title()

        # Type-specific validation
        if self.type == ParameterType.ENUM:
            if not self.enum_values:
                raise ValueError(f"Parameter {self.name}: ENUM type requires enum_values")
            if self.default not in self.enum_values:
                raise ValueError(f"Parameter {self.name}: default must be in enum_values")

        if self.type in (ParameterType.FLOAT, ParameterType.INT):
            if self.min_val is None or self.max_val is None:
                raise ValueError(f"Parameter {self.name}: numeric types require min_val and max_val")
            if self.min_val >= self.max_val:
                raise ValueError(f"Parameter {self.name}: min_val must be < max_val")
            if not (self.min_val <= self.default <= self.max_val):
                raise ValueError(f"Parameter {self.name}: default must be within min/max range")


@dataclass
class PluginMetadata:
    """
    Plugin identity and parameter definitions.

    Attributes:
        id: Unique plugin ID (UPPER_SNAKE_CASE)
        name: Display name
        category: SOURCE or EFFECT
        version: Semantic version string
        author: Plugin author
        description: Brief description
        parameters: List of parameter specifications
    """
    id: str
    name: str
    category: PluginCategory
    version: str
    author: str
    description: str
    parameters: List[ParameterSpec]

    def __post_init__(self):
        """Validate metadata."""
        if not self.id:
            raise ValueError("Plugin ID is required")
        if not self.id.isupper():
            raise ValueError(f"Plugin ID must be UPPER_CASE: {self.id}")
        if not self.name:
            raise ValueError("Plugin name is required")

        # Validate version format (simple semantic versioning check)
        parts = self.version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            raise ValueError(f"Invalid version format: {self.version}. Expected X.Y.Z")

        # Validate no duplicate parameter names
        param_names = [p.name for p in self.parameters]
        if len(param_names) != len(set(param_names)):
            raise ValueError("Duplicate parameter names detected")


@dataclass
class ProcessContext:
    """
    Audio processing context passed to plugins.

    Attributes:
        sample_rate: Sample rate in Hz (typically 44100)
        bpm: Current tempo in beats per minute
        tpqn: Ticks per quarter note (typically 480)
        current_tick: Current playback position in ticks
    """
    sample_rate: int
    bpm: float
    tpqn: int
    current_tick: int = 0


class AudioProcessor(ABC):
    """
    Base class for all audio plugins (sources and effects).

    Plugins must implement:
    1. get_metadata() - Define plugin identity and parameters
    2. process() - Core audio processing function
    3. get_tail_samples() - (Optional) For effects with decay/reverb
    """

    @abstractmethod
    def get_metadata(self) -> PluginMetadata:
        """
        Get plugin metadata.

        This defines the plugin's identity, parameters, and UI.
        Called once during plugin discovery.

        Returns:
            PluginMetadata with all parameter specifications
        """
        raise NotImplementedError()

    @abstractmethod
    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional['Note'],
                context: ProcessContext) -> np.ndarray:
        """
        Process audio buffer.

        PURE FUNCTION CONTRACT:
        - Same inputs must produce same outputs (no hidden state)
        - Thread-safe (may be called from audio process)
        - Fast (runs in real-time audio callback)

        Args:
            input_buffer: Input audio samples
                - For SOURCE plugins: None (generate from scratch)
                - For EFFECT plugins: Audio to process
                - Shape: (num_samples,) - mono float32
                - Range: -1.0 to 1.0

            params: Current parameter values
                - Keys match ParameterSpec.name from metadata
                - Values are type-converted (float, int, str, bool)
                - Example: {"gain_db": -6.0, "mix": 0.5}

            note: MIDI note information
                - For SOURCE plugins: Note to generate (pitch, velocity, duration)
                - For EFFECT plugins: None (not used)
                - Type: Note from core.models

            context: Audio processing context
                - sample_rate: Sample rate in Hz
                - bpm: Current tempo
                - tpqn: Ticks per quarter note
                - current_tick: Playback position

        Returns:
            Output audio samples
                - Shape: (num_samples,) - mono float32
                - Range: -1.0 to 1.0 (values outside will be clipped)
                - Length:
                    * SOURCE: Based on note duration
                    * EFFECT: Same as input_buffer length

        Example (Source):
            >>> def process(self, input_buffer, params, note, context):
            ...     # Calculate note duration
            ...     duration_secs = (note.duration / context.tpqn) * (60 / context.bpm)
            ...     num_samples = int(duration_secs * context.sample_rate)
            ...
            ...     # Generate oscillator
            ...     freq = 440 * (2 ** ((note.note - 69) / 12))
            ...     t = np.arange(num_samples) / context.sample_rate
            ...     output = np.sin(2 * np.pi * freq * t)
            ...
            ...     # Apply velocity
            ...     output *= note.velocity / 127
            ...     return output

        Example (Effect):
            >>> def process(self, input_buffer, params, note, context):
            ...     # Process audio
            ...     gain_db = params["gain_db"]
            ...     gain_linear = 10 ** (gain_db / 20)
            ...     output = input_buffer * gain_linear
            ...
            ...     # Apply dry/wet mix
            ...     mix = params.get("mix", 1.0)
            ...     output = input_buffer * (1 - mix) + output * mix
            ...     return output
        """
        raise NotImplementedError()

    def get_tail_samples(self, params: Dict[str, Any], context: ProcessContext) -> int:
        """
        Get number of tail samples for time-based effects.

        Only needed for effects that produce audio after input ends:
        - Reverb (decay tail)
        - Delay (echo tail)
        - Other time-based effects

        Args:
            params: Current parameter values
            context: Audio processing context

        Returns:
            Number of extra samples to allocate for tail
            Default: 0 (no tail)

        Example:
            >>> def get_tail_samples(self, params, context):
            ...     decay_time = params["decay_time"]  # seconds
            ...     return int(decay_time * context.sample_rate)
        """
        return 0

    def reset(self):
        """
        Reset plugin state.

        Called when:
        - Playback stops
        - User resets the plugin
        - Switching tracks

        Default implementation does nothing (stateless plugins).
        Override if plugin has internal state (buffers, envelopes, etc.).
        """
        pass


# Helper functions for common DSP operations

def midi_to_freq(midi_note: int) -> float:
    """
    Convert MIDI note number to frequency in Hz.

    Args:
        midi_note: MIDI note number (0-127)

    Returns:
        Frequency in Hz

    Example:
        >>> midi_to_freq(69)  # A4
        440.0
        >>> midi_to_freq(60)  # C4
        261.63
    """
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def db_to_linear(db: float) -> float:
    """
    Convert decibels to linear gain.

    Args:
        db: Gain in decibels

    Returns:
        Linear gain multiplier

    Example:
        >>> db_to_linear(0.0)   # 0 dB = unity gain
        1.0
        >>> db_to_linear(-6.0)  # -6 dB ≈ half power
        0.501
        >>> db_to_linear(6.0)   # +6 dB ≈ double power
        1.995
    """
    return 10 ** (db / 20)


def linear_to_db(linear: float) -> float:
    """
    Convert linear gain to decibels.

    Args:
        linear: Linear gain multiplier

    Returns:
        Gain in decibels

    Example:
        >>> linear_to_db(1.0)   # Unity gain
        0.0
        >>> linear_to_db(0.5)   # Half amplitude
        -6.02
        >>> linear_to_db(2.0)   # Double amplitude
        6.02
    """
    return 20 * np.log10(max(linear, 1e-10))  # Avoid log(0)
