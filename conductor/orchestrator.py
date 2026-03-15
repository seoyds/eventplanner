"""Conductor orchestration logic using claude-agent-sdk."""
from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
from conductor.tools.a2a_tools import AGENT_TOOLS

CONDUCTOR_SYSTEM_PROMPT = """You are the Event Orchestrator Conductor. You coordinate
a team of specialist agents to plan events.

## Available Agent Tools
You have tools to call each specialist agent. Each returns structured JSON results.

## Execution Strategy
Execute agents in 3 waves to respect dependencies:

WAVE 1 (call these — they have no dependencies):
- call_venue_agent: Find venues matching location/capacity
- call_weather_agent: Get weather forecasts for the dates
- call_theme_agent: Design the event aesthetic
- call_menu_agent: Plan meals respecting dietary needs

WAVE 2 (these need Wave 1 results as context):
- call_accessibility_agent: Audit venues and activities for accessibility
- call_activity_agent: Plan entertainment and activities
- call_budget_agent: Tally all costs, flag overages

WAVE 3 (these need Wave 1 + 2 results):
- call_logistics_agent: Create day-of timeline
- call_communication_agent: Draft invitations
- call_supplies_agent: Build shopping list

## Budget Enforcement
After each wave, use check_budget to validate costs. If over budget:
1. Identify the most expensive categories
2. Re-call those agents with tighter budget constraints
3. Do NOT proceed to the next wave until budget is resolved

## Final Output
After all waves complete, compile a comprehensive Event Blueprint."""


async def run_orchestrator(user_message: str):
    """Run the conductor using claude-agent-sdk. Yields SDK messages."""
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

    async for message in query(prompt=user_message, options=options):
        yield message
