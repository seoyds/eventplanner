"""FastAPI server for the Accessibility Checker agent."""
import uvicorn
from agents.accessibility.agent import AccessibilityCheckerAgent

agent = AccessibilityCheckerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
