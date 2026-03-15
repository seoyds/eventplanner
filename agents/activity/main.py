"""FastAPI server for the Activity Coordinator agent."""
import uvicorn
from agents.activity.agent import ActivityCoordinatorAgent

agent = ActivityCoordinatorAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
