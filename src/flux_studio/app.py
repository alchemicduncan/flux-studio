"""Main application module for Flux Studio."""

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Button
from textual.screen import ModalScreen
from textual.binding import Binding

from flux_studio.editor.markdown_editor import MarkdownEditor
from flux_studio.agents.agent_registry import AgentRegistry
from flux_studio.agents.agent_panel import AgentPanel


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
        layout: horizontal;
    }
    
    #main-container {
        width: 1fr;
    }
    
    #agent-panel {
        width: 40;
        display: none;
        border-left: solid $primary;
    }
    
    #agent-panel.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("ctrl+n", "new_file", "New File", show=True),
        Binding("ctrl+o", "open_file", "Open File", show=True),
        Binding("ctrl+s", "save_file", "Save File", show=True),
        Binding("ctrl+shift+a", "toggle_agent_panel", "Agents", show=True),
        Binding("ctrl+p", "command_palette", "Command Palette", show=True),
    ]

    def __init__(self):
        super().__init__()
        # Initialize agent registry with current working directory
        self.agent_registry = AgentRegistry(Path.cwd())

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        
        with Horizontal():
            with Vertical(id="main-container"):
                self.editor = MarkdownEditor()
                yield self.editor
            
            self.agent_panel = AgentPanel(self.agent_registry)
            self.agent_panel.id = "agent-panel"
            yield self.agent_panel
        
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application on mount."""
        # Initialize agent workspace if it doesn't exist
        if not self.agent_registry.workspace_exists:
            await self.agent_registry.init_workspace()
            self.agent_panel.refresh_data()

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

    def action_toggle_agent_panel(self) -> None:
        """Toggle the agent panel visibility."""
        panel = self.query_one("#agent-panel")
        if panel.has_class("visible"):
            panel.remove_class("visible")
        else:
            panel.add_class("visible")
            self.agent_panel.refresh_data()

    def on_markdown_editor_vim_command(self, event: MarkdownEditor.VimCommand) -> None:
        """Handle vim commands from the editor."""
        cmd = event.command.lower().strip()
        
        # Command routing
        if cmd == "agents":
            self.action_toggle_agent_panel()
        elif cmd == "w":
            self.run_worker(self.action_save_file())
        elif cmd == "wq":
            self.run_worker(self._save_and_quit())
        elif cmd == "q":
            self.action_quit()
        elif cmd == "q!":
            self.exit()
        elif cmd == "new" or cmd == "n":
            self.action_new_file()
        elif cmd == "dark" or cmd == "d":
            self.action_toggle_dark()
        elif cmd.startswith("e ") or cmd.startswith("open "):
            # :e filename or :open filename
            path = cmd.split(" ", 1)[1].strip()
            if path:
                self.run_worker(self.editor.load_file(path))
        elif cmd.startswith("w "):
            # :w filename - save as
            path = cmd.split(" ", 1)[1].strip()
            if path:
                self.run_worker(self.editor.save_file(path))
        elif cmd == "help" or cmd == "h":
            self.notify(
                "Commands: :agents, :w, :wq, :q, :q!, :new, :dark, :e <file>, :w <file>",
                timeout=5
            )
        else:
            self.notify(f"Unknown command: :{cmd}", severity="warning")

    async def _save_and_quit(self) -> None:
        """Save the current file and quit."""
        if await self.action_save_file():
            self.exit()

    async def on_agent_panel_task_submitted(self, event: AgentPanel.TaskSubmitted) -> None:
        """Handle task submission from agent panel."""
        # Create context with current editor state
        context = {
            "current_file": str(self.editor.current_file) if self.editor.current_file else None,
            "content_preview": self.editor.text_area.text[:500] if self.editor.text_area.text else None,
            "word_count": len(self.editor.text_area.text.split()) if self.editor.text_area.text else 0,
        }
        
        await self.agent_registry.create_task(
            description=event.description,
            context=context,
        )
        
        self.notify(f"Task created: {event.description[:50]}...")
        self.agent_panel.refresh_data()


def main() -> None:
    """Run the application."""
    app = FluxStudioApp()
    app.run()


if __name__ == "__main__":
    main()

