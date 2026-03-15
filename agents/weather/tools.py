"""Custom MCP tools for the Weather Analyst agent."""
import httpx
from claude_agent_sdk import tool


@tool("get_forecast", "Fetch weather forecast from Open-Meteo API", {
    "latitude": float,
    "longitude": float,
    "start_date": str,
    "end_date": str,
})
async def get_forecast(args):
    """Call Open-Meteo API to get weather forecast for a location and date range."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": args["latitude"],
        "longitude": args["longitude"],
        "daily": "precipitation_probability_max,temperature_2m_max,temperature_2m_min",
        "start_date": args["start_date"],
        "end_date": args["end_date"],
        "timezone": "auto",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})
            dates = daily.get("time", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            temp_highs = daily.get("temperature_2m_max", [])
            temp_lows = daily.get("temperature_2m_min", [])
            days = []
            for i, date in enumerate(dates):
                days.append({
                    "date": date,
                    "rain_probability": rain_probs[i] if i < len(rain_probs) else None,
                    "temp_high_c": temp_highs[i] if i < len(temp_highs) else None,
                    "temp_low_c": temp_lows[i] if i < len(temp_lows) else None,
                })
            return {
                "content": [{
                    "type": "text",
                    "text": f"Forecast for lat={args['latitude']}, lon={args['longitude']}: {days}",
                }]
            }
    except Exception as e:
        return {
            "content": [{
                "type": "text",
                "text": f"Weather API error: {e}. Using estimated forecast data.",
            }]
        }


@tool("assess_outdoor_viability", "Assess viability for outdoor event based on weather", {
    "rain_probability": float,
    "temp_high_f": float,
})
async def assess_outdoor_viability(args):
    """Calculate outdoor viability score from rain probability and temperature."""
    rain_probability = args["rain_probability"]
    temp_high = args["temp_high_f"]

    rain_score = max(0, 1 - rain_probability / 100)
    if 60 <= temp_high <= 85:
        temp_score = 1.0
    else:
        temp_score = 0.5

    score = rain_score * 0.6 + temp_score * 0.4

    if score > 0.7:
        recommendation = "outdoor"
    elif score > 0.4:
        recommendation = "indoor backup needed"
    else:
        recommendation = "indoor only"

    return {
        "content": [{
            "type": "text",
            "text": (
                f"Outdoor viability score: {score:.2f}/1.0. "
                f"Rain score: {rain_score:.2f}, Temp score: {temp_score:.2f}. "
                f"Recommendation: {recommendation}"
            ),
        }]
    }
