"""
Quick SPP test - sends a few SPP messages immediately.
"""
import time
from midi.handler import MIDIHandler

def main():
    print("=== Quick SPP Test ===\n")

    handler = MIDIHandler()

    # Open output
    output_devices = handler.list_output_devices()
    if not output_devices:
        print("No MIDI output devices found")
        return

    print(f"Using output: {output_devices[0]}")
    handler.open_output()

    print("\nSending MIDI Start...")
    handler.send_start()
    time.sleep(0.5)

    print("\nSending SPP messages (simulating loop jumps):")
    print("- Tick 0 (loop start)")
    handler.send_spp(0, 480)
    time.sleep(0.5)

    print("- Tick 480 (1 beat in)")
    handler.send_spp(480, 480)
    time.sleep(0.5)

    print("- Tick 960 (2 beats in)")
    handler.send_spp(960, 480)
    time.sleep(0.5)

    print("- Tick 1920 (loop end, jump to 0)")
    handler.send_spp(0, 480)
    time.sleep(0.5)

    print("\nSending MIDI Stop...")
    handler.send_stop()

    print("\nClosing devices...")
    handler.close_all()

    print("\n[OK] Test complete!")
    print("\nIf you have MIDI monitoring software, you should see:")
    print("  - MIDI Start (0xFA)")
    print("  - SPP messages (0xF2 + LSB + MSB)")
    print("  - MIDI Stop (0xFC)")

if __name__ == "__main__":
    main()
