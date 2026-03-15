"""Conductor orchestration logic using claude-agent-sdk.

The conductor dynamically discovers agents from the NANDA registry,
plans a workflow based on the user's request, gets confirmation,
then executes.
"""
from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
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


async def run_orchestrator(conversation: list[dict]):
    """Run the conductor using claude-agent-sdk.

    Args:
        conversation: List of message dicts with 'role' and 'content' keys,
                      representing the full conversation history.

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

    # Build prompt from conversation history
    prompt = _build_conversation_prompt(conversation)

    async for message in query(prompt=prompt, options=options):
        yield message


def _build_conversation_prompt(conversation: list[dict]) -> str:
    """Build a prompt string from the conversation history.

    For single messages, just return the content.
    For multi-turn, include the full conversation so Claude understands
    what was already proposed and can act on confirmations.
    """
    if not conversation:
        return ""

    if len(conversation) == 1:
        return conversation[0].get("content", "")

    # Multi-turn: format as explicit conversation transcript
    parts = ["## Conversation History\n"]
    for msg in conversation:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            parts.append(f"**User:** {content}")
        elif role == "assistant":
            parts.append(f"**You (Assistant) previously said:** {content}")

    # Check if the last user message looks like a confirmation
    last_user = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            last_user = msg.get("content", "").strip().lower()
            break

    confirmation_words = ["yes", "proceed", "go ahead", "confirm", "do it", "ok", "sure", "let's go", "approved", "go", "start"]
    is_confirmation = any(word in last_user for word in confirmation_words)

    if is_confirmation:
        parts.append(
            "\n## IMPORTANT INSTRUCTION\n"
            "The user has confirmed the plan you proposed above. "
            "Do NOT ask what event to plan — you already know from the conversation history. "
            "Do NOT re-discover agents — you already proposed which agents to use. "
            "EXECUTE THE PLAN NOW by calling the agents in the waves you proposed. "
            "Start with Wave 1 immediately using the `call_agent` tool."
        )
    else:
        parts.append(
            "\n## Instruction\n"
            "Continue the conversation naturally based on the history above."
        )

    return "\n\n".join(parts)
