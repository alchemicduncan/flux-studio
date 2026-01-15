"""Agent registry for managing tasks and messages.

The AgentRegistry provides the main interface for the orchestrator,
allowing creation/management of tasks and sending/receiving messages.
"""

import asyncio
from pathlib import Path
from typing import Any, Callable

from flux_studio.agents.agent_protocol import (
    AgentConfig,
    AgentMessage,
    AgentTask,
    MessageType,
    TaskStatus,
    PROTOCOL_VERSION,
)
from flux_studio.agents.file_comm import FileComm


class AgentRegistry:
    """Manages task queue and agent communication.
    
    Uses file-based communication via .flux-studio/ directory
    for agent-agnostic messaging.
    """

    def __init__(self, project_dir: Path | str | None = None):
        """Initialize the registry.
        
        Args:
            project_dir: Project root directory. Defaults to current working directory.
        """
        if project_dir is None:
            project_dir = Path.cwd()
        
        self.project_dir = Path(project_dir).resolve()
        self.file_comm = FileComm(self.project_dir)
        self._watcher_task: asyncio.Task | None = None
        self._message_callbacks: list[Callable[[AgentMessage], Any]] = []
        self._task_callbacks: list[Callable[[AgentTask], Any]] = []
        self._registered_agents: list[AgentConfig] = []

    @property
    def protocol_version(self) -> str:
        """Get the protocol version."""
        return PROTOCOL_VERSION

    @property
    def workspace_exists(self) -> bool:
        """Check if workspace is initialized."""
        return self.file_comm.workspace_exists()

    @property
    def registered_agents(self) -> list[AgentConfig]:
        """Get list of registered agents."""
        return self._registered_agents

    async def init_workspace(self) -> None:
        """Initialize the .flux-studio/ directory structure."""
        await self.file_comm.init_workspace()
        
        # Write orchestrator status file
        status = {
            "protocol_version": PROTOCOL_VERSION,
            "initialized": True,
            "project_dir": str(self.project_dir),
        }
        status_path = self.file_comm.workspace_dir / "orchestrator.json"
        await self.file_comm.write_json(status_path, status)

        # Create empty agents config if it doesn't exist
        await self.load_agent_config()

    def init_workspace_sync(self) -> None:
        """Synchronously initialize the workspace."""
        self.file_comm.init_workspace_sync()
        
        status = {
            "protocol_version": PROTOCOL_VERSION,
            "initialized": True,
            "project_dir": str(self.project_dir),
        }
        status_path = self.file_comm.workspace_dir / "orchestrator.json"
        self.file_comm.write_json_sync(status_path, status)

        # Initialize agents config synchronously
        self.load_agent_config_sync()

    async def load_agent_config(self) -> list[AgentConfig]:
        """Load agents from flux_agents.json."""
        config_path = self.file_comm.workspace_dir / "flux_agents.json"
        data = await self.file_comm.read_json(config_path)

        if not data:
            # Create default empty config
            default_config = {"version": "1.0", "agents": []}
            if self.workspace_exists:
                await self.file_comm.write_json(config_path, default_config)
            data = default_config

        self._registered_agents = []
        for agent_data in data.get("agents", []):
            try:
                self._registered_agents.append(AgentConfig.from_dict(agent_data))
            except (KeyError, ValueError):
                pass

        return self._registered_agents

    def load_agent_config_sync(self) -> list[AgentConfig]:
        """Synchronously load agents from flux_agents.json."""
        config_path = self.file_comm.workspace_dir / "flux_agents.json"
        data = self.file_comm.read_json_sync(config_path)

        if not data:
            # Create default empty config
            default_config = {"version": "1.0", "agents": []}
            if self.workspace_exists:
                self.file_comm.write_json_sync(config_path, default_config)
            data = default_config

        self._registered_agents = []
        for agent_data in data.get("agents", []):
            try:
                self._registered_agents.append(AgentConfig.from_dict(agent_data))
            except (KeyError, ValueError):
                pass

        return self._registered_agents

    # -------------------------------------------------------------------------
    # Task Management
    # -------------------------------------------------------------------------

    async def create_task(
        self,
        description: str,
        context: dict[str, Any] | None = None,
        assigned_to: str | None = None,
    ) -> AgentTask:
        """Create a new task for an agent.
        
        Args:
            description: What the agent should do
            context: Additional context (current file, selection, etc.)
            assigned_to: Specific agent ID if targeting a particular agent
            
        Returns:
            The created task
        """
        task = AgentTask(
            description=description,
            context=context or {},
            assigned_to=assigned_to,
        )
        
        task_path = self.file_comm.tasks_dir / f"task_{task.id}.json"
        await self.file_comm.write_json(task_path, task.to_dict())
        
        return task

    def create_task_sync(
        self,
        description: str,
        context: dict[str, Any] | None = None,
        assigned_to: str | None = None,
    ) -> AgentTask:
        """Synchronously create a new task."""
        task = AgentTask(
            description=description,
            context=context or {},
            assigned_to=assigned_to,
        )
        
        task_path = self.file_comm.tasks_dir / f"task_{task.id}.json"
        self.file_comm.write_json_sync(task_path, task.to_dict())
        
        return task

    async def get_tasks(
        self,
        status_filter: TaskStatus | None = None,
    ) -> list[AgentTask]:
        """Get all tasks, optionally filtered by status.
        
        Args:
            status_filter: Only return tasks with this status
            
        Returns:
            List of tasks
        """
        task_files = await self.file_comm.list_json_files(self.file_comm.tasks_dir)
        tasks = []
        
        for task_file in task_files:
            data = await self.file_comm.read_json(task_file)
            if data:
                task = AgentTask.from_dict(data)
                if status_filter is None or task.status == status_filter:
                    tasks.append(task)
        
        return tasks

    def get_tasks_sync(
        self,
        status_filter: TaskStatus | None = None,
    ) -> list[AgentTask]:
        """Synchronously get all tasks."""
        task_files = self.file_comm.list_json_files_sync(self.file_comm.tasks_dir)
        tasks = []
        
        for task_file in task_files:
            data = self.file_comm.read_json_sync(task_file)
            if data:
                task = AgentTask.from_dict(data)
                if status_filter is None or task.status == status_filter:
                    tasks.append(task)
        
        return tasks

    async def get_task(self, task_id: str) -> AgentTask | None:
        """Get a specific task by ID."""
        task_path = self.file_comm.tasks_dir / f"task_{task_id}.json"
        data = await self.file_comm.read_json(task_path)
        
        if data:
            return AgentTask.from_dict(data)
        return None

    async def update_task(
        self,
        task_id: str,
        status: TaskStatus | None = None,
        result: Any = None,
        error: str | None = None,
    ) -> AgentTask | None:
        """Update a task's status/result.
        
        Args:
            task_id: The task to update
            status: New status
            result: Result data (for completed tasks)
            error: Error message (for failed tasks)
            
        Returns:
            Updated task or None if not found
        """
        task = await self.get_task(task_id)
        if not task:
            return None
        
        if status == TaskStatus.RUNNING:
            task.start()
        elif status == TaskStatus.COMPLETED:
            task.complete(result)
        elif status == TaskStatus.FAILED:
            task.fail(error or "Unknown error")
        elif status == TaskStatus.CANCELLED:
            task.cancel()
        elif status:
            task.status = status
        
        if result is not None and status != TaskStatus.COMPLETED:
            task.result = result
        
        task_path = self.file_comm.tasks_dir / f"task_{task_id}.json"
        await self.file_comm.write_json(task_path, task.to_dict())
        
        return task

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a task.
        
        Returns:
            True if cancelled, False if not found or already completed
        """
        task = await self.get_task(task_id)
        if not task:
            return False
        
        if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            return False
        
        task.cancel()
        task_path = self.file_comm.tasks_dir / f"task_{task_id}.json"
        await self.file_comm.write_json(task_path, task.to_dict())
        
        return True

    async def delete_task(self, task_id: str) -> bool:
        """Delete a task file.
        
        Returns:
            True if deleted
        """
        task_path = self.file_comm.tasks_dir / f"task_{task_id}.json"
        return await self.file_comm.delete_file(task_path)

    # -------------------------------------------------------------------------
    # Message Management
    # -------------------------------------------------------------------------

    async def send_message(
        self,
        content: str,
        recipient: str = "agent",
        msg_type: MessageType = MessageType.REQUEST,
        in_reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Send a message to an agent.
        
        Args:
            content: Message content
            recipient: Target agent ID (or "agent" for any)
            msg_type: Type of message
            in_reply_to: ID of message being replied to
            metadata: Additional metadata
            
        Returns:
            The sent message
        """
        message = AgentMessage(
            type=msg_type,
            sender="flux-studio",
            recipient=recipient,
            content=content,
            in_reply_to=in_reply_to,
            metadata=metadata or {},
        )
        
        msg_path = self.file_comm.outbox_dir / f"msg_{message.id}.json"
        await self.file_comm.write_json(msg_path, message.to_dict())
        
        return message

    def send_message_sync(
        self,
        content: str,
        recipient: str = "agent",
        msg_type: MessageType = MessageType.REQUEST,
        in_reply_to: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """Synchronously send a message."""
        message = AgentMessage(
            type=msg_type,
            sender="flux-studio",
            recipient=recipient,
            content=content,
            in_reply_to=in_reply_to,
            metadata=metadata or {},
        )
        
        msg_path = self.file_comm.outbox_dir / f"msg_{message.id}.json"
        self.file_comm.write_json_sync(msg_path, message.to_dict())
        
        return message

    async def get_inbox_messages(self) -> list[AgentMessage]:
        """Get all messages from agents (inbox)."""
        msg_files = await self.file_comm.list_json_files(self.file_comm.inbox_dir)
        messages = []
        
        for msg_file in msg_files:
            data = await self.file_comm.read_json(msg_file)
            if data:
                messages.append(AgentMessage.from_dict(data))
        
        return messages

    def get_inbox_messages_sync(self) -> list[AgentMessage]:
        """Synchronously get inbox messages."""
        msg_files = self.file_comm.list_json_files_sync(self.file_comm.inbox_dir)
        messages = []
        
        for msg_file in msg_files:
            data = self.file_comm.read_json_sync(msg_file)
            if data:
                messages.append(AgentMessage.from_dict(data))
        
        return messages

    async def get_outbox_messages(self) -> list[AgentMessage]:
        """Get all messages sent to agents (outbox)."""
        msg_files = await self.file_comm.list_json_files(self.file_comm.outbox_dir)
        messages = []
        
        for msg_file in msg_files:
            data = await self.file_comm.read_json(msg_file)
            if data:
                messages.append(AgentMessage.from_dict(data))
        
        return messages

    async def acknowledge_message(self, message_id: str) -> bool:
        """Mark a message as acknowledged by removing it from inbox.
        
        Returns:
            True if message was removed
        """
        msg_path = self.file_comm.inbox_dir / f"msg_{message_id}.json"
        return await self.file_comm.delete_file(msg_path)

    # -------------------------------------------------------------------------
    # Watching for Changes
    # -------------------------------------------------------------------------

    def on_message(self, callback: Callable[[AgentMessage], Any]) -> None:
        """Register a callback for new inbox messages."""
        self._message_callbacks.append(callback)

    def on_task_update(self, callback: Callable[[AgentTask], Any]) -> None:
        """Register a callback for task updates."""
        self._task_callbacks.append(callback)

    async def start_watching(self, poll_interval: float = 1.0) -> None:
        """Start watching for new messages and task updates.
        
        This starts background tasks that poll for changes.
        Call stop_watching() to stop.
        """
        if self._watcher_task:
            return
        
        async def watch_inbox(path: Path) -> None:
            data = await self.file_comm.read_json(path)
            if data:
                message = AgentMessage.from_dict(data)
                for callback in self._message_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(message)
                        else:
                            callback(message)
                    except Exception:
                        pass
        
        self._watcher_task = asyncio.create_task(
            self.file_comm.watch_directory(
                self.file_comm.inbox_dir,
                watch_inbox,
                poll_interval,
            )
        )

    def stop_watching(self) -> None:
        """Stop watching for changes."""
        if self._watcher_task:
            self._watcher_task.cancel()
            self._watcher_task = None

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    async def cleanup_completed_tasks(self, max_age_hours: int = 24) -> int:
        """Delete completed/failed/cancelled tasks older than max_age.
        
        Returns:
            Number of tasks deleted
        """
        from datetime import datetime, timedelta
        
        tasks = await self.get_tasks()
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        deleted = 0
        
        for task in tasks:
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                try:
                    completed_time = datetime.fromisoformat(task.completed_at) if task.completed_at else None
                    if completed_time and completed_time < cutoff:
                        if await self.delete_task(task.id):
                            deleted += 1
                except ValueError:
                    pass
        
        return deleted
