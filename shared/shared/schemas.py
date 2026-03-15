"""Pydantic models shared across all agents and the conductor."""
from pydantic import BaseModel
from datetime import date
from enum import Enum


class EventRequirements(BaseModel):
    """Structured extraction from user's natural language prompt."""
    event_type: str
    event_name: str | None = None
    guest_count: int
    location_preference: str
    date_range: tuple[date, date]
    budget_total: float
    dietary_restrictions: list[str]
    accessibility_needs: list[str]
    theme_preferences: str | None = None
    special_requests: list[str] = []
    age_groups: list[str] = []


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISING = "revising"


class AgentResult(BaseModel):
    """Standard wrapper for every agent's output."""
    agent_id: str
    status: AgentStatus
    result: dict
    estimated_cost: float = 0.0
    warnings: list[str] = []
    execution_time_ms: int = 0


class OrchestratorState(BaseModel):
    """Shared state synced via AG-UI to the frontend."""
    request_id: str
    requirements: EventRequirements | None = None
    agent_statuses: dict[str, AgentStatus] = {}
    agent_results: dict[str, dict] = {}
    budget_remaining: float = 0.0
    current_phase: str = "idle"
    messages: list[str] = []
    blueprint: dict | None = None
