"""
Simple reverb effect plugin.

Uses multiple delay lines to create reverb effect.
Simple algorithm suitable for real-time processing.
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


class SimpleReverb(AudioProcessor):
    """
    Simple reverb effect using multiple delay lines.

    Uses 4 fixed delay times with variable room size multiplier.
    Simple but effective algorithm for basic reverb effect.
    """

    # Fixed delay times in seconds
    DELAY_TIMES = [0.029, 0.037, 0.043, 0.047]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="REVERB",
            name="Simple Reverb",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Blooper Team",
            description="Simple reverb using multiple delay lines",
            parameters=[
                ParameterSpec(
                    name="mix",
                    type=ParameterType.FLOAT,
                    default=0.1,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Wet Mix",
                    description="Dry/wet mix (0=dry, 1=wet)",
                ),
                ParameterSpec(
                    name="size",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Room Size",
                    description="Room size multiplier for delay times",
                ),
            ]
        )

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional['Note'],
                context: ProcessContext) -> np.ndarray:
        """
        Apply simple reverb to input audio.

        Uses multiple delay lines with room size control.

        Args:
            input_buffer: Input audio samples
            params: Dictionary with 'mix' and 'size' parameters
            note: Not used (effect plugin)
            context: Audio processing context

        Returns:
            Reverb-processed audio
        """
        if input_buffer is None or len(input_buffer) == 0:
            return np.array([], dtype=np.float32)

        # Get parameters
        mix = params.get("mix", 0.1)
        size = params.get("size", 0.5)

        # Initialize reverb output
        reverb_out = np.zeros_like(input_buffer)

        # Process each delay line
        for delay_time in self.DELAY_TIMES:
            # Calculate delay in samples
            delay_samples = int(delay_time * size * context.sample_rate)

            # Skip if delay is invalid
            if delay_samples <= 0 or delay_samples >= len(input_buffer):
                continue

            # Create delayed signal
            temp = np.zeros_like(input_buffer)
            temp[delay_samples:] = input_buffer[:-delay_samples] * (0.4 + mix * 0.4)

            # Accumulate delayed signals
            reverb_out += temp

        # Mix dry and wet signals
        # Divide reverb_out by 4 (number of delay lines) for normalization
        output = input_buffer * (1.0 - mix) + (reverb_out / 4.0) * mix

        return output

    def get_tail_samples(self, params: Dict[str, Any], context: ProcessContext) -> int:
        """
        Calculate reverb tail length.

        The tail is the longest delay time * size parameter.

        Args:
            params: Current parameter values
            context: Audio processing context

        Returns:
            Number of tail samples
        """
        size = params.get("size", 0.5)
        max_delay_time = max(self.DELAY_TIMES)
        tail_samples = int(max_delay_time * size * context.sample_rate)
        return tail_samples


# For compatibility with registry discovery
__all__ = ['SimpleReverb']
