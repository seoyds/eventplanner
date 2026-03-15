"""Tests for menu agent tools and agent class."""
import pytest
from agents.menu.tools import estimate_food_cost
from agents.menu.agent import MenuPlannerAgent


@pytest.mark.asyncio
async def test_estimate_food_cost_catered_dinner():
    args = {"meal_type": "dinner", "guest_count": 40, "service_style": "catered"}
    result = await estimate_food_cost.handler(args)
    text = result["content"][0]["text"]
    # dinner $25 * 1.5 catered = $37.50/person * 40 = $1500
    assert "1500.00" in text
    assert "dinner" in text


@pytest.mark.asyncio
async def test_estimate_food_cost_potluck_lunch():
    args = {"meal_type": "lunch", "guest_count": 20, "service_style": "potluck"}
    result = await estimate_food_cost.handler(args)
    text = result["content"][0]["text"]
    # lunch $15 * 0.4 potluck = $6/person * 20 = $120
    assert "120.00" in text


@pytest.mark.asyncio
async def test_estimate_food_cost_breakfast():
    args = {"meal_type": "breakfast", "guest_count": 10, "service_style": "self"}
    result = await estimate_food_cost.handler(args)
    text = result["content"][0]["text"]
    # breakfast $8 * 1.0 self = $8/person * 10 = $80
    assert "80.00" in text


def test_menu_agent_card():
    agent = MenuPlannerAgent()
    card = agent.get_agent_card()
    assert card.name == "menu"
    assert card.url == "http://menu:8004"
    assert len(card.skills) >= 1


def test_menu_agent_mcp_tools():
    agent = MenuPlannerAgent()
    tools = agent.get_mcp_tools()
    assert len(tools) == 1


def test_menu_agent_fastapi_app():
    agent = MenuPlannerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
