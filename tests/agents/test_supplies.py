"""Tests for supplies agent tools and agent class."""
import pytest
from agents.supplies.tools import estimate_supply_cost
from agents.supplies.agent import SuppliesEstimatorAgent


@pytest.mark.asyncio
async def test_estimate_supply_cost_decoration():
    args = {"supply_type": "decoration", "quantity": 10, "unit_override": 0.0}
    result = await estimate_supply_cost.handler(args)
    text = result["content"][0]["text"]
    # $3 * 10 = $30
    assert "30.00" in text
    assert "decoration" in text


@pytest.mark.asyncio
async def test_estimate_supply_cost_favor():
    args = {"supply_type": "favor", "quantity": 40, "unit_override": 0.0}
    result = await estimate_supply_cost.handler(args)
    text = result["content"][0]["text"]
    # $5 * 40 = $200
    assert "200.00" in text


@pytest.mark.asyncio
async def test_estimate_supply_cost_custom_price():
    args = {"supply_type": "rental", "quantity": 5, "unit_override": 25.0}
    result = await estimate_supply_cost.handler(args)
    text = result["content"][0]["text"]
    # $25 * 5 = $125
    assert "125.00" in text
    assert "custom price" in text


def test_supplies_agent_card():
    agent = SuppliesEstimatorAgent()
    card = agent.get_agent_card()
    assert card.name == "supplies"
    assert card.url == "http://supplies:8010"
    assert len(card.skills) >= 1


def test_supplies_agent_mcp_tools():
    agent = SuppliesEstimatorAgent()
    tools = agent.get_mcp_tools()
    assert len(tools) == 1


def test_supplies_agent_fastapi_app():
    agent = SuppliesEstimatorAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
