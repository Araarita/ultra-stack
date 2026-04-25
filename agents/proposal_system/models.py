from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class Category(str, Enum):
    capability = "capability"
    improvement = "improvement"
    maintenance = "maintenance"
    insight = "insight"
    security = "security"
    experience = "experience"
    performance = "performance"
    observability = "observability"


class Impact(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class RiskLevel(str, Enum):
    safe = "safe"
    low = "low"
    medium = "medium"
    high = "high"


class ProposalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    executing = "executing"
    completed = "completed"
    failed = "failed"


class Proposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = Field(max_length=100)
    description: str
    benefit: str
    category: Category
    impact: Impact
    effort: str
    risk_level: RiskLevel
    action_type: str
    action_code: str
    estimated_time_seconds: int = 60
    requires_restart: bool = False
    dependencies: list[str] = Field(default_factory=list)
    rollback_strategy: str = ""
    success_criteria: str = ""
    status: ProposalStatus = ProposalStatus.pending
    created_at: datetime = Field(default_factory=datetime.now)
    responded_at: datetime | None = None
    executed_at: datetime | None = None
    execution_log: str = ""