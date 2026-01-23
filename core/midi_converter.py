"""
MIDI file import/export with loop marker support.

Supports loop marker conventions:
1. Meta Event FF 06 markers: "loopStart" and "loopEnd" (community standard)
2. CC 111: Loop start from RPG Maker (loop end = end of file)
"""
import mido
from pathlib import Path
from typing import Optional, Tuple
from core.models import Song, Track, Note

class MIDIConverter:
    """Handles MIDI file import/export."""

    TPQN = 480  # Blooper5 standard ticks per quarter note

    @classmethod
    def import_midi(cls, path: Path) -> Song:
        """
        Import Standard MIDI File to Song.

        Detects loop markers:
        - Meta Event markers "loopStart" and "loopEnd"
        - CC 111 (RPG Maker style - loop end = file end)

        Args:
            path: Path to .mid file

        Returns:
            Song object with tracks and loop markers
        """
        mid = mido.MidiFile(path)

        # Initialize loop marker detection
        loop_start_tick = None
        loop_end_tick = None

        # Convert tracks
        tracks = []
        absolute_tick = 0

        for track_idx, midi_track in enumerate(mid.tracks):
            notes = []
            current_tick = 0

            # Track active notes for note-off matching
            active_notes = {}  # {pitch: (start_tick, velocity)}

            for msg in midi_track:
                current_tick += msg.time

                # === LOOP MARKER DETECTION ===

                # Method 1: Meta Event markers (FF 06)
                if msg.type == 'marker':
                    if msg.text.lower() in ['loopstart', 'loop_start', 'loop start']:
                        loop_start_tick = current_tick
                    elif msg.text.lower() in ['loopend', 'loop_end', 'loop end']:
                        loop_end_tick = current_tick

                # Method 2: CC 111 (RPG Maker)
                elif msg.type == 'control_change' and msg.control == 111:
                    loop_start_tick = current_tick
                    # For CC 111, loop end is always end of file (set later)

                # === NOTE COLLECTION ===

                elif msg.type == 'note_on' and msg.velocity > 0:
                    active_notes[msg.note] = (current_tick, msg.velocity)

                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    if msg.note in active_notes:
                        start_tick, velocity = active_notes.pop(msg.note)
                        duration = current_tick - start_tick

                        # Convert to Blooper5 Note format
                        note = Note(
                            note=msg.note,
                            start=start_tick / cls.TPQN,  # Convert to beats
                            duration=duration / cls.TPQN,
                            velocity=velocity
                        )
                        notes.append(note)

            # Create track
            if notes:
                track = Track(
                    name=f"Track {track_idx + 1}",
                    notes=tuple(notes)
                )
                tracks.append(track)

            # Track total file length
            absolute_tick = max(absolute_tick, current_tick)

        # If CC 111 was used, loop_end is end of file
        if loop_start_tick is not None and loop_end_tick is None:
            loop_end_tick = absolute_tick

        # Calculate song length
        length_ticks = absolute_tick or cls.TPQN * 4  # Default 1 bar

        # Get tempo from MIDI file (default 120 BPM)
        tempo = 120.0
        for msg in mid.tracks[0]:
            if msg.type == 'set_tempo':
                tempo = mido.tempo2bpm(msg.tempo)
                break

        # Create song
        song = Song(
            name=path.stem,
            bpm=tempo,
            time_signature=(4, 4),  # TODO: Parse from MIDI
            tpqn=cls.TPQN,
            tracks=tuple(tracks[:16]),  # Max 16 tracks
            length_ticks=length_ticks,
            loop_start_tick=loop_start_tick or 0,
            loop_end_tick=loop_end_tick,  # None if no loop detected
            loop_enabled=(loop_end_tick is not None)
        )

        return song

    @classmethod
    def export_midi(cls, song: Song, path: Path):
        """
        Export Song to Standard MIDI File with loop markers.

        Writes both loop conventions for maximum compatibility:
        - Meta Event markers "loopStart" and "loopEnd"
        - CC 111 at loop start position

        Args:
            song: Song to export
            path: Destination .mid file path
        """
        mid = mido.MidiFile(ticks_per_beat=cls.TPQN)

        # Track 0: Meta events and loop markers
        meta_track = mido.MidiTrack()
        mid.tracks.append(meta_track)

        # Track name
        meta_track.append(mido.MetaMessage('track_name', name=song.name, time=0))

        # Tempo
        tempo_us = mido.bpm2tempo(song.bpm)
        meta_track.append(mido.MetaMessage('set_tempo', tempo=tempo_us, time=0))

        # Time signature
        meta_track.append(mido.MetaMessage(
            'time_signature',
            numerator=song.time_signature[0],
            denominator=song.time_signature[1],
            time=0
        ))

        # === WRITE LOOP MARKERS ===

        if song.loop_enabled and song.loop_end_tick is not None:
            # Method 1: Meta Event marker "loopStart" (FF 06)
            meta_track.append(mido.MetaMessage(
                'marker',
                text='loopStart',
                time=song.loop_start_tick
            ))

            # Method 2: CC 111 (RPG Maker compatibility)
            meta_track.append(mido.Message(
                'control_change',
                control=111,
                value=127,
                time=0  # Relative time (already at loop_start_tick)
            ))

            # Loop end marker (only for FF 06 method)
            loop_end_delta = song.loop_end_tick - song.loop_start_tick
            meta_track.append(mido.MetaMessage(
                'marker',
                text='loopEnd',
                time=loop_end_delta
            ))

        # End of track
        meta_track.append(mido.MetaMessage('end_of_track', time=0))

        # Tracks 1-16: Note data
        for track_idx, track in enumerate(song.tracks):
            if not track.notes:
                continue

            midi_track = mido.MidiTrack()
            mid.tracks.append(midi_track)

            midi_track.append(mido.MetaMessage('track_name', name=track.name, time=0))

            # Convert notes to MIDI messages (absolute time -> delta time)
            events = []

            for note in track.notes:
                start_tick = int(note.start * cls.TPQN)
                end_tick = int((note.start + note.duration) * cls.TPQN)

                # Note on
                events.append((start_tick, mido.Message(
                    'note_on',
                    note=note.note,
                    velocity=note.velocity,
                    channel=track.midi_channel
                )))

                # Note off
                events.append((end_tick, mido.Message(
                    'note_off',
                    note=note.note,
                    velocity=0,
                    channel=track.midi_channel
                )))

            # Sort by time
            events.sort(key=lambda x: x[0])

            # Convert absolute time to delta time
            prev_tick = 0
            for abs_tick, msg in events:
                delta_tick = abs_tick - prev_tick
                msg.time = delta_tick
                midi_track.append(msg)
                prev_tick = abs_tick

            # End of track
            midi_track.append(mido.MetaMessage('end_of_track', time=0))

        # Ensure .mid extension
        if path.suffix != '.mid':
            path = path.with_suffix('.mid')

        # Write file
        mid.save(path)
