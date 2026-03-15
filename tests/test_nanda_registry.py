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
