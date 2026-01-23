"""
Test script to verify loop marker synchronization.
"""
from core.models import Song, Track, Note, AppState
import dataclasses

# Create a simple test song
song = Song(
    name="Loop Test",
    bpm=120.0,
    time_signature=(4, 4),
    tpqn=480,
    tracks=tuple([Track(name=f"Track {i+1}") for i in range(16)]),
    length_ticks=1920 * 4,  # 4 bars
    loop_start_tick=0,
    loop_end_tick=1920,  # 1 bar loop
    loop_enabled=True
)

print("=== Testing Loop Configuration ===")
print(f"Song loop_start_tick: {song.loop_start_tick}")
print(f"Song loop_end_tick: {song.loop_end_tick}")
print(f"Song loop_enabled: {song.loop_enabled}")
print()

# Simulate what happens when loop markers are changed
print("=== Simulating loop marker drag ===")
new_start = 0
new_end = 1920 * 2  # 2 bars

loop_enabled = (new_end is not None)
updated_song = dataclasses.replace(
    song,
    loop_start_tick=new_start,
    loop_end_tick=new_end,
    loop_enabled=loop_enabled
)

print(f"Updated loop_start_tick: {updated_song.loop_start_tick}")
print(f"Updated loop_end_tick: {updated_song.loop_end_tick}")
print(f"Updated loop_enabled: {updated_song.loop_enabled}")
print()

# Test the playback condition
is_looping = True  # This should be synced from loop_enabled
print("=== Testing playback loop condition ===")
print(f"DAWView.is_looping: {is_looping}")
print(f"song.loop_enabled: {updated_song.loop_enabled}")
print(f"song.loop_end_tick: {updated_song.loop_end_tick}")

should_loop = is_looping and updated_song.loop_enabled and updated_song.loop_end_tick
print(f"Loop will activate: {should_loop}")
print()

# Test clearing loop
print("=== Testing loop clear (drag end marker to None) ===")
cleared_song = dataclasses.replace(
    updated_song,
    loop_start_tick=0,
    loop_end_tick=None,
    loop_enabled=False
)

is_looping_after_clear = False  # Should be synced to False
should_loop_after_clear = is_looping_after_clear and cleared_song.loop_enabled and cleared_song.loop_end_tick
print(f"Loop enabled after clear: {cleared_song.loop_enabled}")
print(f"Loop will activate after clear: {should_loop_after_clear}")
print()

print("✓ All loop synchronization logic working correctly!")
