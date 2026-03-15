# PRD: Event Orchestration Multi-Agent System

## Project Overview

A multi-agent event planning system where **each agent is a standalone service powered by the Claude Agent SDK**, exposing an **A2A protocol** endpoint. A Conductor agent receives user requests via **AG-UI** (chatbot interface), discovers specialist agents through their Agent Cards, delegates tasks via A2A, and streams real-time progress back to the user.

Each specialist agent uses `claude-agent-sdk` internally — giving it Claude Code's full agentic loop (reasoning, tool use, web search) plus **custom MCP tools** for domain-specific capabilities (weather APIs, cost calculations, etc.).

This is a **greenfield project**.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│              User (Browser)                 │
│         CopilotKit Chat Interface           │
└──────────────────┬──────────────────────────┘
                   │ AG-UI (SSE event stream)
                   ▼
┌─────────────────────────────────────────────┐
│         Conductor Agent Service             │
│   FastAPI + AG-UI endpoint                  │
│                                             │
│   Uses claude-agent-sdk with custom MCP     │
│   tools that make A2A calls to agents       │
└──────┬────┬────┬────┬────┬────┬────┬───┬────┘
       │    │    │    │    │    │    │   │
       ▼    ▼    ▼    ▼    ▼    ▼    ▼   ▼    (A2A / JSON-RPC over HTTP)
    ┌─────┐┌─────┐┌──────┐┌────┐┌────┐┌───┐┌───┐┌───┐
    │Venue││Weath││Budget││Menu││Actv.││Acc││Thm││...│
    └─────┘└─────┘└──────┘└────┘└─────┘└───┘└───┘└───┘
    :8001   :8002  :8003   :8004 :8005  :8006:8007 ...
    
    Each agent internally:
    ┌──────────────────────────┐
    │ FastAPI (A2A endpoint)   │
    │   ↓ receives task        │
    │ claude-agent-sdk         │
    │   query() with:          │
    │   - system_prompt        │
    │   - custom MCP tools     │
    │   - allowed_tools        │
    │   ↓ returns result       │
    │ A2A response             │
    └──────────────────────────┘
```

**Three layers**:
- **AG-UI** (`ag-ui-protocol`): Conductor ↔ User. SSE event stream to CopilotKit frontend.
- **A2A** (`a2a-sdk`): Conductor ↔ Specialist Agents. JSON-RPC 2.0 over HTTP. Each agent has an Agent Card at `/.well-known/agent.json`.
- **Claude Agent SDK** (`claude-agent-sdk`): Powers the reasoning inside each agent. Gives every agent access to Claude's agentic loop, web search, file operations, bash, and custom MCP tools.

---

## Why Claude Agent SDK for Each Agent

The Claude Agent SDK gives each agent far more than just LLM text generation:

1. **Agentic loop**: Each agent can reason, plan, use tools, and iterate — not just generate a single response. If the Venue agent's first search doesn't find good results, it can try different queries automatically.

2. **Built-in web search**: Agents that need real-time data (Venue, Weather, Supplies) get Claude's web search tool natively. No need to wire up separate search APIs.

3. **Custom MCP tools**: Each agent registers domain-specific tools (weather API calls, budget calculators, template generators) as in-process MCP servers. Claude decides when and how to use them.

4. **Structured outputs**: Each agent can return validated JSON matching a Pydantic schema, ensuring consistent output formats across all agents.

5. **Subagent capability**: The Conductor can use the SDK's built-in subagent feature for simpler delegations, while using A2A for the full standalone agents.

6. **Context management**: The SDK handles context windows, compaction, and multi-turn reasoning automatically.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Package Manager | `uv` |
| Agent Runtime | `claude-agent-sdk` (each agent runs Claude's agentic loop) |
| A2A SDK | `a2a-sdk` (official, with FastAPI/Starlette integration) |
| AG-UI SDK | `ag-ui-protocol` (Python, SSE event streaming) |
| Web Framework | FastAPI (A2A endpoints + AG-UI endpoint) |
| Frontend | CopilotKit (React) — minimal chatbot + agent monitor |
| Database | SQLite (registry, run logs) — upgrade to PostgreSQL later |
| Containerization | Docker Compose (one container per agent + conductor + frontend) |
| Deployment | Hetzner VPS |

---

## Project Structure

```
event-orchestrator/
├── conductor/                    # Conductor service
│   ├── main.py                   # FastAPI: AG-UI endpoint
│   ├── orchestrator.py           # Orchestration logic using claude-agent-sdk
│   ├── tools/                    # Custom MCP tools for the conductor
│   │   ├── a2a_tools.py          # MCP tools that call specialist agents via A2A
│   │   ├── prompt_parser.py      # MCP tool: parse user prompt → EventRequirements
│   │   └── blueprint_compiler.py # MCP tool: compile all results into blueprint
│   ├── registry.py               # Agent Card discovery
│   ├── Dockerfile
│   └── pyproject.toml
│
├── agents/                       # Each agent is a standalone service
│   ├── venue/
│   │   ├── main.py               # FastAPI A2A server on :8001
│   │   ├── agent.py              # claude-agent-sdk query with custom tools
│   │   ├── tools.py              # MCP tools: venue search, filtering, scoring
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── weather/
│   │   ├── main.py               # FastAPI A2A server on :8002
│   │   ├── agent.py
│   │   ├── tools.py              # MCP tools: Open-Meteo API, forecast analysis
│   │   ├── Dockerfile
│   │   └── pyproject.toml
│   ├── budget/                   # :8003
│   ├── menu/                     # :8004
│   ├── activity/                 # :8005
│   ├── accessibility/            # :8006
│   ├── theme/                    # :8007
│   ├── logistics/                # :8008
│   ├── communication/            # :8009
│   └── supplies/                 # :8010
│       ├── main.py
│       ├── agent.py
│       ├── tools.py
│       ├── Dockerfile
│       └── pyproject.toml
│
├── shared/                       # Shared library
│   ├── schemas.py                # Pydantic models (EventRequirements, AgentResult, etc.)
│   ├── agent_base.py             # Base class wrapping claude-agent-sdk + A2A server
│   └── pyproject.toml
│
├── frontend/                     # Minimal CopilotKit chat UI
│   ├── src/app/page.tsx          # Chat + agent monitor panel
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── .env
└── README.md
```

---

## Phase 1: Shared Foundation

### 1.1 Shared Schemas

**File**: `shared/schemas.py`

```python
from pydantic import BaseModel
from datetime import date
from enum import Enum

