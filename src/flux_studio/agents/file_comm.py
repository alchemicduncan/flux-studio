"""File-based communication layer for agent orchestration.

Handles low-level file I/O for the agent protocol, including
creating workspace directories, atomic JSON writes, and file watching.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Callable
import aiofiles
import aiofiles.os


WORKSPACE_DIR = ".flux-studio"
TASKS_DIR = "tasks"
MESSAGES_DIR = "messages"
INBOX_DIR = "inbox"
OUTBOX_DIR = "outbox"


class FileComm:
    """Low-level file I/O for agent communication protocol."""

    def __init__(self, project_dir: Path | str):
        """Initialize with project directory.
        
        Args:
            project_dir: The project root directory (typically cwd)
        """
        self.project_dir = Path(project_dir).resolve()
        self.workspace_dir = self.project_dir / WORKSPACE_DIR
        self.tasks_dir = self.workspace_dir / TASKS_DIR
        self.inbox_dir = self.workspace_dir / MESSAGES_DIR / INBOX_DIR
        self.outbox_dir = self.workspace_dir / MESSAGES_DIR / OUTBOX_DIR

    async def init_workspace(self) -> None:
        """Create the .flux-studio/ directory structure."""
        dirs = [
            self.workspace_dir,
            self.tasks_dir,
            self.inbox_dir,
            self.outbox_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def init_workspace_sync(self) -> None:
        """Synchronously create the .flux-studio/ directory structure."""
        dirs = [
            self.workspace_dir,
            self.tasks_dir,
            self.inbox_dir,
            self.outbox_dir,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def workspace_exists(self) -> bool:
        """Check if workspace directory exists."""
        return self.workspace_dir.exists()

    async def write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write data to a JSON file atomically.
        
        Uses write-to-temp-then-rename for atomicity.
        """
        path = Path(path)
        temp_path = path.with_suffix(".tmp")
        
        content = json.dumps(data, indent=2, default=str)
        async with aiofiles.open(temp_path, "w") as f:
            await f.write(content)
        
        # Atomic rename
        temp_path.rename(path)

    def write_json_sync(self, path: Path, data: dict[str, Any]) -> None:
        """Synchronously write data to a JSON file atomically."""
        path = Path(path)
        temp_path = path.with_suffix(".tmp")
        
        content = json.dumps(data, indent=2, default=str)
        with open(temp_path, "w") as f:
            f.write(content)
        
        temp_path.rename(path)

    async def read_json(self, path: Path) -> dict[str, Any] | None:
        """Read and parse a JSON file.
        
        Returns None if file doesn't exist or is invalid.
        """
        path = Path(path)
        if not path.exists():
            return None
        
        try:
            async with aiofiles.open(path, "r") as f:
                content = await f.read()
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return None

    def read_json_sync(self, path: Path) -> dict[str, Any] | None:
        """Synchronously read and parse a JSON file."""
        path = Path(path)
        if not path.exists():
            return None
        
        try:
            with open(path, "r") as f:
                content = f.read()
            return json.loads(content)
        except (json.JSONDecodeError, OSError):
            return None

    async def list_json_files(self, directory: Path) -> list[Path]:
        """List all JSON files in a directory."""
        directory = Path(directory)
        if not directory.exists():
            return []
        
        return sorted(directory.glob("*.json"))

    def list_json_files_sync(self, directory: Path) -> list[Path]:
        """Synchronously list all JSON files in a directory."""
        directory = Path(directory)
        if not directory.exists():
            return []
        
        return sorted(directory.glob("*.json"))

    async def delete_file(self, path: Path) -> bool:
        """Delete a file. Returns True if deleted."""
        path = Path(path)
        try:
            await aiofiles.os.remove(path)
            return True
        except OSError:
            return False

    def delete_file_sync(self, path: Path) -> bool:
        """Synchronously delete a file."""
        path = Path(path)
        try:
            path.unlink()
            return True
        except OSError:
            return False

    async def watch_directory(
        self,
        directory: Path,
        callback: Callable[[Path], Any],
        poll_interval: float = 1.0,
    ) -> None:
        """Watch a directory for new files and call callback.
        
        Uses polling for simplicity and cross-platform compatibility.
        This is a long-running coroutine that should be cancelled to stop.
        """
        directory = Path(directory)
        seen_files: set[Path] = set()
        
        # Initialize with existing files
        if directory.exists():
            seen_files = set(directory.glob("*.json"))
        
        while True:
            await asyncio.sleep(poll_interval)
            
            if not directory.exists():
                continue
            
            current_files = set(directory.glob("*.json"))
            new_files = current_files - seen_files
            
            for new_file in sorted(new_files):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(new_file)
                    else:
                        callback(new_file)
                except Exception:
                    pass  # Don't let callback errors stop the watcher
            
            seen_files = current_files
