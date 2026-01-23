"""
Quick test script to check available MIDI devices.
"""
from midi.handler import MIDIHandler

def main():
    print("=== MIDI Device Detection ===\n")

    handler = MIDIHandler()

    # List input devices
    print("Available MIDI Input Devices:")
    input_devices = handler.list_input_devices()
    if input_devices:
        for i, device in enumerate(input_devices):
            print(f"  {i}: {device}")
    else:
        print("  No input devices found")

    print()

    # List output devices
    print("Available MIDI Output Devices:")
    output_devices = handler.list_output_devices()
    if output_devices:
        for i, device in enumerate(output_devices):
            print(f"  {i}: {device}")
    else:
        print("  No output devices found")

    print("\n=== Testing Device Open ===\n")

    # Try opening first available devices
    if input_devices:
        print("Opening first input device...")
        handler.open_input()
        print("[OK] Input device opened successfully")

    if output_devices:
        print("Opening first output device...")
        handler.open_output()
        print("[OK] Output device opened successfully")

    # Test SPP sending
    if output_devices:
        print("\n=== Testing SPP Send ===\n")
        print("Sending SPP for tick positions: 0, 480, 960, 1920")
        handler.send_spp(0)      # Beat 1
        handler.send_spp(480)    # Beat 2
        handler.send_spp(960)    # Beat 3
        handler.send_spp(1920)   # Beat 5
        print("[OK] SPP messages sent")

    # Test Start/Stop
    if output_devices:
        print("\n=== Testing MIDI Transport ===\n")
        print("Sending MIDI Start...")
        handler.send_start()
        print("Sending MIDI Stop...")
        handler.send_stop()
        print("[OK] Transport messages sent")

    # Cleanup
    print("\n=== Cleanup ===\n")
    handler.close_all()
    print("[OK] All devices closed")

    print("\nTest complete!")

if __name__ == "__main__":
    main()
