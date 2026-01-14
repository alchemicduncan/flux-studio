"""Main application module for Flux Studio."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Static, Label
from textual.binding import Binding


class WelcomeScreen(Static):
    """A welcome screen widget."""

    def compose(self) -> ComposeResult:
        """Compose the welcome screen."""
        yield Label("Welcome to Flux Studio!", id="title")
        yield Label("A Python terminal application template using Textual", id="subtitle")
        yield Label("\nPress 'q' to quit", id="help-text")


class FluxStudioApp(App):
    """A Textual application template."""

    CSS = """
    Screen {
        align: center middle;
    }

    #title {
        text-style: bold;
        color: $accent;
        margin: 1;
        text-align: center;
    }

    #subtitle {
        color: $text-muted;
        margin-bottom: 2;
        text-align: center;
    }

    #help-text {
        color: $text;
        text-align: center;
    }

    WelcomeScreen {
        width: 60;
        height: auto;
        border: solid $primary;
        padding: 2;
    }

    Button {
        margin: 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Toggle Dark Mode", show=True),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield Container(WelcomeScreen())
        yield Footer()

    def action_toggle_dark(self) -> None:
        """Toggle dark mode."""
        self.dark = not self.dark


def main() -> None:
    """Run the application."""
    app = FluxStudioApp()
    app.run()


if __name__ == "__main__":
    main()
