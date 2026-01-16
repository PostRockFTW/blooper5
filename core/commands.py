"""
Command pattern for undo/redo support.

All state modifications go through commands to enable:
- Full undo/redo history
- Command grouping (macros)
- Serialization for auto-save
"""
from abc import ABC, abstractmethod
from typing import Optional
from core.models import AppState, Note


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
        raise NotImplementedError("AddNoteCommand not yet implemented")

    def execute(self, state: AppState) -> AppState:
        """Add note to track."""
        raise NotImplementedError("execute not yet implemented")

    def undo(self, state: AppState) -> AppState:
        """Remove added note."""
        raise NotImplementedError("undo not yet implemented")

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
        raise NotImplementedError("DeleteNoteCommand not yet implemented")

    def execute(self, state: AppState) -> AppState:
        """Delete note from track."""
        raise NotImplementedError("execute not yet implemented")

    def undo(self, state: AppState) -> AppState:
        """Re-add deleted note."""
        raise NotImplementedError("undo not yet implemented")

    @property
    def description(self) -> str:
        return "Delete Note"


class CommandHistory:
    """Manages undo/redo command history."""

    def __init__(self, max_history: int = 100):
        """
        Args:
            max_history: Maximum number of commands to keep
        """
        raise NotImplementedError("CommandHistory not yet implemented")

    def execute(self, command: Command):
        """Execute command and add to history."""
        raise NotImplementedError("execute not yet implemented")

    def undo(self) -> bool:
        """Undo last command. Returns True if successful."""
        raise NotImplementedError("undo not yet implemented")

    def redo(self) -> bool:
        """Redo last undone command. Returns True if successful."""
        raise NotImplementedError("redo not yet implemented")

    def can_undo(self) -> bool:
        """Check if undo is available."""
        raise NotImplementedError("can_undo not yet implemented")

    def can_redo(self) -> bool:
        """Check if redo is available."""
        raise NotImplementedError("can_redo not yet implemented")

    def clear(self):
        """Clear all command history."""
        raise NotImplementedError("clear not yet implemented")
