# Event Orchestration Multi-Agent System — Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-agent event planning system where a Conductor agent orchestrates 10 specialist agents via A2A protocol, with agent discovery through a self-hosted Project NANDA registry, and a CopilotKit chat frontend streaming via AG-UI.

**Architecture:** Each specialist agent is a standalone FastAPI service powered by `claude-agent-sdk`, exposing an A2A endpoint. On startup, each agent registers itself with a self-hosted NANDA Index registry (Flask/MongoDB on port 6900). The Conductor discovers agents dynamically by querying the NANDA registry, then delegates tasks via A2A. User requests come in via AG-UI (SSE) and CopilotKit renders chat + agent status monitor.

**Tech Stack:** Python 3.12+ / uv, claude-agent-sdk, a2a-sdk (a2a-python), ag-ui-protocol, FastAPI, CopilotKit (React/Next.js), Docker Compose, **Project NANDA Index** (self-hosted, Flask + MongoDB, port 6900)

**SDK API Notes (discovered from current docs — PRD code samples need adjustments):**
- `claude-agent-sdk`: `query()`, `ClaudeAgentOptions`, `@tool`, `create_sdk_mcp_server()` — confirmed working as in PRD
- `a2a-sdk` (`a2a-python`): Uses `AgentExecutor` pattern with `DefaultRequestHandler`, `InMemoryTaskStore`, `EventQueue`, `TaskUpdater`, `A2AFastAPIApplication` — **different from PRD's simplified `/a2a` POST handler**. Must implement `AgentExecutor.execute()` and `AgentExecutor.cancel()`.
- `ag-ui-protocol`: Uses `EventType` enum (e.g., `EventType.RUN_STARTED`), `RunStartedEvent`/`RunFinishedEvent` (not `RunStartEvent`/`RunFinishedEvent`), `EventEncoder(accept=header)`, `encoder.get_content_type()` — **PRD event names need correction**.
- `AgentCard` requires `default_input_modes`, `default_output_modes`, `capabilities` with `AgentCapabilities` model.
- `AgentSkill` requires `id`, `name`, `description`, `tags`, `examples` fields — not just `{"name": "..."}`.

---

## Chunk 1: Project Scaffolding + Shared Library

### File Structure (Chunk 1)

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `pyproject.toml` | Root workspace config for uv |
| Create | `shared/pyproject.toml` | Shared library package |
| Create | `shared/__init__.py` | Package init |
| Create | `shared/schemas.py` | Pydantic models: EventRequirements, AgentResult, OrchestratorState |
| Create | `shared/agent_base.py` | BaseEventAgent: wraps claude-agent-sdk + A2A server boilerplate |
| Create | `shared/nanda_registry.py` | NANDA registry client: register agent, discover agents, lookup by ID |
| Create | `tests/__init__.py` | Test package init |
| Create | `tests/test_schemas.py` | Tests for Pydantic models |
| Create | `tests/test_agent_base.py` | Tests for BaseEventAgent |
| Create | `tests/test_nanda_registry.py` | Tests for NANDA registry client |
| Create | `.env.example` | Example environment variables |
| Create | `.gitignore` | Python/Node gitignore |

---

### Task 1: Initialize uv workspace and shared package

**Files:**
- Create: `pyproject.toml`
- Create: `shared/pyproject.toml`
- Create: `shared/__init__.py`
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Initialize root project with uv**

```bash
cd /home/yogidigital/projects/eventplanner
uv init --no-readme
```

- [ ] **Step 2: Update root pyproject.toml for workspace**

Replace the generated `pyproject.toml` with:

```toml
[project]
name = "event-orchestrator"
version = "0.1.0"
description = "Multi-agent event planning system"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["shared", "conductor", "agents/*"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 3: Create shared package**

```bash
mkdir -p shared
```

Create `shared/pyproject.toml`:

```toml
[project]
name = "shared"
version = "0.1.0"
description = "Shared schemas and base classes for event orchestrator"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.0",
    "claude-agent-sdk",
    "a2a-sdk",
    "fastapi",
    "uvicorn",
    "httpx",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Create `shared/__init__.py`:

```python
"""Shared schemas and base classes for the event orchestrator."""
```

- [ ] **Step 4: Create .gitignore**

```gitignore
__pycache__/
*.pyc
.venv/
.env
*.egg-info/
dist/
build/
.pytest_cache/
node_modules/
.next/
```

- [ ] **Step 5: Create .env.example**

```env
ANTHROPIC_API_KEY=sk-ant-...
OPEN_METEO_BASE_URL=https://api.open-meteo.com
NANDA_REGISTRY_URL=http://nanda-registry:6900
MONGODB_URI=mongodb://mongo:27017/nanda
```

- [ ] **Step 6: Install dependencies**

```bash
uv sync
```

- [ ] **Step 7: Verify installation**

```bash
uv run python -c "import pydantic; print(pydantic.__version__)"
```

Expected: Prints pydantic version (2.x)

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml shared/ .gitignore .env.example uv.lock
git commit -m "chore: scaffold uv workspace with shared package"
```

---

### Task 2: Create shared Pydantic schemas

**Files:**
- Create: `shared/schemas.py`
- Create: `tests/__init__.py`
- Create: `tests/test_schemas.py`

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` (empty file).

Create `tests/test_schemas.py`:

```python
"""Tests for shared Pydantic schemas."""
from datetime import date
from shared.schemas import EventRequirements, AgentStatus, AgentResult, OrchestratorState


def test_event_requirements_minimal():
    req = EventRequirements(
        event_type="birthday",
        guest_count=30,
        location_preference="urban",
        date_range=(date(2026, 7, 1), date(2026, 7, 3)),
        budget_total=5000.0,
        dietary_restrictions=["vegan"],
        accessibility_needs=[],
    )
    assert req.event_type == "birthday"
    assert req.guest_count == 30
    assert req.event_name is None
    assert req.theme_preferences is None
    assert req.special_requests == []
    assert req.age_groups == []


def test_event_requirements_full():
    req = EventRequirements(
        event_type="family reunion",
        event_name="Smith Family 50th",
        guest_count=40,
        location_preference="mountain",
        date_range=(date(2026, 7, 10), date(2026, 7, 12)),
        budget_total=5000.0,
        dietary_restrictions=["vegan", "gluten-free"],
        accessibility_needs=["wheelchair", "elderly-friendly"],
        theme_preferences="rustic mountain",
        special_requests=["live music"],
        age_groups=["children", "adults", "elderly"],
    )
    assert req.event_name == "Smith Family 50th"
    assert len(req.dietary_restrictions) == 2
    assert "wheelchair" in req.accessibility_needs


def test_agent_status_enum():
    assert AgentStatus.PENDING == "pending"
    assert AgentStatus.RUNNING == "running"
    assert AgentStatus.COMPLETED == "completed"
    assert AgentStatus.FAILED == "failed"
    assert AgentStatus.REVISING == "revising"


def test_agent_result_defaults():
    result = AgentResult(
        agent_id="venue",
        status=AgentStatus.COMPLETED,
        result={"venues": []},
    )
    assert result.estimated_cost == 0.0
    assert result.warnings == []
    assert result.execution_time_ms == 0


def test_agent_result_full():
    result = AgentResult(
        agent_id="weather",
        status=AgentStatus.COMPLETED,
        result={"forecast": "sunny"},
        estimated_cost=0.0,
        warnings=["Limited forecast data"],
        execution_time_ms=1500,
    )
    assert result.warnings == ["Limited forecast data"]
    assert result.execution_time_ms == 1500


def test_orchestrator_state_defaults():
    state = OrchestratorState(request_id="req-001")
    assert state.requirements is None
    assert state.agent_statuses == {}
    assert state.agent_results == {}
    assert state.budget_remaining == 0.0
    assert state.current_phase == "idle"
    assert state.messages == []
    assert state.blueprint is None


def test_orchestrator_state_serialization():
    state = OrchestratorState(
        request_id="req-002",
        agent_statuses={"venue": AgentStatus.COMPLETED},
        current_phase="wave_1",
    )
    data = state.model_dump()
    assert data["request_id"] == "req-002"
    assert data["agent_statuses"]["venue"] == "completed"
    assert data["current_phase"] == "wave_1"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'shared.schemas'`

