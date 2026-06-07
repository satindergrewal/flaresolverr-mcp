"""Unit tests for FlareSolverr MCP server.

These tests mock the FlareSolverr HTTP API so they run without a live instance.
Run with: pytest test_unit.py -v
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

import server


# --- Fixtures ---

MOCK_FLARESOLVERR_RESPONSE = {
    "status": "ok",
    "message": "Challenge not detected!",
    "solution": {
        "url": "https://example.com",
        "status": 200,
        "cookies": [{"name": "cf_clearance", "value": "abc123"}],
        "userAgent": "Mozilla/5.0 Test",
        "response": "<html><body>Hello</body></html>",
    },
    "startTimestamp": 1700000000000,
    "endTimestamp": 1700000005000,
    "version": "3.5.0",
}


def mock_response(data=None, status_code=200):
    """Create a mock httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        json=data or MOCK_FLARESOLVERR_RESPONSE,
        request=httpx.Request("POST", "http://localhost:8191/v1"),
    )
    return resp


# --- Tool Registration Tests ---

class TestToolRegistration:
    """Verify all expected tools are registered with correct names."""

    def test_all_tools_registered(self):
        tool_names = {t.name for t in server.mcp._tool_manager.list_tools()}
        expected = {"fetch_url", "post_url", "create_session", "list_sessions", "destroy_session"}
        assert tool_names == expected, f"Missing tools: {expected - tool_names}"

    def test_tool_count(self):
        tools = server.mcp._tool_manager.list_tools()
        assert len(tools) == 5


# --- fetch_url Tests ---

