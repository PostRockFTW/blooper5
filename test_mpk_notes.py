"""
Test receiving MIDI notes from MPK25 keyboard.
Monitors all MIDI input from the MPK25 (notes, pads, knobs, transport).
"""
import time
from midi.handler import MIDIHandler


def test_mpk_input():
    """Test receiving MIDI input from MPK25 keyboard."""

    print("=" * 60)
    print("MPK25 KEYBOARD INPUT TEST")
    print("=" * 60)
    print("\nThis test monitors all MIDI input from MPK25:")
    print("  - Keyboard notes (Note On/Off)")
    print("  - Drum pads")
    print("  - Control knobs")
    print("  - Transport buttons (Play/Stop/Record)")
    print("  - Any other MIDI messages")
    print("\nMIDI Port: Akai MPK25 0")
    print("\n" + "=" * 60)

    handler = MIDIHandler()

    try:
        # Open MPK25 input
        print("\n[ACTION] Opening Akai MPK25 0 input...")
        handler.open_input("Akai MPK25 0")
        print("[OK] Input opened")

        print("\n[LISTENING] Waiting for MIDI input from MPK25...")
        print("Try the following:")
        print("  1. Play notes on the keyboard")
        print("  2. Hit the drum pads")
        print("  3. Turn the knobs")
        print("  4. Press transport buttons (Play/Stop/Record)")
        print("\nPress Ctrl+C to stop\n")

        # Custom callback to display all MIDI messages
        message_count = 0

        def display_midi(msg, data):
            nonlocal message_count
            message_count += 1

            # Parse message type
            status = msg[0] if len(msg) > 0 else 0
            msg_type = status & 0xF0
            channel = (status & 0x0F) + 1

            # Decode message
            if msg_type == 0x90 and len(msg) >= 3:  # Note On
                note = msg[1]
                velocity = msg[2]
                if velocity > 0:
                    print(f"  [{message_count:4d}] Note ON  - Ch {channel:2d} | Note {note:3d} | Vel {velocity:3d} | {msg}")
                else:
                    print(f"  [{message_count:4d}] Note OFF - Ch {channel:2d} | Note {note:3d} |          | {msg}")

            elif msg_type == 0x80 and len(msg) >= 3:  # Note Off
                note = msg[1]
                velocity = msg[2]
                print(f"  [{message_count:4d}] Note OFF - Ch {channel:2d} | Note {note:3d} | Vel {velocity:3d} | {msg}")

            elif msg_type == 0xB0 and len(msg) >= 3:  # Control Change
                cc_num = msg[1]
                value = msg[2]
                print(f"  [{message_count:4d}] CC       - Ch {channel:2d} | CC  {cc_num:3d} | Val {value:3d} | {msg}")

            elif msg_type == 0xE0 and len(msg) >= 3:  # Pitch Bend
                lsb = msg[1]
                msb = msg[2]
                value = (msb << 7) | lsb
                print(f"  [{message_count:4d}] PitchBnd - Ch {channel:2d} | Value {value:5d}      | {msg}")

            elif status == 0xFA:  # Start
                print(f"  [{message_count:4d}] START    - System Real-Time          | {msg}")

            elif status == 0xFB:  # Continue
                print(f"  [{message_count:4d}] CONTINUE - System Real-Time          | {msg}")

            elif status == 0xFC:  # Stop
                print(f"  [{message_count:4d}] STOP     - System Real-Time          | {msg}")

            elif status == 0xF8:  # Clock
                # Don't print clock messages (too verbose)
                pass

            elif status == 0xF2 and len(msg) >= 3:  # SPP
                lsb = msg[1]
                msb = msg[2]
                spp = (msb << 7) | lsb
                tick = spp * 6
                print(f"  [{message_count:4d}] SPP      - Position {spp:5d} (tick {tick:5d}) | {msg}")

            else:
                print(f"  [{message_count:4d}] OTHER    - {msg}")

        # Override the input callback
        handler._midi_input_callback = display_midi

        # Monitor indefinitely
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n[STOPPED] Monitoring stopped by user")

        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"\nTotal messages received: {message_count}")

        if message_count == 0:
            print("\n⚠️  No MIDI messages received")
            print("\nPossible issues:")
            print("  - MPK25 not connected via USB")
            print("  - Wrong preset selected (some presets may not send MIDI)")
            print("  - USB connection issue")
            print("  - MIDI channel mismatch")
            print("\nTroubleshooting:")
            print("  1. Check USB cable is connected")
            print("  2. Try different preset (press 'Preset' button on MPK25)")
            print("  3. Check Windows Device Manager for USB MIDI device")
            print("  4. Restart MPK25 (unplug and replug USB)")
        else:
            print("\n✅ SUCCESS: MPK25 is sending MIDI data")
            print("   Integration with Blooper5 should work")
            print("\nNext steps:")
            print("  1. Load test_midi_sync.blooper5 in Blooper5")
            print("  2. Configure MIDI input to 'Akai MPK25 0'")
            print("  3. Play notes on MPK25 to trigger Blooper5 synth")
            print("  4. Verify Blooper5 sends SPP via USB2.0-MIDI output")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[CLEANUP] Closing MIDI input...")
        handler.close_all()
        print("[OK] Input closed")

    print()


if __name__ == "__main__":
    try:
        test_mpk_input()
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
