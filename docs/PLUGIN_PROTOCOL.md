# Blooper5 Plugin Protocol

## Introduction

This document teaches AI agents (and humans) how to create audio plugins for Blooper5. By the end, you'll understand the plugin contract, parameter system, and testing requirements.

**Target Audience:** AI agents, developers new to Blooper5, third-party plugin creators

---

## Quick Start: Your First Plugin

Let's create a simple gain (volume) plugin in 5 steps:

### Step 1: Create Plugin File
```bash
touch blooper5/plugins/effects/simple_gain.py
```

### Step 2: Import Base Classes
```python
from blooper5.plugins.base import (
    AudioProcessor,
    PluginMetadata,
    ParameterSpec,
    ParameterType,
    PluginCategory,
    ProcessContext
)
import numpy as np
from typing import Optional, Dict, Any
from blooper5.core.models import Note
```

### Step 3: Define Plugin Class and Metadata
```python
class SimpleGain(AudioProcessor):
    """
    Simple gain/volume plugin.
    Multiplies audio signal by gain factor.
    """

    def get_metadata(self) -> PluginMetadata:
        """Define plugin identity and parameters."""
        return PluginMetadata(
            id="SIMPLE_GAIN",
            name="Simple Gain",
            category=PluginCategory.EFFECT,
            version="1.0.0",
            author="Your Name",
            description="Adjusts audio volume",
            parameters=[
                ParameterSpec(
                    name="gain_db",
                    type=ParameterType.FLOAT,
                    default=0.0,
                    min_val=-60.0,
                    max_val=12.0,
                    display_name="Gain (dB)",
                    description="Volume adjustment in decibels"
                )
            ]
        )
```

### Step 4: Implement Audio Processing
```python
    def process(self,
                input_buffer: np.ndarray,
                params: Dict[str, Any],
                note: Optional[Note],
                context: ProcessContext) -> np.ndarray:
        """
        Apply gain to input audio.

        Args:
            input_buffer: Input audio samples (mono, float32)
            params: Dictionary of parameter values
            note: MIDI note info (None for effects)
            context: Audio context (sample rate, BPM, etc.)

        Returns:
            Output audio samples (same shape as input)
        """
        # Extract parameter value
        gain_db = params["gain_db"]

        # Convert dB to linear gain
        gain_linear = 10 ** (gain_db / 20)

        # Apply gain (element-wise multiplication)
        output = input_buffer * gain_linear

        return output
```

### Step 5: Register Plugin
```python
# blooper5/plugins/registry.py

EFFECT_PLUGINS = {
    # ... existing plugins
    "SIMPLE_GAIN": "effects.simple_gain",  # Add this line
}
```

**Done!** Your plugin is now usable in Blooper5. The UI is auto-generated from ParameterSpec.

---

## Plugin Contract: The AudioProcessor Interface

All plugins inherit from `AudioProcessor` and implement three methods:

### 1. get_metadata() → PluginMetadata

**Purpose:** Declares plugin identity and parameters

**Returns:** PluginMetadata object with:
- `id` (str): Unique uppercase identifier (e.g., "DUAL_OSC")
- `name` (str): Display name (e.g., "Dual Oscillator")
- `category` (PluginCategory): SOURCE or EFFECT
- `version` (str): Semantic version (e.g., "1.0.0")
- `author` (str): Your name
- `description` (str): Brief description
- `parameters` (List[ParameterSpec]): All controllable parameters

**Example:**
```python
def get_metadata(self) -> PluginMetadata:
    return PluginMetadata(
        id="MY_PLUGIN",
        name="My Plugin",
        category=PluginCategory.EFFECT,
        version="1.0.0",
        author="AI Agent",
        description="Does something cool",
        parameters=[
            ParameterSpec("mix", ParameterType.FLOAT, default=0.5,
                         min_val=0.0, max_val=1.0, display_name="Dry/Wet")
        ]
    )
```

### 2. process() → np.ndarray

**Purpose:** Core audio processing function

**Signature:**
```python
def process(self,
            input_buffer: np.ndarray,
            params: Dict[str, Any],
            note: Optional[Note],
            context: ProcessContext) -> np.ndarray:
```

**Arguments:**
- `input_buffer` (np.ndarray): Input audio samples
  - **For source plugins**: `None` (generate from scratch)
  - **For effect plugins**: Incoming audio to process
  - **Shape**: (num_samples,) - mono audio
  - **Type**: float32, range -1.0 to 1.0

