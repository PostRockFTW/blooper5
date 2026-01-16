"""
DSP utilities and building blocks.

Common filters, effects algorithms, etc.
"""
import numpy as np
from numba import jit


class BiquadFilter:
    """
    Biquad filter (lowpass, highpass, bandpass, etc.).

    Used for:
    - Synth filters
    - EQ bands
    - State variable filters
    """

    def __init__(self, filter_type: str, sample_rate: int):
        """
        Initialize biquad filter.

        Args:
            filter_type: "lowpass", "highpass", "bandpass", "notch", "peaking", "allpass"
            sample_rate: Audio sample rate
        """
        self.filter_type = filter_type
        self.sample_rate = sample_rate

        # Biquad coefficients
        self.b0 = 1.0
        self.b1 = 0.0
        self.b2 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0

        # State variables (delay lines)
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0

        # Filter parameters
        self.freq = 1000.0
        self.q = 0.707
        self.gain_db = 0.0

        self._update_coefficients()

    def set_frequency(self, freq: float):
        """
        Set cutoff frequency.

        Args:
            freq: Cutoff frequency in Hz
        """
        self.freq = max(20.0, min(freq, self.sample_rate / 2.0))
        self._update_coefficients()

    def set_q(self, q: float):
        """
        Set filter resonance/Q.

        Args:
            q: Q value (typically 0.5-10.0)
        """
        self.q = max(0.1, min(q, 20.0))
        self._update_coefficients()

    def set_gain(self, gain_db: float):
        """
        Set filter gain (for peaking/shelving filters).

        Args:
            gain_db: Gain in decibels
        """
        self.gain_db = gain_db
        self._update_coefficients()

    def _update_coefficients(self):
        """Recalculate biquad coefficients based on current parameters."""
        w0 = 2.0 * np.pi * self.freq / self.sample_rate
        cos_w0 = np.cos(w0)
        sin_w0 = np.sin(w0)
        alpha = sin_w0 / (2.0 * self.q)

        if self.filter_type == "lowpass":
            self.b0 = (1.0 - cos_w0) / 2.0
            self.b1 = 1.0 - cos_w0
            self.b2 = (1.0 - cos_w0) / 2.0
            a0 = 1.0 + alpha
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha

        elif self.filter_type == "highpass":
            self.b0 = (1.0 + cos_w0) / 2.0
            self.b1 = -(1.0 + cos_w0)
            self.b2 = (1.0 + cos_w0) / 2.0
            a0 = 1.0 + alpha
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha

        elif self.filter_type == "bandpass":
            self.b0 = alpha
            self.b1 = 0.0
            self.b2 = -alpha
            a0 = 1.0 + alpha
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha

        elif self.filter_type == "notch":
            self.b0 = 1.0
            self.b1 = -2.0 * cos_w0
            self.b2 = 1.0
            a0 = 1.0 + alpha
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha

        elif self.filter_type == "peaking":
            A = 10.0 ** (self.gain_db / 40.0)
            self.b0 = 1.0 + alpha * A
            self.b1 = -2.0 * cos_w0
            self.b2 = 1.0 - alpha * A
            a0 = 1.0 + alpha / A
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha / A

        elif self.filter_type == "allpass":
            self.b0 = 1.0 - alpha
            self.b1 = -2.0 * cos_w0
            self.b2 = 1.0 + alpha
            a0 = 1.0 + alpha
            self.a1 = -2.0 * cos_w0
            self.a2 = 1.0 - alpha

        else:
            raise ValueError(f"Unknown filter type: {self.filter_type}")

        # Normalize coefficients
        self.b0 /= a0
        self.b1 /= a0
        self.b2 /= a0
        self.a1 /= a0
        self.a2 /= a0

    def process(self, input_buffer: np.ndarray) -> np.ndarray:
        """
        Process audio through filter.

        Args:
            input_buffer: Input audio

        Returns:
            Filtered audio
        """
        output = np.zeros_like(input_buffer)

        for i in range(len(input_buffer)):
            x = input_buffer[i]

            # Direct Form II transposed
            y = self.b0 * x + self.x1
            self.x1 = self.b1 * x - self.a1 * y + self.x2
            self.x2 = self.b2 * x - self.a2 * y

            output[i] = y

        return output

    def reset(self):
        """Reset filter state (clear delay lines)."""
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0


class ADSREnvelope:
    """
    ADSR envelope generator.

    Provides attack-decay-sustain-release envelope for amplitude modulation.
    """

    def __init__(self, sample_rate: int):
        """
        Initialize ADSR envelope.

        Args:
            sample_rate: Audio sample rate
        """
        self.sample_rate = sample_rate
        self.current_level = 0.0
        self.stage = "idle"  # idle, attack, decay, sustain, release
        self.stage_samples = 0

        # Parameters (in seconds)
        self.attack_time = 0.01
        self.decay_time = 0.1
        self.sustain_level = 0.7
        self.release_time = 0.3

    def note_on(self):
        """Trigger note on (start attack phase)."""
        self.stage = "attack"
        self.stage_samples = 0

    def note_off(self):
        """Trigger note off (start release phase)."""
        self.stage = "release"
        self.stage_samples = 0

    def process(self, num_samples: int) -> np.ndarray:
        """
        Generate envelope values.

        Args:
            num_samples: Number of samples to generate

        Returns:
            Array of envelope values
        """
        output = np.zeros(num_samples, dtype=np.float32)

        for i in range(num_samples):
            if self.stage == "idle":
                self.current_level = 0.0

            elif self.stage == "attack":
                attack_samples = int(self.attack_time * self.sample_rate)
                if attack_samples > 0:
                    self.current_level = self.stage_samples / attack_samples
                else:
                    self.current_level = 1.0

                self.stage_samples += 1
                if self.current_level >= 1.0:
                    self.current_level = 1.0
                    self.stage = "decay"
                    self.stage_samples = 0

            elif self.stage == "decay":
                decay_samples = int(self.decay_time * self.sample_rate)
                if decay_samples > 0:
                    progress = self.stage_samples / decay_samples
                    self.current_level = 1.0 - progress * (1.0 - self.sustain_level)
                else:
                    self.current_level = self.sustain_level

                self.stage_samples += 1
                if self.current_level <= self.sustain_level:
                    self.current_level = self.sustain_level
                    self.stage = "sustain"
                    self.stage_samples = 0

            elif self.stage == "sustain":
                self.current_level = self.sustain_level

            elif self.stage == "release":
                release_samples = int(self.release_time * self.sample_rate)
                start_level = self.current_level
                if release_samples > 0:
                    progress = self.stage_samples / release_samples
                    self.current_level = start_level * (1.0 - progress)
                else:
                    self.current_level = 0.0

                self.stage_samples += 1
                if self.current_level <= 0.0:
                    self.current_level = 0.0
                    self.stage = "idle"
                    self.stage_samples = 0

            output[i] = self.current_level

        return output


