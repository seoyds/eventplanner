"""FastAPI server with AG-UI SSE endpoint for the Conductor."""
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StateSnapshotEvent,
)
from ag_ui.encoder import EventEncoder
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock

from conductor.orchestrator import run_orchestrator

app = FastAPI(title="Event Orchestrator Conductor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ag-ui/info")
async def ag_ui_info():
    """CopilotKit runtime info endpoint for agent discovery."""
    return {
        "agents": [
            {
                "name": "default",
                "description": "Event Orchestrator Conductor",
            }
        ],
    }


@app.post("/ag-ui")
async def ag_ui_endpoint(request: Request):
    """AG-UI endpoint. CopilotKit sends messages here. Returns SSE stream.

    CopilotKit wraps the payload in {"method", "params", "body"}.
    We extract "body" and parse it as RunAgentInput.
    """
    accept_header = request.headers.get("accept")
    raw = await request.json()

    # Handle CopilotKit RPC methods that aren't agent/run
    method = raw.get("method", "")
    if method in ("getInfo", "agent/info"):
        return JSONResponse({
            "agents": [
                {
                    "name": "default",
                    "description": "Event Orchestrator Conductor",
                }
            ],
        })

    # CopilotKit envelope: unwrap "body" if present
    body = raw.get("body", raw)
    input_data = RunAgentInput(**body)

    # Extract the latest user message (client maintains conversation state)
    user_message = ""
    for msg in reversed(input_data.messages):
        if msg.role == "user":
            if hasattr(msg, "content") and msg.content:
                if isinstance(msg.content, str):
                    user_message = msg.content
                elif isinstance(msg.content, list) and msg.content:
                    first = msg.content[0]
                    user_message = first.text if hasattr(first, "text") else str(first)
                else:
                    user_message = str(msg.content)
            break

    thread_id = input_data.thread_id

    async def event_stream():
        encoder = EventEncoder(accept=accept_header)
        msg_id = str(uuid.uuid4())

        yield encoder.encode(
            RunStartedEvent(
                type=EventType.RUN_STARTED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )
        yield encoder.encode(
            TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant",
            )
        )

        # Track agents currently running — mark completed when next message arrives
        running_agents: list[str] = []

        async for sdk_message in run_orchestrator(thread_id, user_message):
            if isinstance(sdk_message, AssistantMessage):
                # Mark previously running agents as completed
                for agent_name in running_agents:
                    yield encoder.encode(
                        StateSnapshotEvent(
                            type=EventType.STATE_SNAPSHOT,
                            snapshot={"agent_statuses": {agent_name: "completed"}},
                        )
                    )
                running_agents.clear()

                for block in sdk_message.content:
                    if isinstance(block, TextBlock):
                        yield encoder.encode(
                            TextMessageContentEvent(
                                type=EventType.TEXT_MESSAGE_CONTENT,
                                message_id=msg_id,
                                delta=block.text,
                            )
                        )
                    elif isinstance(block, ToolUseBlock):
                        tool_name = block.name
                        # Generic call_agent tool — extract agent_id from the input
                        if tool_name.endswith("call_agent"):
                            try:
                                agent_id = block.input.get("agent_id", "unknown") if hasattr(block, "input") else "unknown"
                            except Exception:
                                agent_id = "unknown"
                            running_agents.append(agent_id)
                            yield encoder.encode(
                                StateSnapshotEvent(
                                    type=EventType.STATE_SNAPSHOT,
                                    snapshot={"agent_statuses": {agent_id: "running"}},
                                )
                            )
            elif isinstance(sdk_message, ResultMessage):
                # Final message — mark any remaining agents as completed
                for agent_name in running_agents:
                    yield encoder.encode(
                        StateSnapshotEvent(
                            type=EventType.STATE_SNAPSHOT,
                            snapshot={"agent_statuses": {agent_name: "completed"}},
                        )
                    )
                running_agents.clear()

        yield encoder.encode(
            TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id,
            )
        )
        yield encoder.encode(
            RunFinishedEvent(
                type=EventType.RUN_FINISHED,
                thread_id=input_data.thread_id,
                run_id=input_data.run_id,
            )
        )

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
