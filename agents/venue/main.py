"""FastAPI server for the Venue & Destination Planner agent."""
import uvicorn
from agents.venue.agent import VenuePlannerAgent

agent = VenuePlannerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
