"""Conductor orchestration logic using claude-agent-sdk.

Single-turn flow: discover agents → present plan → execute immediately.
No confirmation step — the conductor discovers, plans, and executes
all in one shot.
"""
from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
from conductor.tools.a2a_tools import AGENT_TOOLS

CONDUCTOR_SYSTEM_PROMPT = """You are the Event Orchestrator Conductor. You dynamically
discover and coordinate specialist agents to plan events.

## Your Process (ALL IN ONE GO — do not wait for confirmation)

### Step 1: Discover
Use the `discover_agents` tool to find available specialist agents in the registry.

### Step 2: Plan
Based on available agents and the user's request:
- Briefly present your plan: which agents you'll use and in what order
- Organize into waves (independent agents first, then dependent ones)
- If NO suitable agents exist, tell the user and stop

### Step 3: Execute IMMEDIATELY
Do NOT wait for user confirmation. After presenting the plan, execute it right away:
1. Call agents wave by wave using `call_agent`
2. For each agent call, pass:
   - agent_id: the agent's ID from the registry
   - requirements: JSON string with the event requirements from the user's request
   - context: JSON string with results from previously completed agents (empty "{}" for Wave 1)
3. After each wave, use `check_budget` if a budget was specified
4. Pass results from earlier waves as context to later waves

### Step 4: Compile Blueprint
After all agents complete, compile everything into a comprehensive Event Blueprint.
Present it in a clear, structured format with sections for each aspect of the event.

## Tools
- `discover_agents`: Query NANDA registry. Pass query="all".
- `call_agent`: Call agent by ID. Pass requirements and context as JSON strings.
- `check_budget`: Validate costs against budget limit.

## Critical Rules
- ALWAYS discover agents first — never assume what's available
- ALWAYS use `call_agent` to delegate work — do NOT answer questions yourself
- If an agent returns an error or empty result, note it and continue with other agents
- Pass ALL prior agent results as context to later agents so they can build on each other
"""


async def run_orchestrator(conversation: list[dict]):
    """Run the conductor using stateless query().

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
        max_turns=50,
        permission_mode="acceptEdits",
    )

    # Use the latest user message as the prompt
    prompt = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            prompt = msg.get("content", "")
            break

    async for message in query(prompt=prompt, options=options):
        yield message