@jit(nopython=True)
def apply_adsr_envelope(buffer: np.ndarray,
                       attack: float,
                       decay: float,
                       sustain: float,
                       release: float,
                       gate: bool,
                       sample_rate: int) -> np.ndarray:
    """
    Apply ADSR envelope to audio buffer (JIT-compiled for speed).

    Args:
        buffer: Audio buffer to process
        attack: Attack time (seconds)
        decay: Decay time (seconds)
        sustain: Sustain level (0.0-1.0)
        release: Release time (seconds)
        gate: Note on/off gate signal
        sample_rate: Audio sample rate

    Returns:
        Enveloped audio
    """
    output = np.zeros_like(buffer)
    num_samples = len(buffer)

    # Calculate stage lengths in samples
    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)

    for i in range(num_samples):
        if i < attack_samples:
            # Attack phase
            env = i / max(1, attack_samples)
        elif i < attack_samples + decay_samples:
            # Decay phase
            decay_progress = (i - attack_samples) / max(1, decay_samples)
            env = 1.0 - decay_progress * (1.0 - sustain)
        else:
            # Sustain phase
            env = sustain

        output[i] = buffer[i] * env

    return output


def db_to_linear(db: float) -> float:
    """
    Convert decibels to linear gain.

    Args:
        db: Gain in decibels

    Returns:
        Linear gain value

    Example:
        >>> db_to_linear(0.0)
        1.0
        >>> db_to_linear(-6.0)
        0.5011872336272722
    """
    return 10.0 ** (db / 20.0)


def linear_to_db(linear: float) -> float:
    """
    Convert linear gain to decibels.

    Args:
        linear: Linear gain value

    Returns:
        Gain in decibels

    Example:
        >>> linear_to_db(1.0)
        0.0
        >>> linear_to_db(0.5)
        -6.020599913279624
    """
    if linear <= 0.0:
        return -np.inf
    return 20.0 * np.log10(linear)


def rms_level(buffer: np.ndarray) -> float:
    """
    Calculate RMS level of audio buffer.

    Args:
        buffer: Audio buffer

    Returns:
        RMS level (0.0-1.0+)
    """
    if len(buffer) == 0:
        return 0.0
    return np.sqrt(np.mean(buffer ** 2))


def peak_level(buffer: np.ndarray) -> float:
    """
    Calculate peak level of audio buffer.

    Args:
        buffer: Audio buffer

    Returns:
        Peak level (0.0-1.0+)
    """
    if len(buffer) == 0:
        return 0.0
    return np.max(np.abs(buffer))


def apply_gain(buffer: np.ndarray, gain: float) -> np.ndarray:
    """
    Apply gain to audio buffer.

    Args:
        buffer: Audio buffer
        gain: Gain multiplier

    Returns:
        Gained audio
    """
    return buffer * gain


def apply_pan(buffer_stereo: np.ndarray, pan: float) -> np.ndarray:
    """
    Apply stereo panning to audio buffer using constant power panning.

    Args:
        buffer_stereo: Stereo audio buffer (shape: frames x 2)
        pan: Pan position (-1.0=left, 0.0=center, 1.0=right)

    Returns:
        Panned stereo audio
    """
    # Clamp pan to valid range
    pan = np.clip(pan, -1.0, 1.0)

    # Constant power panning (preserves perceived loudness)
    # Convert pan from -1..1 to 0..1
    pan_normalized = (pan + 1.0) / 2.0

    # Calculate pan angles
    theta = pan_normalized * np.pi / 2.0
    left_gain = np.cos(theta)
    right_gain = np.sin(theta)

    output = buffer_stereo.copy()
    output[:, 0] *= left_gain
    output[:, 1] *= right_gain

    return output


def stereo_from_mono(buffer_mono: np.ndarray) -> np.ndarray:
    """
    Convert mono buffer to stereo by duplicating channels.

    Args:
        buffer_mono: Mono audio buffer (1D array)

    Returns:
        Stereo audio buffer (frames x 2)
    """
    return np.stack([buffer_mono, buffer_mono], axis=-1)


def clip_audio(buffer: np.ndarray, threshold: float = 1.0) -> np.ndarray:
    """
    Hard clip audio to prevent overflow.

    Args:
        buffer: Audio buffer
        threshold: Clipping threshold

    Returns:
        Clipped audio
    """
    return np.clip(buffer, -threshold, threshold)
