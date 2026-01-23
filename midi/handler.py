"""
MIDI input/output handling for bidirectional SPP sync.

Uses python-rtmidi for cross-platform MIDI support.
"""
from typing import List, Optional
import queue
import rtmidi


class MIDIHandler:
    """
    Handles MIDI input and output with Song Position Pointer (SPP) support.

    Features:
    - SPP (0xF2) sending on loop jumps
    - SPP reception for playhead control
    - Thread-safe queue communication (MIDI thread -> audio thread)
    - MIDI Start (0xFA) and Stop (0xFC) messages
    - Graceful handling when no devices available
    """

    def __init__(self):
        """Initialize MIDI handler."""
        self.midi_in: Optional[rtmidi.MidiIn] = None
        self.midi_out: Optional[rtmidi.MidiOut] = None

        # Thread-safe queue for SPP messages (MIDI thread -> audio thread)
        # Limit size to 10 to prevent memory buildup
        self.spp_queue: queue.Queue = queue.Queue(maxsize=10)

        # Thread-safe queue for incoming MIDI note events (MIDI thread -> audio thread)
        # Larger size for high-throughput note input
        self.note_event_queue: queue.Queue = queue.Queue(maxsize=1000)

        # Thread-safe queue for transport control events (MIDI thread -> audio thread)
        # For MIDI learn and transport control mapping
        self.control_event_queue: queue.Queue = queue.Queue(maxsize=100)

    @property
    def input_opened(self) -> bool:
        """Check if MIDI input is currently open."""
        return self.midi_in is not None

    @property
    def output_opened(self) -> bool:
        """Check if MIDI output is currently open."""
        return self.midi_out is not None

    def list_input_devices(self) -> List[str]:
        """
        Get list of available MIDI input devices.

        Returns:
            List of device names
        """
        midi_in = rtmidi.MidiIn()
        ports = midi_in.get_ports()
        midi_in.delete()
        return ports

    def list_output_devices(self) -> List[str]:
        """
        Get list of available MIDI output devices.

        Returns:
            List of device names
        """
        midi_out = rtmidi.MidiOut()
        ports = midi_out.get_ports()
        midi_out.delete()
        return ports

    def open_input(self, device_name: Optional[str] = None):
        """
        Open MIDI input device.

        Args:
            device_name: Name of MIDI input device (uses first device if None)
        """
        try:
            self.midi_in = rtmidi.MidiIn()
            ports = self.midi_in.get_ports()

            if not ports:
                print("[MIDI] No input devices available")
                self.midi_in.delete()
                self.midi_in = None
                return

            # Select device
            if device_name is None:
                port_index = 0
            else:
                try:
                    port_index = ports.index(device_name)
                except ValueError:
                    print(f"[MIDI] Device '{device_name}' not found, using first device")
                    port_index = 0

            # Open port and set callback
            self.midi_in.open_port(port_index)
            self.midi_in.set_callback(self._midi_input_callback)

            print(f"[MIDI] Opened input: {ports[port_index]}")

        except Exception as e:
            print(f"[MIDI] Error opening input: {e}")
            if self.midi_in is not None:
                self.midi_in.delete()
                self.midi_in = None

    def open_output(self, device_name: Optional[str] = None):
        """
        Open MIDI output device.

        Args:
            device_name: Name of MIDI output device (uses first device if None)
        """
        try:
            self.midi_out = rtmidi.MidiOut()
            ports = self.midi_out.get_ports()

            if not ports:
                print("[MIDI] No output devices available")
                self.midi_out.delete()
                self.midi_out = None
                return

            # Select device
            if device_name is None:
                port_index = 0
            else:
                try:
                    port_index = ports.index(device_name)
                except ValueError:
                    print(f"[MIDI] Device '{device_name}' not found, using first device")
                    port_index = 0

            # Open port
            self.midi_out.open_port(port_index)

            print(f"[MIDI] Opened output: {ports[port_index]}")

        except Exception as e:
            print(f"[MIDI] Error opening output: {e}")
            if self.midi_out is not None:
                self.midi_out.delete()
                self.midi_out = None

    def send_spp(self, tick_position: int, tpqn: int = 480):
        """
        Send Song Position Pointer (SPP) message.

        SPP format: 0xF2 + LSB + MSB (3 bytes)
        Position is in 16th notes (not MIDI clocks)
        1 SPP unit = 1 sixteenth note = TPQN/4 ticks

        Args:
            tick_position: Current tick position (MIDI ticks)
            tpqn: Ticks per quarter note (default 480)
        """
        if self.midi_out is None:
            return

        try:
            # Convert ticks to 16th notes (SPP units)
            ticks_per_sixteenth = tpqn / 4  # 480 / 4 = 120
            spp_value = int(tick_position / ticks_per_sixteenth)

            # Clamp to 14-bit range (0-16383)
            spp_value = max(0, min(16383, spp_value))

            # Split into 7-bit LSB and MSB
            lsb = spp_value & 0x7F
            msb = (spp_value >> 7) & 0x7F

            # Send SPP message
            message = [0xF2, lsb, msb]
            self.midi_out.send_message(message)

            print(f"[MIDI OUT] SPP: tick={tick_position}, spp={spp_value}, msg=[0xF2, 0x{lsb:02X}, 0x{msb:02X}]")

        except Exception as e:
            print(f"[MIDI] Error sending SPP: {e}")

    def send_start(self):
        """
        Send MIDI Start message (0xFA).

        Tells external devices to start playback from current position.
        """
        if self.midi_out is None:
            return

        try:
            self.midi_out.send_message([0xFA])
            print("[MIDI OUT] Start")
        except Exception as e:
            print(f"[MIDI] Error sending Start: {e}")

    def send_stop(self):
        """
        Send MIDI Stop message (0xFC).

        Tells external devices to stop playback.
        """
        if self.midi_out is None:
            return

        try:
            self.midi_out.send_message([0xFC])
            print("[MIDI OUT] Stop")
        except Exception as e:
            print(f"[MIDI] Error sending Stop: {e}")

    def send_continue(self):
        """
        Send MIDI Continue message (0xFB).

        Tells external devices to resume playback from current SPP position.
        """
        if self.midi_out is None:
            return

        try:
            self.midi_out.send_message([0xFB])
            print("[MIDI OUT] Continue")
        except Exception as e:
            print(f"[MIDI] Error sending Continue: {e}")

    def _midi_input_callback(self, message_data, data=None):
        """
        Internal callback for incoming MIDI messages.

        Runs in rtmidi's own thread (NOT audio thread).
        Thread-safe communication via queue.

        Args:
            message_data: Tuple of (message, timestamp)
            data: Optional user data (unused)
        """
        message, timestamp = message_data

        if not message or len(message) < 1:
            return

        status = message[0]

        # Handle SPP messages (0xF2)
        if status == 0xF2:
            if len(message) >= 3:
                # Extract LSB and MSB
                lsb = message[1] & 0x7F
                msb = message[2] & 0x7F
                spp_value = lsb | (msb << 7)

                # Convert SPP value (16th notes) to ticks (assuming TPQN=480)
                ticks_per_sixteenth = 480 / 4  # 120
                tick_position = int(spp_value * ticks_per_sixteenth)

                print(f"[MIDI IN] SPP: spp={spp_value}, tick={tick_position}")

                # Put in queue for audio thread (non-blocking)
                try:
                    self.spp_queue.put_nowait(tick_position)
                except queue.Full:
                    print("[MIDI] Warning: SPP queue full, dropping message")

        # Handle channel voice messages (0x80-0xEF)
        elif status >= 0x80 and status <= 0xEF:
            # Parse the full MIDI message
            parsed = parse_midi_message(message)

            if parsed and parsed.get('type') != 'unknown':
                # Create event dictionary for audio thread
                event = {
                    'type': parsed['type'],
                    'channel': parsed.get('channel', 0),
                    'timestamp': timestamp
                }

                # Add type-specific fields
                if 'note' in parsed:
                    event['note'] = parsed['note']
                if 'velocity' in parsed:
                    event['velocity'] = parsed['velocity']
                if 'pressure' in parsed:
                    event['pressure'] = parsed['pressure']
                if 'controller' in parsed:
                    event['controller'] = parsed['controller']
                if 'value' in parsed:
                    event['value'] = parsed['value']

                # Route to appropriate queues
                # Control events (CC, Note On, Program Change) go to both queues
                if parsed['type'] in ['cc', 'note_on', 'program_change']:
                    # Add to control queue for transport/MIDI learn
                    try:
                        self.control_event_queue.put_nowait(event.copy())
                    except queue.Full:
                        print("[MIDI] Warning: Control event queue full, dropping message")

                # All note events go to note queue for recording
                try:
                    self.note_event_queue.put_nowait(event)
                except queue.Full:
                    print("[MIDI] Warning: Note event queue full, dropping message")

        # Handle MMC messages (SysEx)
        elif status == 0xF0:
            parsed = parse_midi_message(message)
            if parsed.get('type') == 'mmc':
                # Route MMC to control queue
                event = {
                    'type': 'mmc',
                    'mmc_command': parsed['mmc_command'],
                    'command_name': parsed['command_name'],
                    'timestamp': timestamp
                }
                try:
                    self.control_event_queue.put_nowait(event)
                except queue.Full:
                    print("[MIDI] Warning: Control event queue full, dropping MMC message")

    def get_spp_from_queue(self) -> Optional[int]:
        """
        Get pending SPP tick position from queue (non-blocking).

        Called by audio thread to check for incoming SPP messages.

        Returns:
            Tick position if SPP message available, None otherwise
        """
        try:
            return self.spp_queue.get_nowait()
        except queue.Empty:
            return None

    def get_note_events(self) -> List[dict]:
        """
        Get all pending note events from queue (non-blocking).

        Called by audio thread to process incoming MIDI notes.

        Returns:
            List of event dictionaries with keys:
            - type: Event type (note_on, note_off, cc, aftertouch, etc.)
            - channel: MIDI channel (0-15)
            - note: Note number (for note_on/note_off/poly_aftertouch)
            - velocity: Note velocity (for note_on/note_off)
            - pressure: Aftertouch pressure (for aftertouch events)
            - controller: CC number (for cc events)
            - value: CC value (for cc events)
            - timestamp: Delta time in seconds
        """
        events = []
        while not self.note_event_queue.empty():
            try:
                events.append(self.note_event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def get_control_events(self) -> List[dict]:
        """
        Get all pending control events from queue (non-blocking).

        Called by UI thread to process transport control and MIDI learn.

        Returns:
            List of event dictionaries with keys:
            - type: Event type (cc, note_on, mmc, program_change)
            - channel: MIDI channel (0-15) for channel messages
            - controller: CC number (for cc events)
            - value: CC value (for cc events)
            - note: Note number (for note_on events)
            - velocity: Note velocity (for note_on events)
            - mmc_command: MMC command code (for mmc events)
            - command_name: MMC command name (for mmc events)
            - timestamp: Delta time in seconds
        """
        events = []
        while not self.control_event_queue.empty():
            try:
                events.append(self.control_event_queue.get_nowait())
            except queue.Empty:
                break
        return events

    def close_all(self):
        """Close all open MIDI devices."""
        if self.midi_in is not None:
            try:
                self.midi_in.close_port()
                self.midi_in.delete()
            except Exception as e:
                print(f"[MIDI] Error closing input: {e}")
            finally:
                self.midi_in = None

        if self.midi_out is not None:
            try:
                self.midi_out.close_port()
                self.midi_out.delete()
            except Exception as e:
                print(f"[MIDI] Error closing output: {e}")
            finally:
                self.midi_out = None

        print("[MIDI] All devices closed")


def _get_mmc_command_name(command_code: int) -> str:
    """Get human-readable MMC command name."""
    mmc_commands = {
        0x01: 'stop',
        0x02: 'play',
        0x04: 'fast_forward',
        0x05: 'rewind',
        0x06: 'record',
        0x07: 'pause',
        0x09: 'deferred_play',
    }
    return mmc_commands.get(command_code, f'unknown_{command_code:02X}')


def parse_midi_message(message: List[int]) -> dict:
    """
    Parse MIDI message into structured format.

    Args:
        message: MIDI message bytes

    Returns:
        Dictionary with parsed message info:
        - type: "note_on", "note_off", "cc", "spp", "start", "stop", etc.
        - channel: MIDI channel (0-15) for channel messages
        - Additional fields depending on message type

    Example:
        >>> parse_midi_message([0x90, 60, 100])
        {'type': 'note_on', 'channel': 0, 'note': 60, 'velocity': 100}

        >>> parse_midi_message([0xF2, 0x10, 0x00])
        {'type': 'spp', 'position': 16}
    """
    if not message:
        return {'type': 'unknown'}

    status = message[0]

    # System Real-Time Messages (0xF8-0xFF)
    if status == 0xF8:
        return {'type': 'clock'}
    elif status == 0xFA:
        return {'type': 'start'}
    elif status == 0xFB:
        return {'type': 'continue'}
    elif status == 0xFC:
        return {'type': 'stop'}
    elif status == 0xFE:
        return {'type': 'active_sensing'}
    elif status == 0xFF:
        return {'type': 'reset'}

    # System Common Messages (0xF0-0xF7)
    if status == 0xF0:
        # Check for MMC (MIDI Machine Control)
        # MMC format: F0 7F <device_id> 06 <command> F7
        # Universal device ID (7F) means all devices
        if len(message) >= 5 and message[1] == 0x7F and message[3] == 0x06:
            mmc_command = message[4]
            return {
                'type': 'mmc',
                'mmc_command': mmc_command,
                'command_name': _get_mmc_command_name(mmc_command)
            }
        # Generic SysEx (not MMC)
        return {'type': 'sysex', 'data': message}
    elif status == 0xF2:  # Song Position Pointer
        if len(message) >= 3:
            lsb = message[1] & 0x7F
            msb = message[2] & 0x7F
            position = lsb | (msb << 7)
            return {'type': 'spp', 'position': position}
        return {'type': 'spp', 'position': 0}
    elif status == 0xF3:  # Song Select
        if len(message) >= 2:
            return {'type': 'song_select', 'song': message[1] & 0x7F}
        return {'type': 'song_select', 'song': 0}

    # Channel Messages (0x80-0xEF)
    channel = status & 0x0F
    message_type = status & 0xF0

    if message_type == 0x80:  # Note Off
        if len(message) >= 3:
            return {'type': 'note_off', 'channel': channel, 'note': message[1], 'velocity': message[2]}
    elif message_type == 0x90:  # Note On
        if len(message) >= 3:
            velocity = message[2]
            # Note On with velocity 0 is Note Off
            if velocity == 0:
                return {'type': 'note_off', 'channel': channel, 'note': message[1], 'velocity': 0}
            return {'type': 'note_on', 'channel': channel, 'note': message[1], 'velocity': velocity}
    elif message_type == 0xA0:  # Polyphonic Aftertouch
        if len(message) >= 3:
            return {'type': 'poly_aftertouch', 'channel': channel, 'note': message[1], 'pressure': message[2]}
    elif message_type == 0xB0:  # Control Change
        if len(message) >= 3:
            return {'type': 'cc', 'channel': channel, 'controller': message[1], 'value': message[2]}
    elif message_type == 0xC0:  # Program Change
        if len(message) >= 2:
            return {'type': 'program_change', 'channel': channel, 'program': message[1]}
    elif message_type == 0xD0:  # Channel Aftertouch
        if len(message) >= 2:
            return {'type': 'channel_aftertouch', 'channel': channel, 'pressure': message[1]}
    elif message_type == 0xE0:  # Pitch Bend
        if len(message) >= 3:
            lsb = message[1]
            msb = message[2]
            value = (msb << 7) | lsb
            return {'type': 'pitch_bend', 'channel': channel, 'value': value}

    return {'type': 'unknown', 'data': message}
