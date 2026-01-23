"""
Voice management system for live MIDI input.

Implements a hybrid pre-rendering approach that:
1. Pre-renders notes in 2-second chunks when note_on is received
2. Tracks playback position in the buffer
3. Extends the buffer if notes are held longer than 2 seconds
4. Handles note_off by applying release envelope
5. Reuses the existing Piano Roll streaming pattern
"""

import numpy as np
from typing import Dict, Tuple, Optional, Any
from core.models import Note
from plugins.base import ProcessContext


# Symbol to waveform name mapping for DualOscillator
WAVEFORM_SYMBOL_MAP = {
    "~": "SINE",
    "[]": "SQUARE",
    "|/": "SAW",
    "/\\": "TRIANGLE",
    "-": "NONE"
}


def translate_waveform_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate symbolic waveform notation to proper names.

    Args:
        params: Source parameters that may contain symbolic notation

    Returns:
        Parameters with symbols translated to names
    """
    translated = dict(params)

    # Translate oscillator types if they're symbolic
    for key in ['osc1_type', 'osc2_type']:
        if key in translated:
            value = translated[key]
            if value in WAVEFORM_SYMBOL_MAP:
                translated[key] = WAVEFORM_SYMBOL_MAP[value]

    return translated


class LiveVoice:
    """Manages state for a single playing note."""

    def __init__(self, track_idx: int, note_num: int, velocity: int,
                 synth, source_params: dict, context: ProcessContext,
                 initial_duration: float = 2.0):
        """
        Initialize a live voice.

        Args:
            track_idx: Index of the track this voice belongs to
            note_num: MIDI note number (0-127)
            velocity: MIDI velocity (0-127)
            synth: Synthesizer instance to use for rendering
            source_params: Source parameters for the synth
            context: Song context (tempo, sample_rate, etc.)
            initial_duration: Initial buffer duration in seconds (default 2.0)
        """
        self.track_idx = track_idx
        self.note_num = note_num
        self.velocity = velocity
        self.synth = synth
        self.source_params = source_params
        self.context = context
        self.sample_rate = context.sample_rate

        # State tracking
        self.position = 0  # Current playback position in samples
        self.is_released = False  # Has note_off been received?
        self.is_finished = False  # Has playback completed?

        # Pre-render initial buffer
        self.audio_buffer = self._render_buffer(initial_duration)

    def _render_buffer(self, duration: float) -> np.ndarray:
        """
        Pre-render audio buffer using synth.process().

        Args:
            duration: Duration to render in seconds

        Returns:
            Rendered audio as numpy array (stereo, shape: [samples, 2])
        """
        # Convert duration from seconds to beats
        # Note.duration is in BEATS, not seconds
        bpm = self.context.bpm
        duration_in_beats = duration * (bpm / 60.0)

        # Create temporary Note object for rendering
        temp_note = Note(
            note=self.note_num,
            start=0,
            duration=duration_in_beats,  # In beats
            velocity=self.velocity
        )

        # Translate symbolic waveform notation to proper names
        translated_params = translate_waveform_params(self.source_params)

        # Override synth parameters to force long decay
        # Many synths use 'length' or 'decay' parameter for envelope duration
        override_params = dict(translated_params)
        override_params['length'] = duration  # In seconds
        override_params['decay'] = duration  # In seconds (for synths that use 'decay')

        # Render audio using synth with overridden parameters
        audio = self.synth.process(None, override_params, temp_note, self.context)

        # Ensure stereo format
        if audio.ndim == 1:
            audio = np.column_stack([audio, audio])

        return audio

    def get_next_chunk(self, frames: int) -> np.ndarray:
        """
        Get next audio chunk for output.

        Args:
            frames: Number of frames to retrieve

        Returns:
            Audio chunk as numpy array (stereo, shape: [frames, 2])
        """
        # Check if we need to extend the buffer
        if not self.is_released and self.position + frames >= len(self.audio_buffer):
            self._extend_buffer()

        # Get chunk from buffer
        end_pos = min(self.position + frames, len(self.audio_buffer))
        chunk = self.audio_buffer[self.position:end_pos]

        # Update position
        self.position = end_pos

        # Check if finished
        if self.position >= len(self.audio_buffer):
            self.is_finished = True

        # Pad with zeros if chunk is shorter than requested frames
        if len(chunk) < frames:
            padding = np.zeros((frames - len(chunk), 2), dtype=np.float32)
            chunk = np.vstack([chunk, padding])

        return chunk

    def _extend_buffer(self):
        """Extend buffer by 1 second if held longer than current buffer."""
        extension_duration = 1.0  # Extend by 1 second chunks
        extension = self._render_buffer(extension_duration)

        # Append to existing buffer
        self.audio_buffer = np.vstack([self.audio_buffer, extension])

    def note_off(self, release_time: float = 0.3):
        """
        Apply release envelope when note_off is received.

        Args:
            release_time: Duration of release envelope in seconds
        """
        if self.is_released:
            return  # Already released

        self.is_released = True

        # Calculate decay length in samples
        decay_length = int(release_time * self.sample_rate)

        # Calculate how much buffer remains from current position
        remaining_length = len(self.audio_buffer) - self.position

        # Adjust decay length if it's longer than remaining buffer
        decay_length = min(decay_length, remaining_length)

        if decay_length > 0:
            # Apply exponential decay envelope
            t = np.linspace(0, release_time, decay_length)
            envelope = np.exp(-6.0 * t / release_time)

            # Apply envelope to remaining buffer
            for i in range(decay_length):
                self.audio_buffer[self.position + i] *= envelope[i]

            # Truncate buffer after release (save memory)
            self.audio_buffer = self.audio_buffer[:self.position + decay_length]

    def is_complete(self) -> bool:
        """Check if voice has finished playing."""
        return self.is_finished


class VoiceManager:
    """Manages collection of active live MIDI voices."""

    def __init__(self):
        """Initialize the voice manager."""
        # Active voices: key is (track_idx, note_num)
        self.active_voices: Dict[Tuple[int, int], LiveVoice] = {}

    def note_on(self, track_idx: int, note_num: int, velocity: int,
                synth, source_params: dict, context: ProcessContext):
        """
        Handle note_on event by creating a new voice.

        Args:
            track_idx: Index of the track
            note_num: MIDI note number
            velocity: MIDI velocity
            synth: Synthesizer instance
            source_params: Source parameters for the synth
            context: Song context
        """
        key = (track_idx, note_num)

        # If voice already exists (rapid retriggering), apply quick release
        if key in self.active_voices:
            self.active_voices[key].note_off(release_time=0.05)
            # Remove immediately to create new voice
            del self.active_voices[key]

        # Create new voice
        voice = LiveVoice(
            track_idx=track_idx,
            note_num=note_num,
            velocity=velocity,
            synth=synth,
            source_params=source_params,
            context=context
        )

        self.active_voices[key] = voice

    def note_off(self, track_idx: int, note_num: int):
        """
        Handle note_off event by triggering release envelope.

        Args:
            track_idx: Index of the track
            note_num: MIDI note number
        """
        key = (track_idx, note_num)

        if key in self.active_voices:
            self.active_voices[key].note_off()

    def render_frame(self, frames: int, song, mixer_strips: list,
                    any_solo_active: bool) -> Tuple[np.ndarray, np.ndarray]:
        """
        Render all active voices for the current frame.

        Args:
            frames: Number of frames to render
            song: Song object with tracks
            mixer_strips: List of mixer strip objects
            any_solo_active: Whether any track is soloed

        Returns:
            Tuple of (left_channel, right_channel) numpy arrays
        """
        # Initialize output buffers
        output_left = np.zeros(frames, dtype=np.float32)
        output_right = np.zeros(frames, dtype=np.float32)

        # Track voices to remove after rendering
        voices_to_remove = []

        # Render each active voice
        for key, voice in self.active_voices.items():
            track_idx, note_num = key

            # Check if track exists
            if track_idx >= len(song.tracks):
                voices_to_remove.append(key)
                continue

            track = song.tracks[track_idx]

            # Get mixer strip for this track
            mixer_strip = None
            if track_idx < len(mixer_strips):
                mixer_strip = mixer_strips[track_idx]

            # Check mute/solo state
            is_muted = mixer_strip and mixer_strip.muted
            is_soloed = mixer_strip and mixer_strip.solo

            # Skip if muted or if solo is active on another track
            if is_muted or (any_solo_active and not is_soloed):
                voices_to_remove.append(key)
                continue

            # Get audio chunk from voice
            chunk = voice.get_next_chunk(frames)

            # Apply volume and panning
            volume = mixer_strip.volume if mixer_strip else 1.0
            pan = mixer_strip.pan if mixer_strip else 0.0

            # Constant-power panning
            pan_radians = (pan + 1.0) * np.pi / 4.0  # Map [-1, 1] to [0, π/2]
            left_gain = np.cos(pan_radians) * volume
            right_gain = np.sin(pan_radians) * volume

            # Mix into output buffers
            output_left += chunk[:, 0] * left_gain
            output_right += chunk[:, 1] * right_gain

            # Remove voice if complete
            if voice.is_complete():
                voices_to_remove.append(key)

        # Clean up finished voices
        for key in voices_to_remove:
            if key in self.active_voices:
                del self.active_voices[key]

        return output_left, output_right

    def clear_all(self):
        """Clear all active voices (on transport stop/loop)."""
        self.active_voices.clear()

    def clear_track(self, track_idx: int):
        """
        Clear all voices for a specific track.

        Args:
            track_idx: Index of the track to clear
        """
        voices_to_remove = [
            key for key in self.active_voices.keys()
            if key[0] == track_idx
        ]

        for key in voices_to_remove:
            del self.active_voices[key]
