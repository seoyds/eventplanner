"""Tests for venue agent tools and agent class."""
import pytest
from agents.venue.tools import search_venues, score_venue
from agents.venue.agent import VenuePlannerAgent


@pytest.mark.asyncio
async def test_search_venues_returns_structured_prompt():
    args = {
        "location": "Denver, CO",
        "guest_count": 40,
        "event_type": "family reunion",
        "indoor_required": False,
    }
    result = await search_venues.handler(args)
    assert "content" in result
    text = result["content"][0]["text"]
    assert "family reunion" in text
    assert "Denver" in text
    assert "40" in text


@pytest.mark.asyncio
async def test_search_venues_indoor_required():
    args = {
        "location": "NYC",
        "guest_count": 20,
        "event_type": "birthday",
        "indoor_required": True,
    }
    result = await search_venues.handler(args)
    text = result["content"][0]["text"]
    assert "indoor" in text.lower()


@pytest.mark.asyncio
async def test_score_venue():
    args = {
        "venue_name": "Mountain Lodge",
        "capacity_match": 0.9,
        "price_per_person": 30.0,
        "accessibility_score": 0.8,
        "review_rating": 4.5,
    }
    result = await score_venue.handler(args)
    text = result["content"][0]["text"]
    assert "Mountain Lodge" in text
    assert "/1.0" in text


@pytest.mark.asyncio
async def test_score_venue_expensive():
    args = {
        "venue_name": "Pricey Palace",
        "capacity_match": 1.0,
        "price_per_person": 200.0,
        "accessibility_score": 1.0,
        "review_rating": 5.0,
    }
    result = await score_venue.handler(args)
    text = result["content"][0]["text"]
    score_str = text.split("scored ")[1].split("/")[0]
    score = float(score_str)
    assert score <= 1.0


def test_venue_agent_card():
    agent = VenuePlannerAgent()
    card = agent.get_agent_card()
    assert card.name == "venue"
    assert "venue" in card.description.lower()
    assert card.url == "http://venue:8001"
    assert len(card.skills) >= 1


def test_venue_agent_mcp_tools():
    agent = VenuePlannerAgent()
    tools = agent.get_mcp_tools()
    assert len(tools) == 2


def test_venue_agent_allowed_tools():
    agent = VenuePlannerAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools
    assert "mcp__venue__search_venues" in tools


def test_venue_agent_fastapi_app():
    agent = VenuePlannerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