- `params` (Dict[str, Any]): Current parameter values
  - Keys match `ParameterSpec.name` from metadata
  - Values are already type-converted (float, int, str, bool)
  - Example: `{"gain_db": -6.0, "mix": 0.5}`

- `note` (Optional[Note]): MIDI note information
  - **For source plugins**: The note to generate (pitch, velocity, duration)
  - **For effect plugins**: `None` (not used)
  - **Fields**: `tick`, `pitch` (0-127), `duration` (ticks), `velocity` (0-127)

- `context` (ProcessContext): Audio context
  - `sample_rate` (int): Sample rate in Hz (usually 44100)
  - `bpm` (float): Current tempo
  - `tpqn` (int): Ticks per quarter note (usually 480)
  - `current_tick` (int): Playhead position in ticks

**Returns:**
- `np.ndarray`: Output audio samples
  - **Shape**: (num_samples,) - mono audio
  - **Type**: float32, range -1.0 to 1.0 (values outside clipped)
  - **Length**:
    - Sources: Based on note duration
    - Effects: Same as input_buffer length

**Requirements:**
1. **Pure function**: No side effects, same inputs = same output
2. **Thread-safe**: May be called from audio process
3. **Fast**: Runs in real-time audio callback (<10ms for 512 samples)
4. **Amplitude**: Keep output in -1.0 to 1.0 range

### 3. get_tail_samples() → int (Optional)

**Purpose:** Declare how many extra samples effect produces after input ends

**Only needed for:** Reverb, delay, and other time-based effects

**Returns:** Number of tail samples (0 if no tail)

**Example:**
```python
def get_tail_samples(self, params: Dict[str, Any], context: ProcessContext) -> int:
    """Calculate reverb tail length."""
    decay_time = params["decay_time"]  # seconds
    return int(decay_time * context.sample_rate)
```

**Default:** Returns 0 (no tail) if not overridden

---

## Parameter System

Parameters are defined using `ParameterSpec` in `get_metadata()`.

### ParameterSpec Fields

```python
ParameterSpec(
    name="param_name",           # Internal key (snake_case)
    type=ParameterType.FLOAT,    # Data type
    default=0.5,                 # Initial value
    min_val=0.0,                 # Minimum (for numeric types)
    max_val=1.0,                 # Maximum (for numeric types)
    display_name="Parameter",    # UI label
    description="Does X",        # Tooltip text (optional)
    enum_values=["A", "B"],      # For ENUM type (optional)
    unit="Hz",                   # Display unit (optional)
    logarithmic=False            # Use log scale slider (optional)
)
```

### Parameter Types

| ParameterType | Python Type | Use Case | Required Fields |
|--------------|-------------|----------|----------------|
| FLOAT | float | Continuous values | min_val, max_val, default |
| INT | int | Discrete values | min_val, max_val, default |
| BOOL | bool | On/Off switches | default |
| ENUM | str | Select from list | default, enum_values |

### Parameter Examples

**Frequency (Logarithmic):**
```python
ParameterSpec(
    name="cutoff_freq",
    type=ParameterType.FLOAT,
    default=1000.0,
    min_val=20.0,
    max_val=20000.0,
    display_name="Cutoff",
    unit="Hz",
    logarithmic=True  # Slider uses log scale
)
```

**Waveform Selection:**
```python
ParameterSpec(
    name="waveform",
    type=ParameterType.ENUM,
    default="SAW",
    enum_values=["SINE", "SAW", "SQUARE", "TRIANGLE"],
    display_name="Waveform"
)
```

**Mix (Dry/Wet):**
```python
ParameterSpec(
    name="mix",
    type=ParameterType.FLOAT,
    default=0.5,
    min_val=0.0,
    max_val=1.0,
    display_name="Dry/Wet"
)
```

**Enable/Disable:**
```python
ParameterSpec(
    name="enabled",
    type=ParameterType.BOOL,
    default=True,
    display_name="Enable"
)
```

---

## Source Plugin Pattern

**Purpose:** Generate audio from scratch (synthesizers, drum machines)

**Key Points:**
- `input_buffer` is `None` (ignored)
- `note` contains pitch, velocity, duration
- Must calculate duration from note and context
- Output length depends on note duration

