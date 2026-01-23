"""
Test MPK25 pad configuration.
Monitors pad hits to see note numbers, channels, and aftertouch behavior.
"""
import time
import rtmidi

print("=" * 60)
print("MPK25 PAD CONFIGURATION TEST")
print("=" * 60)
print("\nThis test helps identify:")
print("  - Current pad note numbers")
print("  - Current MIDI channel for pads")
print("  - Which pads have aftertouch")
print("  - Bank switching behavior")
print("\n" + "=" * 60)

# Create MIDI input
midiin = rtmidi.MidiIn()

# Find and open MPK25
available_ports = midiin.get_ports()
mpk_port = None
for i, port in enumerate(available_ports):
    if "Akai MPK25 0" in port:
        mpk_port = i
        break

if mpk_port is None:
    print("\n[ERROR] Akai MPK25 0 not found!")
    exit(1)

print(f"\n[OK] Opening: {available_ports[mpk_port]}")
midiin.open_port(mpk_port)

print("\n" + "=" * 60)
print("INSTRUCTIONS")
print("=" * 60)
print("\n1. Hit each pad in your current bank")
print("2. Try different banks (use Bank button)")
print("3. Note which pads have aftertouch (press and hold)")
print("\nPress Ctrl+C when done\n")
print("=" * 60)

# Track pad hits
pad_data = {}  # key: (channel, note) -> {'hits': count, 'has_aftertouch': bool}
message_count = 0
last_note_on = None

try:
    while True:
        msg = midiin.get_message()

        if msg:
            midi_msg, deltatime = msg

            if len(midi_msg) > 0:
                status = midi_msg[0]
                msg_type = status & 0xF0
                channel = (status & 0x0F) + 1

                if msg_type == 0x90 and len(midi_msg) >= 3:  # Note On
                    note = midi_msg[1]
                    velocity = midi_msg[2]

                    if velocity > 0:
                        message_count += 1
                        last_note_on = (channel, note)

                        # Track this pad
                        key = (channel, note)
                        if key not in pad_data:
                            pad_data[key] = {'hits': 0, 'has_aftertouch': False}
                        pad_data[key]['hits'] += 1

                        print(f"[{message_count:4d}] PAD HIT  - Ch {channel:2d} | Note {note:3d} | Vel {velocity:3d}")
                    else:
                        # Note Off (velocity 0)
                        print(f"         PAD OFF  - Ch {channel:2d} | Note {note:3d}")

                elif msg_type == 0x80 and len(midi_msg) >= 3:  # Note Off
                    note = midi_msg[1]
                    print(f"         PAD OFF  - Ch {channel:2d} | Note {note:3d}")

                elif msg_type == 0xD0:  # Channel Aftertouch
                    pressure = midi_msg[1]

                    # Mark last note as having aftertouch
                    if last_note_on and last_note_on in pad_data:
                        pad_data[last_note_on]['has_aftertouch'] = True

                    print(f"         AFTERTOUCH - Ch {channel:2d} | Pressure {pressure:3d}")

                elif msg_type == 0xA0 and len(midi_msg) >= 3:  # Polyphonic Aftertouch
                    note = midi_msg[1]
                    pressure = midi_msg[2]

                    # Mark this note as having aftertouch
                    key = (channel, note)
                    if key in pad_data:
                        pad_data[key]['has_aftertouch'] = True

                    print(f"         POLY AT  - Ch {channel:2d} | Note {note:3d} | Pressure {pressure:3d}")

                elif msg_type == 0xB0 and len(midi_msg) >= 3:  # Control Change
                    cc_num = midi_msg[1]
                    value = midi_msg[2]

                    # Bank select messages
                    if cc_num == 0:  # Bank Select MSB
                        print(f"         BANK SELECT MSB - Value {value}")
                    elif cc_num == 32:  # Bank Select LSB
                        print(f"         BANK SELECT LSB - Value {value}")
                    else:
                        print(f"         CC {cc_num:3d} - Ch {channel:2d} | Val {value:3d}")

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    if not pad_data:
        print("\nNo pad hits detected!")
        print("\nPossible issues:")
        print("  - Pads may be disabled in current preset")
        print("  - Try a different preset")
        print("  - Check MPK25 manual for pad configuration")
    else:
        print(f"\nTotal unique pads detected: {len(pad_data)}")
        print(f"Total pad hits: {sum(p['hits'] for p in pad_data.values())}")

        # Group by channel
        channels = {}
        for (ch, note), data in sorted(pad_data.items()):
            if ch not in channels:
                channels[ch] = []
            channels[ch].append((note, data))

        print("\n" + "-" * 60)
        print("PADS BY CHANNEL")
        print("-" * 60)

        for ch in sorted(channels.keys()):
            pads = channels[ch]
            print(f"\nChannel {ch}: {len(pads)} pads")

            notes = sorted([note for note, _ in pads])
            print(f"  Note range: {min(notes)} to {max(notes)}")
            print(f"  Notes: {notes}")

            # Check aftertouch
            aftertouch_pads = [note for note, data in pads if data['has_aftertouch']]
            if aftertouch_pads:
                print(f"  Pads with aftertouch: {aftertouch_pads}")
            else:
                print(f"  No aftertouch detected on any pads")

        print("\n" + "-" * 60)
        print("CONFIGURATION NEEDED")
        print("-" * 60)

        print("\nTarget configuration:")
        print("  Keyboard: Channel 1")
        print("  Pads:     Channel 10 (GM drums)")
        print("  Pad notes: 33-81 (4 banks × 12 pads)")

        current_channels = list(channels.keys())
        if 10 in current_channels:
            print("\n[OK] Pads are already on channel 10!")
        else:
            print(f"\n[!] Pads are on channel {current_channels[0] if current_channels else '?'}")
            print("    Need to reconfigure to channel 10")

        # Check note range
        all_notes = [note for ch_pads in channels.values() for note, _ in ch_pads]
        current_min = min(all_notes)
        current_max = max(all_notes)

        if current_min == 33 and current_max == 81:
            print("\n[OK] Pad notes are already 33-81!")
        else:
            print(f"\n[!] Current pad notes: {current_min}-{current_max}")
            print(f"    Target: 33-81")
            print("    Need to remap pads")

midiin.close_port()
print("\n[OK] Port closed\n")