class EventRequirements(BaseModel):
    """Structured extraction from user's natural language prompt."""
    event_type: str                          # "family reunion", "birthday", "retreat"
    event_name: str | None = None
    guest_count: int
    location_preference: str                 # "mountain", "beach", "urban"
    date_range: tuple[date, date]
    budget_total: float
    dietary_restrictions: list[str]          # ["vegan", "gluten-free"]
    accessibility_needs: list[str]           # ["wheelchair", "elderly-friendly"]
    theme_preferences: str | None = None     # "rustic mountain", "elegant garden"
    special_requests: list[str] = []
    age_groups: list[str] = []               # ["children", "adults", "elderly"]

class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    REVISING = "revising"

class AgentResult(BaseModel):
    """Standard wrapper for every agent's output."""
    agent_id: str
    status: AgentStatus
    result: dict                             # agent-specific structured output
    estimated_cost: float = 0.0
    warnings: list[str] = []
    execution_time_ms: int = 0

class OrchestratorState(BaseModel):
    """Shared state synced via AG-UI to the frontend."""
    request_id: str
    requirements: EventRequirements | None = None
    agent_statuses: dict[str, AgentStatus] = {}
    agent_results: dict[str, dict] = {}
    budget_remaining: float = 0.0
    current_phase: str = "idle"
    messages: list[str] = []
    blueprint: dict | None = None
```

### 1.2 Agent Base Class

**File**: `shared/agent_base.py`

Wraps `claude-agent-sdk` + A2A server boilerplate so each agent only defines its tools, system prompt, and output schema.

```python
from claude_agent_sdk import (
    query, ClaudeAgentOptions, tool, create_sdk_mcp_server,
    AssistantMessage, ResultMessage, TextBlock,
)
from a2a.server.apps import A2AStarletteApplication
from a2a.types import AgentCard, AgentSkill
from fastapi import FastAPI
import json

