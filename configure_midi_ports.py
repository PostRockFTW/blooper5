"""
Configure which MIDI ports to use for testing.
Allows selection of specific devices instead of using "first available".
"""
from midi.handler import MIDIHandler


def list_and_select_devices():
    """List all available MIDI devices and provide recommendations."""
    handler = MIDIHandler()

    # List input devices
    print("=" * 60)
    print("MIDI INPUT DEVICES")
    print("=" * 60)
    inputs = handler.list_input_devices()
    if inputs:
        for i, device in enumerate(inputs):
            print(f"  {i}: {device}")
    else:
        print("  No input devices found")

    # List output devices
    print("\n" + "=" * 60)
    print("MIDI OUTPUT DEVICES")
    print("=" * 60)
    outputs = handler.list_output_devices()
    if outputs:
        for i, device in enumerate(outputs):
            print(f"  {i}: {device}")
    else:
        print("  No output devices found")

    # Provide recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDED SETUP FOR SPP TESTING")
    print("=" * 60)
    print("\nTest A: Blooper5 -> USB2.0-MIDI -> MPK25")
    print("  OUTPUT: MIDIOUT2 (USB2.0-MIDI) 4")
    print("  INPUT:  Akai MPK25 0")
    print("  Purpose: Send SPP from Blooper5, receive keyboard notes from MPK25")
    print("  Data Flow: Blooper5 -> USB2.0-MIDI DIN OUT -> MPK25 DIN IN")
    print("              MPK25 keys -> USB Port 0 -> Blooper5")

    print("\nTest B: Physical Loopback (Optional - May be unreliable)")
    print("  OUTPUT: MIDIOUT2 (USB2.0-MIDI) 4")
    print("  INPUT:  USB2.0-MIDI 3")
    print("  Purpose: Test echo via MPK25 DIN passthrough")
    print("  Warning: CH345 adapter has no FIFO buffer, may drop bytes")

    print("\n" + "=" * 60)
    print("DEVICE CAPABILITIES")
    print("=" * 60)
    print("\nAkai MPK25:")
    print("  [+] MIDI Start/Stop/Continue (transport buttons)")
    print("  [+] MIDI Clock transmission (basic)")
    print("  [+] MIDI Clock reception (external sync)")
    print("  [+] Note input (keys, pads)")
    print("  [-] Song Position Pointer (SPP) - NOT confirmed")

    print("\nUSB2.0-MIDI Adapter (CH345):")
    print("  [+] SPP messages (0xF2) - fully supported")
    print("  [+] MIDI Clock messages (0xF8)")
    print("  [+] All System Real-Time messages")
    print("  [!] No hardware MIDI Thru")
    print("  [!] No FIFO buffer (add 3ms delays between messages)")
    print("  [!] Physical loopback testing unreliable")

    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("\n1. Check MPK25 preset (press 'Preset' button on device)")
    print("   Recommended: Preset 1 'LiveLite' (Ableton Live default)")

    print("\n2. Run test scripts:")
    print("   python test_device_selection.py   - Test specific port routing")
    print("   python test_bidirectional_spp.py  - Test simultaneous send/receive")
    print("   python test_mpk_notes.py          - Test MPK25 keyboard input")

    print("\n3. Test in Blooper5:")
    print("   - Load test_midi_sync.blooper5")
    print("   - Enable MIDI clock sending")
    print("   - Configure output to USB2.0-MIDI")
    print("   - Press Play and watch for SPP messages in console")

    print("\n")

    return inputs, outputs


if __name__ == "__main__":
    try:
        list_and_select_devices()
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
