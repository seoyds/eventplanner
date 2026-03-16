"""FastAPI server with AG-UI SSE endpoint for the Conductor.

Streams both AG-UI text events and A2UI surface events for rich UI rendering.
"""
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
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock

from conductor.orchestrator import run_orchestrator
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

        # Track agents currently running — mark completed when next message arrives
        running_agents: list[str] = []
        # Track pending tool use IDs to match with tool results for A2UI
        pending_agent_calls: dict[str, str] = {}  # tool_use_id -> agent_id

        async for sdk_message in run_orchestrator(conversation):
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
                            # Track this tool use for A2UI rendering on result
                            if hasattr(block, "id"):
                                pending_agent_calls[block.id] = agent_id
                            yield encoder.encode(
                                StateSnapshotEvent(
                                    type=EventType.STATE_SNAPSHOT,
                                    snapshot={"agent_statuses": {agent_id: "running"}},
                                )
                            )
                    elif isinstance(block, ToolResultBlock):
                        # When an agent call returns, build A2UI surface from the result
                        tool_use_id = getattr(block, "tool_use_id", None)
                        if tool_use_id and tool_use_id in pending_agent_calls:
                            agent_id = pending_agent_calls.pop(tool_use_id)
                            a2ui_messages = _extract_a2ui_from_tool_result(agent_id, block)
                            if a2ui_messages:
                                yield _encode_a2ui_event(encoder, a2ui_messages)

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


def _extract_a2ui_from_tool_result(agent_id: str, block: ToolResultBlock) -> list[dict] | None:
    """Try to parse an agent result from a tool result block and build A2UI surface."""
    try:
        text = ""
        if hasattr(block, "content"):
            if isinstance(block.content, str):
                text = block.content
            elif isinstance(block.content, list) and block.content:
                first = block.content[0]
                text = first.text if hasattr(first, "text") else str(first)
        if not text:
            return None

        data = json.loads(text)
        # call_agent returns {"agent_id": ..., "result": {...}}
        result_data = data.get("result", data)

        # The A2A result may be nested — dig into artifacts for the agent result JSON
        agent_result = None
        if isinstance(result_data, dict):
            # Check for A2A task wrapper: result.status.message.parts[0].text
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

            # Also check artifacts
            if not agent_result:
                artifacts = result_data.get("artifacts", [])
                if isinstance(artifacts, list):
                    for artifact in artifacts:
                        parts = artifact.get("parts", []) if isinstance(artifact, dict) else []
                        for part in parts:
                            if isinstance(part, dict) and part.get("kind") == "text":
                                try:
                                    agent_result = json.loads(part["text"])
                                except (json.JSONDecodeError, KeyError):
                                    pass

            # Fallback: the result itself might be the agent result
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
    """Encode A2UI messages as a custom SSE event.

    Uses STATE_SNAPSHOT event type with an 'a2ui' key in the snapshot
    so the frontend can detect and process A2UI surfaces.
    """
    return encoder.encode(
        StateSnapshotEvent(
            type=EventType.STATE_SNAPSHOT,
            snapshot={"a2ui_messages": a2ui_messages},
        )
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
