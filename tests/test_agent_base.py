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
