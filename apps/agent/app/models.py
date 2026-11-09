import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    """Lifecycle states of an autonomous deep research workflow."""

    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchJobBase(SQLModel):
    """Base schema for research job parameters."""

    query: str
    depth: int = 2
    breadth: int = 4


class ResearchJob(ResearchJobBase, table=True):
    """Persisted research job record with execution logs, result, and session metadata."""

    id: str | None = Field(default=None, primary_key=True)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    result: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    logs_json: str = Field(default="[]")  # Store logs as JSON string
    session_id: str | None = Field(default=None, index=True)
    client_ip: str | None = Field(default=None, index=True)

    @property
    def logs(self) -> list[dict[str, Any]]:
        """Deserialize and return logs from JSON representation."""
        return json.loads(self.logs_json)

    @logs.setter
    def logs(self, value: list[dict[str, Any]]) -> None:
        """Serialize logs to JSON representation for storage."""
        self.logs_json = json.dumps(value)


class ResearchJobCreate(ResearchJobBase):
    """Payload schema for requesting a new research workflow."""


class ResearchJobRead(ResearchJobBase):
    """Response schema for returning a research job to clients."""

    id: str
    status: JobStatus
    result: str | None
    created_at: datetime
    logs: list[dict[str, Any]]
    is_owner: bool = False


class ResearchUsage(SQLModel, table=True):
    """Durable record of research jobs created per session/IP for rate limiting.

    Retained independently of ResearchJob row deletions to prevent quota circumvention.
    """

    id: str | None = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    session_id: str = Field(index=True)
    client_ip: str = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC), index=True)
