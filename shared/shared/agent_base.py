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
from shared.nanda_registry import NandaRegistryClient


class BaseEventAgent:
    """Base class for all specialist agents."""

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

        @app.get("/.well-known/agent.json")
        async def agent_card():
            return self.get_agent_card().model_dump()

        agent_ref = self

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

        # A2A endpoint via official SDK
        card = self.get_agent_card()
        task_store = InMemoryTaskStore()
        executor = self._create_executor()
        handler = DefaultRequestHandler(
            agent_executor=executor,
            task_store=task_store,
        )
        a2a_app = A2AFastAPIApplication(
            agent_card=card,
            http_handler=handler,
        )
        a2a_app.add_routes_to_app(app)

        return app


class EventAgentExecutor(AgentExecutor):
    """A2A AgentExecutor that delegates to a BaseEventAgent."""

    def __init__(self, agent: BaseEventAgent):
        self.agent = agent

    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = context.current_task or new_task(context.message)
        task_id = task.id if hasattr(task, 'id') else context.task_id
        context_id = context.context_id
        updater = TaskUpdater(event_queue, task_id, context_id)

        requirements = {}
        agent_context = {}

        if context.message and context.message.parts:
            try:
                text = context.message.parts[0].root.text
                data = json.loads(text)
                requirements = data.get("requirements", {})
                agent_context = data.get("context", {})
            except (json.JSONDecodeError, AttributeError):
                if context.message.parts:
                    try:
                        requirements = {"raw_input": context.message.parts[0].root.text}
                    except AttributeError:
                        requirements = {"raw_input": str(context.message.parts[0])}

        result = await self.agent.run(requirements, agent_context)

        await updater.complete(
            new_agent_text_message(
                json.dumps(result.model_dump(), default=str),
                context_id,
                task_id,
            )
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        if context.current_task:
            updater = TaskUpdater(
                event_queue,
                context.current_task.id,
                context.context_id,
            )
            await updater.cancel()
