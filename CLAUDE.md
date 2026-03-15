# Event Orchestrator

Multi-agent event planning system: 10 specialist agents + conductor + CopilotKit frontend + self-hosted NANDA registry.

## Commands

```bash
# Install dependencies
~/.local/bin/uv sync

# Run all tests
~/.local/bin/uv run pytest tests/ -v

# Run a single agent locally
~/.local/bin/uv run python -m agents.venue.main

# Run conductor locally
~/.local/bin/uv run python -m conductor.main

# Docker (full stack)
docker compose up --build        # All 14 services
docker compose up -d mongo nanda-registry  # Just infra
```

## Architecture

- `shared/shared/` — Pydantic schemas, BaseEventAgent, NANDA registry client
- `agents/<name>/` — 10 specialist agents (ports 8001-8010), each a FastAPI + A2A + claude-agent-sdk service
- `conductor/` — Orchestrator (port 8000), AG-UI SSE endpoint, MCP tools wrapping A2A calls
- `nanda-registry/` — Self-hosted Project NANDA Index (port 6900, Flask + MongoDB)
- `frontend/` — Next.js + CopilotKit chat UI (port 3000)

## Key Gotchas

- **Package layout**: Python package is `shared/shared/` (hatchling), not `shared/`. Import as `from shared.schemas import ...`
- **`@tool` decorator**: Returns `SdkMcpTool` object, not a callable. In tests use `.handler(args)` to invoke, `.name` for the tool name
- **uv binary**: Located at `~/.local/bin/uv`, not on default PATH
- **Agent discovery**: Conductor resolves agent URLs dynamically via NANDA registry (`GET /lookup/<agent_id>`), not hardcoded
- **A2A SDK API**: `DefaultRequestHandler(agent_executor, task_store)`, `TaskUpdater(event_queue, task_id, context_id)`, `A2AFastAPIApplication.add_routes_to_app(app)`
- **AG-UI events**: Use `EventType.RUN_STARTED` enum, `RunStartedEvent` (not `RunStartEvent`)
- **Node.js**: v18 installed; Next.js 14 used for compatibility. Upgrade to Node 20+ for production.

## Code Style

- Python 3.12+, type hints with `str | None` syntax
- Pydantic v2 models for all schemas
- Async everywhere (FastAPI, httpx, claude-agent-sdk)
- Each agent subclasses `BaseEventAgent` and overrides: `agent_id`, `name`, `description`, `port`, `system_prompt`, `get_skills()`, optionally `get_mcp_tools()` and `get_allowed_tools()`

## Environment Variables

- `ANTHROPIC_API_KEY` — Required for all agents and conductor
- `NANDA_REGISTRY_URL` — Default: `http://nanda-registry:6900`
- `MONGODB_URI` — For NANDA registry, default: `mongodb://mongo:27017/nanda`