class TestFetchUrl:

    @pytest.mark.asyncio
    async def test_basic_fetch(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            result = await server.fetch_url(url="https://example.com")
            parsed = json.loads(result)

            assert parsed["status"] == "ok"
            assert parsed["solution"]["url"] == "https://example.com"
            assert parsed["solution"]["status"] == 200

            mock.assert_called_once()
            payload = mock.call_args[0][0]
            assert payload["cmd"] == "request.get"
            assert payload["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_fetch_with_cookies(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            cookies = [{"name": "session", "value": "xyz"}]
            await server.fetch_url(url="https://example.com", cookies=cookies)

            payload = mock.call_args[0][0]
            assert payload["cookies"] == cookies

    @pytest.mark.asyncio
    async def test_fetch_with_proxy(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            proxy = {"url": "socks5://10.0.0.1:1080"}
            await server.fetch_url(url="https://example.com", proxy=proxy)

            payload = mock.call_args[0][0]
            assert payload["proxy"] == proxy

    @pytest.mark.asyncio
    async def test_fetch_with_session(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.fetch_url(url="https://example.com", session="my-session")

            payload = mock.call_args[0][0]
            assert payload["session"] == "my-session"

    @pytest.mark.asyncio
    async def test_fetch_return_only_cookies(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.fetch_url(url="https://example.com", return_only_cookies=True)

            payload = mock.call_args[0][0]
            assert payload["returnOnlyCookies"] is True

    @pytest.mark.asyncio
    async def test_fetch_custom_timeout(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.fetch_url(url="https://example.com", max_timeout=30000)

            payload = mock.call_args[0][0]
            assert payload["maxTimeout"] == 30000

    @pytest.mark.asyncio
    async def test_fetch_omits_none_optionals(self):
        """Ensure optional params are NOT sent when not provided."""
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.fetch_url(url="https://example.com")

            payload = mock.call_args[0][0]
            assert "cookies" not in payload
            assert "proxy" not in payload
            assert "session" not in payload
            assert "returnOnlyCookies" not in payload


# --- post_url Tests ---

class TestPostUrl:

    @pytest.mark.asyncio
    async def test_basic_post(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            result = await server.post_url(url="https://example.com/login", post_data="user=test&pass=123")
            parsed = json.loads(result)

            assert parsed["status"] == "ok"
            payload = mock.call_args[0][0]
            assert payload["cmd"] == "request.post"
            assert payload["postData"] == "user=test&pass=123"

    @pytest.mark.asyncio
    async def test_post_with_all_options(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.post_url(
                url="https://example.com",
                post_data="k=v",
                cookies=[{"name": "a", "value": "b"}],
                proxy={"url": "http://10.0.0.1:8080"},
                session="sess1",
                return_only_cookies=True,
            )

            payload = mock.call_args[0][0]
            assert payload["cookies"] == [{"name": "a", "value": "b"}]
            assert payload["proxy"] == {"url": "http://10.0.0.1:8080"}
            assert payload["session"] == "sess1"
            assert payload["returnOnlyCookies"] is True


# --- Session Tests ---

class TestSessions:

    @pytest.mark.asyncio
    async def test_create_session_no_id(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok", "message": "", "session": "auto-generated-id"}
            result = await server.create_session()
            parsed = json.loads(result)

            assert parsed["status"] == "ok"
            payload = mock.call_args[0][0]
            assert payload["cmd"] == "sessions.create"
            assert "session" not in payload

    @pytest.mark.asyncio
    async def test_create_session_with_id(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok", "session": "my-sess"}
            await server.create_session(session="my-sess")

            payload = mock.call_args[0][0]
            assert payload["session"] == "my-sess"

    @pytest.mark.asyncio
    async def test_create_session_with_proxy(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok"}
            await server.create_session(proxy={"url": "socks5://10.0.0.1:1080"})

            payload = mock.call_args[0][0]
            assert payload["proxy"] == {"url": "socks5://10.0.0.1:1080"}

    @pytest.mark.asyncio
    async def test_list_sessions(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok", "sessions": ["s1", "s2"]}
            result = await server.list_sessions()
            parsed = json.loads(result)

            assert parsed["sessions"] == ["s1", "s2"]
            payload = mock.call_args[0][0]
            assert payload["cmd"] == "sessions.list"

    @pytest.mark.asyncio
    async def test_destroy_session(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "ok", "message": ""}
            result = await server.destroy_session(session="s1")
            parsed = json.loads(result)

            assert parsed["status"] == "ok"
            payload = mock.call_args[0][0]
            assert payload["cmd"] == "sessions.destroy"
            assert payload["session"] == "s1"


# --- Error Handling Tests ---

class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_flaresolverr_error_response(self):
        """FlareSolverr returns an error status (e.g. challenge failed)."""
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = {"status": "error", "message": "Error: Timeout after 60s"}
            result = await server.fetch_url(url="https://protected-site.com")
            parsed = json.loads(result)

            assert parsed["status"] == "error"
            assert "Timeout" in parsed["message"]

    @pytest.mark.asyncio
    async def test_flaresolverr_unreachable(self):
        """FlareSolverr is down — returns error dict instead of crashing."""
        mock_transport = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        with patch("httpx.AsyncClient.post", mock_transport):
            result = await server._call_flaresolverr({"cmd": "sessions.list"})
            assert result["status"] == "error"
            assert "not reachable" in result["message"]

    @pytest.mark.asyncio
    async def test_flaresolverr_http_500(self):
        """FlareSolverr returns HTTP 500 — returns error dict."""
        mock_resp = httpx.Response(500, request=httpx.Request("POST", "http://localhost:8191/v1"))
        mock_transport = AsyncMock(return_value=mock_resp)
        with patch("httpx.AsyncClient.post", mock_transport):
            result = await server._call_flaresolverr({"cmd": "sessions.list"})
            assert result["status"] == "error"
            assert "500" in result["message"]

    @pytest.mark.asyncio
    async def test_flaresolverr_timeout(self):
        """FlareSolverr times out — returns error dict."""
        mock_transport = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with patch("httpx.AsyncClient.post", mock_transport):
            result = await server._call_flaresolverr({"cmd": "request.get", "url": "https://example.com"})
            assert result["status"] == "error"
            assert "timed out" in result["message"]


# --- Payload Construction Tests ---

class TestPayloadConstruction:
    """Verify exact payloads sent to FlareSolverr match API spec."""

    @pytest.mark.asyncio
    async def test_fetch_minimal_payload(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.fetch_url(url="https://test.com")

            payload = mock.call_args[0][0]
            assert payload == {
                "cmd": "request.get",
                "url": "https://test.com",
                "maxTimeout": server.DEFAULT_MAX_TIMEOUT,
            }

    @pytest.mark.asyncio
    async def test_post_minimal_payload(self):
        with patch("server._call_flaresolverr", new_callable=AsyncMock) as mock:
            mock.return_value = MOCK_FLARESOLVERR_RESPONSE
            await server.post_url(url="https://test.com", post_data="x=1")

            payload = mock.call_args[0][0]
            assert payload == {
                "cmd": "request.post",
                "url": "https://test.com",
                "postData": "x=1",
                "maxTimeout": server.DEFAULT_MAX_TIMEOUT,
            }
