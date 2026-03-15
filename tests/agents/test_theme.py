"""Tests for theme agent class (no custom tools)."""
from agents.theme.agent import ThemeDesignerAgent


def test_theme_agent_card():
    agent = ThemeDesignerAgent()
    card = agent.get_agent_card()
    assert card.name == "theme"
    assert "theme" in card.description.lower()
    assert card.url == "http://theme:8007"
    assert len(card.skills) >= 1


def test_theme_agent_no_mcp_tools():
    agent = ThemeDesignerAgent()
    tools = agent.get_mcp_tools()
    assert tools == []


def test_theme_agent_allowed_tools():
    agent = ThemeDesignerAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools


def test_theme_agent_fastapi_app():
    agent = ThemeDesignerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