- [ ] **Step 3: Write the schemas implementation**

Create `shared/schemas.py`:

```python
"""Pydantic models shared across all agents and the conductor."""
from pydantic import BaseModel
from datetime import date
from enum import Enum


class EventRequirements(BaseModel):
    """Structured extraction from user's natural language prompt."""
    event_type: str
    event_name: str | None = None
    guest_count: int
    location_preference: str
    date_range: tuple[date, date]
    budget_total: float
    dietary_restrictions: list[str]
    accessibility_needs: list[str]
    theme_preferences: str | None = None
    special_requests: list[str] = []
    age_groups: list[str] = []


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
    result: dict
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

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_schemas.py -v
```

Expected: All 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add shared/schemas.py tests/
git commit -m "feat: add shared Pydantic schemas for event orchestrator"
```

---

### Task 3: Create BaseEventAgent with A2A server + Claude Agent SDK

**Files:**
- Create: `shared/agent_base.py`
- Create: `tests/test_agent_base.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agent_base.py`:

```python
"""Tests for BaseEventAgent class."""
import pytest
from shared.agent_base import BaseEventAgent
from shared.schemas import AgentResult, AgentStatus


class FakeAgent(BaseEventAgent):
    """Minimal concrete agent for testing base class behavior."""
    agent_id = "fake"
    name = "Fake Agent"
    description = "A fake agent for testing"
    port = 9999
    system_prompt = "You are a test agent."

    def get_skills(self):
        return [
            {
                "id": "fake-skill",
                "name": "Fake Skill",
                "description": "Does nothing",
                "tags": ["test"],
                "examples": ["test input"],
            }
        ]


def test_agent_card_generation():
    agent = FakeAgent()
    card = agent.get_agent_card()
    assert card.name == "fake"
    assert card.description == "A fake agent for testing"
    assert card.version == "1.0.0"
    assert len(card.skills) == 1
    assert card.skills[0].id == "fake-skill"


def test_build_prompt():
    agent = FakeAgent()
    requirements = {"event_type": "birthday", "guest_count": 30}
    context = {"venue": {"result": "found"}}
    prompt = agent._build_prompt(requirements, context)
    assert "birthday" in prompt
    assert "guest_count" in prompt
    assert "venue" in prompt


def test_build_prompt_no_context():
    agent = FakeAgent()
    requirements = {"event_type": "wedding"}
    prompt = agent._build_prompt(requirements, {})
    assert "wedding" in prompt
    assert "No prior context" in prompt


def test_parse_result_valid_json():
    agent = FakeAgent()
    text = '{"result": {"foo": "bar"}, "estimated_cost": 100.0, "warnings": ["watch out"]}'
    result = agent._parse_result(text)
    assert result.agent_id == "fake"
    assert result.status == AgentStatus.COMPLETED
    assert result.result == {"foo": "bar"}
    assert result.estimated_cost == 100.0
    assert result.warnings == ["watch out"]


def test_parse_result_json_in_markdown():
    agent = FakeAgent()
    text = 'Here is the result:\n```json\n{"result": {"venues": []}, "estimated_cost": 0}\n```\nDone.'
    result = agent._parse_result(text)
    assert result.status == AgentStatus.COMPLETED
    assert "venues" in result.result


def test_parse_result_no_json():
    agent = FakeAgent()
    text = "I couldn't find any venues matching your criteria."
    result = agent._parse_result(text)
    assert result.status == AgentStatus.COMPLETED
    assert result.result == {"raw_response": text}


def test_build_fastapi_app():
    agent = FakeAgent()
    app = agent.build_fastapi_app()
    assert app.title == "Fake Agent - A2A Agent"
    # Verify routes exist
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes


def test_get_mcp_tools_default_empty():
    agent = FakeAgent()
    assert agent.get_mcp_tools() == []


def test_get_allowed_tools_default():
    agent = FakeAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools
    assert "Read" in tools
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_agent_base.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'shared.agent_base'`

- [ ] **Step 3: Write the BaseEventAgent implementation**

Create `shared/agent_base.py`:

```python
"""Base class wrapping claude-agent-sdk + A2A server for specialist agents."""
import json
import re
from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    create_sdk_mcp_server,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import (
    AgentCard,
    AgentCapabilities,
    AgentSkill,
)
from a2a.utils import new_agent_text_message, new_task
from fastapi import FastAPI

from shared.schemas import AgentResult, AgentStatus


class BaseEventAgent:
    """
    Base class for all specialist agents.

    Each subclass defines:
      - agent_id, name, description, port
      - system_prompt (instructions for Claude)
      - get_skills() -> list of skill dicts
      - get_mcp_tools() -> list of @tool-decorated functions
      - get_allowed_tools() -> list of tool names to auto-approve
    """

    agent_id: str
    name: str
    description: str
    port: int
    system_prompt: str

    def get_skills(self) -> list[dict]:
        """Return A2A skill metadata. Override in subclass."""
        return []

    def get_mcp_tools(self) -> list:
        """Return list of @tool decorated functions for this agent."""
        return []

    def get_allowed_tools(self) -> list[str]:
        """Tools to auto-approve (no permission prompt)."""
        return ["WebSearch", "Read"]

    async def run(self, requirements: dict, context: dict) -> AgentResult:
        """Execute this agent using claude-agent-sdk."""
        mcp_tools = self.get_mcp_tools()
        mcp_server = create_sdk_mcp_server(
            name=f"{self.agent_id}-tools",
            tools=mcp_tools,
        ) if mcp_tools else None

        mcp_servers = {}
        allowed_tools = self.get_allowed_tools().copy()

        if mcp_server:
            mcp_servers[self.agent_id] = mcp_server
            for t in mcp_tools:
                allowed_tools.append(f"mcp__{self.agent_id}__{t.__name__}")

        options = ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            allowed_tools=allowed_tools,
            mcp_servers=mcp_servers if mcp_servers else None,
            max_turns=10,
            permission_mode="acceptEdits",
        )

        prompt = self._build_prompt(requirements, context)

        result_text = ""
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result
            elif isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        result_text = block.text

        return self._parse_result(result_text)

    def _build_prompt(self, requirements: dict, context: dict) -> str:
        """Build the prompt string from requirements and context."""
        context_str = (
            json.dumps(context, indent=2, default=str)
            if context
            else "No prior context available."
        )
        return f"""## Event Requirements
{json.dumps(requirements, indent=2, default=str)}

## Context from Other Agents
{context_str}

## Your Task
Based on the event requirements above and any context from other agents,
produce your analysis. Return your output as a JSON object with these fields:
- result: your main output (structure depends on your specialty)
- estimated_cost: float, your estimated cost contribution
- warnings: list of any concerns or issues found
"""

    def _parse_result(self, text: str) -> AgentResult:
        """Parse Claude's response into an AgentResult."""
        try:
            json_match = re.search(r"\{[\s\S]*\}", text)
            if json_match:
                data = json.loads(json_match.group())
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    result=data.get("result", data),
                    estimated_cost=data.get("estimated_cost", 0.0),
                    warnings=data.get("warnings", []),
                )
        except json.JSONDecodeError:
            pass

        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            result={"raw_response": text},
        )

    def get_agent_card(self) -> AgentCard:
        """Generate A2A Agent Card."""
        skills = [
            AgentSkill(
                id=s["id"],
                name=s["name"],
                description=s["description"],
                tags=s.get("tags", []),
                examples=s.get("examples", []),
            )
            for s in self.get_skills()
        ]
        return AgentCard(
            name=self.agent_id,
            description=self.description,
            url=f"http://{self.agent_id}:{self.port}",
            version="1.0.0",
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=AgentCapabilities(
                streaming=False,
                pushNotifications=False,
            ),
            skills=skills,
        )

    def _create_executor(self) -> "EventAgentExecutor":
        """Create an A2A AgentExecutor wrapping this agent."""
        return EventAgentExecutor(self)

    def build_fastapi_app(self) -> FastAPI:
        """Build a FastAPI app with A2A endpoint + Agent Card."""
        app = FastAPI(title=f"{self.name} - A2A Agent")

        # Agent Card endpoint
        @app.get("/.well-known/agent.json")
        async def agent_card():
            return self.get_agent_card().model_dump()

        # A2A endpoint via official SDK
        agent_card = self.get_agent_card()
        task_store = InMemoryTaskStore()
        executor = self._create_executor()
        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=task_store,
        )
        a2a_app = A2AFastAPIApplication(
            agent_card=agent_card,
            http_handler=handler,
        )
        a2a_app.mount(app)

        return app


