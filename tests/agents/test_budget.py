"""Tests for budget agent tools and agent class."""
import pytest
from agents.budget.tools import calculate_budget, suggest_cost_reduction
from agents.budget.agent import BudgetManagerAgent


@pytest.mark.asyncio
async def test_calculate_budget_within_limit():
    args = {
        "line_items": '[{"name": "Catering", "cost": 500}, {"name": "Venue", "cost": 300}]',
        "budget_limit": 1000.0,
    }
    result = await calculate_budget.handler(args)
    text = result["content"][0]["text"]
    assert "800.00" in text
    assert "within budget" in text


@pytest.mark.asyncio
async def test_calculate_budget_over_limit():
    args = {
        "line_items": '[{"name": "Catering", "cost": 800}, {"name": "Venue", "cost": 500}]',
        "budget_limit": 1000.0,
    }
    result = await calculate_budget.handler(args)
    text = result["content"][0]["text"]
    assert "OVER BUDGET" in text


@pytest.mark.asyncio
async def test_suggest_cost_reduction_needed():
    args = {
        "total_cost": 1500.0,
        "budget_limit": 1000.0,
        "line_items": '[{"name": "Catering", "cost": 800}, {"name": "DJ", "cost": 400}, {"name": "Flowers", "cost": 300}]',
    }
    result = await suggest_cost_reduction.handler(args)
    text = result["content"][0]["text"]
    assert "500.00" in text
    assert "suggestion" in text.lower() or "reduce" in text.lower()


@pytest.mark.asyncio
async def test_suggest_cost_reduction_not_needed():
    args = {
        "total_cost": 800.0,
        "budget_limit": 1000.0,
        "line_items": '[{"name": "Catering", "cost": 800}]',
    }
    result = await suggest_cost_reduction.handler(args)
    text = result["content"][0]["text"]
    assert "No cost reduction needed" in text


def test_budget_agent_card():
    agent = BudgetManagerAgent()
    card = agent.get_agent_card()
    assert card.name == "budget"
    assert card.url == "http://budget:8003"
    assert len(card.skills) >= 1


def test_budget_agent_fastapi_app():
    agent = BudgetManagerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
