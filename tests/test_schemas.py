"""Tests for shared Pydantic schemas."""
from datetime import date
from shared.schemas import EventRequirements, AgentStatus, AgentResult, OrchestratorState


def test_event_requirements_minimal():
    req = EventRequirements(
        event_type="birthday",
        guest_count=30,
        location_preference="urban",
        date_range=(date(2026, 7, 1), date(2026, 7, 3)),
        budget_total=5000.0,
        dietary_restrictions=["vegan"],
        accessibility_needs=[],
    )
    assert req.event_type == "birthday"
    assert req.guest_count == 30
    assert req.event_name is None
    assert req.theme_preferences is None
    assert req.special_requests == []
    assert req.age_groups == []


def test_event_requirements_full():
    req = EventRequirements(
        event_type="family reunion",
        event_name="Smith Family 50th",
        guest_count=40,
        location_preference="mountain",
        date_range=(date(2026, 7, 10), date(2026, 7, 12)),
        budget_total=5000.0,
        dietary_restrictions=["vegan", "gluten-free"],
        accessibility_needs=["wheelchair", "elderly-friendly"],
        theme_preferences="rustic mountain",
        special_requests=["live music"],
        age_groups=["children", "adults", "elderly"],
    )
    assert req.event_name == "Smith Family 50th"
    assert len(req.dietary_restrictions) == 2
    assert "wheelchair" in req.accessibility_needs


def test_agent_status_enum():
    assert AgentStatus.PENDING == "pending"
    assert AgentStatus.RUNNING == "running"
    assert AgentStatus.COMPLETED == "completed"
    assert AgentStatus.FAILED == "failed"
    assert AgentStatus.REVISING == "revising"


def test_agent_result_defaults():
    result = AgentResult(
        agent_id="venue",
        status=AgentStatus.COMPLETED,
        result={"venues": []},
    )
    assert result.estimated_cost == 0.0
    assert result.warnings == []
    assert result.execution_time_ms == 0


def test_agent_result_full():
    result = AgentResult(
        agent_id="weather",
        status=AgentStatus.COMPLETED,
        result={"forecast": "sunny"},
        estimated_cost=0.0,
        warnings=["Limited forecast data"],
        execution_time_ms=1500,
    )
    assert result.warnings == ["Limited forecast data"]
    assert result.execution_time_ms == 1500


def test_orchestrator_state_defaults():
    state = OrchestratorState(request_id="req-001")
    assert state.requirements is None
    assert state.agent_statuses == {}
    assert state.agent_results == {}
    assert state.budget_remaining == 0.0
    assert state.current_phase == "idle"
    assert state.messages == []
    assert state.blueprint is None


def test_orchestrator_state_serialization():
    state = OrchestratorState(
        request_id="req-002",
        agent_statuses={"venue": AgentStatus.COMPLETED},
        current_phase="wave_1",
    )
    data = state.model_dump()
    assert data["request_id"] == "req-002"
    assert data["agent_statuses"]["venue"] == "completed"
    assert data["current_phase"] == "wave_1"
