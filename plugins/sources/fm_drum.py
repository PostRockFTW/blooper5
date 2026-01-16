"""
FM Drum synthesizer plugin.

Uses FM synthesis (frequency modulation) to create drum sounds.
Carrier oscillator modulated by modulator with exponential envelopes.
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


class FMDrum(AudioProcessor):
    """
    FM synthesis drum machine.

    Uses frequency modulation to create punchy drum sounds.
    Good for kicks, toms, and electronic percussion.
    """

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="FM_DRUM",
            name="FM Drum",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="FM synthesis drum machine",
            parameters=[
                ParameterSpec(
                    name="fm_ratio",
                    type=ParameterType.FLOAT,
                    default=3.5,
                    min_val=0.1,
                    max_val=10.0,
                    display_name="FM Ratio",
                    description="Ratio between carrier and modulator frequencies",
                ),
                ParameterSpec(
                    name="fm_depth",
                    type=ParameterType.FLOAT,
                    default=5.0,
                    min_val=0.0,
                    max_val=20.0,
                    display_name="FM Depth",
                    description="Modulation depth (higher = more attack punch)",
                ),
                ParameterSpec(
                    name="length",
                    type=ParameterType.FLOAT,
                    default=0.3,
                    min_val=0.05,
                    max_val=2.0,
                    display_name="Length",
                    description="Drum decay length",
                    unit="s",
                ),
                ParameterSpec(
                    name="gain",
                    type=ParameterType.FLOAT,
                    default=0.8,
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
        Generate FM drum sound.

        Args:
            input_buffer: Not used (source plugin)
            params: Drum parameters
            note: MIDI note to generate
            context: Audio processing context

        Returns:
            Generated drum sound
        """
        if note is None:
            return np.array([], dtype=np.float32)

        # Get parameters
        root_note = params.get("root_note", 60)
        transpose = params.get("transpose", 0)
        gain = params.get("gain", 0.8)
        decay = params.get("length", 0.3)
        fm_ratio = params.get("fm_ratio", 3.5)
        fm_depth = params.get("fm_depth", 5.0)

        # Calculate pitch (neutral at 100Hz for drums)
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        carrier_freq = 100.0 * pitch_multiplier

        # Calculate modulator frequency
        modulator_freq = carrier_freq * fm_ratio

        # Generate time array
        num_samples = int(decay * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        t = np.linspace(0, decay, num_samples, endpoint=False)

        # FM depth envelope (fast decay for attack punch)
        fm_envelope = np.exp(-15.0 * t / decay) * fm_depth

        # Volume envelope (slower decay)
        volume_envelope = np.exp(-8.0 * t / decay)

        # Generate FM synthesis
        # Modulator oscillator
        modulator = np.sin(2 * np.pi * modulator_freq * t) * fm_envelope

        # Carrier oscillator (phase-modulated by modulator)
        output = np.sin(2 * np.pi * carrier_freq * t + modulator) * volume_envelope

        # Apply gain and velocity
        velocity_scale = note.velocity / 127.0
        output = output * gain * velocity_scale

        return output.astype(np.float32)


# For compatibility with registry discovery
__all__ = ['FMDrum']
