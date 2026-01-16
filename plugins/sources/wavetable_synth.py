"""
Wavetable Synthesizer plugin.

8-bit style wavetable synthesis with custom waveform tables.
Reads from wavetable with linear interpolation.
"""
import numpy as np
from typing import Dict, Any, Optional

from plugins.base import (
    AudioProcessor,
    PluginMetadata,
    PluginCategory,
    ParameterSpec,
    ParameterType,
    ProcessContext
)
from core.models import Note


class WavetableSynth(AudioProcessor):
    """
    Wavetable synthesizer for 8-bit style sounds.

    Reads from a 32-sample wavetable with linear interpolation.
    Default table is sine wave, but can be customized.
    """

    # Default wavetable: sine wave
    DEFAULT_TABLE = np.array([np.sin(2 * np.pi * i / 32) for i in range(32)], dtype=np.float32)

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="WAVETABLE_SYNTH",
            name="Wavetable Synth",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="8-bit style wavetable synthesizer",
            parameters=[
                ParameterSpec(
                    name="decay",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.05,
                    max_val=5.0,
                    display_name="Decay",
                    description="Note decay time",
                    unit="s",
                ),
                ParameterSpec(
                    name="gain",
                    type=ParameterType.FLOAT,
                    default=0.7,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Gain",
                    description="Overall volume",
                ),
                ParameterSpec(
                    name="root_note",
                    type=ParameterType.INT,
                    default=60,
                    min_val=0,
                    max_val=127,
                    display_name="Root Note",
                    description="Root MIDI note for pitch calculation",
                ),
                ParameterSpec(
                    name="transpose",
                    type=ParameterType.INT,
                    default=0,
                    min_val=-24,
                    max_val=24,
                    display_name="Transpose",
                    description="Transpose in semitones",
                    unit="st",
                ),
            ]
        )

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Generate wavetable audio.

        Args:
            input_buffer: Not used (source plugin)
            params: Synth parameters
            note: MIDI note to generate
            context: Audio processing context

        Returns:
            Generated audio
        """
        if note is None:
            return np.array([], dtype=np.float32)

        # Get parameters
        root_note = params.get("root_note", 60)
        transpose = params.get("transpose", 0)
        gain = params.get("gain", 0.7)
        decay = params.get("decay", 0.5)

        # Get wavetable (custom or default)
        wavetable = params.get("table", self.DEFAULT_TABLE)
        if not isinstance(wavetable, np.ndarray):
            wavetable = np.array(wavetable, dtype=np.float32)
        table_size = len(wavetable)

        # Calculate pitch
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        frequency = 261.63 * pitch_multiplier  # C4 = 261.63 Hz

        # Generate time array
        num_samples = int(decay * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        # Wavetable synthesis with linear interpolation
        # Phase increment per sample
        phase_inc = (frequency * table_size) / context.sample_rate

        # Generate phase values
        phases = (np.arange(num_samples) * phase_inc) % table_size

        # Linear interpolation
        indices = phases.astype(int)
        next_indices = (indices + 1) % table_size
        frac = phases - indices

        # Interpolated samples
        buffer = ((1.0 - frac) * wavetable[indices] +
                 frac * wavetable[next_indices])

        # Apply exponential decay envelope
        t = np.linspace(0, decay, num_samples, endpoint=False)
        envelope = np.exp(-6.0 * t / decay)

        # Apply envelope, gain, and velocity
        velocity_scale = note.velocity / 127.0
        output = buffer * envelope * gain * velocity_scale * 0.5

        return output.astype(np.float32)


# For compatibility with registry discovery
__all__ = ['WavetableSynth']