**Template:**
```python
class MySynth(AudioProcessor):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="MY_SYNTH",
            category=PluginCategory.SOURCE,
            # ... parameters
        )

    def process(self, input_buffer, params, note, context):
        # Calculate note duration in samples
        duration_seconds = (note.duration / context.tpqn) * (60 / context.bpm)
        num_samples = int(duration_seconds * context.sample_rate)

        # Calculate frequency from MIDI pitch
        frequency = 440 * (2 ** ((note.pitch - 69) / 12))

        # Generate waveform
        t = np.arange(num_samples) / context.sample_rate
        output = np.sin(2 * np.pi * frequency * t)

        # Apply velocity
        velocity_scale = note.velocity / 127
        output *= velocity_scale

        return output
```

---

## Effect Plugin Pattern

**Purpose:** Process existing audio (reverb, EQ, distortion)

**Key Points:**
- `input_buffer` contains audio to process
- `note` is `None` (ignored)
- Output must be same length as input
- Implement `get_tail_samples()` if effect has decay

**Template:**
```python
class MyEffect(AudioProcessor):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="MY_EFFECT",
            category=PluginCategory.EFFECT,
            # ... parameters
        )

    def process(self, input_buffer, params, note, context):
        # Process input audio
        processed = self._apply_effect(input_buffer, params)

        # Apply dry/wet mix
        mix = params.get("mix", 1.0)
        output = input_buffer * (1 - mix) + processed * mix

        return output

    def get_tail_samples(self, params, context):
        # Return tail length if applicable
        return 0
```

---

## Common DSP Patterns

### Oscillator (Waveform Generation)

```python
def _generate_waveform(self, waveform_type: str, frequency: float,
                       num_samples: int, sample_rate: int) -> np.ndarray:
    """Generate basic waveforms."""
    t = np.arange(num_samples) / sample_rate
    phase = 2 * np.pi * frequency * t

    if waveform_type == "SINE":
        return np.sin(phase)
    elif waveform_type == "SAW":
        return 2 * (t * frequency % 1.0) - 1
    elif waveform_type == "SQUARE":
        return np.sign(np.sin(phase))
    elif waveform_type == "TRIANGLE":
        return 2 * np.abs(2 * (t * frequency % 1.0) - 1) - 1
```

### Filter (Low-pass, High-pass)

```python
from scipy.signal import butter, lfilter

def _apply_lowpass(self, audio: np.ndarray, cutoff: float,
                   sample_rate: int) -> np.ndarray:
    """Apply Butterworth low-pass filter."""
    nyquist = sample_rate / 2
    normal_cutoff = cutoff / nyquist
    b, a = butter(4, normal_cutoff, btype='low', analog=False)
    return lfilter(b, a, audio)
```

### ADSR Envelope

```python
def _apply_adsr(self, audio: np.ndarray, attack: float, decay: float,
                sustain: float, release: float, sample_rate: int) -> np.ndarray:
    """Apply ADSR envelope."""
    total_samples = len(audio)

    attack_samples = int(attack * sample_rate)
    decay_samples = int(decay * sample_rate)
    release_samples = int(release * sample_rate)
    sustain_samples = total_samples - attack_samples - decay_samples - release_samples

    envelope = np.concatenate([
        np.linspace(0, 1, attack_samples),  # Attack
        np.linspace(1, sustain, decay_samples),  # Decay
        np.full(sustain_samples, sustain),  # Sustain
        np.linspace(sustain, 0, release_samples)  # Release
    ])

    return audio * envelope[:total_samples]
```

---

## Testing Your Plugin

Every plugin must have tests in `tests/plugins/test_<plugin_name>.py`

### Basic Test Template

```python
import pytest
import numpy as np
from blooper5.plugins.sources.my_synth import MySynth
from blooper5.core.models import Note
from blooper5.plugins.base import ProcessContext

def test_my_synth_generates_audio():
    """Test that plugin generates audio output."""
    plugin = MySynth()
    params = {"waveform": "SINE", "volume": 0.5}
    note = Note(tick=0, pitch=69, duration=480, velocity=100)  # A4
    context = ProcessContext(sample_rate=44100, bpm=120, tpqn=480)

    output = plugin.process(None, params, note, context)

    # Test 1: Output exists
    assert output is not None

    # Test 2: Correct length (1 second note at 120 BPM)
    expected_samples = 44100  # 1 second
    assert len(output) == expected_samples

    # Test 3: Amplitude in valid range
    assert np.max(np.abs(output)) <= 1.0

    # Test 4: Audio is not silent
    assert np.mean(np.abs(output)) > 0.001

def test_my_synth_frequency():
    """Test that plugin generates correct frequency."""
    plugin = MySynth()
    params = {"waveform": "SINE"}
    note = Note(tick=0, pitch=69, duration=480, velocity=127)  # A4 = 440 Hz
    context = ProcessContext(sample_rate=44100, bpm=120, tpqn=480)

    output = plugin.process(None, params, note, context)

    # FFT to verify frequency
    fft = np.fft.rfft(output)
    freqs = np.fft.rfftfreq(len(output), 1/44100)
    peak_freq = freqs[np.argmax(np.abs(fft))]

    # Should be 440 Hz ± 5 Hz tolerance
    assert 435 <= peak_freq <= 445
```

