"""File operations for Flux Studio."""

import json
import os
from pathlib import Path
from typing import List, Optional
import aiofiles

class RecentFilesManager:
    """Track recently opened files."""

    def __init__(self, storage_dir: Path = Path(".flux-studio"), max_files: int = 10):
        self.storage_dir = storage_dir
        self.storage_file = storage_dir / "recent_files.json"
        self.max_files = max_files
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure the storage directory exists."""
        if not self.storage_dir.exists():
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        if not self.storage_file.exists():
            with open(self.storage_file, "w") as f:
                json.dump([], f)

    def add(self, path: str | Path) -> None:
        """Add a file to the recent files list."""
        path_str = str(Path(path).absolute())
        recents = self.get_recent()

        # Remove if already exists (to move to top)
        if path_str in recents:
            recents.remove(path_str)

        recents.insert(0, path_str)
        recents = recents[:self.max_files]

        with open(self.storage_file, "w") as f:
            json.dump(recents, f)

    def get_recent(self) -> List[str]:
        """Get the list of recent files."""
        try:
            with open(self.storage_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def clear(self) -> None:
        """Clear the recent files list."""
        with open(self.storage_file, "w") as f:
            json.dump([], f)


class AutoSaveManager:
    """Manage auto-save backups."""

    def __init__(self, storage_dir: Path = Path(".flux-studio/backups")):
        self.storage_dir = storage_dir
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Ensure the backup directory exists."""
        if not self.storage_dir.exists():
            self.storage_dir.mkdir(parents=True, exist_ok=True)

    def get_backup_path(self, original_path: str | Path) -> Path:
        """Get the path for the backup file."""
        # Create a unique filename from the original path using hash
        import hashlib
        path_str = str(Path(original_path).absolute())
        path_hash = hashlib.md5(path_str.encode()).hexdigest()
        safe_name = f"{Path(original_path).name}.{path_hash}.backup"
        return self.storage_dir / safe_name

    async def create_backup(self, content: str, original_path: str | Path) -> None:
        """Create a backup of the file content."""
        if not original_path:
            return

        backup_path = self.get_backup_path(original_path)
        async with aiofiles.open(backup_path, "w") as f:
            await f.write(content)

    def cleanup_backup(self, original_path: str | Path) -> None:
        """Remove the backup file for the given path."""
        backup_path = self.get_backup_path(original_path)
        if backup_path.exists():
            backup_path.unlink()
