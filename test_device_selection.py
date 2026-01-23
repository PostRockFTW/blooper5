"""
Test MIDI output to specific devices.
Verifies that messages are routed to the correct ports.
"""
import time
from midi.handler import MIDIHandler


def test_specific_output():
    """Test sending MIDI messages to specific output devices."""

    print("=" * 60)
    print("TEST 1: USB2.0-MIDI OUTPUT")
    print("=" * 60)
    print("\nThis test sends MIDI messages to USB2.0-MIDI adapter")
    print("Expected: SPP messages appear on USB2.0-MIDI DIN OUT")
    print("Physical: DIN OUT -> MPK25 DIN IN\n")

    handler = MIDIHandler()

    try:
        # Test 1: Send to USB2.0-MIDI
        print("[ACTION] Opening MIDIOUT2 (USB2.0-MIDI) 4...")
        handler.open_output("MIDIOUT2 (USB2.0-MIDI) 4")
        print("[OK] Output opened")

        print("\n[SENDING] MIDI Start...")
        handler.send_start()
        time.sleep(0.1)

        print("[SENDING] SPP at tick 0 (bar 1, beat 1)...")
        handler.send_spp(0, 480)
        time.sleep(0.1)

        print("[SENDING] SPP at tick 480 (bar 2, beat 1)...")
        handler.send_spp(480, 480)
        time.sleep(0.1)

        print("[SENDING] SPP at tick 960 (bar 3, beat 1)...")
        handler.send_spp(960, 480)
        time.sleep(0.1)

        print("[SENDING] MIDI Stop...")
        handler.send_stop()
        time.sleep(0.1)

        print("\n[OK] Test 1 complete - Check MIDI monitor for messages")

    except Exception as e:
        print(f"\n[ERROR] Test 1 failed: {e}")
    finally:
        handler.close_all()

    print("\n" + "=" * 60)
    print("TEST 2: MPK25 OUTPUT (Optional)")
    print("=" * 60)
    print("\nThis test sends MIDI messages directly to MPK25 USB port")
    print("Note: MPK25 acts as controller, may not respond to SPP")
    print("Expected: Messages sent, but no visible response on MPK25\n")

    handler = MIDIHandler()

    try:
        # Test 2: Send to MPK25 (may not work - MPK25 is a controller)
        print("[ACTION] Opening Akai MPK25 port...")
        # Try different port names the MPK25 might have
        mpk_ports = [
            "Akai MPK25 0",
            "MIDIOUT2 (Akai MPK25) 1",
            "MIDIOUT3 (Akai MPK25) 2"
        ]

        opened = False
        for port in mpk_ports:
            try:
                handler.open_output(port)
                print(f"[OK] Opened: {port}")
                opened = True
                break
            except:
                print(f"[SKIP] Port not available: {port}")

        if opened:
            print("\n[SENDING] MIDI Start...")
            handler.send_start()
            time.sleep(0.1)

            print("[SENDING] SPP at tick 0...")
            handler.send_spp(0, 480)
            time.sleep(0.1)

            print("[SENDING] MIDI Stop...")
            handler.send_stop()
            time.sleep(0.1)

            print("\n[OK] Test 2 complete")
            print("[NOTE] MPK25 is a controller and may ignore these messages")
        else:
            print("\n[SKIP] No MPK25 output port available")

    except Exception as e:
        print(f"\n[ERROR] Test 2 failed: {e}")
    finally:
        handler.close_all()

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)
    print("\nRecommendations:")
    print("1. Use USB2.0-MIDI for SPP output (Test 1)")
    print("2. Use Akai MPK25 0 for keyboard input")
    print("3. Monitor MIDI traffic with external MIDI monitor software")
    print("\nNext steps:")
    print("- Run test_bidirectional_spp.py for loopback testing")
    print("- Run test_mpk_notes.py for keyboard input testing")
    print("- Load test_midi_sync.blooper5 in Blooper5 for full integration test")
    print()


if __name__ == "__main__":
    try:
        test_specific_output()
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
