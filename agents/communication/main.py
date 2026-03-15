"""FastAPI server for the Communication Writer agent."""
import uvicorn
from agents.communication.agent import CommunicationWriterAgent

agent = CommunicationWriterAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
