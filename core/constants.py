"""
Musical constants and utilities.

MIDI note names, scales, intervals, etc.
"""

# MIDI note number to name mapping
MIDI_NOTE_NAMES = [
    "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"
]

# Common scales (semitone intervals from root)
SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}

# Common time signatures (numerator, denominator)
TIME_SIGNATURES = [
    (4, 4),   # Common time
    (3, 4),   # Waltz
    (6, 8),   # Compound duple
    (7, 8),   # Odd meter
    (5, 4),   # Take Five
    (2, 4),   # March
    (3, 8),   # Compound simple
    (12, 8),  # Compound quadruple
]

# Standard TPQN (Ticks Per Quarter Note) values
TPQN_VALUES = [96, 192, 384, 480, 960]

# Standard BPM ranges
BPM_MIN = 20
BPM_MAX = 300
BPM_DEFAULT = 120


def midi_note_to_name(note_number: int) -> str:
    """
    Convert MIDI note number to name with octave.

    Args:
        note_number: MIDI note (0-127)

    Returns:
        Note name (e.g., "C4", "A#3")

    Example:
        >>> midi_note_to_name(60)
        'C4'
        >>> midi_note_to_name(69)
        'A4'
    """
    raise NotImplementedError("midi_note_to_name not yet implemented")


def name_to_midi_note(note_name: str) -> int:
    """
    Convert note name to MIDI number.

    Args:
        note_name: Note name (e.g., "C4", "A#3")

    Returns:
        MIDI note number (0-127)

    Raises:
        ValueError: If note name is invalid

    Example:
        >>> name_to_midi_note("C4")
        60
        >>> name_to_midi_note("A4")
        69
    """
    raise NotImplementedError("name_to_midi_note not yet implemented")


def get_scale_notes(root: int, scale_name: str) -> list[int]:
    """
    Get MIDI note numbers for a scale starting at root.

    Args:
        root: Root note MIDI number (0-127)
        scale_name: Name of scale (from SCALES dict)

    Returns:
        List of MIDI note numbers in the scale

    Raises:
        ValueError: If scale_name is invalid

    Example:
        >>> get_scale_notes(60, "major")  # C major
        [60, 62, 64, 65, 67, 69, 71]
    """
    raise NotImplementedError("get_scale_notes not yet implemented")


def frequency_to_midi(frequency: float) -> int:
    """
    Convert frequency in Hz to nearest MIDI note number.

    Args:
        frequency: Frequency in Hz

    Returns:
        Nearest MIDI note number (0-127)

    Example:
        >>> frequency_to_midi(440.0)  # A4
        69
    """
    raise NotImplementedError("frequency_to_midi not yet implemented")


def midi_to_frequency(note_number: int) -> float:
    """
    Convert MIDI note number to frequency in Hz.

    Args:
        note_number: MIDI note (0-127)

    Returns:
        Frequency in Hz

    Example:
        >>> midi_to_frequency(69)  # A4
        440.0
    """
    raise NotImplementedError("midi_to_frequency not yet implemented")
