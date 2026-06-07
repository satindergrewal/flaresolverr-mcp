"""Integration tests for FlareSolverr MCP server.

These tests require:
  1. FlareSolverr running (default: http://localhost:8191)
  2. MCP server running (default: http://localhost:8192)

Run with: pytest test_integration.py -v
Skip with: pytest test_integration.py -v -k "not integration"

Set FLARESOLVERR_URL and MCP_URL env vars to override defaults.
"""

import os
import json
import pytest
import httpx
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191")
MCP_URL = os.environ.get("MCP_URL", "http://localhost:8192/sse")

pytestmark = pytest.mark.integration


# --- Connectivity Checks ---

class TestConnectivity:

    @pytest.mark.asyncio
    async def test_flaresolverr_is_reachable(self):
        """FlareSolverr health endpoint responds."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{FLARESOLVERR_URL}/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_flaresolverr_index(self):
        """FlareSolverr index returns version info."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{FLARESOLVERR_URL}/")
            assert resp.status_code == 200
            data = resp.json()
            assert "version" in data
            assert "FlareSolverr is ready" in data["msg"]

    @pytest.mark.asyncio
    async def test_mcp_server_connects(self):
        """MCP server accepts SSE connections and completes handshake."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()


# --- Tool Discovery ---

class TestToolDiscovery:

    @pytest.mark.asyncio
    async def test_all_tools_available(self):
        """MCP server exposes all 5 expected tools."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                tool_names = {t.name for t in tools.tools}

                expected = {"fetch_url", "post_url", "create_session", "list_sessions", "destroy_session"}
                assert tool_names == expected

    @pytest.mark.asyncio
    async def test_tools_have_descriptions(self):
        """Every tool has a non-empty description."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                for tool in tools.tools:
                    assert tool.description, f"Tool {tool.name} has no description"


# --- Session Lifecycle ---

class TestSessionLifecycle:

    @pytest.mark.asyncio
    async def test_full_session_lifecycle(self):
        """Create → list → destroy a session."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create
                result = await session.call_tool("create_session", {"session": "test-lifecycle"})
                data = json.loads(result.content[0].text)
                assert data["status"] == "ok"
                assert data["session"] == "test-lifecycle"

                # List — should contain our session
                result = await session.call_tool("list_sessions", {})
                data = json.loads(result.content[0].text)
                assert "test-lifecycle" in data["sessions"]

                # Destroy
                result = await session.call_tool("destroy_session", {"session": "test-lifecycle"})
                data = json.loads(result.content[0].text)
                assert data["status"] == "ok"

                # List again — should be gone
                result = await session.call_tool("list_sessions", {})
                data = json.loads(result.content[0].text)
                assert "test-lifecycle" not in data.get("sessions", [])


# --- Fetch Tests ---

class TestFetchUrl:

    @pytest.mark.asyncio
    async def test_fetch_simple_page(self):
        """Fetch a non-Cloudflare page through FlareSolverr."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("fetch_url", {
                    "url": "https://httpbin.org/get",
                    "max_timeout": 30000,
                })
                data = json.loads(result.content[0].text)

                assert data["status"] == "ok"
                assert data["solution"]["status"] == 200
                assert data["solution"]["url"] == "https://httpbin.org/get"
                assert data["solution"]["userAgent"]  # should have a user agent
                assert "response" in data["solution"]

    @pytest.mark.asyncio
    async def test_fetch_response_has_cookies_field(self):
        """Verify the cookies field exists in the response structure."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("fetch_url", {
                    "url": "https://httpbin.org/get",
                    "max_timeout": 30000,
                })
                data = json.loads(result.content[0].text)

                assert data["status"] == "ok"
                assert "cookies" in data["solution"]
                assert isinstance(data["solution"]["cookies"], list)

    @pytest.mark.asyncio
    async def test_fetch_with_session(self):
        """Fetch using a persistent session."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Create session
                await session.call_tool("create_session", {"session": "test-fetch-sess"})

                try:
                    result = await session.call_tool("fetch_url", {
                        "url": "https://httpbin.org/get",
                        "session": "test-fetch-sess",
                        "max_timeout": 30000,
                    })
                    data = json.loads(result.content[0].text)
                    assert data["status"] == "ok"
                finally:
                    # Always clean up
                    await session.call_tool("destroy_session", {"session": "test-fetch-sess"})

    @pytest.mark.asyncio
    async def test_fetch_invalid_url(self):
        """FlareSolverr handles invalid URLs gracefully — returns error, doesn't crash."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("fetch_url", {
                    "url": "https://this-domain-does-not-exist-xyz123.com",
                    "max_timeout": 15000,
                })
                text = result.content[0].text
                # Should return something (error JSON or error text), not crash silently
                assert len(text) > 0
                # If it's valid JSON, check status
                try:
                    data = json.loads(text)
                    assert data["status"] in ("ok", "error")
                except json.JSONDecodeError:
                    # Non-JSON error response is acceptable — server didn't crash
                    pass


# --- Post Tests ---

class TestPostUrl:

    @pytest.mark.asyncio
    async def test_post_form_data(self):
        """POST form data through FlareSolverr."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("post_url", {
                    "url": "https://httpbin.org/post",
                    "post_data": "key1=value1&key2=value2",
                    "max_timeout": 30000,
                })
                data = json.loads(result.content[0].text)

                assert data["status"] == "ok"
                assert data["solution"]["status"] == 200


# --- Version Compatibility ---

class TestVersionCompat:

    @pytest.mark.asyncio
    async def test_flaresolverr_version(self):
        """Verify FlareSolverr version is returned in responses."""
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool("list_sessions", {})
                data = json.loads(result.content[0].text)

                assert "version" in data
                # Version should be semver-like (e.g. "3.5.0")
                parts = data["version"].split(".")
                assert len(parts) >= 2, f"Unexpected version format: {data['version']}"
