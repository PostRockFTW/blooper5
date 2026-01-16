"""
Square Cymbal synthesizer plugin.

Metallic cymbal sounds using multiple square wave oscillators
at inharmonic frequency ratios, then bandpass filtered.
"""
import numpy as np
from scipy.signal import butter, lfilter
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


class SquareCymbal(AudioProcessor):
    """
    Metallic cymbal synthesizer using square waves.

    Combines 6 square wave oscillators at inharmonic frequency ratios
    to create metallic, bell-like, or cymbal sounds.
    """

    def __init__(self):
        """Initialize with cache for performance."""
        super().__init__()
        self.cache = {}

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        parameters = [
            ParameterSpec(
                name="base_freq",
                type=ParameterType.FLOAT,
                default=200.0,
                min_val=50.0,
                max_val=1000.0,
                display_name="Base Freq",
                description="Base frequency for all oscillators",
                unit="Hz",
            ),
            ParameterSpec(
                name="bp_cutoff",
                type=ParameterType.FLOAT,
                default=5000.0,
                min_val=500.0,
                max_val=12000.0,
                display_name="BP Filter",
                description="Bandpass filter center frequency",
                unit="Hz",
                logarithmic=True,
            ),
            ParameterSpec(
                name="decay",
                type=ParameterType.FLOAT,
                default=0.5,
                min_val=0.05,
                max_val=3.0,
                display_name="Decay",
                description="Cymbal decay time",
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

        # Add 6 ratio parameters for the oscillators
        for i in range(6):
            parameters.append(
                ParameterSpec(
                    name=f"r{i+1}",
                    type=ParameterType.FLOAT,
                    default=1.0 + (i * 0.6),
                    min_val=0.5,
                    max_val=10.0,
                    display_name=f"Ratio {i+1}",
                    description=f"Frequency ratio for oscillator {i+1}",
                )
            )

        return PluginMetadata(
            id="SQUARE_CYMBAL",
            name="Square Cymbal",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="Metallic cymbal using inharmonic square waves",
            parameters=parameters
        )

    def _generate_square(self, frequency: float, num_samples: int,
                        sample_rate: int) -> np.ndarray:
        """
        Generate square wave.

        Args:
            frequency: Frequency in Hz
            num_samples: Number of samples
            sample_rate: Sample rate in Hz

        Returns:
            Square wave samples
        """
        t = np.arange(num_samples) / sample_rate
        phase = 2 * np.pi * frequency * t
        return np.sign(np.sin(phase)).astype(np.float32)

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Generate square cymbal sound.

        Args:
            input_buffer: Not used (source plugin)
            params: Cymbal parameters
            note: MIDI note to generate
            context: Audio processing context

        Returns:
            Generated cymbal sound
        """
        if note is None:
            return np.array([], dtype=np.float32)

        # Get parameters
        root_note = params.get("root_note", 60)
        transpose = params.get("transpose", 0)
        gain = params.get("gain", 0.7)
        decay = params.get("decay", 0.5)
        base_freq = params.get("base_freq", 200.0)
        cutoff = params.get("bp_cutoff", 5000.0)

        # Get frequency ratios for all 6 oscillators
        ratios = [params.get(f"r{i+1}", 1.0 + (i * 0.6)) for i in range(6)]

        # Calculate pitch
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        scaled_base_freq = base_freq * pitch_multiplier

        # Generate time array
        num_samples = int(decay * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        # Combine multiple square wave oscillators at different ratios
        combined_buffer = np.zeros(num_samples, dtype=np.float32)
        for ratio in ratios:
            freq = scaled_base_freq * ratio
            square_wave = self._generate_square(freq, num_samples, context.sample_rate)
            combined_buffer += square_wave * 0.15  # Scale each oscillator

        # Apply bandpass filter
        try:
            nyquist = 0.5 * context.sample_rate
            low_freq = max(20.0, cutoff * 0.8) / nyquist
            high_freq = min(nyquist * 0.95, cutoff * 1.2) / nyquist
            b, a = butter(1, [low_freq, high_freq], btype='band')
            filtered = lfilter(b, a, combined_buffer)
        except:
            filtered = combined_buffer

        # Apply exponential decay envelope
        t = np.linspace(0, decay, num_samples, endpoint=False)
        envelope = np.exp(-8.0 * t / decay)

        # Apply envelope, gain, and velocity
        velocity_scale = note.velocity / 127.0
        output = filtered * envelope * gain * velocity_scale

        return output.astype(np.float32)

    def reset(self):
        """Clear cache."""
        self.cache.clear()


# For compatibility with registry discovery
__all__ = ['SquareCymbal']
