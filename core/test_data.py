"""
Test data generators for Blooper5.

Provides utility functions to create test songs with various configurations
for testing features like per-measure time signature changes.
"""
from core.models import Song, Track, Note, MeasureMetadata


def create_test_track_with_changing_measures() -> Song:
    """
    Create test song with changing time signatures and tempos.

    Measure 1: 3/4 at 60 BPM with 1/16 notes (C4) - SLOW
    Measure 2: 4/4 at 120 BPM with 1/16 notes (C4) - MEDIUM
    Measure 3: 9/8 at 240 BPM with 1/16 notes (C4) - FAST

    Returns:
        Song with three measures, each with different time sig and tempo
    """
    TPQN = 480

    # Calculate measure durations in ticks
    def measure_ticks(numerator: int, denominator: int) -> int:
        """Calculate measure length in ticks based on time signature."""
        ticks_per_denominator = TPQN * (4 / denominator)
        return int(numerator * ticks_per_denominator)

    # Measure metadata
    measure1 = MeasureMetadata(
        measure_index=0,
        start_tick=0,
        time_signature=(3, 4),
        bpm=60.0,  # SLOW
        length_ticks=measure_ticks(3, 4)  # 1440 ticks
    )

    measure2 = MeasureMetadata(
        measure_index=1,
        start_tick=1440,
        time_signature=(4, 4),
        bpm=120.0,  # MEDIUM
        length_ticks=measure_ticks(4, 4)  # 1920 ticks
    )

    measure3 = MeasureMetadata(
        measure_index=2,
        start_tick=3360,  # 1440 + 1920
        time_signature=(9, 8),
        bpm=240.0,  # FAST
        length_ticks=measure_ticks(9, 8)  # 2160 ticks (9 * TPQN/2)
    )

    # Generate repeating 1/16 notes (C4 = MIDI 60)
    sixteenth_note_ticks = TPQN // 4  # 120 ticks
    notes = []

    # Measure 1: Fill with 1/16 notes
    tick = 0
    while tick < measure1.length_ticks:
        notes.append(Note(
            note=60,  # C4
            start=tick / TPQN,  # Convert to beats
            duration=sixteenth_note_ticks / TPQN,
            velocity=80
        ))
        tick += sixteenth_note_ticks

    # Measure 2: Fill with 1/16 notes
    tick = measure2.start_tick
    while tick < measure2.start_tick + measure2.length_ticks:
        notes.append(Note(
            note=60,  # C4
            start=tick / TPQN,
            duration=sixteenth_note_ticks / TPQN,
            velocity=80
        ))
        tick += sixteenth_note_ticks

    # Measure 3: Fill with 1/16 notes
    tick = measure3.start_tick
    while tick < measure3.start_tick + measure3.length_ticks:
        notes.append(Note(
            note=60,  # C4
            start=tick / TPQN,
            duration=sixteenth_note_ticks / TPQN,
            velocity=80
        ))
        tick += sixteenth_note_ticks

    # Create track with notes
    track = Track(
        name="Test Track - Changing Measures",
        notes=tuple(notes),
        mode="SYNTH",
        volume=0.8,
        pan=0.5
    )

    # Create song
    total_length = measure1.length_ticks + measure2.length_ticks + measure3.length_ticks

    return Song(
        name="Test Song - Tempo Changes (60/120/240 BPM)",
        bpm=60.0,  # Default BPM (will be overridden per measure)
        time_signature=(4, 4),  # Default time sig
        tpqn=TPQN,
        tracks=(track,),
        length_ticks=total_length,
        measure_metadata=(measure1, measure2, measure3)
    )
