"""FastAPI server for the Menu & Catering Planner agent."""
import uvicorn
from agents.menu.agent import MenuPlannerAgent

agent = MenuPlannerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
