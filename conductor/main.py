"""FastAPI server with AG-UI SSE endpoint for the Conductor."""
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from conductor.orchestrator import run_orchestrator

app = FastAPI(title="Event Orchestrator Conductor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ag-ui")
async def ag_ui_endpoint(request: Request):
    """AG-UI endpoint. CopilotKit sends messages here. Returns SSE stream.

    CopilotKit wraps the payload in {"method", "params", "body"}.
    We extract "body" and parse it as RunAgentInput.
    """
    accept_header = request.headers.get("accept")
    raw = await request.json()

    # CopilotKit envelope: unwrap "body" if present
    body = raw.get("body", raw)
    input_data = RunAgentInput(**body)

    user_message = ""
    for msg in reversed(input_data.messages):
        if msg.role == "user":
            if msg.content:
                # content can be a string or list of content blocks
                if isinstance(msg.content, str):
                    user_message = msg.content
                elif isinstance(msg.content, list) and msg.content:
                    first = msg.content[0]
                    user_message = first.text if hasattr(first, "text") else str(first)
                else:
                    user_message = str(msg.content)
            break

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

        async for sdk_message in run_orchestrator(user_message):
            if isinstance(sdk_message, AssistantMessage):
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
                        if "call_" in tool_name and "_agent" in tool_name:
                            agent_name = tool_name.split("call_")[-1].replace("_agent", "")
                            yield encoder.encode(
                                StateSnapshotEvent(
                                    type=EventType.STATE_SNAPSHOT,
                                    snapshot={"agent_statuses": {agent_name: "running"}},
                                )
                            )
            elif isinstance(sdk_message, ResultMessage):
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=f"\n\n{sdk_message.result}",
                    )
                )

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
