"""Weather Analyst agent."""
from shared.agent_base import BaseEventAgent
from agents.weather.tools import get_forecast, assess_outdoor_viability


class WeatherAnalystAgent(BaseEventAgent):
    agent_id = "weather"
    name = "Weather Analyst"
    description = "Analyzes weather forecasts and assesses outdoor event viability"
    port = 8002

    system_prompt = """You are an expert weather analyst for event planning. Your job is to
assess weather conditions for an event date and location and advise on indoor/outdoor suitability.

PROCESS:
1. Use get_forecast to retrieve weather data for the event location and dates
2. Use assess_outdoor_viability to score the conditions
3. Provide a clear recommendation

OUTPUT FORMAT (JSON):
{
    "result": {
        "forecast": {
            "date": "YYYY-MM-DD",
            "rain_probability": 20,
            "temp_high_f": 75,
            "temp_low_f": 60
        },
        "viability_score": 0.85,
        "recommendation": "outdoor",
        "notes": "Conditions look great for an outdoor event"
    },
    "estimated_cost": 0,
    "warnings": []
}"""

    def get_skills(self):
        return [
            {
                "id": "weather-forecast",
                "name": "Weather Forecast",
                "description": "Retrieve weather forecast for event location and dates",
                "tags": ["weather", "forecast", "outdoor"],
                "examples": ["What's the weather in Denver on July 4th?"],
            },
            {
                "id": "outdoor-viability",
                "name": "Outdoor Viability Assessment",
                "description": "Assess whether weather conditions support an outdoor event",
                "tags": ["weather", "outdoor", "viability"],
                "examples": ["Is July 4th good for an outdoor party in Denver?"],
            },
        ]

    def get_mcp_tools(self):
        return [get_forecast, assess_outdoor_viability]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__weather__get_forecast",
            "mcp__weather__assess_outdoor_viability",
        ]
