"""
Test simulating loop-based SPP sending.

This simulates what happens in DAWView when playback loops:
- Advances tick position
- Sends SPP when looping back to loop_start
- Shows the bidirectional flow
"""
import time
from midi.handler import MIDIHandler

def simulate_playback_loop(handler, tpqn=480, bpm=120):
    """
    Simulate playback with looping.

    Args:
        handler: MIDIHandler instance
        tpqn: Ticks per quarter note (default 480)
        bpm: Beats per minute (default 120)
    """
    # Loop parameters (2 bars at 4/4)
    loop_start_tick = 0
    loop_end_tick = 1920  # 4 beats * 480 ticks = 1920 ticks per bar, 2 bars = 3840

    # Playback state
    current_tick = 0
    ticks_per_frame = 50  # Simulate ~10fps advancement

    print(f"Loop: {loop_start_tick} -> {loop_end_tick} ticks")
    print(f"TPQN: {tpqn}, BPM: {bpm}")
    print(f"Loop length: {loop_end_tick / tpqn} beats = {(loop_end_tick / tpqn) / 4} measures\n")

    print("[SIMULATION] Press Ctrl+C to stop\n")

    # Send MIDI Start
    handler.send_start()

    try:
        loop_count = 0
        while True:
            # Advance playback
            current_tick += ticks_per_frame

            # Check for loop
            if current_tick >= loop_end_tick:
                loop_count += 1
                overshoot = current_tick - loop_end_tick
                current_tick = loop_start_tick + overshoot

                print(f"[LOOP #{loop_count}] Jumping back! Sending SPP for tick {int(current_tick)}")

                # Send SPP (this is what DAWView does)
                handler.send_spp(int(current_tick), tpqn)

            # Check for incoming SPP
            incoming_tick = handler.get_spp_from_queue()
            if incoming_tick is not None:
                print(f"[RECEIVED SPP] External device jumped to tick {incoming_tick}")
                current_tick = float(incoming_tick)

            # Display progress every second
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n[STOPPED] Stopping playback...")

    # Send MIDI Stop
    handler.send_stop()

def main():
    print("=== MIDI Loop SPP Simulation ===\n")

    handler = MIDIHandler()

    # Open output
    output_devices = handler.list_output_devices()
    if output_devices:
        print(f"Using output: {output_devices[0]}")
        handler.open_output()
    else:
        print("No MIDI output devices found")
        return

    # Open input (optional - for bidirectional test)
    input_devices = handler.list_input_devices()
    if input_devices:
        print(f"Using input: {input_devices[0]}")
        handler.open_input()
        print("(You can send SPP from external device to test bidirectional sync)")

    print()

    # Run simulation
    simulate_playback_loop(handler)

    # Cleanup
    handler.close_all()
    print("[OK] Simulation complete")

if __name__ == "__main__":
    main()