class BaseEventAgent:
    """
    Base class for all specialist agents.
    
    Each subclass defines:
      - agent_id, name, description, port
      - skills (A2A capability metadata)
      - system_prompt (instructions for Claude)
      - get_mcp_tools() → list of @tool-decorated functions
      - get_allowed_tools() → list of tool names to auto-approve
    """
    agent_id: str
    name: str
    description: str
    port: int
    skills: list[AgentSkill]
    system_prompt: str
    
    def get_mcp_tools(self) -> list:
        """Return list of @tool decorated functions for this agent."""
        return []
    
    def get_allowed_tools(self) -> list[str]:
        """Tools to auto-approve (no permission prompt). 
        Always includes WebSearch for agents that need real-time data."""
        return ["WebSearch", "Read"]
    
    async def run(self, requirements: dict, context: dict) -> AgentResult:
        """
        Execute this agent using claude-agent-sdk.
        
        1. Creates an in-process MCP server with custom tools
        2. Runs claude-agent-sdk query() with the system prompt
        3. Extracts structured result from Claude's response
        """
        # Build custom MCP server with agent-specific tools
        mcp_tools = self.get_mcp_tools()
        mcp_server = create_sdk_mcp_server(
            name=f"{self.agent_id}-tools",
            version="1.0.0",
            tools=mcp_tools,
        ) if mcp_tools else None
        
        # Build options
        mcp_servers = {}
        allowed_tools = self.get_allowed_tools()
        
        if mcp_server:
            mcp_servers[self.agent_id] = mcp_server
            # Auto-approve all custom tools
            for t in mcp_tools:
                allowed_tools.append(f"mcp__{self.agent_id}__{t.name}")
        
        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            allowed_tools=allowed_tools,
            mcp_servers=mcp_servers if mcp_servers else None,
            max_turns=10,                   # prevent runaway loops
            permission_mode="acceptEdits",  # non-interactive
        )
        
        # Build the prompt with requirements and context
        prompt = self._build_prompt(requirements, context)
        
        # Run Claude's agentic loop
        result_text = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text = block.text
        
        # Parse structured output
        return self._parse_result(result_text)
    
    def _build_prompt(self, requirements: dict, context: dict) -> str:
        """Build the prompt string from requirements and context."""
        prompt = f"""## Event Requirements
{json.dumps(requirements, indent=2, default=str)}

## Context from Other Agents
{json.dumps(context, indent=2, default=str) if context else "No prior context available."}

## Your Task
Based on the event requirements above and any context from other agents,
produce your analysis. Return your output as a JSON object with these fields:
- result: your main output (structure depends on your specialty)
- estimated_cost: float, your estimated cost contribution
- warnings: list of any concerns or issues found
"""
        return prompt
    
    def _parse_result(self, text: str) -> AgentResult:
        """Parse Claude's response into an AgentResult."""
        # Try to extract JSON from response
        try:
            # Find JSON block in response
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return AgentResult(
                    agent_id=self.agent_id,
                    status="completed",
                    result=data.get("result", data),
                    estimated_cost=data.get("estimated_cost", 0.0),
                    warnings=data.get("warnings", []),
                )
        except json.JSONDecodeError:
            pass
        
        # Fallback: treat entire response as result
        return AgentResult(
            agent_id=self.agent_id,
            status="completed",
            result={"raw_response": text},
        )
    
    def get_agent_card(self) -> AgentCard:
        """Generate A2A Agent Card."""
        return AgentCard(
            name=self.agent_id,
            description=self.description,
            url=f"http://{self.agent_id}:{self.port}",
            version="1.0.0",
            skills=self.skills,
            capabilities={"streaming": False, "pushNotifications": False},
        )
    
    def build_fastapi_app(self) -> FastAPI:
        """
        Build a FastAPI app with:
        1. A2A endpoint (JSON-RPC task handling)
        2. Agent Card at /.well-known/agent.json
        """
        app = FastAPI(title=f"{self.name} - A2A Agent")
        
        @app.get("/.well-known/agent.json")
        async def agent_card():
            return self.get_agent_card().model_dump()
        
        @app.post("/a2a")
        async def handle_task(request: dict):
            """A2A JSON-RPC endpoint. Receives task, runs agent, returns result."""
            requirements = request.get("params", {}).get("requirements", {})
            context = request.get("params", {}).get("context", {})
            
            result = await self.run(requirements, context)
            
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result.model_dump(),
            }
        
        return app
```

---

## Phase 2: Specialist Agents (Each a Standalone Service)

Every agent follows the same pattern: subclass `BaseEventAgent`, define a system prompt and custom MCP tools, run as FastAPI on its own port.

### Agent 1: Venue & Destination Planner

**Service**: `agents/venue/` → port `8001`

**File**: `agents/venue/tools.py`
```python
from claude_agent_sdk import tool

@tool("search_venues", "Search for event venues matching criteria", {
    "location": str,
    "guest_count": int,
    "event_type": str,
    "indoor_required": bool,
})
async def search_venues(args):
    """
    Claude will also have WebSearch built-in, but this tool provides
    structured venue search with scoring logic.
    
    In MVP: this tool can call a free API or just structure the
    search query for Claude's built-in web search to use.
    Later: integrate Google Places API for richer data.
    """
    # For MVP, return a structured prompt for Claude to use with web search
    return {
        "content": [{
            "type": "text",
            "text": f"Search for {args['event_type']} venues near {args['location']} "
                    f"that can hold {args['guest_count']} people. "
                    f"{'Must have indoor option.' if args['indoor_required'] else ''} "
                    f"Find at least 3 options with: name, address, capacity, "
                    f"estimated rental cost, indoor/outdoor, accessibility notes."
        }]
    }

@tool("score_venue", "Score a venue on multiple criteria", {
    "venue_name": str,
    "capacity_match": float,     # 0-1 how well capacity matches
    "price_per_person": float,
    "accessibility_score": float, # 0-1
    "review_rating": float,       # 0-5
})
async def score_venue(args):
    """Calculate a weighted score for venue comparison."""
    score = (
        args["capacity_match"] * 0.25 +
        (1 - min(args["price_per_person"] / 100, 1)) * 0.25 +
        args["accessibility_score"] * 0.25 +
        (args["review_rating"] / 5) * 0.25
    )
    return {
        "content": [{
            "type": "text",
            "text": f"Venue '{args['venue_name']}' scored {score:.2f}/1.0"
        }]
    }
```

**File**: `agents/venue/agent.py`
```python
from shared.agent_base import BaseEventAgent
from tools import search_venues, score_venue

