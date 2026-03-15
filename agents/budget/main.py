"""FastAPI server for the Budget Manager agent."""
import uvicorn
from agents.budget.agent import BudgetManagerAgent

agent = BudgetManagerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
