"""
Test bidirectional SPP communication.
Tests simultaneous sending and receiving of SPP messages via physical loopback.

WARNING: The CH345 adapter has no FIFO buffer and may drop bytes.
This test may be unreliable due to hardware limitations.
"""
import time
from midi.handler import MIDIHandler


def test_bidirectional():
    """Test bidirectional SPP communication via physical loopback."""

    print("=" * 60)
    print("BIDIRECTIONAL SPP LOOPBACK TEST")
    print("=" * 60)
    print("\nPhysical Setup Required:")
    print("  Computer -> USB2.0-MIDI DIN OUT -> MPK25 DIN IN")
    print("  MPK25 DIN OUT -> USB2.0-MIDI DIN IN -> Computer")
    print("\nMIDI Port Configuration:")
    print("  OUTPUT: MIDIOUT2 (USB2.0-MIDI) 4")
    print("  INPUT:  USB2.0-MIDI 3")
    print("\nWARNING: CH345 adapter has no FIFO buffer.")
    print("         May drop bytes during loopback testing.")
    print("         This is a known hardware limitation.")
    print("\n" + "=" * 60)

    handler = MIDIHandler()

    try:
        # Open both ports
        print("\n[ACTION] Opening MIDI ports...")
        handler.open_output("MIDIOUT2 (USB2.0-MIDI) 4")
        print("[OK] Output opened: MIDIOUT2 (USB2.0-MIDI) 4")

        handler.open_input("USB2.0-MIDI 3")
        print("[OK] Input opened: USB2.0-MIDI 3")

        # Wait for ports to stabilize
        print("\n[WAIT] Allowing ports to stabilize (500ms)...")
        time.sleep(0.5)

        # Send test sequence
        print("\n[SENDING] MIDI Start...")
        handler.send_start()
        time.sleep(0.05)

        print("[SENDING] SPP sequence with delays...")
        spp_values = [
            (0, "Bar 1, Beat 1"),
            (480, "Bar 2, Beat 1"),
            (960, "Bar 3, Beat 1"),
            (1440, "Bar 4, Beat 1"),
            (1920, "Bar 5, Beat 1"),
        ]

        for tick, description in spp_values:
            print(f"  -> SPP tick {tick:4d} ({description})")
            handler.send_spp(tick, 480)
            time.sleep(0.05)  # 50ms delay between messages

        print("\n[SENDING] MIDI Stop...")
        handler.send_stop()
        time.sleep(0.05)

        # Check for received messages
        print("\n[RECEIVING] Checking incoming SPP from queue...")
        print("(Waiting 1 second for messages to arrive...)")
        time.sleep(1.0)

        received_count = 0
        received_ticks = []

        for i in range(20):  # Check queue 20 times
            tick = handler.get_spp_from_queue()
            if tick is not None:
                received_count += 1
                received_ticks.append(tick)
                print(f"  ✅ Received: tick={tick}")
            time.sleep(0.01)

        # Results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        print(f"\nSent:     5 SPP messages")
        print(f"Received: {received_count} SPP messages")

        if received_count == 5:
            print("\n✅ SUCCESS: All messages received via loopback")
            print("   Physical MIDI loop is working correctly")
        elif received_count > 0:
            print(f"\n⚠️  PARTIAL: Only {received_count}/5 messages received")
            print("   This is expected with CH345 adapter (no FIFO buffer)")
            print("   Loopback is working but unreliable under load")
        else:
            print("\n❌ FAILURE: No messages received")
            print("   Possible issues:")
            print("   - Physical cables not connected correctly")
            print("   - MPK25 MIDI Thru is disabled (check preset)")
            print("   - Wrong MIDI ports selected")
            print("   - USB2.0-MIDI adapter not functioning")

        if received_ticks:
            print(f"\nReceived ticks: {received_ticks}")
            expected = [0, 480, 960, 1440, 1920]
            if received_ticks == expected:
                print("✅ Tick values are correct and in order")
            else:
                print("⚠️  Tick values or order doesn't match expected")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n[CLEANUP] Closing MIDI ports...")
        handler.close_all()
        print("[OK] Ports closed")

    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    print("\nIf loopback test fails:")
    print("1. Verify physical cable connections:")
    print("   - USB2.0-MIDI DIN OUT -> MPK25 DIN IN")
    print("   - MPK25 DIN OUT -> USB2.0-MIDI DIN IN")
    print("\n2. Check MPK25 MIDI Thru setting:")
    print("   - Some presets may have Thru disabled")
    print("   - Try different presets or use Vyzex editor")
    print("\n3. Use external MIDI monitor to verify:")
    print("   - Messages are being sent from USB2.0-MIDI OUT")
    print("   - Messages are being received at USB2.0-MIDI IN")
    print("\n4. For production testing:")
    print("   - Don't rely on loopback (hardware limitation)")
    print("   - Use test_device_selection.py for output testing")
    print("   - Use test_mpk_notes.py for input testing")
    print("   - Test with actual external MIDI sequencer/synth")
    print()


if __name__ == "__main__":
    try:
        test_bidirectional()
    except KeyboardInterrupt:
        print("\n\n[STOPPED] Test interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