class VenuePlannerAgent(BaseEventAgent):
    agent_id = "venue"
    name = "Venue & Destination Planner"
    description = "Finds and scores event venues matching location, capacity, and accessibility requirements"
    port = 8001
    skills = [{"name": "venue-search"}, {"name": "location-filtering"}, {"name": "capacity-matching"}]
    
    system_prompt = """You are an expert event venue researcher. Your job is to find
the best venues for an event based on the requirements provided.

PROCESS:
1. Use web search to find real venues matching the location and capacity requirements
2. Score each venue using the score_venue tool
3. Return your top 3 recommendations with full details

OUTPUT FORMAT (JSON):
{
    "result": {
        "venues": [
            {
                "name": "Venue Name",
                "address": "Full address",
                "capacity": 50,
                "estimated_rental_cost": 1500.00,
                "indoor_outdoor": "both",
                "accessibility_notes": "Wheelchair accessible, elevator available",
                "contact_info": "phone/email/website",
                "score": 0.85,
                "notes": "Why this venue is a good fit"
            }
        ],
        "recommended_venue": "Name of top pick"
    },
    "estimated_cost": 1500.00,
    "warnings": []
}

Be thorough in your research. Use web search to find REAL venues with actual
pricing. Do not make up venue names or prices."""
    
    def get_mcp_tools(self):
        return [search_venues, score_venue]
    
    def get_allowed_tools(self):
        return ["WebSearch", "Read", "mcp__venue__search_venues", "mcp__venue__score_venue"]
```

**File**: `agents/venue/main.py`
```python
import uvicorn
from agent import VenuePlannerAgent

agent = VenuePlannerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
```

### Agent 2: Weather & Contingency
**Service**: `agents/weather/` → port `8002`

**Custom MCP Tools**:
```python
@tool("get_forecast", "Get weather forecast from Open-Meteo API", {
    "latitude": float,
    "longitude": float, 
    "start_date": str,
    "end_date": str,
})
async def get_forecast(args):
    """Call Open-Meteo free API for actual weather data."""
    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": args["latitude"],
                "longitude": args["longitude"],
                "start_date": args["start_date"],
                "end_date": args["end_date"],
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode",
            }
        )
        return {"content": [{"type": "text", "text": resp.text}]}

@tool("assess_outdoor_viability", "Score how viable an outdoor event is", {
    "rain_probability": float,
    "temperature_high": float,
    "temperature_low": float,
})
async def assess_outdoor_viability(args):
    """Calculate outdoor event viability score."""
    rain_score = max(0, 1 - args["rain_probability"] / 100)
    temp_score = 1.0 if 60 <= args["temperature_high"] <= 85 else 0.5
    score = rain_score * 0.6 + temp_score * 0.4
    recommendation = "outdoor" if score > 0.7 else "indoor backup needed" if score > 0.4 else "indoor only"
    return {"content": [{"type": "text", "text": f"Viability: {score:.2f} — {recommendation}"}]}
```

**System Prompt**: Analyze weather for event dates, call Open-Meteo for real data, assess outdoor viability, recommend contingency plans if rain probability > 50%.

### Agent 3: Budget & Cost Estimator
**Service**: `agents/budget/` → port `8003`

**Custom MCP Tools**:
```python
@tool("calculate_budget", "Calculate and validate total budget against limit", {
    "line_items": str,  # JSON string of {category: cost} items
    "budget_limit": float,
})
async def calculate_budget(args):
    """Tally costs and check against budget."""
    items = json.loads(args["line_items"])
    total = sum(items.values())
    remaining = args["budget_limit"] - total
    status = "within_budget" if remaining >= 0 else "over_budget"
    return {"content": [{"type": "text", "text": json.dumps({
        "total": total, "remaining": remaining, "status": status,
        "breakdown": items,
    })}]}

@tool("suggest_cost_reduction", "Suggest ways to reduce costs for a category", {
    "category": str,
    "current_cost": float,
    "target_cost": float,
})
async def suggest_cost_reduction(args):
    """Generate cost reduction suggestions."""
    reduction_needed = args["current_cost"] - args["target_cost"]
    return {"content": [{"type": "text", "text": 
        f"Need to reduce {args['category']} by ${reduction_needed:.0f}. "
        f"Current: ${args['current_cost']:.0f}, Target: ${args['target_cost']:.0f}"}]}
```

**System Prompt**: Tally all costs from context (venue, menu, theme, supplies), validate against budget, suggest optimizations if overbudget.

### Agent 4: Menu & Dietary Planner
**Service**: `agents/menu/` → port `8004`

**Custom MCP Tools**:
```python
@tool("estimate_food_cost", "Estimate per-person food cost for a meal type", {
    "meal_type": str,       # "breakfast", "lunch", "dinner", "snacks"
    "style": str,           # "potluck", "catered", "self-cooked"
    "dietary_restrictions": str,
    "guest_count": int,
})
async def estimate_food_cost(args):
    """Estimate food costs based on standard market rates."""
    base_rates = {"breakfast": 8, "lunch": 15, "dinner": 25, "snacks": 5}
    rate = base_rates.get(args["meal_type"], 15)
    if args["style"] == "catered": rate *= 1.5
    if args["style"] == "potluck": rate *= 0.4
    total = rate * args["guest_count"]
    return {"content": [{"type": "text", "text": f"${rate:.0f}/person × {args['guest_count']} = ${total:.0f}"}]}
