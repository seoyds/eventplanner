"""FastAPI server for the Supplies Estimator agent."""
import uvicorn
from agents.supplies.agent import SuppliesEstimatorAgent

agent = SuppliesEstimatorAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
