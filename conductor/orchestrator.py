"""Conductor orchestration logic using ClaudeSDKClient for persistent sessions.

Uses ClaudeSDKClient instead of the stateless query() function, so that
conversation context (including tool results from discover_agents) is
preserved across turns. One client per thread_id.
"""
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_sdk_mcp_server
from conductor.tools.a2a_tools import AGENT_TOOLS

CONDUCTOR_SYSTEM_PROMPT = """You are the Event Orchestrator Conductor. You dynamically
discover and coordinate specialist agents to plan events.

## Your Process

### Phase 1: Understand & Discover
1. Analyze the user's request to understand what they need
2. Use the `discover_agents` tool to find available specialist agents in the registry
3. Match the user's needs against available agent capabilities

### Phase 2: Propose Workflow
Based on available agents and the user's needs, propose a workflow:
- List which agents you plan to use and why
- Organize them into waves (agents with no dependencies run first, then agents that need prior results)
- If some aspects of the request CANNOT be fulfilled by any available agent, clearly state this
- If NO suitable agents exist for the request, tell the user: "I don't currently have agents that can help with [X]."

Present the workflow plan to the user and ask for confirmation before executing.
Example: "Here's my plan: [workflow]. Shall I proceed?"

### Phase 3: Execute (only after user confirms)
Once the user confirms (says yes, go ahead, proceed, confirm, etc.):
1. Execute the workflow wave by wave
2. Use `call_agent` with the agent_id, requirements (JSON), and context from previous agents (JSON)
3. After each wave, use `check_budget` if a budget was specified
4. Compile all results into a comprehensive Event Blueprint

## Tools Available
- `discover_agents`: Query the NANDA registry for available agents. Pass query="all" to list everything.
- `call_agent`: Call a specific agent by its agent_id. Pass requirements and context as JSON strings.
- `check_budget`: Validate total costs against a budget limit.

## Important Rules
- ALWAYS discover agents first — never assume what agents are available
- ALWAYS propose and get confirmation before executing
- If the user's request doesn't match any available agent capabilities, say so clearly
- Pass results from earlier agents as context to later agents
- Respect dependencies: some agents need results from others before they can work
"""

# Store active clients by thread_id
_active_clients: dict[str, ClaudeSDKClient] = {}


def _create_client() -> ClaudeSDKClient:
    """Create a new ClaudeSDKClient with conductor tools."""
    conductor_tools = create_sdk_mcp_server(
        name="conductor-tools",
        tools=AGENT_TOOLS,
    )

    allowed = [f"mcp__conductor-tools__{t.name}" for t in AGENT_TOOLS]

    options = ClaudeAgentOptions(
        system_prompt=CONDUCTOR_SYSTEM_PROMPT,
        mcp_servers={"conductor-tools": conductor_tools},
        allowed_tools=allowed + ["WebSearch"],
        max_turns=30,
        permission_mode="acceptEdits",
    )

    return ClaudeSDKClient(options=options)


async def get_or_create_client(thread_id: str) -> tuple[ClaudeSDKClient, bool]:
    """Get an existing client for a thread or create a new one.

    Returns (client, is_new) tuple.
    """
    if thread_id in _active_clients:
        return _active_clients[thread_id], False

    client = _create_client()
    await client.connect()
    _active_clients[thread_id] = client
    return client, True


async def run_orchestrator(thread_id: str, user_message: str):
    """Run the conductor using a persistent ClaudeSDKClient session.

    The client maintains conversation context across turns, so when
    the user confirms a plan, Claude already knows what was proposed.

    Args:
        thread_id: Thread identifier for session persistence
        user_message: The latest user message

    Yields SDK messages for streaming to the frontend.
    """
    client, is_new = await get_or_create_client(thread_id)
    print(f"[conductor] thread={thread_id} is_new={is_new} active_clients={list(_active_clients.keys())}", flush=True)

    # Send the user's message — Claude remembers prior context
    await client.query(user_message, session_id=thread_id)

    # Stream responses
    async for message in client.receive_messages():
        yield message


async def cleanup_client(thread_id: str):
    """Disconnect and remove a client for a thread."""
    if thread_id in _active_clients:
        client = _active_clients.pop(thread_id)
        try:
            client.disconnect()
        except Exception:
            pass
