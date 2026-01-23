"""
Simple MPK25 input test - directly monitors MIDI messages.
"""
import time
import rtmidi

print("=" * 60)
print("SIMPLE MPK25 INPUT TEST")
print("=" * 60)

# Create MIDI input
midiin = rtmidi.MidiIn()

# List available ports
available_ports = midiin.get_ports()
print("\nAvailable MIDI input ports:")
for i, port in enumerate(available_ports):
    print(f"  {i}: {port}")

# Find and open MPK25
mpk_port = None
for i, port in enumerate(available_ports):
    if "Akai MPK25 0" in port:
        mpk_port = i
        break

if mpk_port is None:
    print("\n[ERROR] Akai MPK25 0 not found!")
    exit(1)

print(f"\n[OK] Opening port {mpk_port}: {available_ports[mpk_port]}")
midiin.open_port(mpk_port)

print("\n[LISTENING] Play notes, hit pads, turn knobs...")
print("Press Ctrl+C to stop\n")

message_count = 0

try:
    while True:
        msg = midiin.get_message()

        if msg:
            message_count += 1
            midi_msg, deltatime = msg

            # Parse message
            if len(midi_msg) > 0:
                status = midi_msg[0]
                msg_type = status & 0xF0
                channel = (status & 0x0F) + 1

                if msg_type == 0x90 and len(midi_msg) >= 3:  # Note On
                    note = midi_msg[1]
                    velocity = midi_msg[2]
                    if velocity > 0:
                        print(f"[{message_count:4d}] Note ON  - Ch {channel} | Note {note:3d} | Vel {velocity:3d}")
                    else:
                        print(f"[{message_count:4d}] Note OFF - Ch {channel} | Note {note:3d}")

                elif msg_type == 0x80 and len(midi_msg) >= 3:  # Note Off
                    note = midi_msg[1]
                    print(f"[{message_count:4d}] Note OFF - Ch {channel} | Note {note:3d}")

                elif msg_type == 0xB0 and len(midi_msg) >= 3:  # Control Change
                    cc_num = midi_msg[1]
                    value = midi_msg[2]
                    print(f"[{message_count:4d}] CC       - Ch {channel} | CC {cc_num:3d} | Val {value:3d}")

                elif status == 0xFA:  # Start
                    print(f"[{message_count:4d}] START")

                elif status == 0xFC:  # Stop
                    print(f"[{message_count:4d}] STOP")

                elif status == 0xF8:  # Clock (skip these)
                    message_count -= 1  # Don't count clock messages

                else:
                    print(f"[{message_count:4d}] OTHER    - {midi_msg}")

        time.sleep(0.01)  # 10ms polling

except KeyboardInterrupt:
    print(f"\n\n[STOPPED] Received {message_count} MIDI messages total")

midiin.close_port()
print("[OK] Port closed")