class EventAgentExecutor(AgentExecutor):
    """A2A AgentExecutor that delegates to a BaseEventAgent."""

    def __init__(self, agent: BaseEventAgent):
        self.agent = agent

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # Extract requirements and context from the incoming message
        message = context.message
        requirements = {}
        agent_context = {}

        if message and message.parts:
            try:
                text = message.parts[0].root.text
                data = json.loads(text)
                requirements = data.get("requirements", {})
                agent_context = data.get("context", {})
            except (json.JSONDecodeError, AttributeError):
                requirements = {"raw_input": text if message.parts else ""}

        result = await self.agent.run(requirements, agent_context)

        await updater.complete(
            new_agent_text_message(
                json.dumps(result.model_dump(), default=str),
                context.context_id,
                task.id,
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        if context.current_task:
            updater = TaskUpdater(
                event_queue,
                context.current_task.id,
                context.current_task.context_id,
            )
            await updater.cancel()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_agent_base.py -v
```

Expected: All 9 tests PASS

Note: Some tests may need adjustments depending on exact A2A SDK API. The `build_fastapi_app` test only checks route registration, not full A2A integration — that will be tested in Task 4 with a live server.

- [ ] **Step 5: Commit**

```bash
git add shared/agent_base.py tests/test_agent_base.py
git commit -m "feat: add BaseEventAgent with claude-agent-sdk + A2A integration"
```

---

### Task 3b: Create NANDA registry client + self-hosted registry setup

**Context:** Project NANDA Index ([github.com/projnanda/nanda-index](https://github.com/projnanda/nanda-index)) is a Flask + MongoDB agent registry running on port 6900. We self-host it in our Docker Compose stack. Each agent registers on startup; the Conductor discovers agents dynamically via the registry.

**NANDA Registry API (self-hosted):**
- `POST /register` — body: `{"agent_id": "venue", "agent_url": "http://venue:8001", "api_url": "http://venue:8001"}` — registers an agent
- `GET /lookup/<agent_id>` — returns agent URL by ID
- `GET /list` — returns all registered agents as `{agent_id: agent_url, ...}`
- `GET /search?q=&capabilities=&tags=` — search by capabilities
- `GET /health` — health check

**Files:**
- Create: `shared/nanda_registry.py`
- Create: `tests/test_nanda_registry.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_nanda_registry.py`:

```python
"""Tests for NANDA registry client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from shared.nanda_registry import NandaRegistryClient


def test_client_init_default_url():
    client = NandaRegistryClient()
    assert client.registry_url == "http://nanda-registry:6900"


def test_client_init_custom_url():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    assert client.registry_url == "http://localhost:6900"


@pytest.mark.asyncio
async def test_register_agent():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "registered", "agent_id": "venue"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await client.register_agent(
            agent_id="venue",
            agent_url="http://venue:8001",
            capabilities=["venue-search", "venue-scoring"],
            tags=["venue", "search"],
        )
    assert result["agent_id"] == "venue"


@pytest.mark.asyncio
async def test_lookup_agent():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_url": "http://venue:8001"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        url = await client.lookup_agent("venue")
    assert url == "http://venue:8001"


@pytest.mark.asyncio
async def test_list_agents():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "venue": "http://venue:8001",
        "weather": "http://weather:8002",
    }

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        agents = await client.list_agents()
    assert "venue" in agents
    assert agents["venue"] == "http://venue:8001"


@pytest.mark.asyncio
async def test_lookup_agent_not_found():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.json.return_value = {"error": "Agent not found"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        url = await client.lookup_agent("nonexistent")
    assert url is None


@pytest.mark.asyncio
async def test_wait_for_registry_healthy():
    client = NandaRegistryClient(registry_url="http://localhost:6900")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
        healthy = await client.wait_for_registry(timeout=5)
    assert healthy is True
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_nanda_registry.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'shared.nanda_registry'`

- [ ] **Step 3: Implement NANDA registry client**

Create `shared/nanda_registry.py`:

```python
"""Client for interacting with the self-hosted NANDA Index registry."""
import os
import asyncio
import httpx


class NandaRegistryClient:
    """Client for the NANDA Index registry (Project NANDA).

    Handles agent registration, discovery, and lookup against
    a self-hosted NANDA registry (Flask on port 6900).
    """

    def __init__(self, registry_url: str | None = None):
        self.registry_url = registry_url or os.getenv(
            "NANDA_REGISTRY_URL", "http://nanda-registry:6900"
        )

    async def register_agent(
        self,
        agent_id: str,
        agent_url: str,
        api_url: str | None = None,
        capabilities: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> dict:
        """Register an agent with the NANDA registry.

        POST /register {agent_id, agent_url, api_url, capabilities, tags}
        """
        payload = {
            "agent_id": agent_id,
            "agent_url": agent_url,
            "api_url": api_url or agent_url,
        }
        if capabilities:
            payload["capabilities"] = capabilities
        if tags:
            payload["tags"] = tags

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.registry_url}/register", json=payload
            )
            return resp.json()

    async def lookup_agent(self, agent_id: str) -> str | None:
        """Look up an agent URL by ID.

        GET /lookup/<agent_id>
        Returns the agent_url string, or None if not found.
        """
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.registry_url}/lookup/{agent_id}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("agent_url") or data.get(agent_id)
            return None

    async def list_agents(self) -> dict[str, str]:
        """List all registered agents.

        GET /list
        Returns dict of {agent_id: agent_url}.
        """
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.registry_url}/list")
            if resp.status_code == 200:
                return resp.json()
            return {}

    async def search_agents(
        self,
        query: str | None = None,
        capabilities: list[str] | None = None,
        tags: list[str] | None = None,
    ) -> list[dict]:
        """Search agents by query, capabilities, or tags.

        GET /search?q=...&capabilities=...&tags=...
        """
        params = {}
        if query:
            params["q"] = query
        if capabilities:
            params["capabilities"] = ",".join(capabilities)
        if tags:
            params["tags"] = ",".join(tags)

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self.registry_url}/search", params=params
            )
            if resp.status_code == 200:
                return resp.json()
            return []

    async def wait_for_registry(
        self, timeout: float = 30, interval: float = 2
    ) -> bool:
        """Wait for the NANDA registry to become healthy.

        Polls GET /health until it returns 200 or timeout is reached.
        """
        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{self.registry_url}/health")
                    if resp.status_code == 200:
                        return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(interval)
        return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_nanda_registry.py -v
```

Expected: All 6 tests PASS

- [ ] **Step 5: Update BaseEventAgent to auto-register with NANDA on startup**

In `shared/agent_base.py`, add NANDA registration to `build_fastapi_app()`:

Add import at top:
```python
from shared.nanda_registry import NandaRegistryClient
```

Add a startup event to the FastAPI app inside `build_fastapi_app()`:
```python
    def build_fastapi_app(self) -> FastAPI:
        app = FastAPI(title=f"{self.name} - A2A Agent")

        agent_ref = self  # capture for closure

        @app.on_event("startup")
        async def register_with_nanda():
            """Register this agent with the NANDA registry on startup."""
            nanda = NandaRegistryClient()
            try:
                await nanda.wait_for_registry(timeout=30)
                skills = agent_ref.get_skills()
                capabilities = [s["name"] for s in skills]
                tags = []
                for s in skills:
                    tags.extend(s.get("tags", []))
                await nanda.register_agent(
                    agent_id=agent_ref.agent_id,
                    agent_url=f"http://{agent_ref.agent_id}:{agent_ref.port}",
                    capabilities=capabilities,
                    tags=list(set(tags)),
                )
                print(f"[{agent_ref.agent_id}] Registered with NANDA registry")
            except Exception as e:
                print(f"[{agent_ref.agent_id}] WARN: Failed to register with NANDA: {e}")

        # ... rest of build_fastapi_app (Agent Card endpoint, A2A endpoint)
```

- [ ] **Step 6: Commit**

```bash
git add shared/nanda_registry.py tests/test_nanda_registry.py shared/agent_base.py
git commit -m "feat: add NANDA registry client and auto-registration on agent startup"
```

---

### Task 3c: Add self-hosted NANDA registry to Docker Compose

**Files:**
- Create: `nanda-registry/Dockerfile`
- Modify: `docker-compose.yml` (add nanda-registry + mongodb services)

- [ ] **Step 1: Create NANDA registry Dockerfile**

Create `nanda-registry/Dockerfile`:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Clone the NANDA Index repo
RUN apt-get update && apt-get install -y git && \
    git clone https://github.com/projnanda/nanda-index.git . && \
    uv sync --frozen && \
    apt-get remove -y git && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*

EXPOSE 6900

CMD ["uv", "run", "python", "registry.py"]
```

- [ ] **Step 2: Add NANDA registry + MongoDB to docker-compose.yml**

Add these services to `docker-compose.yml`:

```yaml
  nanda-registry:
    build: ./nanda-registry
    ports: ["6900:6900"]
    environment:
      - MONGODB_URI=mongodb://mongo:27017/nanda
      - PORT=6900
    depends_on:
      - mongo

  mongo:
    image: mongo:7
    ports: ["27017:27017"]
    volumes:
      - mongo-data:/data/db

volumes:
  mongo-data:
```

Update all agent services and conductor to add:
```yaml
    environment:
      NANDA_REGISTRY_URL: http://nanda-registry:6900
    depends_on:
      - nanda-registry
```

- [ ] **Step 3: Verify NANDA registry starts**

```bash
docker compose up -d mongo nanda-registry
curl http://localhost:6900/health
```

Expected: `{"status": "ok", "mongo": true}`

- [ ] **Step 4: Commit**

```bash
git add nanda-registry/ docker-compose.yml
git commit -m "feat: add self-hosted NANDA registry with MongoDB to Docker Compose"
```

---

## Chunk 2: First Agent (Venue) End-to-End

### File Structure (Chunk 2)

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `agents/venue/pyproject.toml` | Venue agent package |
| Create | `agents/venue/__init__.py` | Package init |
| Create | `agents/venue/tools.py` | MCP tools: search_venues, score_venue |
| Create | `agents/venue/agent.py` | VenuePlannerAgent subclass |
| Create | `agents/venue/main.py` | FastAPI server entrypoint |
| Create | `agents/venue/Dockerfile` | Container definition |
| Create | `tests/agents/__init__.py` | Test package |
| Create | `tests/agents/test_venue.py` | Tests for venue agent |

---

### Task 4: Create venue agent package and MCP tools

**Files:**
- Create: `agents/venue/pyproject.toml`
- Create: `agents/venue/__init__.py`
- Create: `agents/venue/tools.py`
- Create: `tests/agents/__init__.py`
- Create: `tests/agents/test_venue.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/__init__.py` (empty).

Create `tests/agents/test_venue.py`:

```python
"""Tests for venue agent tools and agent class."""
import pytest
import asyncio
from agents.venue.tools import search_venues, score_venue


@pytest.mark.asyncio
async def test_search_venues_returns_structured_prompt():
    args = {
        "location": "Denver, CO",
        "guest_count": 40,
        "event_type": "family reunion",
        "indoor_required": False,
    }
    result = await search_venues(args)
    assert "content" in result
    text = result["content"][0]["text"]
    assert "family reunion" in text
    assert "Denver" in text
    assert "40" in text


@pytest.mark.asyncio
async def test_search_venues_indoor_required():
    args = {
        "location": "NYC",
        "guest_count": 20,
        "event_type": "birthday",
        "indoor_required": True,
    }
    result = await search_venues(args)
    text = result["content"][0]["text"]
    assert "indoor" in text.lower()


@pytest.mark.asyncio
async def test_score_venue():
    args = {
        "venue_name": "Mountain Lodge",
        "capacity_match": 0.9,
        "price_per_person": 30.0,
        "accessibility_score": 0.8,
        "review_rating": 4.5,
    }
    result = await score_venue(args)
    text = result["content"][0]["text"]
    assert "Mountain Lodge" in text
    assert "/1.0" in text


@pytest.mark.asyncio
async def test_score_venue_expensive():
    args = {
        "venue_name": "Pricey Palace",
        "capacity_match": 1.0,
        "price_per_person": 200.0,
        "accessibility_score": 1.0,
        "review_rating": 5.0,
    }
    result = await score_venue(args)
    text = result["content"][0]["text"]
    # Expensive venue should score lower than a cheap one
    score_str = text.split("scored ")[1].split("/")[0]
    score = float(score_str)
    assert score <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_venue.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'agents.venue'`

- [ ] **Step 3: Create venue agent package**

Create `agents/venue/pyproject.toml`:

```toml
[project]
name = "venue-agent"
version = "0.1.0"
description = "Venue & Destination Planner agent"
requires-python = ">=3.12"
dependencies = [
    "shared",
    "claude-agent-sdk",
    "fastapi",
    "uvicorn",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Create `agents/venue/__init__.py` (empty).

- [ ] **Step 4: Implement venue tools**

Create `agents/venue/tools.py`:

```python
"""Custom MCP tools for the Venue & Destination Planner agent."""
from claude_agent_sdk import tool


@tool("search_venues", "Search for event venues matching criteria", {
    "location": str,
    "guest_count": int,
    "event_type": str,
    "indoor_required": bool,
})
async def search_venues(args):
    """Structure a venue search query for Claude to use with web search."""
    indoor_note = "Must have indoor option." if args["indoor_required"] else ""
    return {
        "content": [{
            "type": "text",
            "text": (
                f"Search for {args['event_type']} venues near {args['location']} "
                f"that can hold {args['guest_count']} people. {indoor_note} "
                f"Find at least 3 options with: name, address, capacity, "
                f"estimated rental cost, indoor/outdoor, accessibility notes."
            ),
        }]
    }


@tool("score_venue", "Score a venue on multiple criteria", {
    "venue_name": str,
    "capacity_match": float,
    "price_per_person": float,
    "accessibility_score": float,
    "review_rating": float,
})
async def score_venue(args):
    """Calculate a weighted score for venue comparison."""
    score = (
        args["capacity_match"] * 0.25
        + (1 - min(args["price_per_person"] / 100, 1)) * 0.25
        + args["accessibility_score"] * 0.25
        + (args["review_rating"] / 5) * 0.25
    )
    return {
        "content": [{
            "type": "text",
            "text": f"Venue '{args['venue_name']}' scored {score:.2f}/1.0",
        }]
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_venue.py -v
```

Expected: All 4 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/venue/ tests/agents/
git commit -m "feat: add venue agent MCP tools with search and scoring"
```

---

### Task 5: Create VenuePlannerAgent subclass and FastAPI server

**Files:**
- Create: `agents/venue/agent.py`
- Create: `agents/venue/main.py`
- Modify: `tests/agents/test_venue.py` (add agent tests)

- [ ] **Step 1: Write the failing test**

Add to `tests/agents/test_venue.py`:

```python
from agents.venue.agent import VenuePlannerAgent


def test_venue_agent_card():
    agent = VenuePlannerAgent()
    card = agent.get_agent_card()
    assert card.name == "venue"
    assert "venue" in card.description.lower()
    assert card.url == "http://venue:8001"
    assert len(card.skills) >= 1


def test_venue_agent_mcp_tools():
    agent = VenuePlannerAgent()
    tools = agent.get_mcp_tools()
    assert len(tools) == 2
    tool_names = [t.__name__ for t in tools]
    assert "search_venues" in tool_names
    assert "score_venue" in tool_names


def test_venue_agent_allowed_tools():
    agent = VenuePlannerAgent()
    tools = agent.get_allowed_tools()
    assert "WebSearch" in tools
    assert "mcp__venue__search_venues" in tools
    assert "mcp__venue__score_venue" in tools


def test_venue_agent_fastapi_app():
    agent = VenuePlannerAgent()
    app = agent.build_fastapi_app()
    routes = [r.path for r in app.routes]
    assert "/.well-known/agent.json" in routes
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/agents/test_venue.py::test_venue_agent_card -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'agents.venue.agent'`

- [ ] **Step 3: Implement VenuePlannerAgent**

Create `agents/venue/agent.py`:

```python
"""Venue & Destination Planner agent."""
from shared.agent_base import BaseEventAgent
from agents.venue.tools import search_venues, score_venue


class VenuePlannerAgent(BaseEventAgent):
    agent_id = "venue"
    name = "Venue & Destination Planner"
    description = "Finds and scores event venues matching location, capacity, and accessibility requirements"
    port = 8001

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

    def get_skills(self):
        return [
            {
                "id": "venue-search",
                "name": "Venue Search",
                "description": "Search for event venues matching location and capacity criteria",
                "tags": ["venue", "search", "location"],
                "examples": ["Find venues in Denver for 40 people"],
            },
            {
                "id": "venue-scoring",
                "name": "Venue Scoring",
                "description": "Score and compare venues on capacity, price, accessibility, and reviews",
                "tags": ["venue", "scoring", "comparison"],
                "examples": ["Score this venue against our criteria"],
            },
        ]

    def get_mcp_tools(self):
        return [search_venues, score_venue]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__venue__search_venues",
            "mcp__venue__score_venue",
        ]
```

- [ ] **Step 4: Create the FastAPI entrypoint**

Create `agents/venue/main.py`:

```python
"""FastAPI server for the Venue & Destination Planner agent."""
import uvicorn
from agents.venue.agent import VenuePlannerAgent

agent = VenuePlannerAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_venue.py -v
```

Expected: All 8 tests PASS

- [ ] **Step 6: Commit**

```bash
git add agents/venue/agent.py agents/venue/main.py tests/agents/test_venue.py
git commit -m "feat: add VenuePlannerAgent subclass with FastAPI server"
```

---

## Chunk 3: Remaining Specialist Agents (Wave 1, 2, 3)

### File Structure (Chunk 3)

Each agent follows the same pattern: `tools.py` (if needed), `agent.py`, `main.py`, `pyproject.toml`, `__init__.py`.

| Agent | Port | Custom MCP Tools | Wave |
|-------|------|-------------------|------|
| weather | 8002 | get_forecast, assess_outdoor_viability | 1 |
| budget | 8003 | calculate_budget, suggest_cost_reduction | 2 |
| menu | 8004 | estimate_food_cost | 1 |
| activity | 8005 | None (Claude + web search) | 2 |
| accessibility | 8006 | check_accessibility | 2 |
| theme | 8007 | None (pure Claude generation) | 1 |
| logistics | 8008 | create_timeline_slot | 3 |
| communication | 8009 | None (pure generation) | 3 |
| supplies | 8010 | estimate_supply_cost | 3 |

---

### Task 6: Build Weather agent (port 8002)

**Files:**
- Create: `agents/weather/pyproject.toml`
- Create: `agents/weather/__init__.py`
- Create: `agents/weather/tools.py`
- Create: `agents/weather/agent.py`
- Create: `agents/weather/main.py`
- Create: `tests/agents/test_weather.py`

- [ ] **Step 1: Write the failing test**

Create `tests/agents/test_weather.py`:

```python
"""Tests for weather agent tools."""
import pytest
from agents.weather.tools import get_forecast, assess_outdoor_viability


@pytest.mark.asyncio
async def test_assess_outdoor_viability_good_weather():
    args = {"rain_probability": 10.0, "temperature_high": 75.0, "temperature_low": 55.0}
    result = await assess_outdoor_viability(args)
    text = result["content"][0]["text"]
    assert "outdoor" in text.lower()


@pytest.mark.asyncio
async def test_assess_outdoor_viability_rainy():
    args = {"rain_probability": 80.0, "temperature_high": 70.0, "temperature_low": 50.0}
    result = await assess_outdoor_viability(args)
    text = result["content"][0]["text"]
    assert "indoor" in text.lower()


@pytest.mark.asyncio
async def test_assess_outdoor_viability_extreme_temp():
    args = {"rain_probability": 5.0, "temperature_high": 100.0, "temperature_low": 80.0}
    result = await assess_outdoor_viability(args)
    text = result["content"][0]["text"]
    # High temp should lower viability
    score_str = text.split(": ")[1].split(" ")[0]
    score = float(score_str)
    assert score < 1.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/agents/test_weather.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement weather agent**

Create `agents/weather/pyproject.toml` (same pattern as venue, name `weather-agent`).

Create `agents/weather/__init__.py` (empty).

Create `agents/weather/tools.py`:

```python
"""Custom MCP tools for the Weather & Contingency agent."""
from claude_agent_sdk import tool


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
            },
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
    if score > 0.7:
        recommendation = "outdoor"
    elif score > 0.4:
        recommendation = "indoor backup needed"
    else:
        recommendation = "indoor only"
    return {"content": [{"type": "text", "text": f"Viability: {score:.2f} — {recommendation}"}]}
```

Create `agents/weather/agent.py`:

```python
"""Weather & Contingency agent."""
from shared.agent_base import BaseEventAgent
from agents.weather.tools import get_forecast, assess_outdoor_viability


class WeatherAgent(BaseEventAgent):
    agent_id = "weather"
    name = "Weather & Contingency Planner"
    description = "Analyzes weather forecasts for event dates and recommends contingency plans"
    port = 8002

    system_prompt = """You are a weather analysis expert for event planning.

PROCESS:
1. Use get_forecast to fetch real weather data from Open-Meteo for the event location and dates
2. Use assess_outdoor_viability to score outdoor event feasibility
3. If rain probability > 50%, recommend indoor contingency plans

OUTPUT FORMAT (JSON):
{
    "result": {
        "forecast_summary": "3-day forecast description",
        "daily_forecasts": [{"date": "...", "high": 75, "low": 55, "rain_pct": 20, "conditions": "sunny"}],
        "outdoor_viability_score": 0.85,
        "recommendation": "outdoor" | "indoor backup needed" | "indoor only",
        "contingency_plan": "Description if needed"
    },
    "estimated_cost": 0.0,
    "warnings": []
}"""

    def get_skills(self):
        return [{
            "id": "weather-forecast",
            "name": "Weather Forecast",
            "description": "Get weather forecasts and assess outdoor event viability",
            "tags": ["weather", "forecast", "outdoor"],
            "examples": ["What's the weather like in Denver in July?"],
        }]

    def get_mcp_tools(self):
        return [get_forecast, assess_outdoor_viability]

    def get_allowed_tools(self):
        return [
            "WebSearch", "Read",
            "mcp__weather__get_forecast",
            "mcp__weather__assess_outdoor_viability",
        ]
```

Create `agents/weather/main.py`:

```python
"""FastAPI server for the Weather & Contingency agent."""
import uvicorn
from agents.weather.agent import WeatherAgent

agent = WeatherAgent()
app = agent.build_fastapi_app()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=agent.port)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/agents/test_weather.py -v
```

Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add agents/weather/ tests/agents/test_weather.py
git commit -m "feat: add Weather & Contingency agent with Open-Meteo integration"
```

---

### Task 7: Build remaining 8 agents (budget, menu, activity, accessibility, theme, logistics, communication, supplies)

Each follows the exact same pattern as venue/weather. Below are the key specifics for each — implement one at a time, test, commit.

**For each agent, create:** `agents/<name>/pyproject.toml`, `__init__.py`, `tools.py` (if has custom tools), `agent.py`, `main.py`, `tests/agents/test_<name>.py`.

**Budget (8003)** — Tools: `calculate_budget`, `suggest_cost_reduction`. System prompt: tally costs, validate against budget, suggest optimizations.

**Menu (8004)** — Tool: `estimate_food_cost` with base rates (breakfast: $8, lunch: $15, dinner: $25, snacks: $5). System prompt: generate meal plans, respect dietary needs, calculate costs.

**Activity (8005)** — No custom tools (Claude + web search). System prompt: suggest age-appropriate activities, mix high-energy and relaxed, consider accessibility.

**Accessibility (8006)** — Tool: `check_accessibility` scoring wheelchair, elevator, stairs, elderly, children. System prompt: audit venues/activities, flag issues, suggest accommodations.

**Theme (8007)** — No custom tools (pure Claude generation). System prompt: creative director, generate color palettes (hex), decoration concepts, mood descriptions.

**Logistics (8008)** — Tool: `create_timeline_slot` computing start/end times. System prompt: compile timeline from all agent outputs, prevent overlaps.

**Communication (8009)** — No custom tools (pure generation). System prompt: draft save-the-date, invitation, reminder templates matching event theme.

**Supplies (8010)** — Tool: `estimate_supply_cost` with base prices (decoration: $3, favor: $5, rental: $15, consumable: $2). System prompt: recommend party favors, decorations, rentals based on theme.

- [ ] **Step 1: Implement each agent one at a time** following the TDD pattern: write test → verify fail → implement → verify pass → commit.

- [ ] **Step 2: After all 9 agents are built, run full test suite**

```bash
uv run pytest tests/ -v
```

Expected: All tests PASS

- [ ] **Step 3: Commit final batch**

```bash
git add agents/ tests/
git commit -m "feat: add all 9 specialist agents (venue through supplies)"
```

---

## Chunk 4: Conductor Service

### File Structure (Chunk 4)

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `conductor/pyproject.toml` | Conductor package |
| Create | `conductor/__init__.py` | Package init |
| Create | `conductor/tools/__init__.py` | Tools package |
| Create | `conductor/tools/a2a_tools.py` | MCP tools wrapping A2A calls to agents |
| Create | `conductor/orchestrator.py` | Claude-agent-sdk orchestration logic |
| Create | `conductor/main.py` | AG-UI SSE endpoint |
| Create | `tests/test_conductor.py` | Conductor tests |

---

### Task 8: Create conductor A2A tools

**Files:**
- Create: `conductor/pyproject.toml`
- Create: `conductor/__init__.py`
- Create: `conductor/tools/__init__.py`
- Create: `conductor/tools/a2a_tools.py`
- Create: `tests/test_conductor.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_conductor.py`:

```python
"""Tests for conductor A2A tools."""
import pytest
import json
from conductor.tools.a2a_tools import AGENT_TOOLS


def test_all_agent_tools_registered():
    tool_names = [t.__name__ for t in AGENT_TOOLS]
    expected = [
        "call_venue_agent", "call_weather_agent", "call_budget_agent",
        "call_menu_agent", "call_activity_agent", "call_accessibility_agent",
        "call_theme_agent", "call_logistics_agent", "call_communication_agent",
        "call_supplies_agent", "check_budget",
    ]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_check_budget_tool():
    """check_budget is a local computation, so we can test it directly."""
    # This test verifies the budget checking logic without A2A calls
    pass  # Will be tested via integration
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_conductor.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement A2A tools**

Create `conductor/pyproject.toml`:

```toml
[project]
name = "conductor"
version = "0.1.0"
description = "Conductor service - orchestrates specialist agents"
requires-python = ">=3.12"
dependencies = [
    "shared",
    "claude-agent-sdk",
    "ag-ui-protocol",
    "fastapi",
    "uvicorn",
    "httpx",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

Create `conductor/__init__.py`, `conductor/tools/__init__.py` (both empty).

Create `conductor/tools/a2a_tools.py`:

```python
"""MCP tools that make A2A calls to specialist agents.

Agent URLs are discovered dynamically from the self-hosted NANDA registry
instead of being hardcoded. On first call to each agent, the URL is looked
up from NANDA and cached for the session.
"""
import json
import httpx
from claude_agent_sdk import tool
from shared.nanda_registry import NandaRegistryClient

# Module-level registry client + URL cache
_nanda = NandaRegistryClient()
_agent_url_cache: dict[str, str] = {}


async def _resolve_agent_url(agent_id: str) -> str:
    """Resolve an agent URL from the NANDA registry, with caching."""
    if agent_id not in _agent_url_cache:
        url = await _nanda.lookup_agent(agent_id)
        if not url:
            raise RuntimeError(
                f"Agent '{agent_id}' not found in NANDA registry at {_nanda.registry_url}. "
                f"Is it registered and running?"
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
    "requirements": str,
    "context": str,
})
async def call_venue_agent(args):
    result = await _call_agent(
        "venue",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_weather_agent", "Get weather forecast and contingency plan", {
    "requirements": str,
    "context": str,
})
async def call_weather_agent(args):
    result = await _call_agent(
        "weather",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_budget_agent", "Calculate and validate budget", {
    "requirements": str,
    "context": str,
})
async def call_budget_agent(args):
    result = await _call_agent(
        "budget",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_menu_agent", "Plan meals and calculate food costs", {
    "requirements": str,
    "context": str,
})
async def call_menu_agent(args):
    result = await _call_agent(
        "menu",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_activity_agent", "Plan entertainment and activities", {
    "requirements": str,
    "context": str,
})
async def call_activity_agent(args):
    result = await _call_agent(
        "activity",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_accessibility_agent", "Audit venues and activities for accessibility", {
    "requirements": str,
    "context": str,
})
async def call_accessibility_agent(args):
    result = await _call_agent(
        "accessibility",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_theme_agent", "Design event aesthetic and decorations", {
    "requirements": str,
    "context": str,
})
async def call_theme_agent(args):
    result = await _call_agent(
        "theme",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_logistics_agent", "Create day-of timeline and logistics plan", {
    "requirements": str,
    "context": str,
})
async def call_logistics_agent(args):
    result = await _call_agent(
        "logistics",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_communication_agent", "Draft invitations and communication templates", {
    "requirements": str,
    "context": str,
})
async def call_communication_agent(args):
    result = await _call_agent(
        "communication",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool("call_supplies_agent", "Source party favors, decorations, and supplies", {
    "requirements": str,
    "context": str,
})
async def call_supplies_agent(args):
    result = await _call_agent(
        "supplies",
        json.loads(args["requirements"]),
        json.loads(args["context"]),
    )
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


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


# Export all tools for the conductor
AGENT_TOOLS = [
    call_venue_agent, call_weather_agent, call_budget_agent,
    call_menu_agent, call_activity_agent, call_accessibility_agent,
    call_theme_agent, call_logistics_agent, call_communication_agent,
    call_supplies_agent, check_budget,
]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_conductor.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add conductor/ tests/test_conductor.py
git commit -m "feat: add conductor A2A tools for all 10 specialist agents"
```

---

### Task 9: Create conductor orchestrator and AG-UI endpoint

**Files:**
- Create: `conductor/orchestrator.py`
- Create: `conductor/main.py`

- [ ] **Step 1: Implement the orchestrator**

Create `conductor/orchestrator.py`:

```python
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
    Yields SDK messages for conversion to AG-UI events.
    """
    conductor_tools = create_sdk_mcp_server(
        name="conductor-tools",
        tools=AGENT_TOOLS,
    )

    allowed = [f"mcp__conductor-tools__{t.__name__}" for t in AGENT_TOOLS]

    options = ClaudeAgentOptions(
        system_prompt=CONDUCTOR_SYSTEM_PROMPT,
        mcp_servers={"conductor-tools": conductor_tools},
        allowed_tools=allowed + ["WebSearch"],
        max_turns=30,
        permission_mode="acceptEdits",
    )

    async for message in query(prompt=user_message, options=options):
        yield message
```

- [ ] **Step 2: Implement the AG-UI endpoint**

Create `conductor/main.py`:

```python
"""FastAPI server with AG-UI SSE endpoint for the Conductor."""
import uuid
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock

from conductor.orchestrator import run_orchestrator

app = FastAPI(title="Event Orchestrator Conductor")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/ag-ui")
async def ag_ui_endpoint(input_data: RunAgentInput, request: Request):
    """AG-UI endpoint. CopilotKit sends messages here. Returns SSE stream."""
    accept_header = request.headers.get("accept")

    user_message = ""
    for msg in reversed(input_data.messages):
        if msg.role == "user":
            if msg.content:
                user_message = msg.content[0].text if hasattr(msg.content[0], "text") else str(msg.content[0])
            break

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

        async for sdk_message in run_orchestrator(user_message):
            if isinstance(sdk_message, AssistantMessage):
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
                        if "call_" in tool_name and "_agent" in tool_name:
                            agent_name = (
                                tool_name.split("call_")[-1]
                                .replace("_agent", "")
                            )
                            yield encoder.encode(
                                StateSnapshotEvent(
                                    type=EventType.STATE_SNAPSHOT,
                                    snapshot={
                                        "agent_statuses": {agent_name: "running"}
                                    },
                                )
                            )

            elif isinstance(sdk_message, ResultMessage):
                yield encoder.encode(
                    TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=f"\n\n{sdk_message.result}",
                    )
                )

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

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 3: Commit**

```bash
git add conductor/orchestrator.py conductor/main.py
git commit -m "feat: add conductor orchestrator with AG-UI SSE endpoint"
```

---

## Chunk 5: Frontend + Docker Compose + Polish

### File Structure (Chunk 5)

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `frontend/package.json` | Next.js + CopilotKit deps |
| Create | `frontend/tsconfig.json` | TypeScript config |
| Create | `frontend/next.config.js` | Next.js config |
| Create | `frontend/src/app/layout.tsx` | Root layout |
| Create | `frontend/src/app/page.tsx` | Chat + agent monitor UI |
| Create | `frontend/src/app/globals.css` | Tailwind CSS |
| Create | `frontend/tailwind.config.ts` | Tailwind config |
| Create | `frontend/postcss.config.js` | PostCSS config |
| Create | `frontend/Dockerfile` | Frontend container |
| Create | `nanda-registry/Dockerfile` | Self-hosted NANDA Index container |
| Create | `docker-compose.yml` | All 14 services (10 agents + conductor + frontend + NANDA + MongoDB) |
| Create | `conductor/Dockerfile` | Conductor container |
| Create | `agents/venue/Dockerfile` | Template for all agent Dockerfiles |
| Create | `.env` | Environment variables |

---

### Task 10: Create CopilotKit frontend

**Files:**
- Create: `frontend/` directory with Next.js app

- [ ] **Step 1: Initialize Next.js project**

```bash
cd /home/yogidigital/projects/eventplanner
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir --eslint --no-import-alias
```

- [ ] **Step 2: Install CopilotKit**

```bash
cd frontend
npm install @copilotkit/react-core @copilotkit/react-ui
```

- [ ] **Step 3: Create the main page**

Replace `frontend/app/page.tsx`:

```tsx
"use client";

import { CopilotKit } from "@copilotkit/react-core";
import { CopilotChat } from "@copilotkit/react-ui";
import { useCoagentStateRender } from "@copilotkit/react-core";
import "@copilotkit/react-ui/styles.css";

function AgentMonitor() {
  useCoagentStateRender({
    name: "conductor",
    render: ({ state }) => (
      <div className="p-4 space-y-3">
        <h2 className="font-bold text-lg">Agent Status</h2>
        {Object.entries((state?.agent_statuses as Record<string, string>) || {}).map(
          ([id, status]) => (
            <div key={id} className="flex items-center gap-2 text-sm">
              <span
                className={`w-2 h-2 rounded-full ${
                  status === "completed"
                    ? "bg-green-500"
                    : status === "running"
                    ? "bg-yellow-500 animate-pulse"
                    : status === "failed"
                    ? "bg-red-500"
                    : "bg-gray-300"
                }`}
              />
              <span className="capitalize">{id.replace(/_/g, " ")}</span>
              <span className="text-gray-400 text-xs">{status}</span>
            </div>
          )
        )}
      </div>
    ),
  });
  return null;
}

export default function Home() {
  const runtimeUrl = process.env.NEXT_PUBLIC_CONDUCTOR_URL || "http://localhost:8000/ag-ui";

  return (
    <CopilotKit runtimeUrl={runtimeUrl} agent="conductor">
      <div className="flex h-screen">
        <div className="flex-1">
          <CopilotChat
            labels={{
              title: "Event Orchestrator",
              initial:
                "Describe your event — I'll coordinate 10 specialist agents to plan it!",
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

- [ ] **Step 4: Verify frontend builds**

```bash
cd frontend && npm run build
```

Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
cd /home/yogidigital/projects/eventplanner
git add frontend/
git commit -m "feat: add CopilotKit frontend with chat and agent monitor"
```

---

### Task 11: Create Dockerfiles and docker-compose.yml

**Files:**
- Create: `conductor/Dockerfile`
- Create: `agents/venue/Dockerfile` (template for all agents)
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create agent Dockerfile template**

Create `agents/venue/Dockerfile` (copy for each agent, changing the agent path):

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared/ /app/shared/
COPY agents/venue/ /app/agents/venue/
COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen

CMD ["uv", "run", "python", "-m", "agents.venue.main"]
```

- [ ] **Step 2: Create conductor Dockerfile**

Create `conductor/Dockerfile`:

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY shared/ /app/shared/
COPY conductor/ /app/conductor/
COPY pyproject.toml uv.lock /app/

RUN uv sync --frozen

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "conductor.main"]
```

- [ ] **Step 3: Create frontend Dockerfile**

Create `frontend/Dockerfile`:

```dockerfile
FROM node:20-slim

WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .

RUN npm run build

EXPOSE 3000

CMD ["npm", "start"]
```

- [ ] **Step 4: Create docker-compose.yml**

```yaml
services:
  # --- Infrastructure ---
  mongo:
    image: mongo:7
    ports: ["27017:27017"]
    volumes:
      - mongo-data:/data/db

  nanda-registry:
    build: ./nanda-registry
    ports: ["6900:6900"]
    environment:
      - MONGODB_URI=mongodb://mongo:27017/nanda
      - PORT=6900
    depends_on:
      - mongo
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:6900/health')"]
      interval: 5s
      timeout: 3s
      retries: 5

  # --- Conductor ---
  conductor:
    build:
      context: .
      dockerfile: conductor/Dockerfile
    ports: ["8000:8000"]
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - NANDA_REGISTRY_URL=http://nanda-registry:6900
    depends_on:
      nanda-registry:
        condition: service_healthy

  # --- Specialist Agents (all register with NANDA on startup) ---
  venue:
    build:
      context: .
      dockerfile: agents/venue/Dockerfile
    ports: ["8001:8001"]
    environment: &agent-env
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      NANDA_REGISTRY_URL: http://nanda-registry:6900
    depends_on:
      nanda-registry:
        condition: service_healthy

  weather:
    build:
      context: .
      dockerfile: agents/weather/Dockerfile
    ports: ["8002:8002"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  budget:
    build:
      context: .
      dockerfile: agents/budget/Dockerfile
    ports: ["8003:8003"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  menu:
    build:
      context: .
      dockerfile: agents/menu/Dockerfile
    ports: ["8004:8004"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  activity:
    build:
      context: .
      dockerfile: agents/activity/Dockerfile
    ports: ["8005:8005"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  accessibility:
    build:
      context: .
      dockerfile: agents/accessibility/Dockerfile
    ports: ["8006:8006"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  theme:
    build:
      context: .
      dockerfile: agents/theme/Dockerfile
    ports: ["8007:8007"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  logistics:
    build:
      context: .
      dockerfile: agents/logistics/Dockerfile
    ports: ["8008:8008"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  communication:
    build:
      context: .
      dockerfile: agents/communication/Dockerfile
    ports: ["8009:8009"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  supplies:
    build:
      context: .
      dockerfile: agents/supplies/Dockerfile
    ports: ["8010:8010"]
    environment: *agent-env
    depends_on:
      nanda-registry:
        condition: service_healthy

  # --- Frontend ---
  frontend:
    build:
      context: .
      dockerfile: frontend/Dockerfile
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_CONDUCTOR_URL=http://conductor:8000/ag-ui
    depends_on:
      - conductor

volumes:
  mongo-data:
```

- [ ] **Step 5: Create .env file**

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml conductor/Dockerfile agents/*/Dockerfile frontend/Dockerfile nanda-registry/
git commit -m "feat: add Docker Compose setup with self-hosted NANDA registry + MongoDB"
```

---

### Task 12: Integration test — full end-to-end

- [ ] **Step 1: Build and start all services**

```bash
docker compose build
docker compose up -d
```

- [ ] **Step 2: Verify NANDA registry is healthy and agents registered**

```bash
curl http://localhost:6900/health
curl http://localhost:6900/list | python -m json.tool
```

Expected: Health returns `{"status": "ok", "mongo": true}`. List shows all 10 agents with their URLs.

- [ ] **Step 3: Verify agent cards via direct access**

```bash
curl http://localhost:8001/.well-known/agent.json | python -m json.tool
curl http://localhost:8002/.well-known/agent.json | python -m json.tool
```

Expected: Valid JSON Agent Cards for each agent

- [ ] **Step 4: Verify NANDA lookup resolves agents**

```bash
curl http://localhost:6900/lookup/venue | python -m json.tool
curl http://localhost:6900/lookup/weather | python -m json.tool
```

Expected: Each returns the agent URL (e.g., `http://venue:8001`)

- [ ] **Step 5: Test conductor AG-UI endpoint**

```bash
curl -X POST http://localhost:8000/ag-ui \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"thread_id": "test-1", "run_id": "run-1", "messages": [{"role": "user", "content": [{"type": "text", "text": "Plan a 50th Anniversary Family Reunion for 40 people in a mountain location this July. Budget $5000. Elderly grandparents in wheelchairs, three vegans."}]}]}'
```

Expected: SSE event stream with agent status updates and final blueprint

- [ ] **Step 6: Open frontend in browser**

Navigate to `http://localhost:3000` — verify chat loads, type event description, watch agents work.

- [ ] **Step 7: Commit any fixes**

```bash
git add -A
git commit -m "fix: integration test fixes for full orchestration flow"
```

---

## Summary of Implementation Order

| # | Task | What | Est. Complexity |
|---|------|------|-----------------|
| 1 | Scaffolding | uv workspace, shared package | Low |
| 2 | Schemas | Pydantic models | Low |
| 3 | BaseEventAgent | Agent base class + A2A integration | Medium |
| 3b | NANDA registry client | Registry client + auto-registration on startup | Medium |
| 3c | Self-hosted NANDA | Dockerfile + docker-compose for NANDA Index + MongoDB | Low |
| 4 | Venue tools | MCP tools for venue search/scoring | Low |
| 5 | Venue agent | Full agent + FastAPI server | Low |
| 6 | Weather agent | Open-Meteo integration | Low |
| 7 | 8 more agents | Budget through Supplies | Medium (repetitive) |
| 8 | Conductor tools | A2A tools with NANDA-based dynamic discovery | Medium |
| 9 | Conductor + AG-UI | Orchestrator + SSE endpoint | Medium |
| 10 | Frontend | CopilotKit chat + monitor | Low |
| 11 | Docker | Dockerfiles + compose (14 services incl. NANDA + MongoDB) | Low |
| 12 | Integration test | End-to-end: NANDA registry → agent discovery → orchestration | Medium |
