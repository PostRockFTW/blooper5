"""
Create a test project for MIDI input with MPK25.

Configuration based on Generic preset:
- Keyboard notes 84-127 → Track 0 (melodic synth)
- Pad notes 36-83 → Track 1 (drum synth)
- Both on MIDI Channel 1 (0 in 0-indexed)
"""
import dataclasses
from pathlib import Path
from core.models import Song, Track
from core.persistence import ProjectFile

# Create Track 0 - Keyboard (high range melody)
track0 = Track(
    name="Keyboard (Ch 1, High)",
    mode="SYNTH",
    source_type="DUAL_OSC",
    source_params={
        "osc1_type": "SINE",  # Sine wave for smooth melody
        "osc2_type": "SINE",
        "osc_mix": 0.5,
        "osc2_interval": 12,  # Octave up
        "osc2_detune": 5,
        "filter_cutoff": 5000,
        "transpose": 0,
        "gain": 1.0,
        "attack": 0.01,
        "length": 0.5,
        "root_note": 60
    },
    volume=0.75,
    pan=0.5,
    # MIDI input configuration
    receive_midi_input=True,
    midi_channel=0,  # Channel 1 (0-indexed)
    midi_note_min=84,  # C6 and above
    midi_note_max=127
)

# Create Track 1 - Pads (drum range)
track1 = Track(
    name="Pads (Ch 1, Drums)",
    mode="SYNTH",
    source_type="DUAL_OSC",
    source_params={
        "osc1_type": "SAW",  # Sawtooth for punchy percussion
        "osc2_type": "SQUARE",  # Square wave
        "osc_mix": 0.7,
        "osc2_interval": -12,  # Octave down
        "osc2_detune": 20,
        "filter_cutoff": 3000,
        "transpose": 0,
        "gain": 1.2,
        "attack": 0.001,
        "length": 0.3,  # Short percussive hits
        "root_note": 60
    },
    volume=0.85,
    pan=0.5,
    # MIDI input configuration
    receive_midi_input=True,
    midi_channel=0,  # Channel 1 (0-indexed)
    midi_note_min=36,  # C2 (standard drum range)
    midi_note_max=83   # B5 (matches MPK25 Generic preset pads)
)

# Create Track 2 - Keyboard (low/mid range)
track2 = Track(
    name="Keyboard (Ch 1, Low)",
    mode="SYNTH",
    source_type="DUAL_OSC",
    source_params={
        "osc1_type": "SAW",  # Sawtooth for bass
        "osc2_type": "SAW",
        "osc_mix": 0.6,
        "osc2_interval": 0,
        "osc2_detune": 10,
        "filter_cutoff": 2000,
        "transpose": 0,
        "gain": 1.0,
        "attack": 0.01,
        "length": 0.4,
        "root_note": 60
    },
    volume=0.70,
    pan=0.5,
    # MIDI input configuration
    receive_midi_input=True,
    midi_channel=0,  # Channel 1 (0-indexed)
    midi_note_min=0,   # Lowest note
    midi_note_max=35   # B1 (below drum range)
)

# Create empty tracks for the rest (up to 16 total)
empty_tracks = []
for i in range(3, 16):
    empty_tracks.append(Track(
        name=f"Track {i}",
        receive_midi_input=False
    ))

# Create Song
song = Song(
    name="MIDI Input Test",
    bpm=120.0,
    time_signature=(4, 4),
    tpqn=480,
    tracks=(track0, track1, track2, *empty_tracks),
    length_ticks=1920 * 4,  # 4 bars
    file_path="test_midi_input.bloom5"
)

# Save to file using MessagePack format
project_path = Path("test_midi_input.bloom5")
ProjectFile.save(song, project_path)

print("=" * 70)
print("MIDI INPUT TEST PROJECT CREATED")
print("=" * 70)
print(f"\nSaved to: test_midi_input.bloom5")
print(f"\nConfiguration (MPK25 Generic Preset):")
print(f"  Track 0: Keyboard High  (Ch 1, Notes  84-127) - Melody")
print(f"  Track 1: Pads          (Ch 1, Notes  36-83 ) - Drums")
print(f"  Track 2: Keyboard Low  (Ch 1, Notes   0-35 ) - Bass")
print(f"\nAll devices on MIDI Channel 1 (MPK25 Generic preset)")
print(f"\nNote ranges:")
print(f"  Notes 0-35:   Keyboard Low (Track 2)")
print(f"  Notes 36-83:  Pads (Track 1)")
print(f"  Notes 84-127: Keyboard High (Track 0)")
print(f"\nTo test:")
print(f"  1. Load this project in Blooper5")
print(f"  2. Press Play")
print(f"  3. Play keyboard notes above C6 → Track 0 (melody)")
print(f"  4. Hit pads → Track 1 (drums)")
print(f"  5. Play keyboard notes below C2 → Track 2 (bass)")
print("=" * 70)
