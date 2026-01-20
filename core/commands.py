"""
Command pattern for undo/redo support.

All state modifications go through commands to enable:
- Full undo/redo history
- Command grouping (macros)
- Serialization for auto-save
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from dataclasses import replace
from core.models import AppState, Note, Song


class Command(ABC):
    """Base class for all commands."""

    @abstractmethod
    def execute(self, state: AppState) -> AppState:
        """
        Execute command and return new state.

        Args:
            state: Current app state

        Returns:
            New app state after command execution
        """
        raise NotImplementedError()

    @abstractmethod
    def undo(self, state: AppState) -> AppState:
        """
        Undo command and return previous state.

        Args:
            state: Current app state

        Returns:
            App state before command execution
        """
        raise NotImplementedError()

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable command description for UI."""
        raise NotImplementedError()


class AddNoteCommand(Command):
    """Command to add a note to a track."""

    def __init__(self, track_index: int, note: Note):
        """
        Args:
            track_index: Index of track (0-15)
            note: Note to add
        """
        self.track_index = track_index
        self.note = note
        self._previous_song: Optional[Song] = None

    def execute(self, state: AppState) -> AppState:
        """Add note to track."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        if not 0 <= self.track_index < len(song.tracks):
            raise ValueError(f"Track index {self.track_index} out of range")

        # Store previous state for undo
        self._previous_song = song

        # Get the track and add the note
        old_track = song.tracks[self.track_index]
        new_notes = old_track.notes + (self.note,)

        # Create new track with added note
        new_track = replace(old_track, notes=new_notes)

        # Create new song with updated track
        new_tracks = list(song.tracks)
        new_tracks[self.track_index] = new_track
        new_song = replace(song, tracks=tuple(new_tracks))

        # Update state
        state.set_current_song(new_song)
        state.mark_dirty()

        return state

    def undo(self, state: AppState) -> AppState:
        """Remove added note."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()

        return state

    @property
    def description(self) -> str:
        return "Add Note"


class DeleteNoteCommand(Command):
    """Command to delete a note from a track."""

    def __init__(self, track_index: int, note_index: int):
        """
        Args:
            track_index: Index of track (0-15)
            note_index: Index of note to delete
        """
        self.track_index = track_index
        self.note_index = note_index
        self._previous_song: Optional[Song] = None

    def execute(self, state: AppState) -> AppState:
        """Delete note from track."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        if not 0 <= self.track_index < len(song.tracks):
            raise ValueError(f"Track index {self.track_index} out of range")

        # Store previous state for undo
        self._previous_song = song

        # Get the track and remove the note
        old_track = song.tracks[self.track_index]

        if not 0 <= self.note_index < len(old_track.notes):
            raise ValueError(f"Note index {self.note_index} out of range")

        # Create new notes tuple without the deleted note
        notes_list = list(old_track.notes)
        notes_list.pop(self.note_index)
        new_notes = tuple(notes_list)

        # Create new track with removed note
        new_track = replace(old_track, notes=new_notes)

        # Create new song with updated track
        new_tracks = list(song.tracks)
        new_tracks[self.track_index] = new_track
        new_song = replace(song, tracks=tuple(new_tracks))

        # Update state
        state.set_current_song(new_song)
        state.mark_dirty()

        return state

    def undo(self, state: AppState) -> AppState:
        """Re-add deleted note."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()

        return state

    @property
    def description(self) -> str:
        return "Delete Note"


