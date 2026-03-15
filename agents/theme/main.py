"""FastAPI server for the Theme Designer agent."""
import uvicorn
from agents.theme.agent import ThemeDesignerAgent

agent = ThemeDesignerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
