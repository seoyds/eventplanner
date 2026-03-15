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
        """Register an agent with the NANDA registry."""
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
        """Look up an agent URL by ID. Returns agent_url or None."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.registry_url}/lookup/{agent_id}")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("agent_url") or data.get(agent_id)
            return None

    async def list_agents(self) -> dict[str, str]:
        """List all registered agents. Returns {agent_id: agent_url}."""
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
        """Search agents by query, capabilities, or tags."""
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
        """Wait for the NANDA registry to become healthy."""
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
