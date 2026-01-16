"""
Comprehensive Delay effect plugin.

Features: variable delay time, feedback, ping-pong stereo,
tone control, and stateful delay buffer for true echo effect.
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


class Delay(AudioProcessor):
    """
    Stateful delay effect with feedback and modulation.

    Uses a circular delay buffer that persists across calls
    for true echo/feedback effects.

    Note: This plugin has internal state (delay buffer).
    Call reset() to clear the buffer when needed.
    """

    def __init__(self):
        """Initialize delay with circular buffer."""
        super().__init__()

        # Delay buffer - 10 seconds at 44100 Hz (allows long feedback trails)
        # This will be resized if needed based on actual sample rate
        self.delay_buffer_size = int(10.0 * 44100)
        self.delay_buffer = np.zeros(self.delay_buffer_size, dtype=np.float32)
        self.write_pos = 0
        self.ping_pong_state = 1.0  # Alternates for ping-pong effect

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="DELAY",
            name="Delay",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Blooper Team",
            description="Comprehensive delay with feedback and ping-pong",
            parameters=[
                ParameterSpec(
                    name="delay_time",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.1,
                    max_val=5.0,
                    display_name="Delay Time",
                    description="Time between echoes",
                    unit="s",
                ),
                ParameterSpec(
                    name="feedback",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.0,
                    max_val=0.95,
                    display_name="Feedback",
                    description="Amount of echo feedback (be careful with high values!)",
                ),
                ParameterSpec(
                    name="mix",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Dry/Wet",
                    description="Mix between dry and wet signal",
                ),
                ParameterSpec(
                    name="tone",
                    type=ParameterType.FLOAT,
                    default=0.7,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Tone",
                    description="High-frequency content (0=dark, 1=bright)",
                ),
                ParameterSpec(
                    name="pingpong",
                    type=ParameterType.FLOAT,
                    default=0.0,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Ping-Pong",
                    description="Stereo ping-pong amount (0=mono, 1=full)",
                ),
            ]
        )

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional['Note'],
                context: ProcessContext) -> np.ndarray:
        """
        Apply delay effect to input audio.

        Uses stateful circular buffer for feedback.

        Args:
            input_buffer: Input audio samples
            params: Dictionary with delay_time, feedback, mix, tone, pingpong
            note: Not used (effect plugin)
            context: Audio processing context

        Returns:
            Delayed audio with feedback
        """
        if input_buffer is None or len(input_buffer) == 0:
            return np.array([], dtype=np.float32)

        # Resize buffer if sample rate changed
        required_size = int(10.0 * context.sample_rate)
        if required_size != self.delay_buffer_size:
            self.delay_buffer_size = required_size
            self.delay_buffer = np.zeros(self.delay_buffer_size, dtype=np.float32)
            self.write_pos = 0

        # Get parameters
        delay_time = params.get("delay_time", 0.5)
        feedback = params.get("feedback", 0.5)
        mix = params.get("mix", 0.5)
        tone = params.get("tone", 0.7)
        pingpong = params.get("pingpong", 0.0)

        # Convert delay time to samples
        delay_samples = int(delay_time * context.sample_rate)

        # Clamp delay to valid range
        delay_samples = max(int(0.1 * context.sample_rate), delay_samples)  # Min 100ms
        delay_samples = min(self.delay_buffer_size - 1, delay_samples)

        # Create output buffer
        output = np.zeros_like(input_buffer)
        num_samples = len(input_buffer)

        # Process sample by sample (required for circular buffer)
        for i in range(num_samples):
            # Calculate read position (where to read delayed signal from)
            read_pos = (self.write_pos - delay_samples) % self.delay_buffer_size

            # Read delayed sample from delay buffer
            delayed_sample = self.delay_buffer[read_pos]

            # Apply tone control (simple one-pole low-pass filter)
            if tone < 0.95:
                prev_pos = (read_pos - 1) % self.delay_buffer_size
                delayed_sample = (tone * delayed_sample +
                                (1.0 - tone) * self.delay_buffer[prev_pos])

            # Apply ping-pong effect (amplitude modulation for stereo width simulation)
            if pingpong > 0.01:
                # Toggle ping-pong state every delay cycle
                if i % delay_samples == 0 and i > 0:
                    self.ping_pong_state *= -1.0
                # Apply amplitude modulation based on ping-pong state
                delayed_sample *= (1.0 - pingpong * 0.4 * self.ping_pong_state)

            # Mix input with delayed sample (with feedback)
            to_buffer = input_buffer[i] + delayed_sample * feedback

            # Write to delay buffer
            self.delay_buffer[self.write_pos] = to_buffer

            # Output is dry + wet mix
            output[i] = input_buffer[i] * (1.0 - mix) + delayed_sample * mix

            # Advance write position
            self.write_pos = (self.write_pos + 1) % self.delay_buffer_size

        return output

    def get_tail_samples(self, params: Dict[str, Any], context: ProcessContext) -> int:
        """
        Calculate delay tail length.

        Args:
            params: Current parameter values
            context: Audio processing context

        Returns:
            Number of tail samples
        """
        delay_time = params.get("delay_time", 0.5)
        feedback = params.get("feedback", 0.5)

        # Calculate approximate number of echoes before decay below audible threshold
        # Each echo is attenuated by feedback amount
        # Tail = delay_time * number_of_echoes
        if feedback < 0.01:
            num_echoes = 1
        else:
            # Calculate when feedback^n < 0.001 (60 dB down)
            num_echoes = int(np.log(0.001) / np.log(feedback))
            num_echoes = min(num_echoes, 100)  # Cap at reasonable value

        tail_samples = int(delay_time * num_echoes * context.sample_rate)
        return tail_samples

    def reset(self):
        """Clear the delay buffer."""
        self.delay_buffer.fill(0.0)
        self.write_pos = 0
        self.ping_pong_state = 1.0


# For compatibility with registry discovery
__all__ = ['Delay']
