"""FastAPI server with AG-UI SSE endpoint for the Conductor.

Streams both AG-UI text events and A2UI surface events for rich UI rendering.
"""
import asyncio
import json
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

from conductor.orchestrator import run_orchestrator, TextEvent, AgentStatusEvent, A2UIEvent
from conductor.a2ui_builder import build_a2ui_surface

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
                    elif isinstance(event, A2UIEvent):
                        await event_queue.put(_encode_a2ui_event(encoder, event.messages))
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


def _try_build_a2ui(agent_id: str, result_data: dict) -> list[dict] | None:
    """Try to build A2UI surface from an agent's result data."""
    try:
        # The result may be nested in A2A task wrapper
        agent_result = None
        if isinstance(result_data, dict):
            status = result_data.get("status", {})
            message = status.get("message", {}) if isinstance(status, dict) else {}
            parts = message.get("parts", []) if isinstance(message, dict) else []
            if parts:
                for part in parts:
                    if isinstance(part, dict) and part.get("kind") == "text":
                        try:
                            agent_result = json.loads(part["text"])
                        except (json.JSONDecodeError, KeyError):
                            pass

            if not agent_result:
                artifacts = result_data.get("artifacts", [])
                if isinstance(artifacts, list):
                    for artifact in artifacts:
                        a_parts = artifact.get("parts", []) if isinstance(artifact, dict) else []
                        for part in a_parts:
                            if isinstance(part, dict) and part.get("kind") == "text":
                                try:
                                    agent_result = json.loads(part["text"])
                                except (json.JSONDecodeError, KeyError):
                                    pass

            if not agent_result and "result" in result_data:
                agent_result = result_data
            elif not agent_result:
                agent_result = {"result": result_data, "status": "completed"}

        if agent_result:
            return build_a2ui_surface(agent_id, agent_result)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return None


def _encode_a2ui_event(encoder: EventEncoder, a2ui_messages: list[dict]) -> str:
    """Encode A2UI messages as a custom SSE event."""
    return encoder.encode(
        StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={"a2ui_messages": a2ui_messages},
        )
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, timeout_keep_alive=600)
