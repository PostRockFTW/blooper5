"""
Plate Reverb effect plugin.

Models a mechanical plate reverb with bright, dense reflections.
Uses multiple delay lines with diffusion and high-frequency damping.
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


class PlateReverb(AudioProcessor):
    """
    Plate reverb with dense, bright character.

    Models a mechanical plate reverb using multiple delay lines
    with diffusion, damping, and phase variation.
    """

    # Prime number delay times to avoid resonances (seconds)
    DELAY_TIMES = [0.011, 0.017, 0.023, 0.031, 0.037, 0.041, 0.043, 0.047]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="PLATE_REVERB",
            name="Plate Reverb",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Blooper Team",
            description="Bright mechanical plate reverb with dense reflections",
            parameters=[
                ParameterSpec(
                    name="mix",
                    type=ParameterType.FLOAT,
                    default=0.2,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Wet Mix",
                    description="Dry/wet mix (0=dry, 1=wet)",
                ),
                ParameterSpec(
                    name="decay",
                    type=ParameterType.FLOAT,
                    default=0.6,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Decay Time",
                    description="Reverb decay time",
                ),
                ParameterSpec(
                    name="damping",
                    type=ParameterType.FLOAT,
                    default=0.7,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Damping",
                    description="High-frequency damping (0=dark, 1=bright)",
                ),
                ParameterSpec(
                    name="predelay",
                    type=ParameterType.FLOAT,
                    default=0.01,
                    min_val=0.0,
                    max_val=0.1,
                    display_name="Pre-delay",
                    description="Time before reverb starts",
                    unit="s",
                ),
            ]
        )

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional['Note'],
                context: ProcessContext) -> np.ndarray:
        """
        Apply plate reverb to input audio.

        Args:
            input_buffer: Input audio samples
            params: Dictionary with mix, decay, damping, predelay
            note: Not used (effect plugin)
            context: Audio processing context

        Returns:
            Reverb-processed audio
        """
        if input_buffer is None or len(input_buffer) == 0:
            return np.array([], dtype=np.float32)

        # Get parameters
        mix = params.get("mix", 0.2)
        decay = params.get("decay", 0.6)
        damping = params.get("damping", 0.7)
        predelay = params.get("predelay", 0.01)

        # Calculate pre-delay in samples
        predelay_samples = int(predelay * context.sample_rate)
        if predelay_samples >= len(input_buffer):
            predelay_samples = 0

        # Apply pre-delay
        delayed_input = np.zeros_like(input_buffer)
        if 0 < predelay_samples < len(input_buffer):
            delayed_input[predelay_samples:] = input_buffer[:-predelay_samples]
        else:
            delayed_input = input_buffer.copy()

        # Initialize reverb output
        reverb_out = np.zeros_like(input_buffer)

        # Process through delay network
        for i, delay_time in enumerate(self.DELAY_TIMES):
            # Calculate delay in samples (decay affects delay length)
            delay_samples = int(delay_time * decay * 2.0 * context.sample_rate)

            # Skip invalid delays
            if delay_samples <= 0 or delay_samples >= len(input_buffer):
                continue

            # Create delayed signal
            temp = np.zeros_like(input_buffer)
            delayed_signal = delayed_input[:-delay_samples]

            # Apply high-frequency damping (one-pole low-pass filter)
            # Plates lose high frequencies faster than low frequencies
            damped_signal = delayed_signal.copy()
            for j in range(1, len(damped_signal)):
                damped_signal[j] = (damped_signal[j] * damping +
                                   damped_signal[j-1] * (1.0 - damping))

            # Apply feedback with decay
            feedback = 0.6 * decay
            temp[delay_samples:] = damped_signal * feedback

            # Add to output with phase variation
            # Alternates between -1 and 1 to create stereo-like effect
            phase = (i % 2) * 2 - 1
            reverb_out += temp * phase

        # Normalize by number of delay lines
        reverb_out = reverb_out / len(self.DELAY_TIMES)

        # Brighten the reverb (plate characteristic)
        # Simple approximation using differentiation
        if len(reverb_out) > 1:
            brightness = 1.2
            high_freq = np.diff(reverb_out, prepend=reverb_out[0]) * brightness
            reverb_out = reverb_out + high_freq * 0.3

        # Mix dry and wet signals
        output = input_buffer * (1.0 - mix) + reverb_out * mix

        return output

    def get_tail_samples(self, params: Dict[str, Any], context: ProcessContext) -> int:
        """
        Calculate reverb tail length.

        Args:
            params: Current parameter values
            context: Audio processing context

        Returns:
            Number of tail samples
        """
        decay = params.get("decay", 0.6)
        max_delay_time = max(self.DELAY_TIMES)
        # Tail is based on longest delay * decay * feedback cycles
        tail_samples = int(max_delay_time * decay * 2.0 * context.sample_rate * 3)
        return tail_samples


# For compatibility with registry discovery
__all__ = ['PlateReverb']