class ClearBarCommand(Command):
    """Command to clear all notes from selected bar(s)."""

    def __init__(self, track_index: int, bar_start: int, bar_end: int):
        """
        Args:
            track_index: Index of track (0-15)
            bar_start: Starting bar index (0-based)
            bar_end: Ending bar index (inclusive, 0-based)
        """
        self.track_index = track_index
        self.bar_start = bar_start
        self.bar_end = bar_end
        self._previous_song: Optional[Song] = None
        self._removed_notes: List[Note] = []

    def _get_bar_range(self, song: Song) -> tuple:
        """Get tick range for selected bars."""
        if not song.measure_metadata:
            # Fallback: use global time signature
            numerator, denominator = song.time_signature
            ticks_per_note = song.tpqn * (4 / denominator)
            measure_length = int(numerator * ticks_per_note)
            start_tick = self.bar_start * measure_length
            end_tick = (self.bar_end + 1) * measure_length
            return start_tick, end_tick

        # Use measure_metadata
        start_tick = song.measure_metadata[self.bar_start].start_tick
        end_measure = song.measure_metadata[self.bar_end]
        end_tick = end_measure.start_tick + end_measure.length_ticks
        return start_tick, end_tick

    def execute(self, state: AppState) -> AppState:
        """Clear all notes from selected bar(s)."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        self._previous_song = song

        # Get bar tick range
        start_tick, end_tick = self._get_bar_range(song)

        # Remove notes in this range
        old_track = song.tracks[self.track_index]
        new_notes = []
        self._removed_notes = []

        for note in old_track.notes:
            note_start_tick = note.start * song.tpqn
            note_end_tick = note_start_tick + (note.duration * song.tpqn)

            # Keep note if it doesn't overlap the bar range
            if note_end_tick <= start_tick or note_start_tick >= end_tick:
                new_notes.append(note)
            else:
                self._removed_notes.append(note)

        new_track = replace(old_track, notes=tuple(new_notes))
        new_tracks = list(song.tracks)
        new_tracks[self.track_index] = new_track
        new_song = replace(song, tracks=tuple(new_tracks))

        state.set_current_song(new_song)
        state.mark_dirty()
        return state

    def undo(self, state: AppState) -> AppState:
        """Restore cleared notes."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()
        return state

    @property
    def description(self) -> str:
        if self.bar_start == self.bar_end:
            return f"Clear Bar {self.bar_start + 1}"
        return f"Clear Bars {self.bar_start + 1}-{self.bar_end + 1}"


