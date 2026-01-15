"""Agent panel UI for Flux Studio.

Provides a Textual-based panel for managing agent tasks
and viewing messages from agents.
"""

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Input, Label, Static
from textual import work

from flux_studio.agents.agent_protocol import AgentMessage, AgentTask, TaskStatus, MessageType
from flux_studio.agents.agent_registry import AgentRegistry


class TaskCard(Static):
    """Displays a single task with status indicator."""

    DEFAULT_CSS = """
    TaskCard {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $primary-darken-2;
        background: $surface;
    }
    
    TaskCard.pending {
        border: solid $warning;
    }
    
    TaskCard.running {
        border: solid $primary;
    }
    
    TaskCard.completed {
        border: solid $success;
    }
    
    TaskCard.failed {
        border: solid $error;
    }
    
    TaskCard.cancelled {
        border: solid $surface-lighten-2;
    }
    
    TaskCard .task-id {
        color: $text-muted;
        text-style: dim;
    }
    
    TaskCard .task-status {
        text-style: bold;
    }
    
    TaskCard .task-description {
        margin-top: 1;
    }
    """

    def __init__(self, task: AgentTask):
        super().__init__()
        self.task = task
        self.add_class(task.status.value)

    def compose(self) -> ComposeResult:
        status_emoji = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.RUNNING: "🔄",
            TaskStatus.COMPLETED: "✅",
            TaskStatus.FAILED: "❌",
            TaskStatus.CANCELLED: "⛔",
        }
        emoji = status_emoji.get(self.task.status, "❓")
        
        yield Label(f"[dim]#{self.task.id}[/dim]", classes="task-id")
        yield Label(f"{emoji} {self.task.status.value.upper()}", classes="task-status")
        yield Label(self.task.description, classes="task-description")
        
        if self.task.error:
            yield Label(f"[red]Error: {self.task.error}[/red]")
        
        if self.task.result:
            result_preview = str(self.task.result)[:100]
            if len(str(self.task.result)) > 100:
                result_preview += "..."
            yield Label(f"[green]Result: {result_preview}[/green]")


class MessageCard(Static):
    """Displays an agent message."""

    DEFAULT_CSS = """
    MessageCard {
        height: auto;
        margin: 0 0 1 0;
        padding: 1;
        border: solid $secondary;
        background: $surface;
    }
    
    MessageCard .msg-header {
        color: $text-muted;
        text-style: dim;
    }
    
    MessageCard .msg-content {
        margin-top: 1;
    }
    """

    def __init__(self, message: AgentMessage):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        type_emoji = {
            MessageType.REQUEST: "📤",
            MessageType.RESPONSE: "📥",
            MessageType.STATUS: "📊",
            MessageType.ERROR: "🚨",
            MessageType.COMMENT: "💬",
            MessageType.NOTIFICATION: "🔔",
        }
        emoji = type_emoji.get(self.message.type, "📨")
        
        yield Label(
            f"{emoji} From: {self.message.sender} | {self.message.timestamp[:19]}",
            classes="msg-header"
        )
        yield Label(self.message.content, classes="msg-content")


class AgentPanel(Static):
    """Agent orchestrator UI panel."""

    DEFAULT_CSS = """
    AgentPanel {
        height: 100%;
        width: 100%;
        padding: 1;
    }
    
    AgentPanel > .panel-header {
        text-style: bold;
        margin-bottom: 1;
    }
    
    AgentPanel > .section-header {
        text-style: bold;
        margin-top: 1;
        color: $text;
        background: $surface-darken-1;
        padding: 0 1;
    }
    
    AgentPanel #task-input {
        margin: 1 0;
    }
    
    AgentPanel #submit-task {
        margin-bottom: 1;
    }
    
    AgentPanel #task-list {
        height: auto;
        max-height: 15;
        border: solid $primary-darken-3;
    }
    
    AgentPanel #message-list {
        height: auto;
        max-height: 10;
        border: solid $secondary-darken-3;
    }
    
    AgentPanel .status-line {
        color: $text-muted;
        text-style: italic;
        margin-top: 1;
    }
    """

    class TaskSubmitted(Message):
        """Posted when a task is submitted."""
        def __init__(self, description: str):
            super().__init__()
            self.description = description

    class RefreshRequested(Message):
        """Posted when refresh is requested."""
        pass

    registry: reactive[AgentRegistry | None] = reactive(None)

    def __init__(self, registry: AgentRegistry | None = None):
        super().__init__()
        self._registry = registry

    def compose(self) -> ComposeResult:
        yield Label("🤖 Agent Orchestrator", classes="panel-header")
        
        yield Label("Create Task", classes="section-header")
        yield Input(placeholder="Describe what the agent should do...", id="task-input")
        yield Button("Submit Task", id="submit-task", variant="primary")
        
        yield Label("Tasks", classes="section-header")
        yield VerticalScroll(id="task-list")
        
        yield Label("Messages from Agents", classes="section-header")
        yield VerticalScroll(id="message-list")
        
        workspace_status = "🟢 Workspace ready" if self._registry and self._registry.workspace_exists else "🔴 Workspace not initialized"
        yield Label(workspace_status, classes="status-line", id="status-line")

    def on_mount(self) -> None:
        """Load initial data on mount."""
        if self._registry:
            self.refresh_data()

    def set_registry(self, registry: AgentRegistry) -> None:
        """Set the agent registry."""
        self._registry = registry
        self.refresh_data()

    @work(exclusive=True)
    async def refresh_data(self) -> None:
        """Refresh tasks and messages from files."""
        if not self._registry:
            return
        
        # Update status line
        status_label = self.query_one("#status-line", Label)
        if self._registry.workspace_exists:
            status_label.update("🟢 Workspace ready")
        else:
            status_label.update("🔴 Workspace not initialized")
            return
        
        # Load tasks
        task_list = self.query_one("#task-list", VerticalScroll)
        await task_list.remove_children()
        
        tasks = await self._registry.get_tasks()
        if tasks:
            for task in sorted(tasks, key=lambda t: t.created_at, reverse=True):
                await task_list.mount(TaskCard(task))
        else:
            await task_list.mount(Label("[dim]No tasks yet[/dim]"))
        
        # Load inbox messages
        message_list = self.query_one("#message-list", VerticalScroll)
        await message_list.remove_children()
        
        messages = await self._registry.get_inbox_messages()
        if messages:
            for msg in sorted(messages, key=lambda m: m.timestamp, reverse=True):
                await message_list.mount(MessageCard(msg))
        else:
            await message_list.mount(Label("[dim]No messages from agents[/dim]"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "submit-task":
            input_widget = self.query_one("#task-input", Input)
            description = input_widget.value.strip()
            
            if description:
                self.post_message(self.TaskSubmitted(description))
                input_widget.value = ""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input."""
        if event.input.id == "task-input":
            description = event.value.strip()
            if description:
                self.post_message(self.TaskSubmitted(description))
                event.input.value = ""
