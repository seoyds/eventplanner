"""Conductor orchestration logic using claude-agent-sdk.

Uses stateless query() with full conversation history in each call.
The system prompt instructs Claude to discover agents, propose a plan,
and execute on confirmation — all based on conversation context.
"""
from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
from conductor.tools.a2a_tools import AGENT_TOOLS

CONDUCTOR_SYSTEM_PROMPT = """You are the Event Orchestrator Conductor. You dynamically
discover and coordinate specialist agents to plan events.

## Your Process

### Phase 1: Understand & Discover (first user message)
1. Analyze the user's request to understand what they need
2. Use the `discover_agents` tool to find available specialist agents in the registry
3. Match the user's needs against available agent capabilities
4. Propose a workflow: list agents, organize into waves, explain why
5. Ask "Shall I proceed?"

### Phase 2: Execute (after user confirms)
When the conversation history shows you already proposed a plan AND the user confirmed:
1. DO NOT re-discover agents or re-propose — go straight to execution
2. Execute the workflow wave by wave using `call_agent`
3. Pass results from earlier agents as context to later agents
4. After each wave, use `check_budget` if a budget was specified
5. Compile all results into a comprehensive Event Blueprint

## Tools Available
- `discover_agents`: Query the NANDA registry. Pass query="all" to list everything.
- `call_agent`: Call an agent by ID. Pass requirements and context as JSON strings.
- `check_budget`: Validate total costs against a budget limit.

## Important Rules
- ALWAYS discover agents first on a new request
- ALWAYS propose and get confirmation before executing
- If no suitable agents exist, tell the user clearly
- When executing, pass results from earlier agents as context to later ones
"""


async def run_orchestrator(conversation: list[dict]):
    """Run the conductor using stateless query() with full conversation.

    Args:
        conversation: List of {"role": "user"|"assistant", "content": "..."} dicts

    Yields SDK messages for streaming to the frontend.
    """
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

    prompt = _build_prompt(conversation)

    async for message in query(prompt=prompt, options=options):
        yield message


def _build_prompt(conversation: list[dict]) -> str:
    """Build prompt from conversation history."""
    if not conversation:
        return ""

    if len(conversation) == 1:
        return conversation[0].get("content", "")

    # Multi-turn: include full history so Claude knows what it proposed
    parts = []
    for msg in conversation:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"[USER]: {content}")
        elif role == "assistant":
            parts.append(f"[ASSISTANT (you said this earlier)]: {content}")

    # Detect confirmation
    last_user = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user = msg.get("content", "").strip().lower()
            break

    confirms = ["yes", "proceed", "go ahead", "confirm", "do it", "ok", "sure", "start", "approved"]
    if any(w in last_user for w in confirms):
        parts.append(
            "\n[SYSTEM INSTRUCTION]: The user confirmed your proposed plan above. "
            "Execute it NOW. Call the agents in the waves you proposed using the `call_agent` tool. "
            "Do NOT re-discover agents. Do NOT re-propose the plan. Start executing Wave 1 immediately."
        )

    return "\n\n".join(parts)
