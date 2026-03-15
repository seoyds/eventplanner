"""Tests for logistics agent tools and agent class."""
import pytest
from agents.logistics.tools import create_timeline_slot
from agents.logistics.agent import LogisticsCoordinatorAgent


@pytest.mark.asyncio
async def test_create_timeline_slot_basic():
    args = {"start_time": "10:00", "duration_minutes": 60, "label": "Guest Arrival"}
    result = await create_timeline_slot.handler(args)
    text = result["content"][0]["text"]
    assert "10:00" in text
    assert "11:00" in text
    assert "Guest Arrival" in text


@pytest.mark.asyncio
async def test_create_timeline_slot_overnight():
    args = {"start_time": "23:30", "duration_minutes": 45, "label": "Late Night Snacks"}
    result = await create_timeline_slot.handler(args)
    text = result["content"][0]["text"]
    assert "23:30" in text
    assert "00:15" in text


@pytest.mark.asyncio
async def test_create_timeline_slot_invalid_time():
    args = {"start_time": "25:99", "duration_minutes": 30, "label": "Bad Time"}
    result = await create_timeline_slot.handler(args)
    text = result["content"][0]["text"]
    assert "Error" in text or "error" in text.lower()


def test_logistics_agent_card():
    agent = LogisticsCoordinatorAgent()
    card = agent.get_agent_card()
    assert card.name == "logistics"
    assert card.url == "http://logistics:8008"
    assert len(card.skills) >= 1


def test_logistics_agent_fastapi_app():
    agent = LogisticsCoordinatorAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
