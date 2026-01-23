"""
Create a test project with MIDI sync enabled and loop markers.
"""
import msgpack
from core.models import Song, Track, Note, MeasureMetadata

def create_test_project():
    # Create a simple song with 2 measures, loop enabled
    # First create empty tracks
    tracks = tuple(Track(name=f"Track {i+1}", notes=tuple()) for i in range(16))

    song = Song(
        name="MIDI SPP Test",
        bpm=120.0,
        time_signature=(4, 4),
        tpqn=480,
        tracks=tracks,
        length_ticks=3840,  # 2 measures (1920 ticks per measure)
        loop_enabled=True,
        loop_start_tick=0,
        loop_end_tick=1920,  # Loop after 1 measure
        send_midi_clock=True,
        receive_midi_clock=True
    )

    # Create notes for track 0 (beats 1, 2, 3, 4 of first measure)
    notes = []
    for beat in range(4):
        note = Note(
            note=60 + beat,  # C4, C#4, D4, D#4
            start=float(beat),  # Beat position (0.0, 1.0, 2.0, 3.0)
            duration=0.5,  # Eighth note (half a beat)
            velocity=100
        )
        notes.append(note)

    # Create new track 0 with notes
    new_track0 = Track(name="Track 1", notes=tuple(notes))

    # Update song with new track 0 (Song is immutable, so create new one)
    new_tracks = list(song.tracks)
    new_tracks[0] = new_track0

    # Create measure metadata for tempo
    measure1 = MeasureMetadata(
        measure_index=0,
        start_tick=0,
        time_signature=(4, 4),
        bpm=120.0,
        length_ticks=1920  # 4 beats * 480 ticks/beat
    )
    measure2 = MeasureMetadata(
        measure_index=1,
        start_tick=1920,
        time_signature=(4, 4),
        bpm=120.0,
        length_ticks=1920
    )

    # Create final song with notes and measure metadata
    from dataclasses import replace
    song = replace(
        song,
        tracks=tuple(new_tracks),
        measure_metadata=tuple([measure1, measure2])
    )

    # Serialize to msgpack
    data = song.to_dict()

    # Write to file
    output_path = "test_midi_sync.blooper5"
    with open(output_path, 'wb') as f:
        f.write(msgpack.packb(data, use_bin_type=True))

    print(f"[OK] Created test project: {output_path}")
    print(f"     - BPM: 120")
    print(f"     - Loop: tick 0 -> 1920 (1 measure)")
    print(f"     - MIDI sync: send=True, receive=True")
    print(f"     - Notes: 4 notes on track 0")
    print(f"\nTo test:")
    print(f"  1. python main.py")
    print(f"  2. Load '{output_path}'")
    print(f"  3. Enable loop mode (click loop button)")
    print(f"  4. Press Play")
    print(f"  5. Watch console for SPP messages when loop cycles")

if __name__ == "__main__":
    create_test_project()
