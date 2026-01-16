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
