"""
Project file I/O for .bloom5 format.

File format:
- MessagePack binary format (fast, compact)
- Contains: Song model + metadata
- Auto-backup on save
"""
from pathlib import Path
from typing import Optional
from core.models import Song


class ProjectFile:
    """Handles .bloom5 project file I/O."""

    @staticmethod
    def save(song: Song, path: Path):
        """
        Save song to .bloom5 file.

        Args:
            song: Song to save
            path: Destination file path

        Raises:
            IOError: If save fails
        """
        raise NotImplementedError("Project save not yet implemented")

    @staticmethod
    def load(path: Path) -> Song:
        """
        Load song from .bloom5 file.

        Args:
            path: Source file path

        Returns:
            Loaded song

        Raises:
            IOError: If load fails
            ValueError: If file format invalid
        """
        raise NotImplementedError("Project load not yet implemented")

    @staticmethod
    def auto_save(song: Song, project_name: str):
        """
        Auto-save song to temporary location.

        Args:
            song: Song to auto-save
            project_name: Project name for backup file
        """
        raise NotImplementedError("Auto-save not yet implemented")

    @staticmethod
    def get_auto_save_path(project_name: str) -> Path:
        """
        Get path to auto-save file for a project.

        Args:
            project_name: Project name

        Returns:
            Path to auto-save file
        """
        raise NotImplementedError("get_auto_save_path not yet implemented")

    @staticmethod
    def has_auto_save(project_name: str) -> bool:
        """
        Check if auto-save file exists for a project.

        Args:
            project_name: Project name

        Returns:
            True if auto-save exists
        """
        raise NotImplementedError("has_auto_save not yet implemented")
