"""Tests for activity agent class (no custom tools)."""
from agents.activity.agent import ActivityCoordinatorAgent


def test_activity_agent_card():
    agent = ActivityCoordinatorAgent()
    card = agent.get_agent_card()
    assert card.name == "activity"
    assert "activit" in card.description.lower()
    assert card.url == "http://activity:8005"
    assert len(card.skills) >= 1


def test_activity_agent_no_mcp_tools():
    agent = ActivityCoordinatorAgent()
    tools = agent.get_mcp_tools()
    assert tools == []


def test_activity_agent_allowed_tools():
    agent = ActivityCoordinatorAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools


def test_activity_agent_fastapi_app():
    agent = ActivityCoordinatorAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
