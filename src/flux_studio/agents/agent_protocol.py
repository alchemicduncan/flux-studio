"""Agent protocol types for Flux Studio agent orchestration.

This module defines the communication protocol between Flux Studio and
external AI coding agents via file-based messaging.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# Protocol version for compatibility checking
PROTOCOL_VERSION = "1.0.0"


class AgentCapability(Enum):
    """Capabilities an agent can provide."""

    RESEARCH = "research"
    WRITING = "writing"
    REVIEW = "review"
    EDITING = "editing"
    CODING = "coding"
    ANALYSIS = "analysis"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"


class TaskStatus(Enum):
    """Status of a task in the orchestrator."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageType(Enum):
    """Type of message in agent communication."""

    REQUEST = "request"
    RESPONSE = "response"
    STATUS = "status"
    ERROR = "error"
    COMMENT = "comment"
    NOTIFICATION = "notification"


def _generate_id() -> str:
    """Generate a unique ID for tasks/messages."""
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now().isoformat()


@dataclass
class AgentConfig:
    """Configuration for an ACP agent."""

    id: str
    name: str
    command: list[str]
    env: dict[str, str] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "command": self.command,
            "env": self.env,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentConfig":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            command=data.get("command", []),
            env=data.get("env", {}),
            description=data.get("description", ""),
        )


@dataclass
class AgentInfo:
    """Information about an available agent."""

    id: str
    name: str
    description: str = ""
    capabilities: list[AgentCapability] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.value for c in self.capabilities],
            "version": self.version,
            "author": self.author,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentInfo":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            capabilities=[AgentCapability(c) for c in data.get("capabilities", [])],
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
        )


@dataclass
class AgentMessage:
    """A message exchanged between the editor and agents."""

    id: str = field(default_factory=_generate_id)
    type: MessageType = MessageType.REQUEST
    sender: str = "flux-studio"
    recipient: str = "agent"
    content: str = ""
    timestamp: str = field(default_factory=_now_iso)
    in_reply_to: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "protocol_version": PROTOCOL_VERSION,
            "id": self.id,
            "type": self.type.value,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "timestamp": self.timestamp,
            "in_reply_to": self.in_reply_to,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentMessage":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            type=MessageType(data["type"]),
            sender=data.get("sender", "unknown"),
            recipient=data.get("recipient", "flux-studio"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", _now_iso()),
            in_reply_to=data.get("in_reply_to"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AgentTask:
    """A task for an agent to execute."""

    id: str = field(default_factory=_generate_id)
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: str = field(default_factory=_now_iso)
    started_at: str | None = None
    completed_at: str | None = None
    assigned_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "protocol_version": PROTOCOL_VERSION,
            "id": self.id,
            "description": self.description,
            "context": self.context,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_to": self.assigned_to,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentTask":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            context=data.get("context", {}),
            status=TaskStatus(data.get("status", "pending")),
            result=data.get("result"),
            error=data.get("error"),
            created_at=data.get("created_at", _now_iso()),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            assigned_to=data.get("assigned_to"),
        )

    def start(self) -> None:
        """Mark the task as started."""
        self.status = TaskStatus.RUNNING
        self.started_at = _now_iso()

    def complete(self, result: Any = None) -> None:
        """Mark the task as completed."""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = _now_iso()

    def fail(self, error: str) -> None:
        """Mark the task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = _now_iso()

    def cancel(self) -> None:
        """Mark the task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = _now_iso()
