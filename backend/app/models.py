import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlmodel import Field, SQLModel


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchJobBase(SQLModel):
    query: str
    depth: int = 2
    breadth: int = 4


class ResearchJob(ResearchJobBase, table=True):
    id: str | None = Field(default=None, primary_key=True)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    result: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    logs_json: str = Field(default="[]")  # Store logs as JSON string
    session_id: str | None = Field(default=None, index=True)
    client_ip: str | None = Field(default=None, index=True)

    @property
    def logs(self) -> list[dict[str, Any]]:
        return json.loads(self.logs_json)

    @logs.setter
    def logs(self, value: list[dict[str, Any]]):
        self.logs_json = json.dumps(value)


class ResearchJobCreate(ResearchJobBase):
    pass


class ResearchJobRead(ResearchJobBase):
    id: str
    status: JobStatus
    result: str | None
    created_at: datetime
    logs: list[dict[str, Any]]
    is_owner: bool = False
