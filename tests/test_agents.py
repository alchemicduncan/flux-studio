"""Tests for the agent orchestrator module."""

import pytest
from pathlib import Path
import json

from flux_studio.agents.agent_protocol import (
    AgentCapability,
    AgentInfo,
    AgentMessage,
    AgentTask,
    MessageType,
    TaskStatus,
    PROTOCOL_VERSION,
)
from flux_studio.agents.file_comm import FileComm
from flux_studio.agents.agent_registry import AgentRegistry


class TestAgentProtocol:
    """Tests for agent protocol types."""

    def test_protocol_version_defined(self):
        """Protocol version should be defined."""
        assert PROTOCOL_VERSION == "1.0.0"

    def test_agent_task_creation(self):
        """AgentTask should have correct defaults."""
        task = AgentTask(description="Test task")
        
        assert task.description == "Test task"
        assert task.status == TaskStatus.PENDING
        assert task.result is None
        assert task.error is None
        assert len(task.id) == 12

    def test_agent_task_serialization(self):
        """AgentTask should serialize and deserialize correctly."""
        task = AgentTask(
            description="Test task",
            context={"file": "test.md"},
        )
        
        data = task.to_dict()
        assert data["protocol_version"] == PROTOCOL_VERSION
        assert data["description"] == "Test task"
        assert data["context"] == {"file": "test.md"}
        
        restored = AgentTask.from_dict(data)
        assert restored.id == task.id
        assert restored.description == task.description
        assert restored.context == task.context

    def test_agent_task_lifecycle(self):
        """AgentTask should transition through states correctly."""
        task = AgentTask(description="Test")
        assert task.status == TaskStatus.PENDING
        
        task.start()
        assert task.status == TaskStatus.RUNNING
        assert task.started_at is not None
        
        task.complete(result={"done": True})
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"done": True}
        assert task.completed_at is not None

    def test_agent_task_failure(self):
        """AgentTask should handle failure correctly."""
        task = AgentTask(description="Test")
        task.start()
        task.fail("Something went wrong")
        
        assert task.status == TaskStatus.FAILED
        assert task.error == "Something went wrong"
        assert task.completed_at is not None

    def test_agent_message_creation(self):
        """AgentMessage should have correct defaults."""
        msg = AgentMessage(content="Hello")
        
        assert msg.content == "Hello"
        assert msg.type == MessageType.REQUEST
        assert msg.sender == "flux-studio"
        assert len(msg.id) == 12

    def test_agent_message_serialization(self):
        """AgentMessage should serialize and deserialize correctly."""
        msg = AgentMessage(
            content="Test message",
            type=MessageType.NOTIFICATION,
            recipient="test-agent",
        )
        
        data = msg.to_dict()
        assert data["protocol_version"] == PROTOCOL_VERSION
        assert data["content"] == "Test message"
        assert data["type"] == "notification"
        
        restored = AgentMessage.from_dict(data)
        assert restored.id == msg.id
        assert restored.content == msg.content
        assert restored.type == msg.type

    def test_agent_info_serialization(self):
        """AgentInfo should serialize and deserialize correctly."""
        info = AgentInfo(
            id="test-agent",
            name="Test Agent",
            capabilities=[AgentCapability.CODING, AgentCapability.REVIEW],
        )
        
        data = info.to_dict()
        assert data["id"] == "test-agent"
        assert "coding" in data["capabilities"]
        assert "review" in data["capabilities"]
        
        restored = AgentInfo.from_dict(data)
        assert restored.id == info.id
        assert AgentCapability.CODING in restored.capabilities


class TestFileComm:
    """Tests for file communication layer."""

    def test_init_workspace(self, tmp_path):
        """FileComm should create workspace directory structure."""
        file_comm = FileComm(tmp_path)
        file_comm.init_workspace_sync()
        
        assert (tmp_path / ".flux-studio").exists()
        assert (tmp_path / ".flux-studio" / "tasks").exists()
        assert (tmp_path / ".flux-studio" / "messages" / "inbox").exists()
        assert (tmp_path / ".flux-studio" / "messages" / "outbox").exists()

    def test_write_read_json(self, tmp_path):
        """FileComm should write and read JSON files correctly."""
        file_comm = FileComm(tmp_path)
        file_comm.init_workspace_sync()
        
        test_data = {"key": "value", "number": 42}
        test_path = tmp_path / ".flux-studio" / "test.json"
        
        file_comm.write_json_sync(test_path, test_data)
        assert test_path.exists()
        
        read_data = file_comm.read_json_sync(test_path)
        assert read_data == test_data

    def test_read_nonexistent_json(self, tmp_path):
        """FileComm should return None for nonexistent files."""
        file_comm = FileComm(tmp_path)
        
        result = file_comm.read_json_sync(tmp_path / "doesnt_exist.json")
        assert result is None

    def test_list_json_files(self, tmp_path):
        """FileComm should list JSON files in a directory."""
        file_comm = FileComm(tmp_path)
        file_comm.init_workspace_sync()
        
        # Create some test files
        tasks_dir = tmp_path / ".flux-studio" / "tasks"
        file_comm.write_json_sync(tasks_dir / "task_001.json", {"id": "001"})
        file_comm.write_json_sync(tasks_dir / "task_002.json", {"id": "002"})
        
        files = file_comm.list_json_files_sync(tasks_dir)
        assert len(files) == 2
        assert any("task_001.json" in str(f) for f in files)


