"""Tests for weather agent tools and agent class."""
import pytest
from agents.weather.tools import assess_outdoor_viability
from agents.weather.agent import WeatherAnalystAgent


@pytest.mark.asyncio
async def test_assess_outdoor_viability_great_conditions():
    args = {"rain_probability": 10.0, "temp_high_f": 75.0}
    result = await assess_outdoor_viability.handler(args)
    assert "content" in result
    text = result["content"][0]["text"]
    assert "outdoor" in text
    assert "0." in text


@pytest.mark.asyncio
async def test_assess_outdoor_viability_bad_conditions():
    args = {"rain_probability": 90.0, "temp_high_f": 95.0}
    result = await assess_outdoor_viability.handler(args)
    text = result["content"][0]["text"]
    assert "indoor" in text


@pytest.mark.asyncio
async def test_assess_outdoor_viability_marginal():
    args = {"rain_probability": 50.0, "temp_high_f": 70.0}
    result = await assess_outdoor_viability.handler(args)
    text = result["content"][0]["text"]
    assert "score" in text.lower() or "viability" in text.lower()


def test_weather_agent_card():
    agent = WeatherAnalystAgent()
    card = agent.get_agent_card()
    assert card.name == "weather"
    assert "weather" in card.description.lower()
    assert card.url == "http://weather:8002"
    assert len(card.skills) >= 1


def test_weather_agent_mcp_tools():
    agent = WeatherAnalystAgent()
    tools = agent.get_mcp_tools()
    assert len(tools) == 2


def test_weather_agent_fastapi_app():
    agent = WeatherAnalystAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
