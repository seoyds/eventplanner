"""Dynamic MCP tools for the conductor.

Instead of hardcoded per-agent tools, provides:
- discover_agents: Query NANDA registry for available agents + capabilities
- call_agent: Call any agent by ID (resolved via NANDA)
- check_budget: Local budget validation
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


@tool("discover_agents", "Query the NANDA registry for available specialist agents and their capabilities", {
    "query": str,
})
async def discover_agents(args):
    """Discover available agents from the NANDA registry.

    Args:
        query: Search query or 'all' to list everything.
    """
    query_str = args.get("query", "all")

    # Get all registered agents
    agents = await _nanda.list_agents()

    if not agents:
        return {"content": [{"type": "text", "text": json.dumps({
            "agents": [],
            "message": "No agents registered in the NANDA registry."
        })}]}

    # For each agent, fetch its agent card for detailed capabilities
    agent_details = []
    for agent_id, agent_url in agents.items():
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{agent_url}/.well-known/agent.json")
                if resp.status_code == 200:
                    card = resp.json()
                    agent_details.append({
                        "agent_id": agent_id,
                        "name": card.get("name", agent_id),
                        "description": card.get("description", "No description"),
                        "skills": [
                            {"name": s.get("name", ""), "description": s.get("description", "")}
                            for s in card.get("skills", [])
                        ],
                        "url": agent_url,
                    })
                else:
                    agent_details.append({
                        "agent_id": agent_id,
                        "description": "Agent registered but card unavailable",
                        "url": agent_url,
                    })
        except Exception:
            agent_details.append({
                "agent_id": agent_id,
                "description": "Agent registered but unreachable",
                "url": agent_url,
            })

    return {"content": [{"type": "text", "text": json.dumps({
        "agents": agent_details,
        "total": len(agent_details),
    }, indent=2)}]}


@tool("call_agent", "Call a specialist agent by ID to perform a task", {
    "agent_id": str,
    "requirements": str,
    "context": str,
})
async def call_agent(args):
    """Call any registered agent by its ID.

    Args:
        agent_id: The agent to call (e.g., 'venue', 'weather', 'budget')
        requirements: JSON string of event requirements to pass to the agent
        context: JSON string of context from other agents' results
    """
    agent_id = args["agent_id"]
    requirements = json.loads(args["requirements"])
    context = json.loads(args["context"]) if args.get("context") else {}

    agent_url = await _resolve_agent_url(agent_id)

    # A2A protocol: use message/send with a Message containing TextPart
    message_payload = json.dumps({"requirements": requirements, "context": context})
    async with httpx.AsyncClient(timeout=300) as client:
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
        resp_data = resp.json()
        # Extract result from A2A response — could be in result.artifacts or result itself
        result = resp_data.get("result", {})

    return {"content": [{"type": "text", "text": json.dumps({
        "agent_id": agent_id,
        "result": result,
    })}]}


@tool("check_budget", "Validate total costs against budget limit", {
    "all_results": str,
    "budget_limit": float,
})
async def check_budget(args):
    """Quick budget check without calling the full budget agent."""
    results = json.loads(args["all_results"])
    total = sum(r.get("estimated_cost", 0) for r in results.values())
    remaining = args["budget_limit"] - total
    return {"content": [{"type": "text", "text": json.dumps({
        "total": total,
        "remaining": remaining,
        "status": "ok" if remaining >= 0 else "over_budget",
    })}]}


AGENT_TOOLS = [discover_agents, call_agent, check_budget]
