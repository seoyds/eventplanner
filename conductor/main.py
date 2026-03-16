"""FastAPI server with AG-UI SSE endpoint for the Conductor."""
import asyncio
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

from conductor.orchestrator import run_orchestrator, TextEvent, AgentStatusEvent

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
    """AG-UI endpoint. CopilotKit sends messages here. Returns SSE stream."""
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

    # Build full conversation history for the orchestrator
    conversation = []
    for msg in input_data.messages:
        content = ""
        if hasattr(msg, "content") and msg.content:
            if isinstance(msg.content, str):
                content = msg.content
            elif isinstance(msg.content, list) and msg.content:
                first = msg.content[0]
                content = first.text if hasattr(first, "text") else str(first)
            else:
                content = str(msg.content)
        if content:
            conversation.append({"role": msg.role, "content": content})

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

        # Use an async queue to interleave orchestrator events with keepalives
        event_queue: asyncio.Queue[str | None] = asyncio.Queue()

        async def orchestrator_producer():
            """Run the orchestrator and push encoded events into the queue."""
            try:
                async for event in run_orchestrator(conversation):
                    if isinstance(event, TextEvent):
                        await event_queue.put(encoder.encode(
                            TextMessageContentEvent(
                                type=EventType.TEXT_MESSAGE_CONTENT,
                                message_id=msg_id,
                                delta=event.text,
                            )
                        ))
                    elif isinstance(event, AgentStatusEvent):
                        await event_queue.put(encoder.encode(
                            StateSnapshotEvent(
                                type=EventType.STATE_SNAPSHOT,
                                snapshot={"agent_statuses": {event.agent_id: event.status}},
                            )
                        ))
            except Exception as e:
                await event_queue.put(encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=f"\n\n**Error:** {type(e).__name__}: {e}",
                    )
                ))
            finally:
                await event_queue.put(None)

        # Start the orchestrator in a background task
        producer_task = asyncio.create_task(orchestrator_producer())

        # Consume events from the queue, sending keepalives during idle periods
        try:
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=5)
                except asyncio.TimeoutError:
                    # No event for 5s — send SSE keepalive to prevent connection drop
                    yield ": keepalive\n\n"
                    continue

                if event is None:
                    break
                yield event
        finally:
            producer_task.cancel()
            try:
                await producer_task
            except asyncio.CancelledError:
                pass

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
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=600)
