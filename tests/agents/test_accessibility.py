"""Tests for accessibility agent tools and agent class."""
import pytest
from agents.accessibility.tools import check_accessibility
from agents.accessibility.agent import AccessibilityCheckerAgent


@pytest.mark.asyncio
async def test_check_accessibility_fully_accessible():
    args = {
        "wheelchair_access": True,
        "has_elevator": True,
        "has_stairs_only": False,
        "suitable_for_elderly": True,
        "suitable_for_children": True,
    }
    result = await check_accessibility.handler(args)
    text = result["content"][0]["text"]
    assert "1.00" in text
    assert "Excellent" in text


@pytest.mark.asyncio
async def test_check_accessibility_poor():
    args = {
        "wheelchair_access": False,
        "has_elevator": False,
        "has_stairs_only": True,
        "suitable_for_elderly": False,
        "suitable_for_children": False,
    }
    result = await check_accessibility.handler(args)
    text = result["content"][0]["text"]
    assert "0.00" in text
    assert "Poor" in text


@pytest.mark.asyncio
async def test_check_accessibility_partial():
    args = {
        "wheelchair_access": True,
        "has_elevator": False,
        "has_stairs_only": False,
        "suitable_for_elderly": True,
        "suitable_for_children": False,
    }
    result = await check_accessibility.handler(args)
    text = result["content"][0]["text"]
    assert "/1.0" in text or "score" in text.lower()


def test_accessibility_agent_card():
    agent = AccessibilityCheckerAgent()
    card = agent.get_agent_card()
    assert card.name == "accessibility"
    assert card.url == "http://accessibility:8006"
    assert len(card.skills) >= 1


def test_accessibility_agent_fastapi_app():
    agent = AccessibilityCheckerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
