"""
Dual Oscillator synthesizer plugin.

Two oscillators with independent waveform selection, tuning,
and mixing. Includes lowpass filter and AR envelope.
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
    ProcessContext,
    midi_to_freq
)
from core.models import Note


class DualOscillator(AudioProcessor):
    """
    Two-oscillator subtractive synth.

    Features:
    - Two independent oscillators with waveform selection
    - Interval and detune control
    - Lowpass filter
    - AR envelope
    """

    # Waveform types
    WAVEFORMS = ["SINE", "SQUARE", "SAW", "TRIANGLE", "NONE"]

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="DUAL_OSC",
            name="Dual Oscillator",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Blooper Team",
            description="Two-oscillator synthesizer with filter and envelope",
            parameters=[
                # Oscillator 1
                ParameterSpec(
                    name="osc1_type",
                    type=ParameterType.ENUM,
                    default="SAW",
                    enum_values=self.WAVEFORMS,
                    display_name="Osc 1 Wave",
                    description="Oscillator 1 waveform",
                ),
                # Oscillator 2
                ParameterSpec(
                    name="osc2_type",
                    type=ParameterType.ENUM,
                    default="SINE",
                    enum_values=self.WAVEFORMS,
                    display_name="Osc 2 Wave",
                    description="Oscillator 2 waveform",
                ),
                ParameterSpec(
                    name="osc2_interval",
                    type=ParameterType.INT,
                    default=0,
                    min_val=-24,
                    max_val=24,
                    display_name="Osc 2 Interval",
                    description="Pitch interval in semitones",
                    unit="st",
                ),
                ParameterSpec(
                    name="osc2_detune",
                    type=ParameterType.FLOAT,
                    default=10.0,
                    min_val=-50.0,
                    max_val=50.0,
                    display_name="Osc 2 Detune",
                    description="Fine tuning in cents",
                    unit="cents",
                ),
                ParameterSpec(
                    name="osc_mix",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.0,
                    max_val=1.0,
                    display_name="Osc Mix",
                    description="Mix between osc1 and osc2",
                ),
                # Filter
                ParameterSpec(
                    name="filter_cutoff",
                    type=ParameterType.FLOAT,
                    default=5000.0,
                    min_val=50.0,
                    max_val=12000.0,
                    display_name="Filter Cutoff",
                    description="Lowpass filter cutoff frequency",
                    unit="Hz",
                    logarithmic=True,
                ),
                # Envelope
                ParameterSpec(
                    name="attack",
                    type=ParameterType.FLOAT,
                    default=0.01,
                    min_val=0.001,
                    max_val=2.0,
                    display_name="Attack",
                    description="Attack time",
                    unit="s",
                ),
                ParameterSpec(
                    name="length",
                    type=ParameterType.FLOAT,
                    default=0.5,
                    min_val=0.01,
                    max_val=5.0,
                    display_name="Length",
                    description="Note decay length",
                    unit="s",
                ),
                # Global
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

    def _generate_waveform(self, waveform_type: str, frequency: float,
                          num_samples: int, sample_rate: int) -> np.ndarray:
        """
        Generate waveform samples.

        Args:
            waveform_type: Type of waveform (SINE, SQUARE, SAW, TRIANGLE, NONE)
            frequency: Frequency in Hz
            num_samples: Number of samples to generate
            sample_rate: Sample rate in Hz

        Returns:
            Waveform samples
        """
        if waveform_type == "NONE":
            return np.zeros(num_samples, dtype=np.float32)

        # Generate time array
        t = np.arange(num_samples) / sample_rate
        phase = 2 * np.pi * frequency * t

        if waveform_type == "SINE":
            return np.sin(phase).astype(np.float32)
        elif waveform_type == "SQUARE":
            return np.sign(np.sin(phase)).astype(np.float32)
        elif waveform_type == "SAW":
            # Sawtooth: 2 * (t * freq % 1) - 1
            return (2.0 * ((frequency * t) % 1.0) - 1.0).astype(np.float32)
        elif waveform_type == "TRIANGLE":
            # Triangle: 2 * abs(2 * (t * freq % 1) - 1) - 1
            return (2.0 * np.abs(2.0 * ((frequency * t) % 1.0) - 1.0) - 1.0).astype(np.float32)
        else:
            return np.zeros(num_samples, dtype=np.float32)

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Generate dual oscillator audio.

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
        attack = params.get("attack", 0.01)
        decay = params.get("length", 0.5)

        # Calculate total duration
        total_dur = attack + decay
        num_samples = int(total_dur * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        # Calculate pitch multiplier
        pitch_multiplier = 2.0 ** ((note.note - root_note + transpose) / 12.0)
        freq1 = 261.63 * pitch_multiplier  # C4 = 261.63 Hz

        # Oscillator 2 frequency (with interval and detune)
        interval = params.get("osc2_interval", 0)
        detune_cents = params.get("osc2_detune", 10.0)
        freq2 = freq1 * (2.0 ** ((interval + (detune_cents / 100.0)) / 12.0))

        # Generate oscillators
        osc1_type = params.get("osc1_type", "SAW")
        osc2_type = params.get("osc2_type", "SINE")
        osc_mix = params.get("osc_mix", 0.5)

        buf1 = self._generate_waveform(osc1_type, freq1, num_samples, context.sample_rate)
        buf2 = self._generate_waveform(osc2_type, freq2, num_samples, context.sample_rate)

        # Mix oscillators
        combined = buf1 * (1.0 - osc_mix) + buf2 * osc_mix

        # Apply lowpass filter
        cutoff = params.get("filter_cutoff", 5000.0)
        try:
            nyquist = 0.5 * context.sample_rate
            normalized_cutoff = np.clip(cutoff / nyquist, 0.01, 0.99)
            b, a = butter(1, normalized_cutoff, btype='low')
            filtered = lfilter(b, a, combined)
        except:
            filtered = combined

        # Apply AR envelope
        envelope = np.ones(num_samples, dtype=np.float32)

        # Attack phase
        attack_samples = int(attack * context.sample_rate)
        if attack_samples > 0 and attack_samples < num_samples:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)

        # Decay phase (exponential)
        if attack_samples < num_samples:
            decay_samples = num_samples - attack_samples
            t_decay = np.linspace(0, decay, decay_samples)
            envelope[attack_samples:] = np.exp(-6.0 * t_decay / decay)

        # Apply envelope, gain, and velocity
        velocity_scale = note.velocity / 127.0
        output = filtered * envelope * gain * velocity_scale

        return output.astype(np.float32)


# For compatibility with registry discovery
__all__ = ['DualOscillator']
