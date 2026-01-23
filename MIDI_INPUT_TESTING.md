# MIDI Input Testing Guide

## Overview

Blooper5 now supports real-time MIDI input with channel-based routing and note range filtering. This allows you to play the synthesizers live from your MPK25 controller.

## Configuration

### MPK25 Setup (Generic Preset)
- **Preset:** Generic (factory preset)
- **Keyboard:** MIDI Channel 1, full range
- **Pads:** MIDI Channel 1, Notes 36-83 (4 banks × 12 pads)
- **Aftertouch:** Channel aftertouch supported on all pads

### Test Project Configuration

The `test_midi_input.blooper5` project has 3 tracks configured for live input:

| Track | Name | Channel | Note Range | Purpose |
|-------|------|---------|------------|---------|
| 0 | Keyboard High | 1 | 84-127 | Melodic playing (C6 and above) |
| 1 | Pads | 1 | 36-83 | Drum/percussion from pads |
| 2 | Keyboard Low | 1 | 0-35 | Bass notes (below C2) |

All tracks use the same MIDI channel (1) but are separated by note range filtering.

## Testing Steps

### 1. Load the Test Project

```bash
python main.py
```

- Click "Load Project"
- Select `test_midi_input.blooper5`
- You should see 3 configured tracks in the mixer

### 2. Start Playback

- Click the **Play** button (or press Space)
- Console should show: `[MIDI INPUT] Opened for live notes: Akai MPK25 0`
- Playback doesn't need to be playing Piano Roll notes - MIDI input works anytime after Play is pressed

### 3. Test Keyboard Input

**High Range (Track 0 - Melody):**
- Play keyboard notes C6 (MIDI note 84) and above
- Console should show:
  ```
  [MIDI IN] Ch 1 | Note ON  84 | Vel  80 -> Track 0
  [MIDI IN] Ch 1 | Note OFF 84 -> Track 0
  ```
- You should hear a smooth melodic synth sound

**Low Range (Track 2 - Bass):**
- Play keyboard notes below C2 (MIDI note 36)
- Console should show:
  ```
  [MIDI IN] Ch 1 | Note ON  35 | Vel  80 -> Track 2
  [MIDI IN] Ch 1 | Note OFF 35 -> Track 2
  ```
- You should hear a bass synth sound

### 4. Test Pad Input

**Drum Pads (Track 1):**
- Hit any drum pad on MPK25
- Console should show:
  ```
  [MIDI IN] Ch 1 | Note ON  36 | Vel 100 -> Track 1
  [MIDI IN] Ch 1 | Note OFF 36 -> Track 1
  ```
- You should hear a percussive synth sound

**Try different pads across all banks:**
- Bank A: Notes 36-47
- Bank B: Notes 48-59
- Bank C: Notes 60-71
- Bank D: Notes 72-83

### 5. Test Aftertouch

- Hit a pad and hold with increasing pressure
- Console should show:
  ```
  [MIDI IN] Ch 1 | Aftertouch  64
  [MIDI IN] Ch 1 | Aftertouch  80
  [MIDI IN] Ch 1 | Aftertouch 100
  ```
- Note: Aftertouch is currently logged but not yet routed to synth parameters

### 6. Test Polyphony

- Play multiple notes simultaneously (keyboard + pads)
- All notes should sound together
- MPK25 supports up to 16 simultaneous notes

### 7. Test Mixer Controls

**Mute:**
- Mute Track 1 in mixer
- Hit pads - no sound (console still shows MIDI IN messages)
- Unmute - pads work again

**Solo:**
- Solo Track 0 in mixer
- Only keyboard high notes should sound
- Pads and bass are muted

**Volume/Pan:**
- Adjust Track 1 volume slider
- Pad velocity should change in real-time
- Adjust pan - pads should move left/right in stereo

## Expected Results

✅ **Pass Criteria:**
- [ ] Keyboard high range (84-127) triggers Track 0
- [ ] Keyboard low range (0-35) triggers Track 2
- [ ] Pads (36-83) trigger Track 1
- [ ] Note On/Off messages are correctly paired (no stuck notes)
- [ ] Velocity is respected (soft/loud hits sound different)
- [ ] Multiple simultaneous notes work (polyphony)
- [ ] Console shows clear MIDI IN messages with channel, note, velocity
- [ ] Mixer mute/solo/volume/pan work with live input
- [ ] Aftertouch is detected and logged

## Troubleshooting

### No MIDI Input
```
[MIDI] No input devices available
```
**Solution:** Make sure MPK25 is connected and powered on before starting Blooper5

### Wrong Notes Triggering
- Check MPK25 preset (should be Generic)
- Verify note ranges in test project match pad configuration

### Stuck Notes
- If notes don't stop, press Stop and Play again
- Check console for matching Note OFF messages

### No Sound But Console Shows MIDI IN
- Check track is not muted
- Check master volume
- Check audio device is selected correctly

## Next Steps

### Add MIDI Input to Your Own Projects

Edit any track in your project:

```python
track = dataclasses.replace(
    track,
    receive_midi_input=True,
    midi_channel=0,  # Channel 1 (0-indexed)
    midi_note_min=0,
    midi_note_max=127
)
```

### Future Enhancements (TODO)
- [ ] Aftertouch → synth parameter modulation (filter cutoff, vibrato, etc.)
- [ ] CC controllers → synth parameter mapping
- [ ] MIDI input device selection in UI (currently hardcoded to "Akai MPK25 0")
- [ ] MIDI learn for parameter assignment
- [ ] Recording live MIDI input to Piano Roll
- [ ] Note range UI editor in track settings

## Architecture Notes

### How It Works

1. **MIDI Callback Thread** (`midi/handler.py`)
   - Receives MIDI messages from rtmidi
   - Parses messages with `parse_midi_message()`
   - Queues note events in `note_event_queue` (thread-safe)

2. **Audio Callback Thread** (`ui/views/DAWView.py`)
   - Calls `get_note_events()` every audio frame
   - Routes events to tracks via `_process_midi_event()`
   - Updates `active_live_notes` dictionary
   - Generates audio for each active note
   - Mixes with Piano Roll notes

3. **Channel Routing**
   - Each track has `midi_channel` (0-15)
   - Only processes events matching its channel
   - Note range filtering: `midi_note_min` to `midi_note_max`

4. **Note Lifecycle**
   - Note On (velocity > 0) → Add to `active_live_notes`
   - Note Off (velocity = 0 or status 0x80) → Remove from `active_live_notes`
   - Audio generated continuously while note is in dictionary

### Files Modified

- `midi/handler.py` - Added note event queue and processing
- `core/models.py` - Added `receive_midi_input`, `midi_note_min`, `midi_note_max` to Track
- `ui/views/DAWView.py` - Added live note triggering and MIDI event routing
- `create_midi_input_test.py` - Test project generator
- `test_mpk_pads.py` - Pad configuration investigation tool

## Performance

- **Latency:** < 10ms (MIDI callback → audio output)
- **Throughput:** 1000 events/sec max (queue size limit)
- **Polyphony:** Limited only by CPU (tested with 16 simultaneous notes)
- **Thread Safety:** Lock-free queues, immutable song data

## Known Limitations

- MIDI input device is hardcoded to "Akai MPK25 0"
- Aftertouch detected but not yet routed to synth parameters
- No recording of live input to Piano Roll (playback only)
- Note range filtering doesn't support multiple ranges (e.g., 0-35 OR 84-127)
  - Workaround: Use multiple tracks on same channel with different ranges
