"""Markdown editor widget for Flux Studio."""

from pathlib import Path
from typing import Optional
import asyncio

import aiofiles
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Static, TextArea
from textual import work

from flux_studio.editor.file_operations import AutoSaveManager, RecentFilesManager


class EditorStatusBar(Static):
    """Status bar showing file name, modified state, cursor position, word count."""

    DEFAULT_CSS = """
    EditorStatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    file_path: reactive[Optional[str]] = reactive(None)
    modified: reactive[bool] = reactive(False)
    cursor_position: reactive[tuple[int, int]] = reactive((0, 0))
    word_count: reactive[int] = reactive(0)

    def watch_file_path(self, path: Optional[str]) -> None:
        self.update_status()

    def watch_modified(self, modified: bool) -> None:
        self.update_status()

    def watch_cursor_position(self, pos: tuple[int, int]) -> None:
        self.update_status()

    def watch_word_count(self, count: int) -> None:
        self.update_status()

    def update_status(self) -> None:
        fname = self.file_path if self.file_path else "Untitled"
        mod_str = "*" if self.modified else ""
        row, col = self.cursor_position
        self.update(
            f"{fname}{mod_str} | Ln {row+1}, Col {col+1} | Words: {self.word_count}"
        )


class MarkdownEditor(Vertical):
    """Main editor widget."""

    class FileLoaded(Message):
        """Posted when a file is loaded."""
        def __init__(self, path: str):
            super().__init__()
            self.path = path

    class FileSaved(Message):
        """Posted when a file is saved."""
        def __init__(self, path: str):
            super().__init__()
            self.path = path

    class ContentChanged(Message):
        """Posted when content changes."""

    def __init__(self):
        super().__init__()
        self.current_file: Optional[Path] = None
        self.is_modified = False
        self.recent_manager = RecentFilesManager()
        self.autosave_manager = AutoSaveManager()
        self._autosave_timer = None
        self.autosave_interval = 2.0  # seconds

    def compose(self) -> ComposeResult:
        """Compose the editor."""
        self.text_area = TextArea(language="markdown", show_line_numbers=True)
        self.status_bar = EditorStatusBar()
        yield self.text_area
        yield self.status_bar

    def on_mount(self) -> None:
        """Handle mount event."""
        self.text_area.focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handle text changes."""
        self.is_modified = True
        self.status_bar.modified = True

        # Update word count
        content = self.text_area.text
        self.status_bar.word_count = len(content.split())

        # Debounced autosave
        self._schedule_autosave(content)

        self.post_message(self.ContentChanged())

    def _schedule_autosave(self, content: str) -> None:
        """Schedule an autosave operation."""
        if self._autosave_timer:
            self._autosave_timer.cancel()

        if self.current_file:
            # We use a simple task cancellation approach for debouncing
            self._autosave_timer = asyncio.create_task(self._debounce_autosave(content))

    async def _debounce_autosave(self, content: str) -> None:
        """Wait and then trigger autosave."""
        try:
            await asyncio.sleep(self.autosave_interval)
            # Check if still modified and current_file matches (simple check)
            if self.current_file:
                 await self.autosave_manager.create_backup(content, self.current_file)
        except asyncio.CancelledError:
            pass

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Handle cursor movement."""
        self.status_bar.cursor_position = event.selection.start

    def new_file(self) -> None:
        """Create a new file."""
        self.current_file = None

        with self.text_area.prevent(TextArea.Changed):
            if hasattr(self.text_area, "load_text"):
                self.text_area.load_text("")
            else:
                self.text_area.text = ""

        self.is_modified = False
        self.status_bar.file_path = None
        self.status_bar.modified = False
        self.text_area.focus()

    async def load_file(self, path: str | Path) -> None:
        """Load a file from disk."""
        path_obj = Path(path)
        try:
            async with aiofiles.open(path_obj, "r") as f:
                content = await f.read()

            with self.text_area.prevent(TextArea.Changed):
                if hasattr(self.text_area, "load_text"):
                    self.text_area.load_text(content)
                else:
                    self.text_area.text = content

            self.current_file = path_obj
            self.is_modified = False

            self.status_bar.file_path = str(path_obj)
            self.status_bar.modified = False
            self.recent_manager.add(path_obj)
            self.post_message(self.FileLoaded(str(path_obj)))
            self.text_area.focus()

        except Exception as e:
            self.notify(f"Error loading file: {e}", severity="error")

    async def save_file(self, path: Optional[str | Path] = None) -> bool:
        """Save the file to disk. Returns True if successful."""
        target_path = path or self.current_file

        if not target_path:
            return False

        target_path = Path(target_path)

        try:
            async with aiofiles.open(target_path, "w") as f:
                await f.write(self.text_area.text)

            self.current_file = target_path
            self.is_modified = False

            self.status_bar.file_path = str(target_path)
            self.status_bar.modified = False
            self.recent_manager.add(target_path)
            self.autosave_manager.cleanup_backup(target_path)
            self.post_message(self.FileSaved(str(target_path)))
            return True

        except Exception as e:
            self.notify(f"Error saving file: {e}", severity="error")
            return False
