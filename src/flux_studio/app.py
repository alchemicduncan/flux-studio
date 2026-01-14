"""Main application module for Flux Studio."""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Footer, Header, Input, Label, Button
from textual.screen import ModalScreen
from textual.binding import Binding

from flux_studio.editor.markdown_editor import MarkdownEditor


class InputScreen(ModalScreen[str]):
    """Screen for getting string input from user."""

    CSS = """
    InputScreen {
        align: center middle;
    }

    InputScreen > Vertical {
        width: 60;
        height: auto;
        border: solid $primary;
        background: $surface;
        padding: 2;
    }

    Label {
        margin-bottom: 1;
    }
    """

    def __init__(self, prompt: str, initial_value: str = ""):
        super().__init__()
        self.prompt_text = prompt
        self.initial_value = initial_value

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.prompt_text),
            Input(self.initial_value, id="input"),
        )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class FluxStudioApp(App):
    """Flux Studio - AI-powered Markdown Editor."""

    CSS = """
    Screen {
        align: center middle;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode", show=True),
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("ctrl+o", "open_file", "Open File", show=True),
        Binding("ctrl+s", "save_file", "Save File", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        self.editor = MarkdownEditor()
        yield self.editor
        yield Footer()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark

    def action_new_file(self) -> None:
        """Create a new file."""
        self.editor.new_file()

    def action_open_file(self) -> None:
        """Open a file."""
        def open_callback(path: str) -> None:
            if path:
                self.run_worker(self.editor.load_file(path))

        self.push_screen(InputScreen("Enter file path to open:"), open_callback)

    async def action_save_file(self) -> None:
        """Save the current file."""
        if self.editor.current_file:
            await self.editor.save_file()
        else:
            def save_callback(path: str) -> None:
                if path:
                    self.run_worker(self.editor.save_file(path))

            self.push_screen(InputScreen("Enter file path to save:"), save_callback)


def main() -> None:
    """Run the application."""
    app = FluxStudioApp()
    app.run()


if __name__ == "__main__":
    main()
