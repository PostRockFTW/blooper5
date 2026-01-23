"""
Helper script to enable MIDI sync on a project file.

Usage: python enable_midi_sync.py <project_file.blooper5>

This modifies the project file to enable both send_midi_clock and receive_midi_clock.
"""
import sys
import msgpack

def enable_midi_sync(filepath):
    """Enable MIDI sync in a project file."""
    print(f"Reading project: {filepath}")

    # Read project file
    with open(filepath, 'rb') as f:
        data = msgpack.unpackb(f.read(), raw=False)

    # Enable MIDI sync
    if 'send_midi_clock' in data:
        data['send_midi_clock'] = True
    if 'receive_midi_clock' in data:
        data['receive_midi_clock'] = True

    print("Enabled: send_midi_clock = True")
    print("Enabled: receive_midi_clock = True")

    # Write back
    with open(filepath, 'wb') as f:
        f.write(msgpack.packb(data, use_bin_type=True))

    print(f"[OK] Project updated: {filepath}")
    print("\nYou can now open this project in Blooper5 to test MIDI sync.")

def main():
    if len(sys.argv) != 2:
        print("Usage: python enable_midi_sync.py <project_file.blooper5>")
        print("\nExample:")
        print("  python enable_midi_sync.py my_project.blooper5")
        return

    filepath = sys.argv[1]
    enable_midi_sync(filepath)

if __name__ == "__main__":
    main()
