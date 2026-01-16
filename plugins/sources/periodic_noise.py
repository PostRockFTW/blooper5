"""
Periodic Noise synthesizer plugin.

NES-style periodic noise using LFSR (Linear Feedback Shift Register) emulation.
Creates retro 8-bit noise sounds with two modes: STATIC and METALLIC.
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


class PeriodicNoise(AudioProcessor):
    """
    NES-style periodic noise generator.

    Emulates LFSR (Linear Feedback Shift Register) noise generation
    from classic 8-bit game consoles.
    """

    # Noise modes
    NOISE_MODES = ["STATIC", "METALLIC"]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="PERIODIC_NOISE",
            name="Periodic Noise",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="NES-style periodic noise with LFSR emulation",
            parameters=[
                ParameterSpec(
                    name="noise_mode",
                    type=ParameterType.ENUM,
                    default="STATIC",
                    enum_values=self.NOISE_MODES,
                    display_name="Mode",
                    description="Noise mode (STATIC=long period, METALLIC=short period)",
                ),
                ParameterSpec(
                    name="sample_rate_div",
                    type=ParameterType.INT,
                    default=4,
                    min_val=1,
                    max_val=32,
                    display_name="Rate Divider",
                    description="Sample rate divider (higher = lower pitch)",
                ),
                ParameterSpec(
                    name="length",
                    type=ParameterType.FLOAT,
                    default=0.3,
                    min_val=0.05,
                    max_val=2.0,
                    display_name="Length",
                    description="Noise decay length",
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
        Generate periodic noise.

        Args:
            input_buffer: Not used (source plugin)
            params: Noise parameters
            note: MIDI note to generate
            context: Audio processing context

        Returns:
            Generated noise
        """
        if note is None:
            return np.array([], dtype=np.float32)

        # Get parameters
        root_note = params.get("root_note", 60)
        transpose = params.get("transpose", 0)
        gain = params.get("gain", 0.7)
        duration = params.get("length", 0.3)
        noise_mode = params.get("noise_mode", "STATIC")
        base_rate_div = params.get("sample_rate_div", 4)

        # Calculate pitch-based rate divider
        # Higher pitch = faster shifts (lower divider)
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        effective_rate_div = max(1, int(base_rate_div / pitch_multiplier))

        # Generate time array
        num_samples = int(duration * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        # LFSR period depends on mode
        # METALLIC: short period (93 samples) for metallic/tonal sound
        # STATIC: long period (32767 samples) for white noise-like sound
        period = 93 if noise_mode == "METALLIC" else 32767

        # Generate locked random sequence for this trigger
        # This emulates the LFSR behavior
        seed_sequence = np.random.uniform(-1, 1, period).astype(np.float32)

        # Create output buffer by stepping through the sequence
        # at the effective hardware rate
        buffer = np.zeros(num_samples, dtype=np.float32)
        for i in range(num_samples):
            seq_idx = (i // effective_rate_div) % period
            buffer[i] = seed_sequence[seq_idx]

        # Apply exponential decay envelope
        t = np.linspace(0, duration, num_samples, endpoint=False)
        envelope = np.exp(-10.0 * t / duration)

        # Apply envelope, gain, and velocity
        velocity_scale = note.velocity / 127.0
        output = buffer * envelope * gain * velocity_scale

        return output.astype(np.float32)


# For compatibility with registry discovery
__all__ = ['PeriodicNoise']
