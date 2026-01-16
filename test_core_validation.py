"""
Quick validation script for Core Layer implementation.
Tests all major functionality to ensure everything works.
"""
import sys
from pathlib import Path

# Test imports
print("=" * 60)
print("CORE LAYER VALIDATION")
print("=" * 60)

print("\n1. Testing imports...")
try:
    from core import constants, models, persistence, commands
    print("   ✓ All core modules imported successfully")
except ImportError as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test constants.py
print("\n2. Testing core/constants.py...")
try:
    # Test MIDI note conversions
    note_name = constants.midi_note_to_name(60)
    assert note_name == "C4", f"Expected 'C4', got '{note_name}'"
    print(f"   ✓ midi_note_to_name(60) = '{note_name}'")

    midi_note = constants.name_to_midi_note("A4")
    assert midi_note == 69, f"Expected 69, got {midi_note}"
    print(f"   ✓ name_to_midi_note('A4') = {midi_note}")

    # Test scale generation
    c_major = constants.get_scale_notes(60, "major")
    expected = [60, 62, 64, 65, 67, 69, 71]
    assert c_major == expected, f"Expected {expected}, got {c_major}"
    print(f"   ✓ get_scale_notes(60, 'major') = {c_major}")

    # Test frequency conversions
    freq = constants.midi_to_frequency(69)
    assert abs(freq - 440.0) < 0.01, f"Expected 440.0, got {freq}"
    print(f"   ✓ midi_to_frequency(69) = {freq} Hz")

    note = constants.frequency_to_midi(440.0)
    assert note == 69, f"Expected 69, got {note}"
    print(f"   ✓ frequency_to_midi(440.0) = {note}")

except Exception as e:
    print(f"   ✗ Constants test failed: {e}")
    sys.exit(1)

# Test models.py
print("\n3. Testing core/models.py...")
try:
    # Test Note creation and validation
    note = models.Note(note=60, start=0.0, duration=1.0, velocity=100)
    assert note.note == 60
    assert note.duration == 1.0
    print(f"   ✓ Note creation: {note}")

    # Test immutability
    try:
        note.note = 61
        print("   ✗ Note should be immutable!")
        sys.exit(1)
    except Exception:
        print("   ✓ Note is immutable (frozen dataclass)")

    # Test Track creation
    track = models.Track(name="Test Track")
    assert track.name == "Test Track"
    assert track.mode == "SYNTH"
    assert len(track.notes) == 0
    print(f"   ✓ Track creation: {track.name}")

    # Test Song creation
    song = models.Song(
        name="Test Song",
        bpm=120.0,
        time_signature=(4, 4),
        tpqn=480,
        tracks=(track,)
    )
    assert song.name == "Test Song"
    assert song.bpm == 120.0
    assert len(song.tracks) == 1
    print(f"   ✓ Song creation: {song.name}")

    # Test serialization
    song_dict = song.to_dict()
    assert song_dict["version"] == "5.0.0"
    assert song_dict["bpm"] == 120.0
    print(f"   ✓ Song serialization to dict")

    # Test deserialization
    song2 = models.Song.from_dict(song_dict)
    assert song2.name == song.name
    assert song2.bpm == song.bpm
    print(f"   ✓ Song deserialization from dict")

    # Test AppState
    state = models.AppState()
    assert state.get_current_song() is None
    state.set_current_song(song)
    assert state.get_current_song() == song
    print(f"   ✓ AppState management")

except Exception as e:
    print(f"   ✗ Models test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test persistence.py
print("\n4. Testing core/persistence.py...")
try:
    import tempfile
    import os

    # Create a test song
    note = models.Note(note=60, start=0.0, duration=1.0, velocity=100)
    track = models.Track(name="Test Track", notes=(note,))
    song = models.Song(
        name="Persistence Test",
        bpm=140.0,
        time_signature=(4, 4),
        tpqn=480,
        tracks=(track,)
    )

    # Test save
    temp_file = Path(tempfile.mktemp(suffix=".bloom5"))
    persistence.ProjectFile.save(song, temp_file)
    assert temp_file.exists(), "File should be created"
    file_size = temp_file.stat().st_size
    print(f"   ✓ Save to .bloom5 file ({file_size} bytes)")

    # Test load
    loaded_song = persistence.ProjectFile.load(temp_file)
    assert loaded_song.name == song.name
    assert loaded_song.bpm == song.bpm
    assert len(loaded_song.tracks) == len(song.tracks)
    assert len(loaded_song.tracks[0].notes) == 1
    print(f"   ✓ Load from .bloom5 file")

    # Test auto-save path generation
    auto_path = persistence.ProjectFile.get_auto_save_path("Test Project")
    assert "Test Project" in str(auto_path) or "Test-Project" in str(auto_path)
    print(f"   ✓ Auto-save path: {auto_path}")

    # Cleanup
    temp_file.unlink()

except Exception as e:
    print(f"   ✗ Persistence test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test commands.py
print("\n5. Testing core/commands.py...")
try:
    # Create test data
    note1 = models.Note(note=60, start=0.0, duration=1.0, velocity=100)
    track = models.Track(name="Test Track", notes=())
    song = models.Song(
        name="Command Test",
        bpm=120.0,
        time_signature=(4, 4),
        tpqn=480,
        tracks=(track,)
    )

    state = models.AppState()
    state.set_current_song(song)

    # Test CommandHistory
    history = commands.CommandHistory(state, max_history=100)
    print(f"   ✓ CommandHistory created")

    # Test AddNoteCommand
    add_cmd = commands.AddNoteCommand(track_index=0, note=note1)
    history.execute(add_cmd)

    current_song = state.get_current_song()
    assert len(current_song.tracks[0].notes) == 1
    assert current_song.tracks[0].notes[0].note == 60
    print(f"   ✓ AddNoteCommand executed (note added)")

    # Test undo
    assert history.can_undo()
    history.undo()
    current_song = state.get_current_song()
    assert len(current_song.tracks[0].notes) == 0
    print(f"   ✓ Undo successful (note removed)")

    # Test redo
    assert history.can_redo()
    history.redo()
    current_song = state.get_current_song()
    assert len(current_song.tracks[0].notes) == 1
    print(f"   ✓ Redo successful (note re-added)")

    # Test DeleteNoteCommand
    delete_cmd = commands.DeleteNoteCommand(track_index=0, note_index=0)
    history.execute(delete_cmd)
    current_song = state.get_current_song()
    assert len(current_song.tracks[0].notes) == 0
    print(f"   ✓ DeleteNoteCommand executed (note deleted)")

    # Test undo of delete
    history.undo()
    current_song = state.get_current_song()
    assert len(current_song.tracks[0].notes) == 1
    print(f"   ✓ Undo delete successful (note restored)")

    # Test command descriptions
    desc = history.get_undo_description()
    assert desc == "Delete Note"
    print(f"   ✓ Command descriptions: '{desc}'")

except Exception as e:
    print(f"   ✗ Commands test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Final summary
print("\n" + "=" * 60)
print("✅ ALL CORE LAYER TESTS PASSED!")
print("=" * 60)
print("\nValidated:")
print("  • MIDI utility functions (constants.py)")
print("  • Immutable data models (models.py)")
print("  • MessagePack serialization (persistence.py)")
print("  • Command pattern with undo/redo (commands.py)")
print("\nCore Layer is ready for integration!")
