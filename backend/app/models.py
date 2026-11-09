from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
import json
from enum import Enum

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
    id: Optional[str] = Field(default=None, primary_key=True)
    status: JobStatus = Field(default=JobStatus.QUEUED)
    result: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    logs_json: str = Field(default="[]")  # Store logs as JSON string
    
    @property
    def logs(self) -> List[Dict[str, Any]]:
        return json.loads(self.logs_json)
    
    @logs.setter
    def logs(self, value: List[Dict[str, Any]]):
        self.logs_json = json.dumps(value)

class ResearchJobCreate(ResearchJobBase):
    pass

class ResearchJobRead(ResearchJobBase):
    id: str
    status: JobStatus
    result: Optional[str]
    created_at: datetime
    logs: List[Dict[str, Any]]
