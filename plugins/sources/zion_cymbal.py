"""
Zion Jaymes Physical Modeling Cymbal Plugin.

Physical modeling cymbal synthesizer using the Zion Jaymes Method:
- Dual-stage architecture with feedback dispersion and modal resonators
- Impulse generator with FM modulation
- Feedback loop with phase distortion and diffusion
- Modal resonator bank with inharmonic frequency distribution
- Frequency shifting for metallic character

Implementation follows staged approach with toggle switches for each component.
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
from audio.dsp import safety_limiter, phase_distortion, BiquadFilter, calculate_cymbal_modal_ratios


class ZionCymbal(AudioProcessor):
    """
    Physical modeling cymbal synthesizer using Zion Jaymes Method.

    Staged implementation with toggle switches:
    - Stage 1: Impulse generation (baseline)
    - Stage 2: Feedback loop + limiter
    - Stage 3: Phase distortion
    - Stage 4: Diffusion (all-pass filters)
    - Stage 5: Vibrato/chaos
    - Stage 6: Resonator bank
    - Stage 7: Frequency shifting
    """

    def __init__(self):
        """Initialize cymbal synthesizer with stateful buffers."""
        super().__init__()

        # Stage 2: Feedback loop state
        self.feedback_buffer = np.zeros(8192, dtype=np.float32)
        self.fb_write_pos = 0

        # Stage 4: All-pass filters for diffusion (lazy initialization)
        self.allpass_filters = []
        self.allpass_initialized = False

        # Stage 5: Vibrato/chaos state
        self.vibrato_phase = 0.0

        # Stage 6: Resonator bank state (lazy initialization)
        self.resonator_buffers = []
        self.resonator_write_positions = []
        self.resonators_initialized = False
        self.resonator_buffer_size = 8192  # Will be resized if needed

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        parameters = [
            # === STAGE 1: IMPULSE GENERATION ===
            ParameterSpec(
                name="excitation_freq",
                type=ParameterType.FLOAT,
                default=4000.0,
                min_val=2000.0,
                max_val=8000.0,
                display_name="Excitation Freq",
                description="Stick impact brightness frequency",
                unit="Hz",
                logarithmic=True,
            ),
            ParameterSpec(
                name="excitation_decay",
                type=ParameterType.FLOAT,
                default=0.001,
                min_val=0.0001,
                max_val=0.01,
                display_name="Excitation Decay",
                description="Stick attack transient decay time",
                unit="s",
                logarithmic=True,
            ),
            ParameterSpec(
                name="excitation_fm_depth",
                type=ParameterType.FLOAT,
                default=150.0,
                min_val=0.0,
                max_val=500.0,
                display_name="FM Depth",
                description="Stick hardness (FM modulation depth)",
                unit="Hz",
            ),
            ParameterSpec(
                name="decay_time",
                type=ParameterType.FLOAT,
                default=2.0,
                min_val=0.1,
                max_val=10.0,
                display_name="Decay Time",
                description="Overall cymbal sustain envelope",
                unit="s",
            ),
            ParameterSpec(
                name="gain",
                type=ParameterType.FLOAT,
                default=0.7,
                min_val=0.0,
                max_val=1.0,
                display_name="Gain",
                description="Overall output volume",
            ),

            # === STAGE 2: FEEDBACK LOOP ===
            ParameterSpec(
                name="enable_feedback",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Feedback",
                description="Toggle feedback dispersion loop (Stage 2)",
            ),
            ParameterSpec(
                name="feedback_delay",
                type=ParameterType.FLOAT,
                default=5.0,
                min_val=0.1,
                max_val=100.0,
                display_name="Feedback Delay",
                description="Feedback delay determines cymbal size (splash=3ms, gong=80ms)",
                unit="ms",
            ),
            ParameterSpec(
                name="feedback_gain",
                type=ParameterType.FLOAT,
                default=0.7,
                min_val=0.0,
                max_val=0.95,
                display_name="Feedback Gain",
                description="Feedback amount (DANGER ZONE above 0.9)",
            ),

            # === STAGE 3: PHASE DISTORTION ===
            ParameterSpec(
                name="enable_phase_distortion",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Phase Dist",
                description="Toggle phase distortion brightness bloom (Stage 3)",
            ),
            ParameterSpec(
                name="phase_distortion",
                type=ParameterType.FLOAT,
                default=8.0,
                min_val=0.0,
                max_val=20.0,
                display_name="Phase Distortion",
                description="Brightness bloom intensity (velocity-scaled)",
            ),

            # === STAGE 4: DIFFUSION ===
            ParameterSpec(
                name="enable_diffusion",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Diffusion",
                description="Toggle all-pass filter diffusion (Stage 4)",
            ),
            ParameterSpec(
                name="diffusion_amount",
                type=ParameterType.FLOAT,
                default=0.5,
                min_val=0.0,
                max_val=1.0,
                display_name="Diffusion Amount",
                description="Diffusion mix (0=ringy, 1=washy)",
            ),

            # === STAGE 5: VIBRATO/CHAOS ===
            ParameterSpec(
                name="enable_vibrato",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Vibrato",
                description="Toggle chaotic LFO modulation (Stage 5)",
            ),
            ParameterSpec(
                name="vibrato_rate",
                type=ParameterType.FLOAT,
                default=5.0,
                min_val=0.5,
                max_val=20.0,
                display_name="Vibrato Rate",
                description="LFO rate for chaos/shimmer",
                unit="Hz",
            ),
            ParameterSpec(
                name="vibrato_depth",
                type=ParameterType.FLOAT,
                default=15.0,
                min_val=0.0,
                max_val=50.0,
                display_name="Vibrato Depth",
                description="LFO depth for detuning",
                unit="Hz",
            ),

            # === STAGE 6: RESONATOR BANK ===
            ParameterSpec(
                name="enable_resonators",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Resonators",
                description="Toggle modal resonator bank (Stage 6)",
            ),
            ParameterSpec(
                name="base_freq",
                type=ParameterType.FLOAT,
                default=200.0,
                min_val=50.0,
                max_val=500.0,
                display_name="Base Freq",
                description="Fundamental modal frequency",
                unit="Hz",
            ),
            ParameterSpec(
                name="num_modes",
                type=ParameterType.INT,
                default=12,
                min_val=4,
                max_val=16,
                display_name="Num Modes",
                description="Number of parallel resonators",
            ),
            ParameterSpec(
                name="mode_feedback",
                type=ParameterType.FLOAT,
                default=0.85,
                min_val=0.5,
                max_val=0.99,
                display_name="Mode Feedback",
                description="Resonator decay/feedback amount",
            ),

            # === STAGE 7: FREQUENCY SHIFTING ===
            ParameterSpec(
                name="enable_frequency_shift",
                type=ParameterType.BOOL,
                default=True,
                display_name="Enable Freq Shift",
                description="Toggle frequency shifting for inharmonicity (Stage 7)",
            ),
            ParameterSpec(
                name="inharmonicity",
                type=ParameterType.FLOAT,
                default=25.0,
                min_val=0.0,
                max_val=100.0,
                display_name="Inharmonicity",
                description="Frequency shift for metallic/trashy character",
                unit="Hz",
            ),
        ]

        return PluginMetadata(
            id="ZION_CYMBAL",
            name="Zion Cymbal",
            category=PluginCategory.SOURCE,
            version="1.0.0",
            author="Zion Jaymes / Blooper Team",
            description="Physical modeling cymbal using dual-stage architecture with feedback dispersion",
            parameters=parameters
        )

    def _generate_stick_impulse(self,
                                excitation_freq: float,
                                excitation_decay: float,
                                fm_depth: float,
                                velocity: float,
                                num_samples: int,
                                sample_rate: int) -> np.ndarray:
        """
        Generate realistic stick impact impulse.

        High-frequency sine oscillator with FM modulation and near-instant decay
        to simulate the transient of a stick hitting metal.

        Args:
            excitation_freq: Base frequency for stick impact (2-8 kHz)
            excitation_decay: Exponential decay time (<10ms)
            fm_depth: FM modulation depth (stick hardness)
            velocity: MIDI velocity (0-1)
            num_samples: Number of samples to generate
            sample_rate: Sample rate in Hz

        Returns:
            Impulse waveform
        """
        # Time array
        t = np.arange(num_samples, dtype=np.float32) / sample_rate

        # Velocity scaling for FM depth and amplitude
        # Velocity response: soft hits = dull (less FM), loud hits = bright (more FM)
        velocity_fm_scale = velocity ** 2  # Quadratic for aggressive brightness scaling
        scaled_fm_depth = fm_depth * velocity_fm_scale

        # FM modulation envelope: exponential decay for "snap"
        fm_envelope = np.exp(-t / (excitation_decay * 0.5))

        # Phase calculation with FM modulation
        # Base phase
        phase = 2.0 * np.pi * excitation_freq * t

        # Add FM modulation (creates harmonics and brightness)
        # FM modulator is a lower frequency (roughly excitation_freq / 20)
        modulator_freq = excitation_freq / 20.0
        fm_modulation = scaled_fm_depth * fm_envelope * np.sin(2.0 * np.pi * modulator_freq * t)
        phase += fm_modulation

        # Generate carrier sine wave
        impulse = np.sin(phase)

        # Apply fast exponential decay for attack transient
        attack_envelope = np.exp(-t / excitation_decay)
        impulse *= attack_envelope

        # Apply velocity scaling to amplitude
        impulse *= velocity

        return impulse.astype(np.float32)

    def _process_feedback_loop(self,
                               input_signal: np.ndarray,
                               feedback_delay_ms: float,
                               feedback_gain: float,
                               sample_rate: int) -> np.ndarray:
        """
        Process signal through feedback dispersion loop.

        Implements sample-by-sample circular buffer feedback with safety limiting.
        This is the core of the "dispersion" stage that creates the cymbal's
        sustain and complexity.

        Args:
            input_signal: Input audio signal
            feedback_delay_ms: Feedback delay time in milliseconds
            feedback_gain: Feedback amount (0-0.95)
            sample_rate: Sample rate in Hz

        Returns:
            Feedback-processed signal
        """
        # Convert delay time to samples
        delay_samples = int((feedback_delay_ms / 1000.0) * sample_rate)

        # Clamp delay to valid range
        delay_samples = max(1, min(delay_samples, len(self.feedback_buffer) - 1))

        # Create output buffer
        output = np.zeros_like(input_signal)

        # Process sample-by-sample (REQUIRED for feedback causality)
        for i in range(len(input_signal)):
            # Calculate read position (where to read delayed signal from)
            read_pos = (self.fb_write_pos - delay_samples) % len(self.feedback_buffer)

            # Read delayed sample from feedback buffer
            delayed_sample = self.feedback_buffer[read_pos]

            # Mix input with feedback
            mixed_signal = input_signal[i] + delayed_sample * feedback_gain

            # Apply safety limiter BEFORE writing to buffer (CRITICAL!)
            limited_signal = np.tanh(mixed_signal / 0.95) * 0.95

            # Write to feedback buffer
            self.feedback_buffer[self.fb_write_pos] = limited_signal

            # Output is the limited mixed signal
            output[i] = limited_signal

            # Advance write position
            self.fb_write_pos = (self.fb_write_pos + 1) % len(self.feedback_buffer)

        return output

    def _initialize_allpass_filters(self, sample_rate: int):
        """
        Initialize all-pass filters for diffusion (lazy initialization).

        Creates 6 all-pass filters distributed across the frequency spectrum
        to smear the impulse into a washy, noise-like texture.

        Args:
            sample_rate: Sample rate in Hz
        """
        if self.allpass_initialized:
            return

        # All-pass filter frequencies distributed across spectrum
        # Lower Q (0.7) for gentle phase smearing
        allpass_freqs = [800, 1200, 1900, 3400, 5600, 8900]
        allpass_q = 0.7

        self.allpass_filters = []
        for freq in allpass_freqs:
            filter_obj = BiquadFilter(filter_type="allpass", sample_rate=sample_rate)
            filter_obj.set_frequency(freq)
            filter_obj.set_q(allpass_q)
            self.allpass_filters.append(filter_obj)

        self.allpass_initialized = True

    def _process_diffusion(self,
                          input_signal: np.ndarray,
                          diffusion_amount: float,
                          sample_rate: int) -> np.ndarray:
        """
        Process signal through all-pass filter bank for diffusion.

        Creates a washy, noise-like texture by phase-smearing the signal
        through multiple all-pass filters.

        Args:
            input_signal: Input audio signal
            diffusion_amount: Diffusion mix (0=dry, 1=fully diffused)
            sample_rate: Sample rate in Hz

        Returns:
            Diffused signal
        """
        # Lazy initialize filters
        self._initialize_allpass_filters(sample_rate)

        # Process through all-pass filter bank (parallel, then sum)
        diffused = np.zeros_like(input_signal)
        for filter_obj in self.allpass_filters:
            filtered = filter_obj.process(input_signal)
            diffused += filtered

        # Normalize (6 filters summed)
        diffused /= len(self.allpass_filters)

        # Mix dry and wet
        output = input_signal * (1.0 - diffusion_amount) + diffused * diffusion_amount

        return output

    def _process_vibrato(self,
                        input_signal: np.ndarray,
                        vibrato_rate: float,
                        vibrato_depth: float,
                        sample_rate: int) -> np.ndarray:
        """
        Apply chaotic LFO modulation for shimmer and unpredictability.

        Uses sine LFO to modulate amplitude, creating warble and detuning effects.

        Args:
            input_signal: Input audio signal
            vibrato_rate: LFO rate in Hz
            vibrato_depth: LFO depth (amplitude modulation amount)
            sample_rate: Sample rate in Hz

        Returns:
            Modulated signal with vibrato/chaos
        """
        num_samples = len(input_signal)

        # Generate LFO
        t = np.arange(num_samples, dtype=np.float32) / sample_rate

        # Sine LFO for smooth modulation
        lfo = np.sin(2.0 * np.pi * vibrato_rate * t + self.vibrato_phase)

        # Update vibrato phase for continuity across buffer boundaries
        self.vibrato_phase += 2.0 * np.pi * vibrato_rate * num_samples / sample_rate
        self.vibrato_phase = self.vibrato_phase % (2.0 * np.pi)

        # Convert depth parameter to modulation amount (0-1 range)
        # vibrato_depth is in Hz, but we're using it as amplitude modulation
        mod_amount = np.clip(vibrato_depth / 100.0, 0.0, 0.5)

        # Apply amplitude modulation
        # LFO ranges from -1 to +1, so we bias to 0.5 to 1.5 range
        amplitude_mod = 1.0 + (lfo * mod_amount)

        # Apply modulation
        output = input_signal * amplitude_mod

        return output

    def _initialize_resonators(self, num_modes: int, sample_rate: int):
        """
        Initialize resonator buffers (lazy initialization).

        Creates circular buffers for each modal resonator.

        Args:
            num_modes: Number of resonator modes to create
            sample_rate: Sample rate in Hz
        """
        # Calculate required buffer size (enough for lowest frequency mode)
        # Assume lowest freq is around 50 Hz, so period is ~0.02s
        required_size = int(0.5 * sample_rate)  # 0.5 seconds buffer

        # Only reinitialize if configuration changed
        if (self.resonators_initialized and
            len(self.resonator_buffers) == num_modes and
            self.resonator_buffer_size == required_size):
            return

        self.resonator_buffer_size = required_size
        self.resonator_buffers = []
        self.resonator_write_positions = []

        for _ in range(num_modes):
            buffer = np.zeros(self.resonator_buffer_size, dtype=np.float32)
            self.resonator_buffers.append(buffer)
            self.resonator_write_positions.append(0)

        self.resonators_initialized = True

    def _process_resonator_bank(self,
                                input_signal: np.ndarray,
                                base_freq: float,
                                num_modes: int,
                                mode_feedback: float,
                                sample_rate: int) -> np.ndarray:
        """
        Process signal through modal resonator bank.

        Implements parallel comb filters representing vibrational modes
        with inharmonic frequency distribution for metallic character.

        Args:
            input_signal: Input audio signal
            base_freq: Fundamental modal frequency
            num_modes: Number of parallel resonators (4-16)
            mode_feedback: Resonator feedback/decay amount (0.5-0.99)
            sample_rate: Sample rate in Hz

        Returns:
            Resonated signal with modal character
        """
        # Initialize resonators if needed
        self._initialize_resonators(num_modes, sample_rate)

        # Calculate inharmonic modal frequencies
        modal_freqs = calculate_cymbal_modal_ratios(base_freq, num_modes)

        # Create output buffer
        output = np.zeros_like(input_signal)

        # Process through each modal resonator (parallel comb filters)
        for mode_idx in range(num_modes):
            freq = modal_freqs[mode_idx]

            # Calculate delay time in samples (one period)
            delay_samples = int(sample_rate / freq)
            delay_samples = max(1, min(delay_samples, self.resonator_buffer_size - 1))

            # Get buffer and write position for this mode
            buffer = self.resonator_buffers[mode_idx]
            write_pos = self.resonator_write_positions[mode_idx]

            # Process sample-by-sample for this resonator
            mode_output = np.zeros_like(input_signal)
            for i in range(len(input_signal)):
                # Read from delay line
                read_pos = (write_pos - delay_samples) % self.resonator_buffer_size
                delayed_sample = buffer[read_pos]

                # Comb filter: input + feedback
                comb_output = input_signal[i] + delayed_sample * mode_feedback

                # Write to buffer
                buffer[write_pos] = comb_output

                # Output
                mode_output[i] = comb_output

                # Advance write position
                write_pos = (write_pos + 1) % self.resonator_buffer_size

            # Update write position for this mode
            self.resonator_write_positions[mode_idx] = write_pos

            # Sum this mode's output
            output += mode_output

        # Normalize by number of modes
        output /= num_modes

        # Dry nulling circuit: subtract dry signal to isolate resonances
        # This removes the direct signal, leaving only the resonant additions
        output = output - input_signal

        return output

    def _process_frequency_shift(self,
                                 input_signal: np.ndarray,
                                 shift_hz: float,
                                 sample_rate: int) -> np.ndarray:
        """
        Apply frequency shifting for inharmonic/metallic character.

        Uses simple ring modulation for computational efficiency.
        Creates inharmonic sidebands that add "trashy" or "china cymbal" character.

        Args:
            input_signal: Input audio signal
            shift_hz: Frequency shift amount in Hz
            sample_rate: Sample rate in Hz

        Returns:
            Frequency-shifted signal with metallic character
        """
        if shift_hz <= 0.0:
            return input_signal

        # Generate carrier for ring modulation
        num_samples = len(input_signal)
        t = np.arange(num_samples, dtype=np.float32) / sample_rate
        carrier = np.sin(2.0 * np.pi * shift_hz * t)

        # Ring modulation (creates sum and difference frequencies)
        shifted = input_signal * carrier

        # Mix with original for partial effect (too much sounds too digital)
        mix_amount = 0.3  # 30% shifted, 70% original
        output = input_signal * (1.0 - mix_amount) + shifted * mix_amount

        return output

    def process(self,
                input_buffer: Optional[np.ndarray],
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Generate cymbal sound using staged physical modeling.

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

        # === EXTRACT PARAMETERS ===

        # Stage 1: Impulse generation
        excitation_freq = params.get("excitation_freq", 4000.0)
        excitation_decay = params.get("excitation_decay", 0.001)
        fm_depth = params.get("excitation_fm_depth", 150.0)
        decay_time = params.get("decay_time", 2.0)
        gain = params.get("gain", 0.7)

        # Stage 2: Feedback loop
        enable_feedback = params.get("enable_feedback", False)
        feedback_delay = params.get("feedback_delay", 5.0)
        feedback_gain = params.get("feedback_gain", 0.7)

        # Stage 3: Phase distortion
        enable_phase_distortion = params.get("enable_phase_distortion", False)
        phase_distortion_amount = params.get("phase_distortion", 8.0)

        # Stage 4: Diffusion
        enable_diffusion = params.get("enable_diffusion", False)
        diffusion_amount = params.get("diffusion_amount", 0.5)

        # Stage 5: Vibrato
        enable_vibrato = params.get("enable_vibrato", False)
        vibrato_rate = params.get("vibrato_rate", 5.0)
        vibrato_depth = params.get("vibrato_depth", 15.0)

        # Stage 6: Resonators
        enable_resonators = params.get("enable_resonators", False)
        base_freq = params.get("base_freq", 200.0)
        num_modes = params.get("num_modes", 12)
        mode_feedback = params.get("mode_feedback", 0.85)

        # Stage 7: Frequency shift
        enable_frequency_shift = params.get("enable_frequency_shift", False)
        inharmonicity = params.get("inharmonicity", 25.0)

        # === CALCULATE NOTE PARAMETERS ===

        # Velocity scaling (0-1)
        velocity = note.velocity / 127.0

        # Calculate number of samples based on decay time
        num_samples = int(decay_time * context.sample_rate)
        if num_samples <= 0:
            return np.zeros(512, dtype=np.float32)

        # === STAGE 1: GENERATE STICK IMPULSE ===

        output = self._generate_stick_impulse(
            excitation_freq=excitation_freq,
            excitation_decay=excitation_decay,
            fm_depth=fm_depth,
            velocity=velocity,
            num_samples=num_samples,
            sample_rate=context.sample_rate
        )

        # === STAGE 2-7: ADDITIONAL PROCESSING ===

        # Stage 2: Feedback loop
        if enable_feedback:
            output = self._process_feedback_loop(
                input_signal=output,
                feedback_delay_ms=feedback_delay,
                feedback_gain=feedback_gain,
                sample_rate=context.sample_rate
            )

        # Stage 3: Phase distortion (brightness bloom)
        if enable_phase_distortion:
            # Scale distortion amount by velocity (loud hits = more bloom)
            velocity_scaled_distortion = phase_distortion_amount * (velocity ** 2)
            output = phase_distortion(output, amount=velocity_scaled_distortion)

        # Stage 4: Diffusion (all-pass filters)
        if enable_diffusion:
            output = self._process_diffusion(
                input_signal=output,
                diffusion_amount=diffusion_amount,
                sample_rate=context.sample_rate
            )

        # Stage 5: Vibrato/chaos (LFO modulation)
        if enable_vibrato:
            output = self._process_vibrato(
                input_signal=output,
                vibrato_rate=vibrato_rate,
                vibrato_depth=vibrato_depth,
                sample_rate=context.sample_rate
            )

        # Stage 6: Resonator bank (modal resonances)
        if enable_resonators:
            resonator_output = self._process_resonator_bank(
                input_signal=output,
                base_freq=base_freq,
                num_modes=num_modes,
                mode_feedback=mode_feedback,
                sample_rate=context.sample_rate
            )
            # Mix resonator output with original (resonator already does dry nulling)
            # So we add the resonances back to the original signal
            output = output + resonator_output

        # Stage 7: Frequency shifting (inharmonicity)
        if enable_frequency_shift:
            output = self._process_frequency_shift(
                input_signal=output,
                shift_hz=inharmonicity,
                sample_rate=context.sample_rate
            )

        # === APPLY OVERALL DECAY ENVELOPE ===

        # Exponential decay envelope for overall sustain
        t = np.linspace(0, decay_time, num_samples, endpoint=False)
        envelope = np.exp(-5.0 * t / decay_time)
        output *= envelope

        # === APPLY GAIN ===

        output *= gain

        # Soft clip to prevent overflow
        output = np.tanh(output)

        return output.astype(np.float32)

    def reset(self):
        """Reset all plugin state (clear buffers)."""
        # Stage 2: Feedback buffer
        self.feedback_buffer.fill(0.0)
        self.fb_write_pos = 0

        # Stage 4: All-pass filters
        for filter_obj in self.allpass_filters:
            filter_obj.reset()

        # Stage 5: Vibrato phase
        self.vibrato_phase = 0.0

        # Stage 6: Resonator buffers
        for buffer in self.resonator_buffers:
            buffer.fill(0.0)
        self.resonator_write_positions = [0] * len(self.resonator_buffers)


# For compatibility with registry discovery
__all__ = ['ZionCymbal']


# === PRESET CONFIGURATIONS ===
# These presets represent classic cymbal types with optimized parameter settings.
# Users can manually apply these values for specific cymbal sounds.

PRESET_RIDE = {
    "feedback_delay": 15.0,  # Medium size
    "phase_distortion": 4.0,  # Subtle brightness
    "base_freq": 180.0,  # Low fundamental
    "num_modes": 14,  # Dense resonances
    "decay_time": 3.0,  # Long sustain
    "feedback_gain": 0.75,
    "diffusion_amount": 0.4,
    "vibrato_rate": 3.0,
    "vibrato_depth": 10.0,
    "inharmonicity": 15.0,  # Subtle metallic character
    "mode_feedback": 0.88,
}

PRESET_CRASH = {
    "feedback_delay": 25.0,  # Large size
    "phase_distortion": 12.0,  # Strong brightness bloom
    "base_freq": 220.0,  # Medium-high fundamental
    "num_modes": 16,  # Maximum density
    "decay_time": 4.5,  # Very long sustain
    "feedback_gain": 0.85,  # High feedback
    "diffusion_amount": 0.6,  # Washy character
    "vibrato_rate": 5.0,
    "vibrato_depth": 20.0,
    "inharmonicity": 30.0,  # Strong metallic character
    "mode_feedback": 0.92,  # Long modal decay
}

PRESET_SPLASH = {
    "feedback_delay": 3.0,  # Small/fast
    "phase_distortion": 8.0,  # Bright attack
    "base_freq": 400.0,  # High fundamental
    "num_modes": 8,  # Sparse resonances
    "decay_time": 0.8,  # Short sustain
    "feedback_gain": 0.65,
    "diffusion_amount": 0.3,  # More tonal
    "vibrato_rate": 7.0,  # Fast shimmer
    "vibrato_depth": 15.0,
    "inharmonicity": 20.0,
    "mode_feedback": 0.75,  # Quick decay
}

PRESET_CHINA = {
    "feedback_delay": 20.0,  # Medium-large
    "phase_distortion": 15.0,  # Very bright/harsh
    "base_freq": 150.0,  # Low fundamental
    "num_modes": 12,
    "decay_time": 3.5,
    "feedback_gain": 0.80,
    "diffusion_amount": 0.5,
    "vibrato_rate": 6.0,
    "vibrato_depth": 30.0,  # Heavy detuning
    "inharmonicity": 60.0,  # Very trashy/inharmonic
    "mode_feedback": 0.85,
}

PRESET_GONG = {
    "feedback_delay": 80.0,  # Very large
    "phase_distortion": 6.0,  # Dark character
    "base_freq": 80.0,  # Very low fundamental
    "num_modes": 16,  # Maximum density
    "decay_time": 10.0,  # Extremely long sustain
    "feedback_gain": 0.90,  # Very high feedback
    "diffusion_amount": 0.7,  # Maximum wash
    "vibrato_rate": 2.0,  # Slow wobble
    "vibrato_depth": 25.0,
    "inharmonicity": 40.0,  # Deep metallic rumble
    "mode_feedback": 0.95,  # Very long modal decay
}
