#!/usr/bin/env python3
"""
Real-time MIDI input monitor for debugging.

Displays all incoming MIDI messages with timestamp, parsed format, and raw bytes.

Usage:
    python test_midi_monitor.py [device_index]

Examples:
    python test_midi_monitor.py       # Auto-select first device
    python test_midi_monitor.py 0     # Use device 0
    python test_midi_monitor.py 1     # Use device 1
"""

import rtmidi
import time
import sys
from typing import List, Optional
from midi.handler import parse_midi_message


def list_midi_devices() -> List[str]:
    """List all available MIDI input devices."""
    midi_in = rtmidi.MidiIn()
    ports = midi_in.get_ports()
    midi_in.delete()
    return ports


def select_device(devices: List[str], device_arg: Optional[int] = None) -> int:
    """
    Select MIDI device.

    Args:
        devices: List of available MIDI devices
        device_arg: Optional device index from command line

    Returns:
        Selected device index
    """
    print("\n=== MIDI Input Monitor ===")
    print("Available devices:")
    for i, device in enumerate(devices):
        print(f"  [{i}] {device}")

    if not devices:
        print("ERROR: No MIDI devices found!")
        sys.exit(1)

    # Use command-line argument if provided
    if device_arg is not None:
        if 0 <= device_arg < len(devices):
            return device_arg
        else:
            print(f"Invalid device index {device_arg}, using device 0")
            return 0

    # Check if running in interactive mode
    if not sys.stdin.isatty():
        print(f"\nNon-interactive mode detected, using device 0")
        return 0

    # Interactive mode - ask user to select
    try:
        choice = input(f"\nSelect device (0-{len(devices)-1}) or press Enter for [0]: ").strip()
        if choice == "":
            return 0
        index = int(choice)
        if 0 <= index < len(devices):
            return index
        else:
            print(f"Invalid choice, using device 0")
            return 0
    except (ValueError, KeyboardInterrupt):
        print(f"\nUsing device 0")
        return 0


def format_message(message: List[int], parsed: dict) -> str:
    """Format a MIDI message for display."""
    # Raw bytes in hex
    raw_hex = " ".join(f"{b:02X}" for b in message)

    # Message type and details
    msg_type = parsed.get('type', 'unknown').upper()

    details = ""
    if parsed['type'] == 'cc':
        details = f"Ch:{parsed['channel']}  CC#{parsed['controller']:3d}  Value:{parsed['value']:3d}"
    elif parsed['type'] == 'note_on':
        details = f"Ch:{parsed['channel']}  Note:{parsed['note']:3d}   Vel:{parsed['velocity']:3d}"
    elif parsed['type'] == 'note_off':
        details = f"Ch:{parsed['channel']}  Note:{parsed['note']:3d}   Vel:{parsed['velocity']:3d}"
    elif parsed['type'] == 'mmc':
        cmd_name = parsed.get('command_name', 'unknown')
        cmd_code = parsed.get('mmc_command', 0)
        details = f"Command:{cmd_name} (0x{cmd_code:02X})"
    elif parsed['type'] == 'program_change':
        details = f"Ch:{parsed['channel']}  Program:{parsed['program']}"
    elif parsed['type'] == 'pitch_bend':
        details = f"Ch:{parsed['channel']}  Value:{parsed['value']}"
    elif parsed['type'] == 'spp':
        details = f"Position:{parsed['position']}"
    elif parsed['type'] in ['start', 'stop', 'continue', 'clock']:
        details = "Real-time message"
    elif parsed['type'] == 'poly_aftertouch':
        details = f"Ch:{parsed['channel']}  Note:{parsed['note']}  Pressure:{parsed['pressure']}"
    elif parsed['type'] == 'channel_aftertouch':
        details = f"Ch:{parsed['channel']}  Pressure:{parsed['pressure']}"
    elif parsed['type'] == 'song_select':
        details = f"Song:{parsed['song']}"
    elif parsed['type'] == 'sysex':
        details = f"Length:{len(message)} bytes"
    else:
        details = str(parsed)

    return f"{msg_type:14} | {details:50} | Raw: [{raw_hex}]"


def main():
    """Main entry point."""
    # Parse command-line arguments
    device_arg = None
    if len(sys.argv) > 1:
        try:
            device_arg = int(sys.argv[1])
        except ValueError:
            print(f"ERROR: Invalid device index '{sys.argv[1]}'. Must be an integer.")
            sys.exit(1)

    # List devices
    devices = list_midi_devices()

    # Select device
    device_index = select_device(devices, device_arg)
    device_name = devices[device_index]

    print(f"\nOpening: {device_name}")
    print("Listening for MIDI... (Press Ctrl+C to exit)\n")

    # Open MIDI input
    midi_in = rtmidi.MidiIn()
    midi_in.open_port(device_index)

    # Message counter
    message_count = [0]  # Use list to allow modification in callback

    def midi_callback(message_data, data):
        """Callback for incoming MIDI messages."""
        message, delta_time = message_data
        message_count[0] += 1

        # Parse message
        parsed = parse_midi_message(message)

        # Format timestamp (current time with milliseconds)
        current_time = time.time()
        time_str = time.strftime("%H:%M:%S", time.localtime(current_time))
        ms = int((current_time % 1) * 1000)
        timestamp_str = f"[{time_str}.{ms:03d}]"

        # Format and print message
        formatted = format_message(message, parsed)
        print(f"{timestamp_str} {formatted}")

    # Set up callback
    midi_in.set_callback(midi_callback)

    try:
        # Keep running until Ctrl+C
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n\n=== Exiting ===")
        print(f"Total messages received: {message_count[0]}")
    finally:
        midi_in.close_port()
        midi_in.delete()


if __name__ == "__main__":
    main()
