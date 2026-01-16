"""
Project file I/O for .bloom5 format.

File format:
- MessagePack binary format (fast, compact)
- Contains: Song model + metadata
- Auto-backup on save
"""
from pathlib import Path
from typing import Optional
import msgpack
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
        try:
            # Convert path to Path object if it's a string
            if isinstance(path, str):
                path = Path(path)

            # Ensure .bloom5 extension
            if path.suffix != ".bloom5":
                path = path.with_suffix(".bloom5")

            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)

            # Serialize song to dictionary
            song_data = song.to_dict()

            # Pack to MessagePack binary format
            packed_data = msgpack.packb(song_data, use_bin_type=True)

            # Write to file
            with open(path, "wb") as f:
                f.write(packed_data)

        except Exception as e:
            raise IOError(f"Failed to save project to {path}: {e}") from e

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
        try:
            # Convert path to Path object if it's a string
            if isinstance(path, str):
                path = Path(path)

            # Check if file exists
            if not path.exists():
                raise IOError(f"Project file not found: {path}")

            # Read binary data
            with open(path, "rb") as f:
                packed_data = f.read()

            # Unpack from MessagePack
            song_data = msgpack.unpackb(packed_data, raw=False)

            # Validate version
            version = song_data.get("version", "unknown")
            if not version.startswith("5."):
                raise ValueError(f"Incompatible project version: {version}. Expected 5.x")

            # Reconstruct song from dictionary
            song = Song.from_dict(song_data)

            return song

        except msgpack.exceptions.ExtraData as e:
            raise ValueError(f"Invalid .bloom5 file format: {e}") from e
        except Exception as e:
            raise IOError(f"Failed to load project from {path}: {e}") from e

    @staticmethod
    def auto_save(song: Song, project_name: str):
        """
        Auto-save song to temporary location.

        Args:
            song: Song to auto-save
            project_name: Project name for backup file
        """
        try:
            auto_save_path = ProjectFile.get_auto_save_path(project_name)
            ProjectFile.save(song, auto_save_path)
        except Exception as e:
            # Log error but don't crash the application
            print(f"Auto-save failed: {e}")

    @staticmethod
    def get_auto_save_path(project_name: str) -> Path:
        """
        Get path to auto-save file for a project.

        Args:
            project_name: Project name

        Returns:
            Path to auto-save file
        """
        # Get user's home directory
        home = Path.home()

        # Create auto-save directory in user's documents or home folder
        auto_save_dir = home / ".blooper5" / "autosave"
        auto_save_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize project name for file system
        safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "untitled"

        return auto_save_dir / f"{safe_name}.bloom5"

    @staticmethod
    def has_auto_save(project_name: str) -> bool:
        """
        Check if auto-save file exists for a project.

        Args:
            project_name: Project name

        Returns:
            True if auto-save exists
        """
        auto_save_path = ProjectFile.get_auto_save_path(project_name)
        return auto_save_path.exists()