class CopyBarCommand(Command):
    """Command to copy notes from selected bar(s) to clipboard (read-only operation)."""

    def __init__(self, track_index: int, bar_start: int, bar_end: int):
        """
        Args:
            track_index: Index of track (0-15)
            bar_start: Starting bar index (0-based)
            bar_end: Ending bar index (inclusive, 0-based)
        """
        self.track_index = track_index
        self.bar_start = bar_start
        self.bar_end = bar_end
        self.copied_notes: List[Note] = []
        self.copied_bar_length: int = 0

    def _get_bar_range(self, song: Song) -> tuple:
        """Get tick range for selected bars."""
        if not song.measure_metadata:
            # Fallback: use global time signature
            numerator, denominator = song.time_signature
            ticks_per_note = song.tpqn * (4 / denominator)
            measure_length = int(numerator * ticks_per_note)
            start_tick = self.bar_start * measure_length
            end_tick = (self.bar_end + 1) * measure_length
            return start_tick, end_tick

        # Use measure_metadata
        start_tick = song.measure_metadata[self.bar_start].start_tick
        end_measure = song.measure_metadata[self.bar_end]
        end_tick = end_measure.start_tick + end_measure.length_ticks
        return start_tick, end_tick

    def execute(self, state: AppState) -> AppState:
        """Copy notes from selected bar(s)."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        # Get bar tick range
        start_tick, end_tick = self._get_bar_range(song)
        self.copied_bar_length = end_tick - start_tick

        # Copy notes in this range (normalize to start at 0)
        track = song.tracks[self.track_index]
        self.copied_notes = []

        for note in track.notes:
            note_start_tick = note.start * song.tpqn
            note_end_tick = note_start_tick + (note.duration * song.tpqn)

            # Check if note is fully within the bar range
            if note_start_tick >= start_tick and note_end_tick <= end_tick:
                # Normalize start position relative to bar start
                normalized_note = replace(
                    note,
                    start=(note_start_tick - start_tick) / song.tpqn
                )
                self.copied_notes.append(normalized_note)

        return state  # Read-only operation

    def undo(self, state: AppState) -> AppState:
        """No changes to undo."""
        return state

    @property
    def description(self) -> str:
        if self.bar_start == self.bar_end:
            return f"Copy Bar {self.bar_start + 1}"
        return f"Copy Bars {self.bar_start + 1}-{self.bar_end + 1}"


class PasteBarCommand(Command):
    """Command to paste copied notes, repeating if selection is longer."""

    def __init__(self, track_index: int, paste_bar_start: int, paste_bar_end: int,
                 copied_notes: List[Note], source_bar_length: int):
        """
        Args:
            track_index: Index of track (0-15)
            paste_bar_start: Starting bar index for paste (0-based)
            paste_bar_end: Ending bar index for paste (inclusive, 0-based)
            copied_notes: Notes to paste (normalized to start at 0)
            source_bar_length: Length of source bar(s) in ticks
        """
        self.track_index = track_index
        self.paste_bar_start = paste_bar_start
        self.paste_bar_end = paste_bar_end
        self.copied_notes = copied_notes
        self.source_bar_length = source_bar_length
        self._previous_song: Optional[Song] = None

    def _get_paste_range(self, song: Song) -> tuple:
        """Get tick range for paste destination."""
        if not song.measure_metadata:
            # Fallback: use global time signature
            numerator, denominator = song.time_signature
            ticks_per_note = song.tpqn * (4 / denominator)
            measure_length = int(numerator * ticks_per_note)
            start_tick = self.paste_bar_start * measure_length
            end_tick = (self.paste_bar_end + 1) * measure_length
            return start_tick, end_tick

        # Use measure_metadata
        start_tick = song.measure_metadata[self.paste_bar_start].start_tick
        end_measure = song.measure_metadata[self.paste_bar_end]
        end_tick = end_measure.start_tick + end_measure.length_ticks
        return start_tick, end_tick

    def execute(self, state: AppState) -> AppState:
        """Paste copied notes, repeating pattern if needed."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        self._previous_song = song

        # Get paste range
        paste_start_tick, paste_end_tick = self._get_paste_range(song)
        paste_duration = paste_end_tick - paste_start_tick

        # First, clear destination bars
        old_track = song.tracks[self.track_index]
        cleared_notes = []

        for note in old_track.notes:
            note_start_tick = note.start * song.tpqn
            note_end_tick = note_start_tick + (note.duration * song.tpqn)

            # Keep note if it doesn't overlap the paste range
            if note_end_tick <= paste_start_tick or note_start_tick >= paste_end_tick:
                cleared_notes.append(note)

        # Repeat copied notes to fill selection
        pasted_notes = []
        current_offset = 0

        while current_offset < paste_duration:
            for note in self.copied_notes:
                new_start_tick = paste_start_tick + current_offset + (note.start * song.tpqn)

                # Don't paste beyond selection
                if new_start_tick >= paste_end_tick:
                    break

                # Check if note would extend beyond paste range
                note_end_tick = new_start_tick + (note.duration * song.tpqn)
                if note_end_tick > paste_end_tick:
                    # Truncate note to fit
                    adjusted_duration = (paste_end_tick - new_start_tick) / song.tpqn
                    pasted_note = replace(
                        note,
                        start=new_start_tick / song.tpqn,
                        duration=adjusted_duration
                    )
                else:
                    pasted_note = replace(
                        note,
                        start=new_start_tick / song.tpqn
                    )

                pasted_notes.append(pasted_note)

            current_offset += self.source_bar_length

        # Combine cleared notes with pasted notes
        new_notes = tuple(cleared_notes + pasted_notes)
        new_track = replace(old_track, notes=new_notes)

        new_tracks = list(song.tracks)
        new_tracks[self.track_index] = new_track
        new_song = replace(song, tracks=tuple(new_tracks))

        state.set_current_song(new_song)
        state.mark_dirty()
        return state

    def undo(self, state: AppState) -> AppState:
        """Restore previous state."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()
        return state

    @property
    def description(self) -> str:
        if self.paste_bar_start == self.paste_bar_end:
            return f"Paste to Bar {self.paste_bar_start + 1}"
        return f"Paste to Bars {self.paste_bar_start + 1}-{self.paste_bar_end + 1}"


class RemoveBarCommand(Command):
    """Command to remove bar(s) entirely, shifting later bars left."""

    def __init__(self, bar_start: int, bar_end: int):
        """
        Args:
            bar_start: Starting bar index to remove (0-based)
            bar_end: Ending bar index to remove (inclusive, 0-based)
        """
        self.bar_start = bar_start
        self.bar_end = bar_end
        self._previous_song: Optional[Song] = None

    def execute(self, state: AppState) -> AppState:
        """Remove bar(s) and shift later content."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        self._previous_song = song

        # Calculate removed duration
        removed_duration = 0
        if song.measure_metadata:
            for bar_index in range(self.bar_start, self.bar_end + 1):
                if bar_index < len(song.measure_metadata):
                    measure = song.measure_metadata[bar_index]
                    removed_duration += measure.length_ticks
        else:
            # Fallback: use global time signature
            numerator, denominator = song.time_signature
            ticks_per_note = song.tpqn * (4 / denominator)
            measure_length = int(numerator * ticks_per_note)
            removed_duration = measure_length * (self.bar_end - self.bar_start + 1)

        # Get start tick of first removed bar
        if song.measure_metadata:
            removal_start_tick = song.measure_metadata[self.bar_start].start_tick
        else:
            # Fallback
            numerator, denominator = song.time_signature
            ticks_per_note = song.tpqn * (4 / denominator)
            measure_length = int(numerator * ticks_per_note)
            removal_start_tick = self.bar_start * measure_length

        # Remove measures from metadata
        new_measures = None
        if song.measure_metadata:
            measures_list = list(song.measure_metadata)
            # Remove the bars
            del measures_list[self.bar_start:self.bar_end + 1]

            # Update start_tick and measure_index for remaining measures
            for i, measure in enumerate(measures_list):
                if i >= self.bar_start:
                    # Shift back
                    from core.models import MeasureMetadata
                    measures_list[i] = MeasureMetadata(
                        measure_index=i,
                        start_tick=measure.start_tick - removed_duration,
                        time_signature=measure.time_signature,
                        bpm=measure.bpm,
                        length_ticks=measure.length_ticks
                    )

            new_measures = tuple(measures_list)

        # Shift notes from all tracks
        new_tracks = []
        for track in song.tracks:
            shifted_notes = []
            for note in track.notes:
                note_start_tick = note.start * song.tpqn
                note_end_tick = note_start_tick + (note.duration * song.tpqn)

                # Skip notes that are completely within removed range
                if note_start_tick >= removal_start_tick and \
                   note_end_tick <= removal_start_tick + removed_duration:
                    continue

                # Shift notes that come after removed range
                if note_start_tick >= removal_start_tick + removed_duration:
                    new_note = replace(
                        note,
                        start=(note_start_tick - removed_duration) / song.tpqn
                    )
                    shifted_notes.append(new_note)
                else:
                    # Keep notes before removed range unchanged
                    shifted_notes.append(note)

            new_track = replace(track, notes=tuple(shifted_notes))
            new_tracks.append(new_track)

        new_song = replace(
            song,
            tracks=tuple(new_tracks),
            measure_metadata=new_measures,
            length_ticks=song.length_ticks - removed_duration
        )

        state.set_current_song(new_song)
        state.mark_dirty()
        return state

    def undo(self, state: AppState) -> AppState:
        """Restore removed bars."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()
        return state

    @property
    def description(self) -> str:
        if self.bar_start == self.bar_end:
            return f"Remove Bar {self.bar_start + 1}"
        return f"Remove Bars {self.bar_start + 1}-{self.bar_end + 1}"


class AddBarCommand(Command):
    """Command to add new bar before or after selection."""

    def __init__(self, bar_index: int, position: str = "after",
                 time_signature: tuple = (4, 4), bpm: float = 120.0):
        """
        Args:
            bar_index: Bar index for insertion reference (0-based)
            position: "before" or "after"
            time_signature: Time signature for new bar (numerator, denominator)
            bpm: Tempo for new bar
        """
        self.bar_index = bar_index
        self.position = position
        self.time_signature = time_signature
        self.bpm = bpm
        self._previous_song: Optional[Song] = None

    def execute(self, state: AppState) -> AppState:
        """Add new bar and shift later content."""
        song = state.get_current_song()
        if song is None:
            raise ValueError("No song loaded")

        self._previous_song = song

        # Calculate insert index
        insert_index = self.bar_index if self.position == "before" else self.bar_index + 1

        # Calculate measure length
        numerator, denominator = self.time_signature
        ticks_per_note = song.tpqn * (4 / denominator)
        measure_length = int(numerator * ticks_per_note)

        # Initialize measure_metadata if it doesn't exist
        if not song.measure_metadata:
            # Calculate number of existing bars
            numerator_orig, denominator_orig = song.time_signature
            ticks_per_note_orig = song.tpqn * (4 / denominator_orig)
            bar_length = int(numerator_orig * ticks_per_note_orig)
            num_existing_bars = (song.length_ticks + bar_length - 1) // bar_length

            # Create metadata for all existing bars
            from core.models import MeasureMetadata
            measures_list = []
            for i in range(num_existing_bars):
                measures_list.append(MeasureMetadata(
                    measure_index=i,
                    start_tick=i * bar_length,
                    time_signature=song.time_signature,
                    bpm=song.bpm,
                    length_ticks=bar_length
                ))
            song = replace(song, measure_metadata=tuple(measures_list))

        # Now measure_metadata is guaranteed to exist
        # Calculate start tick for new measure
        if insert_index < len(song.measure_metadata):
            start_tick = song.measure_metadata[insert_index].start_tick
        else:
            # Append at end
            last_measure = song.measure_metadata[-1]
            start_tick = last_measure.start_tick + last_measure.length_ticks

        # Create new measure
        from core.models import MeasureMetadata
        new_measure = MeasureMetadata(
            measure_index=insert_index,
            start_tick=start_tick,
            time_signature=self.time_signature,
            bpm=self.bpm,
            length_ticks=measure_length
        )

        # Insert into measure_metadata
        measures_list = list(song.measure_metadata)
        measures_list.insert(insert_index, new_measure)

        # Update measure_index and start_tick for measures after insertion
        for i in range(insert_index + 1, len(measures_list)):
            measure = measures_list[i]
            measures_list[i] = MeasureMetadata(
                measure_index=i,
                start_tick=measure.start_tick + measure_length,
                time_signature=measure.time_signature,
                bpm=measure.bpm,
                length_ticks=measure.length_ticks
            )

        new_measures = tuple(measures_list)

        # Shift notes in all tracks after insertion point
        new_tracks = []
        for track in song.tracks:
            shifted_notes = []
            for note in track.notes:
                note_start_tick = note.start * song.tpqn

                # Shift notes that come after insertion point
                if note_start_tick >= start_tick:
                    new_note = replace(
                        note,
                        start=(note_start_tick + measure_length) / song.tpqn
                    )
                    shifted_notes.append(new_note)
                else:
                    # Keep notes before insertion point unchanged
                    shifted_notes.append(note)

            new_track = replace(track, notes=tuple(shifted_notes))
            new_tracks.append(new_track)

        new_song = replace(
            song,
            tracks=tuple(new_tracks),
            measure_metadata=new_measures,
            length_ticks=song.length_ticks + measure_length
        )

        state.set_current_song(new_song)
        state.mark_dirty()
        return state

    def undo(self, state: AppState) -> AppState:
        """Remove added bar."""
        if self._previous_song is None:
            raise ValueError("Command has not been executed yet")

        state.set_current_song(self._previous_song)
        state.mark_dirty()
        return state

    @property
    def description(self) -> str:
        position_str = "Before" if self.position == "before" else "After"
        return f"Add Bar {position_str} Bar {self.bar_index + 1}"


class CommandHistory:
    """Manages undo/redo command history."""

    def __init__(self, app_state: AppState, max_history: int = 100):
        """
        Args:
            app_state: Application state to operate on
            max_history: Maximum number of commands to keep
        """
        self.app_state = app_state
        self.max_history = max_history
        self._undo_stack: List[Command] = []
        self._redo_stack: List[Command] = []

    def execute(self, command: Command):
        """Execute command and add to history."""
        # Execute the command
        command.execute(self.app_state)

        # Add to undo stack
        self._undo_stack.append(command)

        # Limit history size
        if len(self._undo_stack) > self.max_history:
            self._undo_stack.pop(0)

        # Clear redo stack when new command is executed
        self._redo_stack.clear()

    def undo(self) -> bool:
        """Undo last command. Returns True if successful."""
        if not self.can_undo():
            return False

        # Pop command from undo stack
        command = self._undo_stack.pop()

        # Undo the command
        command.undo(self.app_state)

        # Add to redo stack
        self._redo_stack.append(command)

        return True

    def redo(self) -> bool:
        """Redo last undone command. Returns True if successful."""
        if not self.can_redo():
            return False

        # Pop command from redo stack
        command = self._redo_stack.pop()

        # Re-execute the command
        command.execute(self.app_state)

        # Add back to undo stack
        self._undo_stack.append(command)

        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def clear(self):
        """Clear all command history."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_undo_description(self) -> Optional[str]:
        """Get description of command that would be undone."""
        if self.can_undo():
            return self._undo_stack[-1].description
        return None

    def get_redo_description(self) -> Optional[str]:
        """Get description of command that would be redone."""
        if self.can_redo():
            return self._redo_stack[-1].description
        return None