### Effect Test Template

```python
def test_my_effect_preserves_length():
    """Test that effect doesn't change audio length."""
    plugin = MyEffect()
    params = {"mix": 0.5}
    context = ProcessContext(sample_rate=44100, bpm=120, tpqn=480)

    # Create test input
    input_buffer = np.random.randn(4410)  # 0.1 second noise

    output = plugin.process(input_buffer, params, None, context)

    assert len(output) == len(input_buffer)

def test_my_effect_dry_wet():
    """Test that dry/wet mix works correctly."""
    plugin = MyEffect()
    context = ProcessContext(sample_rate=44100, bpm=120, tpqn=480)
    input_buffer = np.random.randn(1000)

    # 100% dry (mix=0.0)
    output_dry = plugin.process(input_buffer, {"mix": 0.0}, None, context)
    np.testing.assert_array_almost_equal(output_dry, input_buffer)

    # 100% wet (mix=1.0)
    output_wet = plugin.process(input_buffer, {"mix": 1.0}, None, context)
    # Should be different from input
    assert not np.allclose(output_wet, input_buffer)
```

---

## File Length Guidelines

- **Target**: 150-200 lines total
- **Max**: 300 lines (if complex DSP)
- **If exceeding 300 lines**: Extract helper functions to `plugins/utils/`

**Example:**
```
# Before: dual_osc.py (350 lines)
# After:
#   - dual_osc.py (180 lines) - Main plugin
#   - plugins/utils/oscillators.py (100 lines) - Shared waveform functions
#   - plugins/utils/envelopes.py (70 lines) - ADSR, etc.
```

---

## Common Pitfalls

### 1. Forgetting to Handle Edge Cases
```python
# BAD: Assumes parameter exists
gain = params["gain_db"]

# GOOD: Provide default
gain = params.get("gain_db", 0.0)
```

### 2. Returning Wrong Shape
```python
# BAD: Returns stereo
output = np.array([left_channel, right_channel])

# GOOD: Returns mono
output = (left_channel + right_channel) / 2
```

### 3. Not Clamping Output
```python
# BAD: Can exceed ±1.0
output = input_buffer * 10

# GOOD: Clamp to safe range
output = np.clip(input_buffer * 10, -1.0, 1.0)
```

### 4. Slow Processing
```python
# BAD: Python loop (slow)
output = np.zeros_like(input_buffer)
for i in range(len(input_buffer)):
    output[i] = input_buffer[i] * gain

# GOOD: NumPy vectorized (fast)
output = input_buffer * gain
```

---

## Plugin Checklist

Before submitting a plugin:
- [ ] Inherits from `AudioProcessor`
- [ ] Implements `get_metadata()` with all ParameterSpec
- [ ] Implements `process()` with correct signature
- [ ] Implements `get_tail_samples()` if time-based effect
- [ ] Returns audio in -1.0 to 1.0 range
- [ ] Processing is fast (use NumPy, avoid loops)
- [ ] Has tests in `tests/plugins/`
- [ ] Tests verify output length, amplitude, frequency (if applicable)
- [ ] File is under 300 lines
- [ ] Registered in `plugins/registry.py`
- [ ] Docstrings on class and methods

---

## Next Steps

1. **Study existing plugins**: See `plugins/sources/dual_osc.py` for reference
2. **Run tests**: `pytest tests/plugins/test_dual_osc.py -v`
3. **Create your plugin**: Follow template above
4. **Test thoroughly**: Write unit tests first (TDD)
5. **Ask questions**: Reference ARCHITECTURE.md, CONVENTIONS.md if stuck

Welcome to Blooper5 plugin development!
