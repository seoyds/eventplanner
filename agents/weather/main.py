"""FastAPI server for the Weather Analyst agent."""
import uvicorn
from agents.weather.agent import WeatherAnalystAgent

agent = WeatherAnalystAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
