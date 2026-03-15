"""MCP tools that make A2A calls to specialist agents.

Agent URLs are discovered dynamically from the self-hosted NANDA registry.
"""
import json
import httpx
from claude_agent_sdk import tool
from shared.nanda_registry import NandaRegistryClient

_nanda = NandaRegistryClient()
_agent_url_cache: dict[str, str] = {}


async def _resolve_agent_url(agent_id: str) -> str:
    """Resolve an agent URL from the NANDA registry, with caching."""
    if agent_id not in _agent_url_cache:
        url = await _nanda.lookup_agent(agent_id)
        if not url:
            raise RuntimeError(
                f"Agent '{agent_id}' not found in NANDA registry at {_nanda.registry_url}."
            )
        _agent_url_cache[agent_id] = url
    return _agent_url_cache[agent_id]


async def _call_agent(agent_id: str, requirements: dict, context: dict) -> dict:
    """Discover agent via NANDA registry, then make A2A call."""
    agent_url = await _resolve_agent_url(agent_id)
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{agent_url}/a2a",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "execute",
                "params": {"requirements": requirements, "context": context},
            },
        )
        return resp.json().get("result", {})


@tool("call_venue_agent", "Find and score event venues", {
    "requirements": str, "context": str,
})
async def call_venue_agent(args):
    result = await _call_agent("venue", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_weather_agent", "Get weather forecast and contingency plan", {
    "requirements": str, "context": str,
})
async def call_weather_agent(args):
    result = await _call_agent("weather", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_budget_agent", "Calculate and validate budget", {
    "requirements": str, "context": str,
})
async def call_budget_agent(args):
    result = await _call_agent("budget", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_menu_agent", "Plan meals and calculate food costs", {
    "requirements": str, "context": str,
})
async def call_menu_agent(args):
    result = await _call_agent("menu", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_activity_agent", "Plan entertainment and activities", {
    "requirements": str, "context": str,
})
async def call_activity_agent(args):
    result = await _call_agent("activity", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_accessibility_agent", "Audit venues and activities for accessibility", {
    "requirements": str, "context": str,
})
async def call_accessibility_agent(args):
    result = await _call_agent("accessibility", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_theme_agent", "Design event aesthetic and decorations", {
    "requirements": str, "context": str,
})
async def call_theme_agent(args):
    result = await _call_agent("theme", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_logistics_agent", "Create day-of timeline and logistics plan", {
    "requirements": str, "context": str,
})
async def call_logistics_agent(args):
    result = await _call_agent("logistics", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_communication_agent", "Draft invitations and communication templates", {
    "requirements": str, "context": str,
})
async def call_communication_agent(args):
    result = await _call_agent("communication", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_supplies_agent", "Source party favors, decorations, and supplies", {
    "requirements": str, "context": str,
})
async def call_supplies_agent(args):
    result = await _call_agent("supplies", json.loads(args["requirements"]), json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("check_budget", "Validate total costs against budget limit", {
    "all_results": str, "budget_limit": float,
})
async def check_budget(args):
    """Quick budget check without calling the full budget agent."""
    results = json.loads(args["all_results"])
    total = sum(r.get("estimated_cost", 0) for r in results.values())
    remaining = args["budget_limit"] - total
    return {"content": [{"type": "text", "text": json.dumps({
        "total": total, "remaining": remaining,
        "status": "ok" if remaining >= 0 else "over_budget",
    })}]}

AGENT_TOOLS = [
    call_venue_agent, call_weather_agent, call_budget_agent,
    call_menu_agent, call_activity_agent, call_accessibility_agent,
    call_theme_agent, call_logistics_agent, call_communication_agent,
    call_supplies_agent, check_budget,
]
