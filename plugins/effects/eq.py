"""
8-Band Equalizer effect plugin.

Provides gain control for 8 frequency bands:
60Hz, 150Hz, 400Hz, 1kHz, 2.4kHz, 5kHz, 10kHz, 16kHz
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


class EightBandEQ(AudioProcessor):
    """
    8-band graphic equalizer with fixed frequency centers.

    Uses Butterworth bandpass filters for each frequency band.
    Each band can be boosted or cut independently.
    """

    # Fixed frequency centers for 8 bands (Hz)
    FREQ_BANDS = [60, 150, 400, 1000, 2400, 5000, 10000, 16000]
    BAND_LABELS = ["60Hz", "150Hz", "400Hz", "1kHz", "2.4kHz", "5kHz", "10kHz", "16kHz"]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        # Create parameter spec for each band
        parameters = []
        for i, (freq, label) in enumerate(zip(self.FREQ_BANDS, self.BAND_LABELS)):
            parameters.append(
                ParameterSpec(
                    name=f"band_{i}",
                    type=ParameterType.FLOAT,
                    default=1.0,  # Unity gain
                    min_val=0.0,  # -inf dB (silence)
                    max_val=2.0,  # +6 dB (double amplitude)
                    display_name=label,
                    description=f"Gain for {label} band",
                    unit="x",  # Multiplier
                )
            )

        # Add dry/wet mix parameter
        parameters.append(
            ParameterSpec(
                name="mix",
                type=ParameterType.FLOAT,
                default=1.0,  # Fully wet
                min_val=0.0,
                max_val=1.0,
                display_name="Dry/Wet",
                description="Mix between original and equalized signal",
            )
        )

        return PluginMetadata(
            id="EQ",
            name="8-Band EQ",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Blooper Team",
            description="Graphic equalizer with 8 frequency bands",
            parameters=parameters
        )

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional['Note'],
                context: ProcessContext) -> np.ndarray:
        """
        Apply 8-band EQ to input audio.

        Args:
            input_buffer: Input audio samples
            params: Dictionary with band_0 through band_7 and mix
            note: Not used (effect plugin)
            context: Audio processing context

        Returns:
            Equalized audio
        """
        if input_buffer is None or len(input_buffer) == 0:
            return np.array([], dtype=np.float32)

        # Get mix parameter
        mix = params.get("mix", 1.0)

        # Initialize output buffer
        output = np.zeros_like(input_buffer)

        # Nyquist frequency (half of sample rate)
        nyquist = 0.5 * context.sample_rate

        # Process each band
        for i, center_freq in enumerate(self.FREQ_BANDS):
            gain = params.get(f"band_{i}", 1.0)

            # Skip processing if gain is unity (no change)
            # This matches Blooper4 behavior: only process bands with gain != 1.0
            if gain == 1.0:
                continue

            # Calculate bandpass filter range
            # Band covers center_freq * 0.5 to center_freq * 1.5
            low_freq = center_freq * 0.5
            high_freq = min(center_freq * 1.5, nyquist * 0.95)  # Stay below Nyquist

            # Normalize frequencies
            low_norm = low_freq / nyquist
            high_norm = high_freq / nyquist

            # Design Butterworth bandpass filter (order 1 for smooth response)
            b, a = butter(1, [low_norm, high_norm], btype='band')

            # Apply filter and accumulate with gain
            filtered = lfilter(b, a, input_buffer)
            output += filtered * gain

        # Blooper4 behavior: if no bands were modified, return original (bypass)
        # Otherwise return the accumulated filtered bands
        if not np.any(output):
            processed = input_buffer.copy()
        else:
            processed = output

        # Apply dry/wet mix
        # mix=0.0: fully dry (original)
        # mix=1.0: fully wet (equalized)
        final_output = input_buffer * (1 - mix) + processed * mix

        return final_output


# For compatibility with registry discovery
__all__ = ['EightBandEQ']
