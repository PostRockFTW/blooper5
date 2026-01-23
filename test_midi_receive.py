"""
Test MIDI SPP reception from external device.

This script listens for incoming SPP messages from your MIDI controller.
If your MPK25 can send SPP, press buttons/controls to send position changes.
"""
import time
from midi.handler import MIDIHandler

def main():
    print("=== MIDI SPP Receive Test ===\n")

    handler = MIDIHandler()

    # List and open input device
    input_devices = handler.list_input_devices()
    print("Available MIDI Input Devices:")
    for i, device in enumerate(input_devices):
        print(f"  {i}: {device}")

    if not input_devices:
        print("No MIDI input devices found!")
        return

    print("\nOpening first input device...")
    handler.open_input()

    print("\n[LISTENING] Waiting for SPP messages from MIDI device...")
    print("(Press Ctrl+C to stop)\n")

    try:
        while True:
            # Check for incoming SPP messages
            tick = handler.get_spp_from_queue()
            if tick is not None:
                # Convert back to SPP value for display
                spp_value = tick // 120  # 480 / 4 = 120 ticks per sixteenth
                print(f"[RECEIVED] SPP: {spp_value} -> Tick: {tick}")

            time.sleep(0.01)  # 10ms polling

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Stopping test...")

    handler.close_all()
    print("[OK] Test complete")

if __name__ == "__main__":
    main()
