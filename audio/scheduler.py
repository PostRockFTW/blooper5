"""
Note scheduler for real-time audio playback.

Based on Blooper4's tick-based master clock system.
"""
from plugins.base import ProcessContext


class NoteScheduler:
    """
    Tick-based note scheduler (Blooper4-style).

    Advances playback position in musical ticks and triggers notes
    when the playhead crosses their position.
    """

    def __init__(self, sample_rate=44100):
        """
        Initialize scheduler.

        Args:
            sample_rate: Audio sample rate in Hz
        """
        self.sample_rate = sample_rate
        self.current_tick = 0.0
        self.bpm = 120.0
        self.tpqn = 480  # Ticks per quarter note

    def advance(self, num_samples):
        """
        Advance playback position by num_samples.

        Args:
            num_samples: Number of audio samples to advance
        """
        # Calculate time advancement
        dt_seconds = num_samples / self.sample_rate
        dt_ms = dt_seconds * 1000.0

        # Convert to ticks: ticks_per_ms = (BPM * TPQN) / 60000
        ticks_per_ms = (self.bpm * self.tpqn) / 60000.0
        self.current_tick += dt_ms * ticks_per_ms

    def check_and_trigger(self, notes, synth, params, prev_tick, current_tick):
        """
        Check which notes should trigger in this time window.

        Args:
            notes: List of Note objects to check
            synth: Synthesizer instance to generate audio
            params: Synth parameter dictionary
            prev_tick: Previous playback position in ticks
            current_tick: Current playback position in ticks

        Returns:
            List of triggered voice dictionaries with 'audio', 'position', and 'note' keys
        """
        triggered = []

        # Create process context for audio generation
        context = ProcessContext(
            sample_rate=self.sample_rate,
            bpm=self.bpm,
            tpqn=self.tpqn,
            current_tick=int(current_tick)
        )

        for note in notes:
            # Convert note.start (beats) to ticks
            note_tick = note.start * self.tpqn

            # Check if note triggers in this window
            if prev_tick <= note_tick < current_tick:
                # Generate full audio for this note
                audio = synth.process(None, params, note, context)

                triggered.append({
                    'audio': audio,
                    'position': 0,  # Playback position in buffer
                    'note': note
                })

        return triggered

    def reset(self):
        """Reset scheduler to beginning."""
        self.current_tick = 0.0
