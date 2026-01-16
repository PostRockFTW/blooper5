"""
MIDI input/output handling.

Uses python-rtmidi for cross-platform MIDI support.
"""
from typing import Callable, List, Optional
import rtmidi


class MIDIHandler:
    """
    Handles MIDI input and output.

    Features:
    - Multiple MIDI input devices
    - Multiple MIDI output devices
    - Real-time MIDI event callback
    - MIDI learn for parameter mapping
    """

    def __init__(self):
        """Initialize MIDI handler."""
        raise NotImplementedError("MIDIHandler not yet implemented")

    def list_input_devices(self) -> List[str]:
        """
        Get list of available MIDI input devices.

        Returns:
            List of device names
        """
        raise NotImplementedError("list_input_devices not yet implemented")

    def list_output_devices(self) -> List[str]:
        """
        Get list of available MIDI output devices.

        Returns:
            List of device names
        """
        raise NotImplementedError("list_output_devices not yet implemented")

    def open_input(self, device_name: str, callback: Callable):
        """
        Open MIDI input device.

        Args:
            device_name: Name of MIDI input device
            callback: Function called on MIDI message (message, timestamp)
                     message: List of MIDI bytes
                     timestamp: Time in seconds
        """
        raise NotImplementedError("open_input not yet implemented")

    def close_input(self, device_name: str):
        """
        Close MIDI input device.

        Args:
            device_name: Name of MIDI input device to close
        """
        raise NotImplementedError("close_input not yet implemented")

    def open_output(self, device_name: str):
        """
        Open MIDI output device.

        Args:
            device_name: Name of MIDI output device
        """
        raise NotImplementedError("open_output not yet implemented")

    def close_output(self, device_name: str):
        """
        Close MIDI output device.

        Args:
            device_name: Name of MIDI output device to close
        """
        raise NotImplementedError("close_output not yet implemented")

    def send_message(self, message: List[int], device_name: Optional[str] = None):
        """
        Send MIDI message to output.

        Args:
            message: MIDI message bytes
            device_name: Optional device name (uses default if None)
        """
        raise NotImplementedError("send_message not yet implemented")

    def send_note_on(self, note: int, velocity: int, channel: int = 0):
        """
        Send MIDI note on message.

        Args:
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: MIDI channel (0-15)
        """
        raise NotImplementedError("send_note_on not yet implemented")

    def send_note_off(self, note: int, channel: int = 0):
        """
        Send MIDI note off message.

        Args:
            note: MIDI note number (0-127)
            channel: MIDI channel (0-15)
        """
        raise NotImplementedError("send_note_off not yet implemented")

    def send_cc(self, controller: int, value: int, channel: int = 0):
        """
        Send MIDI control change message.

        Args:
            controller: CC number (0-127)
            value: CC value (0-127)
            channel: MIDI channel (0-15)
        """
        raise NotImplementedError("send_cc not yet implemented")

    def close_all(self):
        """Close all open MIDI devices."""
        raise NotImplementedError("close_all not yet implemented")


def parse_midi_message(message: List[int]) -> dict:
    """
    Parse MIDI message into structured format.

    Args:
        message: MIDI message bytes

    Returns:
        Dictionary with parsed message info:
        - type: "note_on", "note_off", "cc", "program_change", etc.
        - channel: MIDI channel (0-15)
        - Additional fields depending on message type

    Example:
        >>> parse_midi_message([144, 60, 100])
        {'type': 'note_on', 'channel': 0, 'note': 60, 'velocity': 100}
    """
    raise NotImplementedError("parse_midi_message not yet implemented")
