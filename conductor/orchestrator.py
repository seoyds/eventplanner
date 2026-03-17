"""Conductor orchestration logic.

Multi-phase flow that keeps each Claude SDK session short to avoid
CLI subprocess timeout (CLIConnectionError).

Phase 1: Short query() — discover agents, generate plan text
Phase 2: Direct httpx calls — call each agent via A2A (parallel per wave)
Phase 3: Short query() — compile results into final blueprint
"""
import asyncio
import json
import httpx
from dataclasses import dataclass

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock
from shared.nanda_registry import NandaRegistryClient


@dataclass
class TextEvent:
    """A chunk of text to stream to the frontend."""
    text: str


@dataclass
class AgentStatusEvent:
    """An agent status change to stream to the frontend."""
    agent_id: str
    status: str  # "running", "completed", "error"


# Agents that can run independently (Wave 1) vs those needing prior context (Wave 2/3)
WAVE_1 = ["theme", "venue", "menu", "weather", "activity", "supplies"]
WAVE_2 = ["accessibility", "logistics", "communication"]
WAVE_3 = ["budget"]


async def _discover_agents() -> dict[str, dict]:
    """Discover agents from NANDA registry and fetch their cards."""
    nanda = NandaRegistryClient()
    agents = await nanda.list_agents()
    if not agents:
        return {}

    details = {}
    for agent_id, agent_url in agents.items():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{agent_url}/.well-known/agent.json")
                if resp.status_code == 200:
                    card = resp.json()
                    details[agent_id] = {
                        "url": agent_url,
                        "name": card.get("name", agent_id),
                        "description": card.get("description", ""),
                    }
                else:
                    details[agent_id] = {"url": agent_url, "name": agent_id, "description": ""}
        except Exception:
            details[agent_id] = {"url": agent_url, "name": agent_id, "description": "unreachable"}
    return details


async def _call_agent(agent_url: str, agent_id: str, requirements: dict, context: dict) -> dict:
    """Call a specialist agent via A2A protocol (direct httpx, no SDK)."""
    message_payload = json.dumps({"requirements": requirements, "context": context})
    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(
            agent_url,
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "messageId": f"msg-{agent_id}",
                        "kind": "message",
                        "parts": [{"kind": "text", "text": message_payload}],
                    }
                },
            },
        )
        data = resp.json()
        return data.get("result", {})


async def _short_query(prompt: str, system: str) -> str:
    """Run a short Claude query (no tools, max 1 turn) and return the text."""
    options = ClaudeAgentOptions(
        system_prompt=system,
        max_turns=1,
        permission_mode="acceptEdits",
    )
    result_text = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    result_text += block.text
        elif isinstance(message, ResultMessage):
            if message.result:
                result_text = message.result
    return result_text


async def run_orchestrator(conversation: list[dict]):
    """Run the multi-phase conductor.

    Yields TextEvent and AgentStatusEvent for streaming to the frontend.
    """
    # Extract the latest user message
    user_message = ""
    for msg in reversed(conversation):
        if msg.get("role") == "user":
            user_message = msg.get("content", "")
            break

    if not user_message:
        yield TextEvent(text="Please describe the event you'd like to plan!")
        return

    # --- Phase 1: Discover agents ---
    agents = await _discover_agents()
    if not agents:
        yield TextEvent(text="No specialist agents are available. Please check that agents are running.")
        return

    agent_list = "\n".join(
        f"- **{d['name']}** (`{aid}`): {d['description']}"
        for aid, d in agents.items()
    )

    # --- Phase 1b: Generate plan text (short query, no tools) ---
    plan_text = await _short_query(
        prompt=f"""User request: {user_message}

Available specialist agents:
{agent_list}

Create a brief, exciting plan showing which agents you'll use organized into waves.
Wave 1 (independent): {', '.join(a for a in WAVE_1 if a in agents)}
Wave 2 (needs Wave 1 context): {', '.join(a for a in WAVE_2 if a in agents)}
Wave 3 (final): {', '.join(a for a in WAVE_3 if a in agents)}

Keep it concise — just the plan overview. Do NOT execute anything.""",
        system="You are the Event Orchestrator Conductor. Present a brief plan for coordinating specialist agents. Be enthusiastic but concise.",
    )
    yield TextEvent(text=plan_text)
    yield TextEvent(text="\n\n---\n\n")

    # --- Phase 2: Execute agent calls in parallel per wave ---
    requirements = {"user_request": user_message}
    all_results: dict[str, dict] = {}

    for wave_name, wave_agents in [("Wave 1", WAVE_1), ("Wave 2", WAVE_2), ("Wave 3", WAVE_3)]:
        wave_active = [a for a in wave_agents if a in agents]
        if not wave_active:
            continue

        yield TextEvent(text=f"\n**{wave_name}** — calling {', '.join(wave_active)} in parallel...\n")

        # Mark all agents in this wave as running
        for agent_id in wave_active:
            yield AgentStatusEvent(agent_id=agent_id, status="running")

        # Call all agents in this wave concurrently
        async def _call_one(aid: str) -> tuple[str, dict | None, str | None]:
            """Call a single agent, return (agent_id, result, error)."""
            try:
                result = await _call_agent(
                    agent_url=agents[aid]["url"],
                    agent_id=aid,
                    requirements=requirements,
                    context=all_results,
                )
                return (aid, result, None)
            except Exception as e:
                return (aid, None, f"{type(e).__name__}: {e}")

        results = await asyncio.gather(*[_call_one(aid) for aid in wave_active])

        # Process results and emit status events
        for agent_id, result, error in results:
            if error:
                all_results[agent_id] = {"error": error}
                yield AgentStatusEvent(agent_id=agent_id, status="error")
                yield TextEvent(text=f"\n> {agent_id} error: {error}\n")
            else:
                all_results[agent_id] = result
                yield AgentStatusEvent(agent_id=agent_id, status="completed")

    # --- Phase 3: Compile blueprint (short query, no tools) ---
    yield TextEvent(text="\n\n---\n\n**Compiling your Event Blueprint...**\n\n")

    results_summary = json.dumps(all_results, indent=2, default=str)
    try:
        blueprint = await _short_query(
            prompt=f"""Original request: {user_message}

Here are all the results from the specialist agents:
{results_summary}

Compile these into a comprehensive, well-organized Event Blueprint.
Include sections for each aspect (venue, menu, theme, activities, etc.).
Highlight the top recommendations, total estimated cost vs budget, and any warnings.
Make it practical and actionable.""",
            system="""You are the Event Orchestrator Conductor compiling a final Event Blueprint.
Organize the agent results into a clear, structured, actionable plan.
Use markdown formatting with headers, bullet points, and tables where appropriate.
Always include a budget summary comparing estimated costs to the stated budget.""",
        )
        yield TextEvent(text=blueprint)
    except Exception as e:
        # If the compile query fails, dump raw results as fallback
        yield TextEvent(text=f"**Note:** Blueprint compilation encountered an error ({type(e).__name__}). Here are the raw agent results:\n\n")
        for agent_id, result in all_results.items():
            yield TextEvent(text=f"### {agent_id}\n```json\n{json.dumps(result, indent=2, default=str)[:2000]}\n```\n\n")
