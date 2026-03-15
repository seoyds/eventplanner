"""FastAPI server for the Logistics Coordinator agent."""
import uvicorn
from agents.logistics.agent import LogisticsCoordinatorAgent

agent = LogisticsCoordinatorAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
