# MIDI SPP Bidirectional Testing Guide

Complete guide for testing MIDI Song Position Pointer (SPP) functionality with physical hardware.

## Table of Contents

1. [Hardware Setup](#hardware-setup)
2. [Device Capabilities](#device-capabilities)
3. [Quick Start](#quick-start)
4. [Test Scripts](#test-scripts)
5. [Testing Procedures](#testing-procedures)
6. [Expected Console Output](#expected-console-output)
7. [Troubleshooting](#troubleshooting)
8. [Integration with Blooper5](#integration-with-blooper5)

---

## Hardware Setup

### Connected Devices

**1. Akai MPK25** - USB MIDI keyboard controller
- Connected via USB to computer
- 3 virtual MIDI ports:
  - Port 0: `Akai MPK25 0` - Main controller output (keys, pads, knobs)
  - Port 1: `MIDIIN2 (Akai MPK25) 1` - DIN IN pass-through
  - Port 2: `MIDIIN3 (Akai MPK25) 2` - DIN OUT pass-through

**2. USB2.0-MIDI Adapter** (CH345 chipset)
- Connected via USB to computer
- Physical 5-pin DIN cables connected to MPK25's physical MIDI ports
- 2 virtual MIDI ports:
  - Port 3: `USB2.0-MIDI 3` - MIDI IN
  - Port 4: `MIDIOUT2 (USB2.0-MIDI) 4` - MIDI OUT

### Physical Topology

```
┌──────────────────────────────────────────────────────────┐
│                       Computer                           │
│                                                          │
│  USB ←──────────────→ MPK25 (Controller)                │
│                         ↓ ↑                              │
│                    DIN OUT/IN (5-pin MIDI)               │
│                         ↓ ↑                              │
│                  USB2.0-MIDI Adapter                     │
│  USB ←──────────────→ (DIN IN/OUT)                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

### Data Flow Diagram

```
Blooper5 SPP Output Path:
  Blooper5 → MIDIOUT2 (USB2.0-MIDI) 4 → DIN OUT → MPK25 DIN IN

MPK25 Keyboard Input Path:
  MPK25 keys/pads → Akai MPK25 0 → Blooper5

Physical Loopback (Optional):
  Blooper5 → USB2.0-MIDI OUT → MPK25 DIN IN → MPK25 DIN OUT → USB2.0-MIDI IN → Blooper5
```

### Cable Connections

Verify the following physical connections:

1. **USB Connections:**
   - MPK25 USB cable → Computer USB port
   - USB2.0-MIDI adapter → Computer USB port

2. **DIN Connections (5-pin MIDI):**
   - USB2.0-MIDI DIN OUT → MPK25 DIN IN (back panel)
   - MPK25 DIN OUT (back panel) → USB2.0-MIDI DIN IN

---

## Device Capabilities

### Akai MPK25

**Supported:**
- ✅ MIDI Start/Stop/Continue messages (transport buttons)
- ✅ MIDI Clock transmission (basic, 0xF8)
- ✅ MIDI Clock reception (external sync)
- ✅ Note input (keys, pads, knobs)
- ✅ 30 factory presets for different DAWs
- ✅ Configurable transport control modes (MMC, MIDI, MMC/MIDI, CTRL)

**NOT Supported:**
- ❌ **Song Position Pointer (SPP)** - No documentation confirms 0xF2 support
- ❌ Precise MIDI clock sync (known timing issues with arpeggiator)
- ❌ Acts as controller, not a sequencer

**Notes:**
- When connected via USB, DIN ports become computer I/O pass-throughs
- Port A (primary) and Port B (secondary) provide 32 MIDI channels total
- Transport buttons are fully configurable

### USB2.0-MIDI Adapter (CH345)

**Supported:**
- ✅ **SPP messages (0xF2)** - Fully supported by USB MIDI spec
- ✅ MIDI Clock messages (0xF8)
- ✅ All MIDI System Real-Time messages
- ✅ Bidirectional communication

**Limitations:**
- ⚠️ No hardware MIDI Thru
- ⚠️ No FIFO buffer (can drop bytes under heavy load)
- ⚠️ No Running Status support
- ⚠️ Physical loopback testing is unreliable

**Best Practices:**
- Add 3ms delays between rapid messages
- Use dedicated USB port (not hub)
- Avoid SysEx transfers
- Monitor for dropped messages during testing

---

## Quick Start

### Step 1: List Available Devices

```bash
python configure_midi_ports.py
```

This will show all available MIDI input/output devices and provide recommendations.

### Step 2: MPK25 Preset Selection

Check current preset on MPK25:
1. Press "Preset" button on MPK25
2. View preset number on display
3. Recommended: Use **Preset 1 "LiveLite"** (Ableton Live default)

If transport buttons don't work:
- Try presets 1-5
- Use Vyzex MPK25 editor to create custom preset
- Configure transport mode to "MIDI" (not MMC)

### Step 3: Run Test Scripts

Execute in this order:

```bash
# 1. Test output routing
python test_device_selection.py

# 2. Test keyboard input from MPK25
python test_mpk_notes.py

# 3. Test bidirectional loopback (optional - may be unreliable)
python test_bidirectional_spp.py
```

### Step 4: Test in Blooper5

1. Load `test_midi_sync.blooper5` project
2. Enable MIDI clock sending in settings
3. Configure output to `MIDIOUT2 (USB2.0-MIDI) 4`
4. Press Play
5. Watch console for SPP messages every 4 seconds

---

## Test Scripts

### 1. configure_midi_ports.py

**Purpose:** List all MIDI devices and provide setup recommendations

**Usage:**
```bash
python configure_midi_ports.py
```

**Output:**
- List of all MIDI input devices
- List of all MIDI output devices
- Recommended port configurations for testing
- Device capability summary
- Next steps

**When to use:**
- First time setup
- Verifying device connections
- Checking available MIDI ports
- After connecting new hardware

---

### 2. test_device_selection.py

**Purpose:** Test sending MIDI messages to specific output devices

**Usage:**
```bash
python test_device_selection.py
```

**What it does:**
- **Test 1:** Sends SPP sequence to USB2.0-MIDI adapter
  - MIDI Start
  - SPP at tick 0, 480, 960 (3 bars)
  - MIDI Stop

- **Test 2:** Sends SPP to MPK25 (optional, may not respond)
  - Same sequence as Test 1
  - MPK25 may ignore (it's a controller, not sequencer)

**Expected behavior:**
- Messages sent without errors
- Console shows all sent messages
- Use external MIDI monitor to verify output

**When to use:**
- Verify SPP output routing
- Test USB2.0-MIDI adapter functionality
- Confirm MIDI Start/Stop sending

---

### 3. test_mpk_notes.py

**Purpose:** Monitor all MIDI input from MPK25 keyboard

**Usage:**
```bash
python test_mpk_notes.py
```

**What it monitors:**
- Note On/Off (keyboard keys)
- Drum pads
- Control Change (knobs, sliders)
- Pitch Bend
- Transport buttons (Start/Stop/Continue)
- Song Position Pointer (if MPK25 sends it)

**Interaction:**
1. Run script
2. Play notes on MPK25 keyboard
3. Hit drum pads
4. Turn knobs
5. Press transport buttons
6. Press Ctrl+C to stop

**Expected output:**
```
[   1] Note ON  - Ch  1 | Note  60 | Vel  64 | [144, 60, 64]
[   2] Note OFF - Ch  1 | Note  60 |          | [144, 60, 0]
[   3] CC       - Ch  1 | CC   22  | Val  45  | [176, 22, 45]
```

**When to use:**
- Verify MPK25 keyboard is working
- Test MIDI input reception
- Check preset configuration
- Monitor transport button messages

---

### 4. test_bidirectional_spp.py

**Purpose:** Test physical MIDI loopback via MPK25 pass-through

**Usage:**
```bash
python test_bidirectional_spp.py
```

**What it does:**
1. Opens USB2.0-MIDI output
2. Opens USB2.0-MIDI input
3. Sends 5 SPP messages + Start/Stop
4. Waits for messages to loop back
5. Reports success/failure

**Physical path:**
```
Computer → USB2.0-MIDI OUT → MPK25 DIN IN → MPK25 DIN OUT → USB2.0-MIDI IN → Computer
```

**Expected results:**
- ✅ **Best case:** All 5 SPP messages received
- ⚠️ **Typical:** 3-4 messages received (CH345 limitation)
- ❌ **Failure:** 0 messages received (connection issue)

**Known issues:**
- CH345 adapter has no FIFO buffer
- May drop bytes under load
- Not suitable for real-world sync testing
- Use only for connectivity verification

**When to use:**
- Verify physical cable connections
- Test MPK25 MIDI Thru functionality
- Debug connection issues
- **NOT recommended for production testing**

---

## Testing Procedures

### Test A: Blooper5 → USB2.0-MIDI → MPK25

**Goal:** Verify Blooper5 sends SPP messages via USB2.0-MIDI adapter

**Configuration:**
- OUTPUT: `MIDIOUT2 (USB2.0-MIDI) 4`
- INPUT: `Akai MPK25 0` (for keyboard notes)

**Procedure:**

1. **Load test project:**
   ```
   File → Open → test_midi_sync.blooper5
   ```

2. **Configure MIDI settings:**
   - Enable "Send MIDI Clock"
   - Select output device: `MIDIOUT2 (USB2.0-MIDI) 4`

3. **Enable loop mode:**
   - Loop should be configured (4 bars, 4 seconds)
   - Check loop is enabled in transport

4. **Start playback:**
   - Press Play (spacebar or transport button)
   - Watch console output

5. **Verify SPP messages:**
   - Should appear every 4 seconds (loop duration)
   - Format: `[MIDI OUT] SPP: tick=0, spp=0, msg=[0xF2, 0x00, 0x00]`

**Expected console output:**
```
[MIDI] Opening output: MIDIOUT2 (USB2.0-MIDI) 4
[MIDI OUT] Start
[MIDI OUT] SPP: tick=0, spp=0, msg=[0xF2, 0x00, 0x00]
[MIDI OUT] Clock (x96 per quarter note)
[MIDI OUT] SPP: tick=1920, spp=320, msg=[0xF2, 0x40, 0x02]  # Loop jump
[MIDI OUT] SPP: tick=1920, spp=320, msg=[0xF2, 0x40, 0x02]  # Loop jump
```

**Success criteria:**
- ✅ No errors opening MIDI output
- ✅ SPP messages appear on loop jumps
- ✅ No crashes or freezes
- ✅ Playback continues smoothly

---

### Test B: MPK25 → Blooper5 Note Input

**Goal:** Verify MPK25 keyboard sends notes to Blooper5

**Configuration:**
- INPUT: `Akai MPK25 0`
- OUTPUT: Any (not critical for this test)

**Procedure:**

1. **Configure MIDI input:**
   - Enable "Receive MIDI Clock" (or MIDI input)
   - Select input device: `Akai MPK25 0`

2. **Load synth/instrument:**
   - Ensure audio track with synth is active
   - Set MIDI channel to match MPK25 (usually Channel 1)

3. **Play notes on MPK25:**
   - Press keys on keyboard
   - Hit drum pads
   - Try different velocities

4. **Verify audio output:**
   - Notes should trigger synth sound
   - Check audio meter shows activity
   - Verify different notes play different pitches

**Expected behavior:**
- ✅ Notes trigger synth in real-time
- ✅ Audio responds to keyboard velocity
- ✅ No latency or stuck notes
- ✅ Transport buttons may send Start/Stop (depends on preset)

---

### Test C: Physical Loopback (Optional)

**Goal:** Verify physical MIDI cable connections

**Configuration:**
- OUTPUT: `MIDIOUT2 (USB2.0-MIDI) 4`
- INPUT: `USB2.0-MIDI 3`

**Procedure:**

1. **Verify physical connections:**
   - USB2.0-MIDI DIN OUT → MPK25 DIN IN
   - MPK25 DIN OUT → USB2.0-MIDI DIN IN

2. **Run loopback test:**
   ```bash
   python test_bidirectional_spp.py
   ```

3. **Check results:**
   - 5 SPP messages sent
   - Count received messages
   - Compare sent vs. received

**Expected results:**
- ✅ **Ideal:** 5/5 messages received (rare with CH345)
- ⚠️ **Typical:** 3-4/5 messages received (acceptable)
- ❌ **Problem:** 0-1/5 messages received (check connections)

**Known limitations:**
- CH345 adapter drops bytes under load
- Not suitable for production use
- Use only for connection verification

---

## Expected Console Output

### Successful SPP Output (Blooper5)

```
[MIDI] Opening output: MIDIOUT2 (USB2.0-MIDI) 4
[MIDI OUT] Start
[MIDI OUT] SPP: tick=0, spp=0, msg=[0xF2, 0x00, 0x00]
[MIDI OUT] Clock
[MIDI OUT] Clock
...
[MIDI OUT] SPP: tick=1920, spp=320, msg=[0xF2, 0x40, 0x02]  # Loop jump at bar 5
[MIDI OUT] Clock
...
[MIDI OUT] Stop
[MIDI] Closing output
```

### SPP Message Format

```
[MIDI OUT] SPP: tick=<tick>, spp=<spp>, msg=[0xF2, <lsb>, <msb>]

Where:
  tick = Current position in MIDI ticks (480 ppqn)
  spp  = Song Position Pointer value (tick / 6)
  lsb  = Low 7 bits of SPP
  msb  = High 7 bits of SPP
```

**Example values:**
```
tick=0     → spp=0    → msg=[0xF2, 0x00, 0x00]  # Bar 1, beat 1
tick=480   → spp=80   → msg=[0xF2, 0x50, 0x00]  # Bar 2, beat 1
tick=960   → spp=160  → msg=[0xF2, 0x20, 0x01]  # Bar 3, beat 1
tick=1920  → spp=320  → msg=[0xF2, 0x40, 0x02]  # Bar 5, beat 1
```

### MPK25 Keyboard Input

```
[   1] Note ON  - Ch  1 | Note  60 | Vel  64 | [144, 60, 64]
[   2] Note OFF - Ch  1 | Note  60 |          | [144, 60, 0]
[   3] Note ON  - Ch  1 | Note  64 | Vel  80 | [144, 64, 80]
[   4] Note OFF - Ch  1 | Note  64 |          | [144, 64, 0]
[   5] CC       - Ch  1 | CC   22  | Val  45  | [176, 22, 45]
[   6] START    - System Real-Time          | [250]
[   7] STOP     - System Real-Time          | [252]
```

### Error Messages

**Port not found:**
```
[ERROR] MIDI output port not found: MIDIOUT2 (USB2.0-MIDI) 4
Available ports: ['Akai MPK25 0', 'MIDIIN2 (Akai MPK25) 1']
```

**Port in use:**
```
[ERROR] Failed to open MIDI port: Port already in use
```

**No devices connected:**
```
[ERROR] No MIDI input devices available
[ERROR] No MIDI output devices available
```

---

## Troubleshooting

### No MIDI Devices Found

**Symptoms:**
- `configure_midi_ports.py` shows no devices
- Blooper5 shows "No MIDI devices available"

**Solutions:**

1. **Check USB connections:**
   - Verify MPK25 USB cable is connected
   - Verify USB2.0-MIDI adapter is plugged in
   - Try different USB ports

2. **Check Device Manager (Windows):**
   - Open Device Manager
   - Look under "Sound, video and game controllers"
   - Should see "Akai MPK25" and "USB Audio Device"
   - If yellow warning icon, reinstall drivers

3. **Restart devices:**
   - Unplug both USB devices
   - Wait 10 seconds
   - Plug back in
   - Restart Blooper5

4. **Check Python MIDI library:**
   ```bash
   python -c "import rtmidi; print(rtmidi.get_compiled_api())"
   ```
   Should show available MIDI APIs

---

### SPP Messages Not Appearing

**Symptoms:**
- Blooper5 plays but no console output
- No `[MIDI OUT] SPP:` messages

**Solutions:**

1. **Verify MIDI output is enabled:**
   - Check "Send MIDI Clock" is enabled in settings
   - Verify output device is selected
   - Try restarting playback

2. **Check loop is enabled:**
   - SPP only sent on loop jumps
   - Verify loop region is set in DAWView
   - Check loop mode is active

3. **Console output redirected:**
   - Check if running in IDE (output may be in different panel)
   - Try running from terminal: `python -m blooper5`
   - Check log files if console is disabled

4. **Code changes not applied:**
   - Restart Blooper5 application
   - Verify `midi/handler.py` has SPP implementation
   - Check `ui/views/DAWView.py` calls `send_spp()`

---

### MPK25 Keyboard Not Working

**Symptoms:**
- No notes received when pressing keys
- `test_mpk_notes.py` shows 0 messages

**Solutions:**

1. **Check preset:**
   - Press "Preset" button on MPK25
   - Try Preset 1 "LiveLite"
   - Some presets may have different MIDI mappings

2. **Check MIDI channel:**
   - Default is Channel 1
   - Verify Blooper5 is listening on same channel
   - Try changing MPK25 channel (consult manual)

3. **Check USB connection:**
   - Try different USB port
   - Restart MPK25 (unplug and replug)
   - Check Device Manager for errors

4. **Test with external MIDI monitor:**
   - Use MIDI-OX (Windows) or MIDI Monitor (Mac)
   - Verify MPK25 is sending MIDI data
   - If no data, hardware issue with MPK25

---

### Loopback Test Fails

**Symptoms:**
- `test_bidirectional_spp.py` shows 0/5 messages received
- Physical loopback not working

**Solutions:**

1. **Verify cable connections:**
   - USB2.0-MIDI DIN OUT → MPK25 DIN IN (check polarity!)
   - MPK25 DIN OUT → USB2.0-MIDI DIN IN (check polarity!)
   - MIDI cables are directional (IN/OUT must match)

2. **Check MPK25 MIDI Thru:**
   - Some presets disable MIDI Thru
   - Try different preset
   - Use Vyzex editor to enable MIDI Thru

3. **Test individual directions:**
   - Use external MIDI monitor on USB2.0-MIDI OUT
   - Verify messages are being sent
   - Use external MIDI source to test USB2.0-MIDI IN
   - Verify messages are received

4. **Accept limitation:**
   - CH345 adapter is known to drop bytes
   - Loopback testing is inherently unreliable
   - Focus on uni-directional tests instead:
     - Test A: Blooper5 → USB2.0-MIDI (output only)
     - Test B: MPK25 → Blooper5 (input only)

---

### Partial Messages Received (3-4 out of 5)

**Symptoms:**
- Loopback test shows partial success
- Some SPP messages dropped

**Status:**
- ⚠️ **This is EXPECTED with CH345 adapter**
- Hardware limitation (no FIFO buffer)
- Not a bug in Blooper5

**Solutions:**
- Accept as normal behavior
- Use external MIDI monitor to verify output
- Don't rely on loopback for production testing
- Test with real MIDI sequencer/synth instead

---

### MIDI Port Already in Use

**Symptoms:**
```
[ERROR] Failed to open MIDI port: Port already in use
```

**Solutions:**

1. **Close other applications:**
   - Close DAWs (Ableton, FL Studio, etc.)
   - Close MIDI monitor software
   - Close other instances of Blooper5

2. **Check background processes:**
   - Some MIDI drivers hold ports open
   - Restart computer to release all ports

3. **Use different port:**
   - USB2.0-MIDI has 2 ports (IN and OUT)
   - MPK25 has 3 ports (try different one)

---

## Integration with Blooper5

### Enabling MIDI SPP in Blooper5

**File:** `ui/views/DAWView.py`

SPP is automatically sent when:
1. Loop mode is enabled
2. Playback crosses loop end point
3. MIDI clock output is enabled

**Code location:**
```python
# In _handle_audio_clock():
if self.song.send_midi_clock and self.midi_handler.output_opened:
    if self.is_looping and tick_position < previous_tick:
        # Loop jumped - send SPP
        self.midi_handler.send_spp(tick_position, ticks_per_quarter)
```

### MIDI Handler API

**File:** `midi/handler.py`

Key methods:

```python
# Device management
handler.list_input_devices() → List[str]
handler.list_output_devices() → List[str]
handler.open_input(device_name: Optional[str] = None)
handler.open_output(device_name: Optional[str] = None)

# Sending messages
handler.send_start()
handler.send_stop()
handler.send_continue()
handler.send_clock()
handler.send_spp(tick_position: int, ticks_per_quarter: int)

# Receiving messages
spp_tick = handler.get_spp_from_queue()  # Returns None if queue empty

# Cleanup
handler.close_all()
```

### Adding Device Selection to Song Model

**Optional enhancement:** Allow users to select specific MIDI devices

**File:** `core/models.py`

```python
@dataclass
class Song:
    # ... existing fields ...
    midi_input_device: Optional[str] = None  # e.g., "Akai MPK25 0"
    midi_output_device: Optional[str] = None  # e.g., "MIDIOUT2 (USB2.0-MIDI) 4"
```

**File:** `ui/views/DAWView.py`

```python
# In _start_playback():
if song.send_midi_clock:
    output_device = getattr(song, 'midi_output_device', None)
    self.midi_handler.open_output(output_device)

if song.receive_midi_clock:
    input_device = getattr(song, 'midi_input_device', None)
    self.midi_handler.open_input(input_device)
```

This allows per-project MIDI device configuration.

---

## Success Criteria

### Must Have ✅

- [x] Blooper5 sends SPP via USB2.0-MIDI output
- [x] Console shows correct SPP messages when loop cycles
- [x] No crashes or errors during playback
- [x] MPK25 keyboard can send notes to Blooper5
- [x] Test scripts execute without errors

### Nice to Have ⚠️

- [ ] Physical loopback test passes (may be unreliable due to CH345)
- [ ] MPK25 sends MIDI Clock (if supported by preset)
- [ ] Transport buttons work (depends on preset configuration)
- [ ] External MIDI sequencer responds to Blooper5 SPP

### Out of Scope ❌

- [ ] SPP sending from MPK25 (not confirmed supported by hardware)
- [ ] High-precision MIDI Clock sync (MPK25 has known timing issues)
- [ ] Multiple device simultaneous control
- [ ] MMC (MIDI Machine Control) support
- [ ] SMPTE timecode synchronization

---

## Additional Resources

### MIDI Technical References

- **MIDI 1.0 Specification:** [Official MIDI Association](https://www.midi.org/specifications)
- **USB MIDI Device Class:** [USB.org MIDI 1.0 Spec](https://www.usb.org/sites/default/files/midi10.pdf)
- **Song Position Pointer:** Status 0xF2, 2 data bytes (14-bit value)

### Akai MPK25 Resources

- **User Manual:** [Akai Professional](https://www.strumentimusicali.net/manuali/AKAI_MPK25_ENG.pdf)
- **Preset Overview:** [NoteRepeat.com](https://www.noterepeat.com/products/akai-professional/mpk-2-series/407-akai-mpk2-complete-preset-overview)
- **Vyzex Editor:** Download from Akai website for custom preset creation

### CH345 MIDI Adapter

- **Device Information:** [DeviceHunt](https://devicehunt.com/view/type/usb/vendor/1A86/device/752D)
- **Known Issues:** No FIFO buffer, drops bytes under heavy load
- **Recommendation:** Add 3ms delays between rapid MIDI messages

### External MIDI Monitoring Tools

**Windows:**
- MIDI-OX - Free MIDI monitor and router
- MidiView - Simple MIDI message viewer

**Mac:**
- MIDI Monitor - Free utility from Snoize
- MIDI Scope - Real-time MIDI visualization

**Linux:**
- aseqdump - Command-line MIDI monitor
- gmidimonitor - GTK-based MIDI monitor

---

## Appendix: MIDI Message Reference

### System Real-Time Messages

| Message  | Status Byte | Description                    |
|----------|-------------|--------------------------------|
| Clock    | 0xF8        | Sent 24 times per quarter note |
| Start    | 0xFA        | Start playback from beginning  |
| Continue | 0xFB        | Resume playback                |
| Stop     | 0xFC        | Stop playback                  |

### Song Position Pointer (SPP)

**Status Byte:** 0xF2
**Data Bytes:** 2 (14-bit value, LSB first)
**Format:** `[0xF2, LSB, MSB]`

**Calculation:**
```
SPP = tick_position / 6
LSB = SPP & 0x7F
MSB = (SPP >> 7) & 0x7F
```

**Examples:**
```
tick=0     → SPP=0    → [0xF2, 0x00, 0x00]
tick=480   → SPP=80   → [0xF2, 0x50, 0x00]
tick=960   → SPP=160  → [0xF2, 0x20, 0x01]
tick=1920  → SPP=320  → [0xF2, 0x40, 0x02]
```

### Channel Voice Messages

| Message      | Status Byte | Data Bytes     | Description          |
|--------------|-------------|----------------|----------------------|
| Note Off     | 0x80-0x8F   | Note, Velocity | Release note         |
| Note On      | 0x90-0x9F   | Note, Velocity | Trigger note         |
| Poly AT      | 0xA0-0xAF   | Note, Pressure | Key aftertouch       |
| Control      | 0xB0-0xBF   | CC#, Value     | Control change       |
| Program      | 0xC0-0xCF   | Program#       | Change patch         |
| Channel AT   | 0xD0-0xDF   | Pressure       | Channel aftertouch   |
| Pitch Bend   | 0xE0-0xEF   | LSB, MSB       | Pitch wheel          |

**Note:** Lower nibble (0-F) represents MIDI channel (0-15 = Ch 1-16)

---

## Version History

- **v1.0** (2026-01-21) - Initial testing documentation
  - Hardware setup guide
  - Test script documentation
  - Troubleshooting procedures
  - Integration guide for Blooper5

---

## Contact & Support

For issues with:
- **Blooper5:** Check project README and issue tracker
- **Akai MPK25:** Consult user manual or Akai support
- **CH345 Adapter:** Hardware limitation (no FIFO buffer) is known issue

**Testing Feedback:**
- Report successful configurations
- Share preset settings that work well
- Document any hardware quirks discovered