```

**System Prompt**: Generate meal plans respecting dietary needs, calculate per-person costs, produce grocery lists. Use web search for recipe inspiration. Heavy Claude usage for creative menu generation.

### Agent 5: Activity & Entertainment
**Service**: `agents/activity/` → port `8005`
**Tools**: No custom MCP tools needed — relies on Claude's web search and reasoning
**System Prompt**: Suggest age-appropriate activities mixing high-energy and relaxed options. Use web search for local sightseeing. Consider accessibility constraints.

### Agent 6: Accessibility & Inclusivity
**Service**: `agents/accessibility/` → port `8006`

**Custom MCP Tools**:
```python
@tool("check_accessibility", "Check a venue or activity against accessibility criteria", {
    "item_name": str,
    "item_type": str,          # "venue" or "activity"
    "has_wheelchair_access": bool,
    "has_elevator": bool,
    "min_stairs": int,
    "suitable_for_elderly": bool,
    "suitable_for_children": bool,
})
async def check_accessibility(args):
    """Score accessibility of a venue or activity."""
    score = 1.0
    issues = []
    if not args["has_wheelchair_access"]: score -= 0.3; issues.append("No wheelchair access")
    if args["min_stairs"] > 3 and not args["has_elevator"]: score -= 0.2; issues.append(f"{args['min_stairs']} stairs, no elevator")
    if not args["suitable_for_elderly"]: score -= 0.2; issues.append("Not elderly-friendly")
    if not args["suitable_for_children"]: score -= 0.1; issues.append("Not child-safe")
    return {"content": [{"type": "text", "text": json.dumps({
        "item": args["item_name"], "score": score, "issues": issues, "pass": score >= 0.6
    })}]}
```

**System Prompt**: Cross-reference venues and activities against accessibility needs. Flag issues. Suggest accommodations.

### Agent 7: Theme & Aesthetic
**Service**: `agents/theme/` → port `8007`
**Tools**: No custom MCP tools — purely creative generation by Claude
**System Prompt**: Act as creative director. Generate color palettes (hex codes), decoration concepts, mood descriptions. Use web search for inspiration and current trends.

### Agent 8: Logistics & Timeline
**Service**: `agents/logistics/` → port `8008`

**Custom MCP Tools**:
```python
@tool("create_timeline_slot", "Create a time slot for the event schedule", {
    "activity": str,
    "start_time": str,    # "HH:MM"
    "duration_minutes": int,
    "location": str,
    "setup_minutes": int,
    "notes": str,
})
async def create_timeline_slot(args):
    """Create and validate a timeline entry."""
    # Calculate end time
    start_h, start_m = map(int, args["start_time"].split(":"))
    total_min = start_h * 60 + start_m + args["duration_minutes"]
    end_h, end_m = divmod(total_min, 60)
    return {"content": [{"type": "text", "text": json.dumps({
        "activity": args["activity"],
        "start": args["start_time"],
        "end": f"{end_h:02d}:{end_m:02d}",
        "duration_min": args["duration_minutes"],
        "setup_min": args["setup_minutes"],
        "location": args["location"],
        "notes": args["notes"],
    })}]}
```

**System Prompt**: Compile minute-by-minute timeline from all agent outputs. Prevent overlaps. Account for setup/teardown. Runs in Wave 3 with full context.

### Agent 9: Communication & Invitation
**Service**: `agents/communication/` → port `8009`
**Tools**: No custom MCP tools — purely generative copywriting
**System Prompt**: Draft save-the-date, invitation, and reminder templates. Match tone to event theme. Provide copy-paste-ready text.

### Agent 10: Favor & Supply Sourcing
**Service**: `agents/supplies/` → port `8010`

**Custom MCP Tools**:
```python
@tool("estimate_supply_cost", "Estimate cost for a supply item", {
    "item": str,
    "quantity": int,
    "category": str,  # "decoration", "favor", "rental", "consumable"
})
async def estimate_supply_cost(args):
    """Estimate supply costs using standard pricing."""
    base_prices = {"decoration": 3, "favor": 5, "rental": 15, "consumable": 2}
    unit_cost = base_prices.get(args["category"], 5)
    total = unit_cost * args["quantity"]
    return {"content": [{"type": "text", "text": f"{args['item']}: ${unit_cost}/ea × {args['quantity']} = ${total}"}]}
```

**System Prompt**: Recommend party favors, decorations, rentals based on theme. Use web search for current pricing. Build consolidated shopping checklist.

---

## Phase 3: Conductor Service

The Conductor is special: it uses `claude-agent-sdk` with **custom MCP tools that make A2A calls** to the specialist agents. Claude orchestrates the workflow — deciding which agents to call, in what order, and how to handle failures.

### 3.1 Conductor's A2A Tools

**File**: `conductor/tools/a2a_tools.py`

Each specialist agent is exposed to the Conductor's Claude as an MCP tool:

```python
from claude_agent_sdk import tool
import httpx

