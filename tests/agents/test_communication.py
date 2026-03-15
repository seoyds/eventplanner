"""Tests for communication agent class (no custom tools)."""
from agents.communication.agent import CommunicationWriterAgent


def test_communication_agent_card():
    agent = CommunicationWriterAgent()
    card = agent.get_agent_card()
    assert card.name == "communication"
    assert card.url == "http://communication:8009"
    assert len(card.skills) >= 1


def test_communication_agent_no_mcp_tools():
    agent = CommunicationWriterAgent()
    tools = agent.get_mcp_tools()
    assert tools == []


def test_communication_agent_allowed_tools():
    agent = CommunicationWriterAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools


def test_communication_agent_fastapi_app():
    agent = CommunicationWriterAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
