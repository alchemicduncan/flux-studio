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
from textual.binding import Binding
from textual import work

from flux_studio.editor.file_operations import AutoSaveManager, RecentFilesManager


class VimTextArea(TextArea):
    """TextArea with vim-like keybindings."""

    # Key mappings for NORMAL mode - maps key to (action_name, description)
    NORMAL_MODE_KEYS = {
        # Navigation
        "h": ("cursor_left", "Move left"),
        "j": ("cursor_down", "Move down"),
        "k": ("cursor_up", "Move up"),
        "l": ("cursor_right", "Move right"),
        "w": ("cursor_word_right", "Word forward"),
        "b": ("cursor_word_left", "Word backward"),
        "0": ("cursor_line_start", "Line start"),
        "$": ("cursor_line_end", "Line end"),
        "g": ("vim_document_start", "Document start"),
        "G": ("vim_document_end", "Document end"),
        # Editing
        "x": ("delete_right", "Delete char"),
        "u": ("undo", "Undo"),
        # Mode changes
        "i": ("vim_insert", "Insert mode"),
        "a": ("vim_append", "Append"),
        "o": ("vim_open_below", "New line below"),
        "O": ("vim_open_above", "New line above"),
        ":": ("vim_command_mode", "Command mode"),
    }

    class VimModeChanged(Message):
        """Posted when vim mode changes."""
        def __init__(self, mode: str, command_buffer: str = ""):
            super().__init__()
            self.mode = mode
            self.command_buffer = command_buffer

    class VimCommandExecuted(Message):
        """Posted when a vim command is executed (e.g., :agents)."""
        def __init__(self, command: str):
            super().__init__()
            self.command = command

    vim_mode: reactive[str] = reactive("NORMAL")
    command_buffer: reactive[str] = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def watch_vim_mode(self, mode: str) -> None:
        """Post mode change message when vim mode changes."""
        self.post_message(self.VimModeChanged(mode, self.command_buffer))

    def watch_command_buffer(self, buffer: str) -> None:
        """Post mode change message when command buffer changes."""
        if self.vim_mode == "COMMAND":
            self.post_message(self.VimModeChanged(self.vim_mode, buffer))

    def _on_key(self, event) -> None:
        """Intercept key events before TextArea handles them."""
        key = event.key
        char = event.character

        # COMMAND mode - building a command like :agents
        if self.vim_mode == "COMMAND":
            if key == "escape":
                self.command_buffer = ""
                self.vim_mode = "NORMAL"
                event.prevent_default()
                event.stop()
                return
            elif key == "enter":
                cmd = self.command_buffer[1:].strip()
                self.post_message(self.VimCommandExecuted(cmd))
                self.command_buffer = ""
                self.vim_mode = "NORMAL"
                event.prevent_default()
                event.stop()
                return
            elif key == "backspace":
                if len(self.command_buffer) > 1:
                    self.command_buffer = self.command_buffer[:-1]
                else:
                    self.command_buffer = ""
                    self.vim_mode = "NORMAL"
                event.prevent_default()
                event.stop()
                return
            elif event.is_printable and char:
                self.command_buffer += char
                event.prevent_default()
                event.stop()
                return
            else:
                event.prevent_default()
                event.stop()
                return

        # NORMAL mode - keys are commands, not text input
        if self.vim_mode == "NORMAL":
            # Check for vim key commands
            if char in self.NORMAL_MODE_KEYS:
                action_name, _ = self.NORMAL_MODE_KEYS[char]
                # Call the action method
                action_method = getattr(self, f"action_{action_name}", None)
                if action_method:
                    action_method()
                event.prevent_default()
                event.stop()
                return
            
            # Handle Ctrl+u for page up
            if key == "ctrl+u":
                self.action_cursor_page_up()
                event.prevent_default()
                event.stop()
                return
            
            # Handle Ctrl+d for page down
            if key == "ctrl+d":
                self.action_cursor_page_down()
                event.prevent_default()
                event.stop()
                return

            # In NORMAL mode, block all printable characters from being typed
            if event.is_printable:
                event.prevent_default()
                event.stop()
                return

        # INSERT mode - allow normal text input, but Escape returns to NORMAL
        if self.vim_mode == "INSERT":
            if key == "escape":
                self.vim_mode = "NORMAL"
                event.prevent_default()
                event.stop()
                return
            # Let TextArea handle the key normally
            super()._on_key(event)
            return

        # Default: let TextArea handle it
        super()._on_key(event)

    # Vim action methods
    def action_vim_insert(self) -> None:
        """Enter insert mode at cursor."""
        self.vim_mode = "INSERT"

    def action_vim_append(self) -> None:
        """Enter insert mode after cursor."""
        self.action_cursor_right()
        self.vim_mode = "INSERT"

    def action_vim_open_below(self) -> None:
        """Insert new line below and enter insert mode."""
        self.action_cursor_line_end()
        self.insert("\n")
        self.vim_mode = "INSERT"

    def action_vim_open_above(self) -> None:
        """Insert new line above and enter insert mode."""
        self.action_cursor_line_start()
        self.insert("\n")
        self.action_cursor_up()
        self.vim_mode = "INSERT"

    def action_vim_command_mode(self) -> None:
        """Enter command mode (: prefix)."""
        self.command_buffer = ":"
        self.vim_mode = "COMMAND"

    def action_vim_document_start(self) -> None:
        """Move cursor to document start."""
        self.move_cursor((0, 0))

    def action_vim_document_end(self) -> None:
        """Move cursor to document end."""
        lines = self.text.split("\n")
        last_line = len(lines) - 1
        last_col = len(lines[-1]) if lines else 0
        self.move_cursor((last_line, last_col))


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
    vim_mode: reactive[str] = reactive("NORMAL")
    command_buffer: reactive[str] = reactive("")

    def watch_file_path(self, path: Optional[str]) -> None:
        self.update_status()

    def watch_modified(self, modified: bool) -> None:
        self.update_status()

    def watch_cursor_position(self, pos: tuple[int, int]) -> None:
        self.update_status()

    def watch_word_count(self, count: int) -> None:
        self.update_status()

    def watch_vim_mode(self, mode: str) -> None:
        self.update_status()

    def watch_command_buffer(self, buffer: str) -> None:
        self.update_status()

    def update_status(self) -> None:
        # In command mode, show the command buffer prominently
        if self.vim_mode == "COMMAND":
            self.update(self.command_buffer)
            return
        
        fname = self.file_path if self.file_path else "Untitled"
        mod_str = "*" if self.modified else ""
        row, col = self.cursor_position
        mode_indicator = f"[{self.vim_mode}]" if self.vim_mode else ""
        self.update(
            f"{mode_indicator} {fname}{mod_str} | Ln {row+1}, Col {col+1} | Words: {self.word_count}"
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

    class VimCommand(Message):
        """Posted when a vim command is executed (e.g., :agents, :w, :q)."""
        def __init__(self, command: str):
            super().__init__()
            self.command = command

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
        self.text_area = VimTextArea(language="markdown", show_line_numbers=True)
        self.status_bar = EditorStatusBar()
        yield self.text_area
        yield self.status_bar

    def on_mount(self) -> None:
        """Handle mount event."""
        self.text_area.focus()

    def on_vim_text_area_vim_mode_changed(self, event: VimTextArea.VimModeChanged) -> None:
        """Handle vim mode changes from the text area."""
        self.status_bar.vim_mode = event.mode
        self.status_bar.command_buffer = event.command_buffer

    def on_vim_text_area_vim_command_executed(self, event: VimTextArea.VimCommandExecuted) -> None:
        """Handle vim commands from the text area and bubble up to app."""
        self.post_message(self.VimCommand(event.command))

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