async def _call_agent(agent_url: str, requirements: dict, context: dict) -> dict:
    """Generic A2A call to a specialist agent."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{agent_url}/a2a", json={
            "jsonrpc": "2.0",
            "id": "1",
            "method": "execute",
            "params": {"requirements": requirements, "context": context},
        })
        return resp.json().get("result", {})

@tool("call_venue_agent", "Find and score event venues", {
    "requirements": str,  # JSON string of EventRequirements
    "context": str,       # JSON string of context from other agents
})
async def call_venue_agent(args):
    result = await _call_agent("http://venue:8001", 
                                json.loads(args["requirements"]), 
                                json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

@tool("call_weather_agent", "Get weather forecast and contingency plan", {
    "requirements": str,
    "context": str,
})
async def call_weather_agent(args):
    result = await _call_agent("http://weather:8002",
                                json.loads(args["requirements"]),
                                json.loads(args["context"]))
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

# ... repeat for all 10 agents (budget, menu, activity, accessibility, theme, logistics, communication, supplies)

@tool("check_budget", "Validate total costs against budget limit", {
    "all_results": str,  # JSON of all agent results so far
    "budget_limit": float,
})
async def check_budget(args):
    """Quick budget check without calling the full budget agent."""
    results = json.loads(args["all_results"])
    total = sum(r.get("estimated_cost", 0) for r in results.values())
    remaining = args["budget_limit"] - total
    return {"content": [{"type": "text", "text": json.dumps({
        "total": total, "remaining": remaining, 
        "status": "ok" if remaining >= 0 else "over_budget"
    })}]}
```

### 3.2 Conductor Orchestration

**File**: `conductor/orchestrator.py`

```python
from claude_agent_sdk import query, ClaudeAgentOptions, create_sdk_mcp_server
from tools.a2a_tools import (
    call_venue_agent, call_weather_agent, call_budget_agent,
    call_menu_agent, call_activity_agent, call_accessibility_agent,
    call_theme_agent, call_logistics_agent, call_communication_agent,
    call_supplies_agent, check_budget,
)

CONDUCTOR_SYSTEM_PROMPT = """You are the Event Orchestrator Conductor. You coordinate
a team of specialist agents to plan events.

## Available Agent Tools
You have tools to call each specialist agent. Each returns structured JSON results.

## Execution Strategy
Execute agents in 3 waves to respect dependencies:

WAVE 1 (call these in parallel — they have no dependencies):
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
After all waves complete, compile a comprehensive Event Blueprint with:
- Event summary
- Venue recommendation
- Weather outlook and contingency
- Menu and dietary plan
- Activities schedule  
- Accessibility report
- Theme and decorations
- Day-of timeline
- Invitation templates
- Shopping/supply list
- Total budget breakdown

