"""Tests for conductor A2A tools."""
import pytest
from conductor.tools.a2a_tools import AGENT_TOOLS, _resolve_agent_url, _agent_url_cache, _nanda
from unittest.mock import AsyncMock, patch, MagicMock


def test_all_agent_tools_registered():
    tool_names = [t.name for t in AGENT_TOOLS]
    expected = ["discover_agents", "call_agent", "check_budget"]
    for name in expected:
        assert name in tool_names, f"Missing tool: {name}"


def test_agent_tools_count():
    assert len(AGENT_TOOLS) == 3


@pytest.mark.asyncio
async def test_resolve_agent_url_caches():
    _agent_url_cache.clear()
    with patch.object(_nanda, 'lookup_agent', new_callable=AsyncMock, return_value="http://venue:8001"):
        url1 = await _resolve_agent_url("venue")
        url2 = await _resolve_agent_url("venue")
    assert url1 == "http://venue:8001"
    assert url2 == "http://venue:8001"
    assert "venue" in _agent_url_cache
    _agent_url_cache.clear()


@pytest.mark.asyncio
async def test_resolve_agent_url_not_found():
    _agent_url_cache.clear()
    with patch.object(_nanda, 'lookup_agent', new_callable=AsyncMock, return_value=None):
        with pytest.raises(RuntimeError, match="not found in NANDA"):
            await _resolve_agent_url("nonexistent")
    _agent_url_cache.clear()