class TestAgentRegistry:
    """Tests for agent registry."""

    def test_init_workspace(self, tmp_path):
        """AgentRegistry should initialize workspace."""
        registry = AgentRegistry(tmp_path)
        registry.init_workspace_sync()
        
        assert registry.workspace_exists
        assert (tmp_path / ".flux-studio" / "orchestrator.json").exists()

    def test_create_task_sync(self, tmp_path):
        """AgentRegistry should create tasks."""
        registry = AgentRegistry(tmp_path)
        registry.init_workspace_sync()
        
        task = registry.create_task_sync(
            description="Test task",
            context={"test": True},
        )
        
        assert task.description == "Test task"
        assert task.context == {"test": True}
        assert task.status == TaskStatus.PENDING
        
        # Verify file was created
        task_file = tmp_path / ".flux-studio" / "tasks" / f"task_{task.id}.json"
        assert task_file.exists()

    def test_get_tasks_sync(self, tmp_path):
        """AgentRegistry should retrieve tasks."""
        registry = AgentRegistry(tmp_path)
        registry.init_workspace_sync()
        
        # Create multiple tasks
        registry.create_task_sync("Task 1")
        registry.create_task_sync("Task 2")
        registry.create_task_sync("Task 3")
        
        tasks = registry.get_tasks_sync()
        assert len(tasks) == 3

    def test_get_tasks_filtered_sync(self, tmp_path):
        """AgentRegistry should filter tasks by status."""
        registry = AgentRegistry(tmp_path)
        registry.init_workspace_sync()
        
        # Create tasks with different statuses
        task1 = registry.create_task_sync("Pending task")
        task2 = registry.create_task_sync("Running task")
        
        # Manually update task2 status
        task2.start()
        task2_path = tmp_path / ".flux-studio" / "tasks" / f"task_{task2.id}.json"
        registry.file_comm.write_json_sync(task2_path, task2.to_dict())
        
        pending = registry.get_tasks_sync(status_filter=TaskStatus.PENDING)
        running = registry.get_tasks_sync(status_filter=TaskStatus.RUNNING)
        
        assert len(pending) == 1
        assert len(running) == 1

    def test_send_message_sync(self, tmp_path):
        """AgentRegistry should send messages."""
        registry = AgentRegistry(tmp_path)
        registry.init_workspace_sync()
        
        msg = registry.send_message_sync(
            content="Hello agent!",
            recipient="test-agent",
        )
        
        assert msg.content == "Hello agent!"
        assert msg.recipient == "test-agent"
        
        # Verify file was created in outbox
        msg_file = tmp_path / ".flux-studio" / "messages" / "outbox" / f"msg_{msg.id}.json"
        assert msg_file.exists()

    def test_protocol_version(self, tmp_path):
        """AgentRegistry should expose protocol version."""
        registry = AgentRegistry(tmp_path)
        assert registry.protocol_version == PROTOCOL_VERSION


@pytest.mark.asyncio
class TestAgentRegistryAsync:
    """Async tests for agent registry."""

    async def test_create_and_get_task(self, tmp_path):
        """AgentRegistry should create and retrieve tasks asynchronously."""
        registry = AgentRegistry(tmp_path)
        await registry.init_workspace()
        
        task = await registry.create_task("Async test task")
        
        retrieved = await registry.get_task(task.id)
        assert retrieved is not None
        assert retrieved.description == "Async test task"

    async def test_update_task(self, tmp_path):
        """AgentRegistry should update tasks."""
        registry = AgentRegistry(tmp_path)
        await registry.init_workspace()
        
        task = await registry.create_task("Test task")
        
        updated = await registry.update_task(
            task.id,
            status=TaskStatus.COMPLETED,
            result={"success": True},
        )
        
        assert updated is not None
        assert updated.status == TaskStatus.COMPLETED
        assert updated.result == {"success": True}

    async def test_cancel_task(self, tmp_path):
        """AgentRegistry should cancel tasks."""
        registry = AgentRegistry(tmp_path)
        await registry.init_workspace()
        
        task = await registry.create_task("Test task")
        
        result = await registry.cancel_task(task.id)
        assert result is True
        
        cancelled = await registry.get_task(task.id)
        assert cancelled.status == TaskStatus.CANCELLED

    async def test_send_and_receive_messages(self, tmp_path):
        """AgentRegistry should handle message round-trip."""
        registry = AgentRegistry(tmp_path)
        await registry.init_workspace()
        
        # Send a message (goes to outbox)
        sent = await registry.send_message("Test message")
        
        outbox = await registry.get_outbox_messages()
        assert len(outbox) == 1
        assert outbox[0].content == "Test message"

    async def test_inbox_messages(self, tmp_path):
        """AgentRegistry should read inbox messages."""
        registry = AgentRegistry(tmp_path)
        await registry.init_workspace()
        
        # Simulate an agent putting a message in inbox
        inbox_msg = AgentMessage(
            sender="test-agent",
            recipient="flux-studio",
            content="Hello from agent!",
            type=MessageType.RESPONSE,
        )
        inbox_path = tmp_path / ".flux-studio" / "messages" / "inbox" / f"msg_{inbox_msg.id}.json"
        await registry.file_comm.write_json(inbox_path, inbox_msg.to_dict())
        
        inbox = await registry.get_inbox_messages()
        assert len(inbox) == 1
        assert inbox[0].content == "Hello from agent!"
