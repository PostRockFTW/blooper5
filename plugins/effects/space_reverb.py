"""
Space Reverb effect plugin.

Dramatic room simulation from small closet to large cathedral.
Features multiple delay taps with feedback, early reflections,
and room size control for realistic space simulation.
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


class SpaceReverb(AudioProcessor):
    """
    Algorithmic space reverb with room size control.

    Simulates acoustic spaces from small rooms to large cathedrals.
    Uses multiple delay taps with feedback and early reflections
    for realistic room character.
    """

    # Base delay times in seconds (will be scaled by room size)
    BASE_DELAYS = [0.029, 0.037, 0.041, 0.043, 0.047, 0.053, 0.061, 0.067]

    # Early reflection times (create room character)
    EARLY_REFLECTION_TIMES = [0.01, 0.017, 0.023]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="SPACE_REVERB",
            name="Space Reverb",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Blooper Team",
            description="Room simulation from closet to cathedral",
            parameters=[
                ParameterSpec(
                    name="mix",
                    type=ParameterType.FLOAT,
                    default=0.3,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Wet Mix",
                    description="Dry/wet mix (0=dry, 1=wet)",
                ),
                ParameterSpec(
                    name="room_size",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Room Size",
                    description="Room size (0=closet, 1=cathedral)",
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
                    default=0.5,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Damping",
                    description="High-frequency damping (0=bright, 1=dark)",
                ),
                ParameterSpec(
                    name="predelay",
                    type=ParameterType.FLOAT,
                    default=0.02,
                    min_val=0.0,
                    max_val=0.1,
                    display_name="Pre-delay",
                    description="Time before reverb starts (creates sense of space)",
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
        Apply space reverb to input audio.

        Args:
            input_buffer: Input audio samples
            params: Dictionary with mix, room_size, decay, damping, predelay
            note: Not used (effect plugin)
            context: Audio processing context

        Returns:
            Reverb-processed audio
        """
        if input_buffer is None or len(input_buffer) == 0:
            return np.array([], dtype=np.float32)

        # Get parameters
        mix = params.get("mix", 0.3)
        room_size = params.get("room_size", 0.5)
        decay = params.get("decay", 0.6)
        damping = params.get("damping", 0.5)
        predelay = params.get("predelay", 0.02)

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

        # Scale delays by room size (1x to 10x)
        # Small room: 20-50ms delays
        # Cathedral: 200-500ms delays
        room_multiplier = 1.0 + (room_size * 9.0)
        scaled_delays = [d * room_multiplier for d in self.BASE_DELAYS]

        # Initialize reverb output
        reverb_out = np.zeros_like(input_buffer)

        # Process each delay tap with multiple reflections
        for i, delay_time in enumerate(scaled_delays):
            delay_samples = int(delay_time * context.sample_rate)

            if delay_samples <= 0 or delay_samples >= len(input_buffer):
                continue

            # Create delay buffer for this tap
            temp = np.zeros_like(input_buffer)

            # Simulate multiple reflections (feedback loop)
            # Larger decay = more reflections
            num_reflections = int(3 + decay * 4)  # 3-7 reflections
            current_signal = delayed_input.copy()

            for reflection in range(num_reflections):
                # Calculate reflection delay
                reflection_delay = delay_samples * (reflection + 1)
                if reflection_delay >= len(input_buffer):
                    break

                # Attenuation per reflection (exponential decay)
                # Larger rooms have less attenuation per reflection
                attenuation = (0.3 + decay * 0.5) ** (reflection + 1)

                # Get reflected signal
                damped = current_signal[:-reflection_delay].copy()

                # Apply damping (high-frequency loss per reflection)
                # Simple one-pole low-pass filter
                if damping < 1.0:
                    for j in range(1, len(damped)):
                        damped[j] = (damped[j] * (1.0 - damping) +
                                    damped[j-1] * damping)

                # Add this reflection to output
                temp[reflection_delay:reflection_delay + len(damped)] += damped * attenuation

            # Add to reverb output with phase alternation for stereo spread
            phase = (-1) ** i  # Alternates between -1 and 1
            reverb_out += temp * phase

        # Normalize by number of delay taps
        reverb_out = reverb_out / (len(scaled_delays) * 0.5)

        # Add early reflections (critical for room character)
        # Early reflections arrive before main reverb tail
        early_out = np.zeros_like(input_buffer)
        for er_time in self.EARLY_REFLECTION_TIMES:
            er_samples = int(er_time * room_multiplier * context.sample_rate)
            if 0 < er_samples < len(input_buffer):
                early_out[er_samples:] += delayed_input[:-er_samples] * 0.3

        # Combine early reflections with main reverb
        reverb_out += early_out

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
        room_size = params.get("room_size", 0.5)
        decay = params.get("decay", 0.6)

        # Maximum delay time scaled by room size
        max_delay_time = max(self.BASE_DELAYS) * (1.0 + room_size * 9.0)

        # Number of reflections
        num_reflections = int(3 + decay * 4)

        # Tail is longest delay * number of reflections
        tail_samples = int(max_delay_time * num_reflections * context.sample_rate)

        return tail_samples


# For compatibility with registry discovery
__all__ = ['SpaceReverb']