Present this as a well-structured, actionable plan the user can follow."""

async def run_orchestrator(user_message: str):
    """
    Run the conductor using claude-agent-sdk.
    Claude decides the orchestration strategy based on the system prompt.
    Yields AG-UI events for streaming to the frontend.
    """
    # Build MCP server with all A2A tools
    conductor_tools = create_sdk_mcp_server(
        name="conductor-tools",
        version="1.0.0",
        tools=[
            call_venue_agent, call_weather_agent, call_budget_agent,
            call_menu_agent, call_activity_agent, call_accessibility_agent,
            call_theme_agent, call_logistics_agent, call_communication_agent,
            call_supplies_agent, check_budget,
        ],
    )
    
    # Auto-approve all conductor tools
    allowed = [f"mcp__conductor-tools__{t.name}" for t in [
        call_venue_agent, call_weather_agent, call_budget_agent,
        call_menu_agent, call_activity_agent, call_accessibility_agent,
        call_theme_agent, call_logistics_agent, call_communication_agent,
        call_supplies_agent, check_budget,
    ]]
    
    options = ClaudeAgentOptions(
        system_prompt=CONDUCTOR_SYSTEM_PROMPT,
        mcp_servers={"conductor-tools": conductor_tools},
        allowed_tools=allowed + ["WebSearch"],
        max_turns=30,                    # allow many tool calls
        permission_mode="acceptEdits",
    )
    
    async for message in query(prompt=user_message, options=options):
        yield message  # Forward to AG-UI event converter
```

### 3.3 AG-UI Endpoint

**File**: `conductor/main.py`

```python
from fastapi import FastAPI, Request
from ag_ui.core import (
    RunAgentInput, EventEncoder, RunStartEvent, RunFinishedEvent,
    TextMessageStartEvent, TextMessageContentEvent, TextMessageEndEvent,
    StateSnapshotEvent, CustomEvent,
)
from ag_ui.encoder import EventEncoder
from fastapi.responses import StreamingResponse
from orchestrator import run_orchestrator
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock, ToolResultBlock
import uuid

app = FastAPI(title="Event Orchestrator Conductor")

@app.post("/ag-ui")
async def ag_ui_endpoint(input_data: RunAgentInput):
    """AG-UI endpoint. CopilotKit sends messages here. Returns SSE stream."""
    
    # Extract latest user message
    user_message = ""
    for msg in reversed(input_data.messages):
        if msg.role == "user":
            user_message = msg.content[0].text if msg.content else ""
            break
    
    async def event_stream():
        encoder = EventEncoder()
        msg_id = str(uuid.uuid4())
        
        yield encoder.encode(RunStartEvent(thread_id=input_data.thread_id))
        yield encoder.encode(TextMessageStartEvent(message_id=msg_id, role="assistant"))
        
        async for sdk_message in run_orchestrator(user_message):
            if isinstance(sdk_message, AssistantMessage):
                for block in sdk_message.content:
                    if isinstance(block, TextBlock):
                        yield encoder.encode(TextMessageContentEvent(
                            message_id=msg_id, delta=block.text
                        ))
                    elif isinstance(block, ToolUseBlock):
                        # Emit custom event showing which agent is being called
                        tool_name = block.name
                        if tool_name.startswith("mcp__conductor-tools__call_"):
                            agent_name = tool_name.replace("mcp__conductor-tools__call_", "").replace("_agent", "")
                            yield encoder.encode(StateSnapshotEvent(
                                snapshot={"agent_statuses": {agent_name: "running"}}
                            ))
            
            elif isinstance(sdk_message, ResultMessage):
                yield encoder.encode(TextMessageContentEvent(
                    message_id=msg_id, delta=f"\n\n{sdk_message.result}"
                ))
        
        yield encoder.encode(TextMessageEndEvent(message_id=msg_id))
        yield encoder.encode(RunFinishedEvent())
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## Phase 4: Frontend (Minimal CopilotKit)

Single page: CopilotKit chat on the left, agent status monitor on the right.

**File**: `frontend/src/app/page.tsx`
```tsx
import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoagentStateRender } from "@copilotkit/react-core";

function AgentMonitor() {
  useCoagentStateRender({
    name: "conductor",
    render: ({ state }) => (
      <div className="p-4 space-y-3">
        <h2 className="font-bold text-lg">Agent Status</h2>
        {Object.entries(state?.agent_statuses || {}).map(([id, status]) => (
          <div key={id} className="flex items-center gap-2 text-sm">
            <span className={`w-2 h-2 rounded-full ${
              status === "completed" ? "bg-green-500" :
              status === "running" ? "bg-yellow-500 animate-pulse" :
              status === "failed" ? "bg-red-500" : "bg-gray-300"
            }`} />
            <span className="capitalize">{id}</span>
            <span className="text-gray-400 text-xs">{status}</span>
          </div>
        ))}
      </div>
    ),
  });
  return null;
}

export default function Home() {
  return (
    <CopilotKit runtimeUrl="http://localhost:8000/ag-ui" agent="conductor">
      <div className="flex h-screen">
        <div className="flex-1">
          <CopilotChat
            labels={{
              title: "Event Orchestrator",
              initial: "Describe your event — I'll coordinate 10 specialist agents to plan it!"
            }}
          />
        </div>
        <div className="w-80 border-l bg-gray-50">
          <AgentMonitor />
        </div>
      </div>
    </CopilotKit>
  );
}
```

---

## Phase 5: Docker Compose

**File**: `docker-compose.yml`

```yaml
services:
  conductor:
    build: ./conductor
    ports: ["8000:8000"]
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on: [venue, weather, budget, menu, activity, accessibility, theme, logistics, communication, supplies]

  venue:
    build: ./agents/venue
    ports: ["8001:8001"]
    environment: &agent-env
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

  weather:
    build: ./agents/weather
    ports: ["8002:8002"]
    environment: *agent-env

  budget:
    build: ./agents/budget
    ports: ["8003:8003"]
    environment: *agent-env

  menu:
    build: ./agents/menu
    ports: ["8004:8004"]
    environment: *agent-env

  activity:
    build: ./agents/activity
    ports: ["8005:8005"]
    environment: *agent-env

  accessibility:
    build: ./agents/accessibility
    ports: ["8006:8006"]
    environment: *agent-env

  theme:
    build: ./agents/theme
    ports: ["8007:8007"]
    environment: *agent-env

  logistics:
    build: ./agents/logistics
    ports: ["8008:8008"]
    environment: *agent-env

  communication:
    build: ./agents/communication
    ports: ["8009:8009"]
    environment: *agent-env

  supplies:
    build: ./agents/supplies
    ports: ["8010:8010"]
    environment: *agent-env

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_CONDUCTOR_URL=http://conductor:8000
```

---

## Implementation Order for Claude Code

### Step 1: Project Scaffolding + Shared Library
- Init monorepo with `uv`
- Create `shared/schemas.py` (all Pydantic models)
- Create `shared/agent_base.py` (BaseEventAgent with claude-agent-sdk + A2A boilerplate)
- **Test**: Import shared models, verify BaseEventAgent class structure

### Step 2: Build ONE Agent (Venue) End-to-End
- Create `agents/venue/tools.py` with `@tool` decorated MCP tools
- Create `agents/venue/agent.py` subclassing `BaseEventAgent`
- Create `agents/venue/main.py` as FastAPI server
- **Test**: `curl http://localhost:8001/.well-known/agent.json` → Agent Card
- **Test**: POST A2A task → Claude Agent SDK runs → returns venue results

### Step 3: Build the Conductor
- Create `conductor/tools/a2a_tools.py` (MCP tools wrapping A2A calls)
- Create `conductor/orchestrator.py` (claude-agent-sdk with conductor system prompt)
- Create `conductor/main.py` (AG-UI SSE endpoint)
- Wire up: user message → Claude orchestrates → calls venue agent via A2A tool → streams result
- **Test**: Full conductor → venue agent flow works via curl against AG-UI endpoint

### Step 4: Build Wave 1 Agents
- Weather (port 8002) — Open-Meteo MCP tool for real data
- Theme (port 8007) — no custom tools, pure Claude generation
- Menu (port 8004) — food cost estimation MCP tool
- **Test**: Each responds to direct A2A calls independently

### Step 5: Build Wave 2 Agents
- Accessibility (port 8006) — accessibility checker MCP tool
- Activity (port 8005) — no custom tools, Claude + web search
- Budget (port 8003) — budget calculator MCP tool
- **Test**: Each works with mock Wave 1 context

### Step 6: Build Wave 3 Agents
- Logistics (port 8008) — timeline slot MCP tool
- Communication (port 8009) — no custom tools, pure generation
- Supplies (port 8010) — supply cost estimator MCP tool
- **Test**: Each works with mock Wave 1 + 2 context

### Step 7: Full Orchestration Flow
- Update conductor system prompt with all 10 agent tools
- Test full 3-wave execution end-to-end
- Implement budget gate (Claude checks budget after each wave, re-calls agents if over)
- **Test**: Submit "Plan a 50th Anniversary Family Reunion for 40 people in a mountain location this July. Budget $5,000. Elderly grandparents in wheelchairs, three vegans." → get complete blueprint

### Step 8: Docker Compose + Frontend
- Dockerfiles for all 12 services
- `docker-compose.yml` with YAML anchors for shared env
- CopilotKit frontend with chat + agent monitor
- **Test**: `docker compose up` → browser → type prompt → watch agents work → receive blueprint

### Step 9: Polish
- Error handling: agent timeouts (60s), retry once on failure
- Graceful degradation: if an agent fails, mark that section as "unavailable" in blueprint
- User revision: "make it cheaper" → conductor re-runs budget-sensitive agents
- Logging: all A2A calls and claude-agent-sdk messages logged to SQLite

---

## Key Design Decisions

1. **Claude Agent SDK as the runtime for every agent**: Each specialist agent isn't just calling the Claude API for text generation — it runs Claude's full agentic loop with tools, web search, multi-step reasoning, and retry logic. This means agents can self-correct, search for more info, and iterate on their output.

2. **Custom MCP tools per agent**: Each agent registers domain-specific tools (`@tool` decorator → in-process MCP server). Claude decides when to use them. Some agents (Theme, Communication) need no custom tools — they rely purely on Claude's reasoning + web search.

3. **Conductor uses Claude to orchestrate**: Instead of hardcoded DAG logic, the Conductor's Claude instance decides the execution order based on its system prompt. It calls specialist agents via MCP tools that make A2A HTTP calls. This means the orchestration logic can adapt — if Claude notices bad weather, it can re-call the venue agent before proceeding, without us coding that specific flow.

4. **A2A as the inter-service boundary**: Each agent is a standalone HTTP service with a standard A2A endpoint. The Conductor's Claude calls them via MCP tools wrapping HTTP requests. This keeps agents fully independent and testable.

5. **AG-UI for the user layer**: The Conductor streams Claude's output + state updates as AG-UI events. CopilotKit renders the chat and agent monitor. Zero custom frontend beyond CopilotKit components.

6. **Structured output via system prompts**: Each agent's system prompt specifies a JSON output format. The base class extracts JSON from Claude's response. For stricter validation, you can later switch to the SDK's structured output feature.

---

## Cost Considerations

Each agent call triggers a claude-agent-sdk session (which runs Claude Code under the hood). A full 10-agent orchestration will make roughly 11 Claude API calls (1 conductor + 10 agents). With multi-turn reasoning inside each agent, expect 15-30 total API calls per event plan.

**Estimated cost per full event plan**: $0.50 - $2.00 using claude-sonnet-4-20250514, depending on web search usage and reasoning depth.

**Optimizations**:
- Set `max_turns=10` per agent to cap runaway loops
- Use `max_budget_usd` option to cap per-agent spend
- Simple agents (Theme, Communication) may only need 1-2 turns
- Cache Agent Cards on conductor startup (not per-request)

---

## Environment Variables

```env
ANTHROPIC_API_KEY=sk-ant-...
OPEN_METEO_BASE_URL=https://api.open-meteo.com  # free, no key needed
```
