"""
Note scheduler for real-time audio playback.

Based on Blooper4's tick-based master clock system.
"""
from plugins.base import ProcessContext
from typing import Optional, Tuple


class NoteScheduler:
    """
    Tick-based note scheduler (Blooper4-style).

    Advances playback position in musical ticks and triggers notes
    when the playhead crosses their position.

    Supports per-measure tempo changes via MeasureMetadata.
    """

    def __init__(self, sample_rate=44100, measure_metadata=None):
        """
        Initialize scheduler.

        Args:
            sample_rate: Audio sample rate in Hz
            measure_metadata: Optional tuple of MeasureMetadata for per-measure tempo
        """
        self.sample_rate = sample_rate
        self.current_tick = 0.0
        self.elapsed_time = 0.0  # Actual elapsed time in seconds
        self.bpm = 120.0  # Default/fallback BPM
        self.tpqn = 480  # Ticks per quarter note
        self.measure_metadata = measure_metadata  # Per-measure tempo/time sig data

    def get_bpm_at_tick(self, tick: float) -> float:
        """
        Get the BPM at a specific tick position.

        Args:
            tick: Tick position to query

        Returns:
            BPM at that position (uses measure_metadata if available, else fallback)
        """
        if not self.measure_metadata:
            return self.bpm

        # Find which measure contains this tick
        for measure in self.measure_metadata:
            if measure.start_tick <= tick < measure.start_tick + measure.length_ticks:
                return measure.bpm

        # If tick is beyond all measures, use last measure's BPM
        if self.measure_metadata:
            return self.measure_metadata[-1].bpm

        return self.bpm

    def advance(self, num_samples):
        """
        Advance playback position by num_samples.

        Uses per-measure tempo if measure_metadata is available.

        Args:
            num_samples: Number of audio samples to advance
        """
        # Calculate time advancement
        dt_seconds = num_samples / self.sample_rate
        dt_ms = dt_seconds * 1000.0

        # Track actual elapsed time
        self.elapsed_time += dt_seconds

        # Get BPM at current tick position (tempo-aware)
        current_bpm = self.get_bpm_at_tick(self.current_tick)

        # Convert to ticks: ticks_per_ms = (BPM * TPQN) / 60000
        ticks_per_ms = (current_bpm * self.tpqn) / 60000.0
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

        # Create process context for audio generation (use BPM at current position)
        current_bpm = self.get_bpm_at_tick(current_tick)
        context = ProcessContext(
            sample_rate=self.sample_rate,
            bpm=current_bpm,
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
        self.elapsed_time = 0.0
