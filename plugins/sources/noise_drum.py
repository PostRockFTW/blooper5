"""
Noise Drum synthesizer plugin.

Generates drum sounds using colored noise with filtering and envelopes.
Supports DRUM mode (kick/tom) and HI-HAT mode.
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


class NoiseDrum(AudioProcessor):
    """
    Noise-based drum synthesizer.

    Generates drum sounds using colored noise (white, pink, brown)
    with filtering and pitch sweeps.
    """

    # Noise colors
    NOISE_COLORS = ["WHITE", "PINK", "BROWN"]

    # Drum types
    DRUM_TYPES = ["DRUM", "HI-HAT"]

    def __init__(self):
        """Initialize with sample cache."""
        super().__init__()
        self.drum_cache = {}

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="NOISE_DRUM",
            name="Noise Drum",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="Noise-based drum synthesizer",
            parameters=[
                ParameterSpec(
                    name="type",
                    type=ParameterType.ENUM,
                    default="DRUM",
                    enum_values=self.DRUM_TYPES,
                    display_name="Type",
                    description="Drum type (DRUM=kick/tom, HI-HAT=hi-hat/cymbal)",
                ),
                ParameterSpec(
                    name="color",
                    type=ParameterType.ENUM,
                    default="WHITE",
                    enum_values=self.NOISE_COLORS,
                    display_name="Noise Color",
                    description="Noise spectrum (WHITE=full, PINK=less highs, BROWN=bass)",
                ),
                ParameterSpec(
                    name="pitch_hpf",
                    type=ParameterType.FLOAT,
                    default=60.0,
                    min_val=20.0,
                    max_val=200.0,
                    display_name="Pitch/HPF",
                    description="Base pitch (DRUM) or highpass cutoff (HI-HAT)",
                    unit="Hz",
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

    def _generate_colored_noise(self, num_samples: int, noise_color: str) -> np.ndarray:
        """
        Generate colored noise.

        Args:
            num_samples: Number of samples
            noise_color: Noise type (WHITE, PINK, BROWN)

        Returns:
            Colored noise samples
        """
        # Start with white noise
        white = np.random.uniform(-1, 1, num_samples).astype(np.float32)

        if noise_color == "PINK":
            # Simple 1-pole lowpass to approximate pink noise
            b, a = butter(1, 0.1, btype='low')
            pink = lfilter(b, a, white)
            # Normalize
            if np.max(np.abs(pink)) > 0:
                pink = pink / np.max(np.abs(pink))
            return pink.astype(np.float32)

        elif noise_color == "BROWN":
            # Integrate white noise for brown noise
            brown = np.cumsum(white).astype(np.float32)
            # Remove DC offset with highpass
            b, a = butter(1, 0.001, btype='high')
            brown = lfilter(b, a, brown)
            # Normalize
            if np.max(np.abs(brown)) > 0:
                brown = brown / np.max(np.abs(brown))
            return brown.astype(np.float32)

        return white

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Generate noise drum sound.

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
        duration = params.get("length", 0.3)
        noise_color = params.get("color", "WHITE")
        drum_type = params.get("type", "DRUM")

        # Calculate pitch
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        base_pitch = params.get("pitch_hpf", 60.0)
        pitch_val = base_pitch * pitch_multiplier

        # Generate time array and noise
        num_samples = int(duration * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        t = np.linspace(0, duration, num_samples, endpoint=False)
        noise = self._generate_colored_noise(num_samples, noise_color)

        if drum_type == "DRUM":
            # KICK/TOM: Pitch sweep + bandpass
            freq_start = pitch_val * 4.0
            freq_end = max(20.0, pitch_val)

            # Exponential pitch sweep
            pitch_env = np.exp(-8.0 * t / duration)
            freq_sweep = freq_end + (freq_start - freq_end) * pitch_env

            # Apply pitch modulation using running integral
            phase = np.cumsum(2.0 * np.pi * freq_sweep / context.sample_rate)
            pitch_mod = np.sin(phase)

            # Bandpass filter around pitch
            try:
                nyquist = 0.5 * context.sample_rate
                low_freq = max(20.0, pitch_val * 0.5)
                high_freq = min(nyquist * 0.95, pitch_val * 4.0)
                b, a = butter(2, [low_freq / nyquist, high_freq / nyquist], btype='band')
                filtered = lfilter(b, a, noise)
            except:
                filtered = noise

            # Mix noise with pitch modulation
            output = filtered * 0.7 + pitch_mod * 0.3

            # Volume envelope
            vol_env = np.exp(-6.0 * t / duration)
            output = output * vol_env

        else:  # HI-HAT
            # HI-HAT: Highpass filtered noise
            try:
                nyquist = 0.5 * context.sample_rate
                hpf_freq = max(500.0, pitch_val)
                hpf_freq = min(nyquist * 0.95, hpf_freq)
                b, a = butter(2, hpf_freq / nyquist, btype='high')
                output = lfilter(b, a, noise)
            except:
                output = noise

            # Fast decay envelope for hi-hat
            vol_env = np.exp(-12.0 * t / duration)
            output = output * vol_env

        # Apply gain and velocity
        velocity_scale = note.velocity / 127.0
        output = output * gain * velocity_scale

        return output.astype(np.float32)

    def reset(self):
        """Clear sample cache."""
        self.drum_cache.clear()


# For compatibility with registry discovery
__all__ = ['NoiseDrum']
