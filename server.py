import os
import json
import httpx
from mcp.server.fastmcp import FastMCP

FLARESOLVERR_URL = os.environ.get("FLARESOLVERR_URL", "http://localhost:8191")
DEFAULT_MAX_TIMEOUT = int(os.environ.get("FLARESOLVERR_TIMEOUT", "60000"))

MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", "8192"))

mcp = FastMCP("FlareSolverr", host=MCP_HOST, port=MCP_PORT)


async def _call_flaresolverr(payload: dict) -> dict:
    """Send a request to the FlareSolverr v1 endpoint."""
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{FLARESOLVERR_URL}/v1", json=payload)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        return {"status": "error", "message": f"FlareSolverr HTTP {e.response.status_code}"}
    except httpx.ConnectError:
        return {"status": "error", "message": "FlareSolverr is not reachable"}
    except httpx.TimeoutException:
        return {"status": "error", "message": "FlareSolverr request timed out"}


@mcp.tool()
async def fetch_url(
    url: str,
    max_timeout: int = DEFAULT_MAX_TIMEOUT,
    cookies: list[dict] | None = None,
    proxy: dict | None = None,
    session: str | None = None,
    return_only_cookies: bool = False,
) -> str:
    """Fetch a URL through FlareSolverr, bypassing Cloudflare protection.

    Use this when a normal HTTP request fails due to Cloudflare or DDoS-GUARD
    challenges. Returns the page HTML content and cookies.

    Args:
        url: The URL to fetch.
        max_timeout: Max time in ms to wait for challenge to solve (default 60000).
        cookies: Optional list of cookies to send, e.g. [{"name": "x", "value": "y"}].
        proxy: Optional proxy config, e.g. {"url": "socks5://..."}
        session: Optional session ID to reuse a browser instance.
        return_only_cookies: If True, return only cookies without page HTML.
    """
    payload = {"cmd": "request.get", "url": url, "maxTimeout": max_timeout}
    if cookies:
        payload["cookies"] = cookies
    if proxy:
        payload["proxy"] = proxy
    if session:
        payload["session"] = session
    if return_only_cookies:
        payload["returnOnlyCookies"] = True

    result = await _call_flaresolverr(payload)
    return json.dumps(result, indent=2)


@mcp.tool()
async def post_url(
    url: str,
    post_data: str,
    max_timeout: int = DEFAULT_MAX_TIMEOUT,
    cookies: list[dict] | None = None,
    proxy: dict | None = None,
    session: str | None = None,
    return_only_cookies: bool = False,
) -> str:
    """POST to a URL through FlareSolverr, bypassing Cloudflare protection.

    Args:
        url: The URL to POST to.
        post_data: URL-encoded form data to send (e.g. "key1=value1&key2=value2").
        max_timeout: Max time in ms to wait for challenge to solve.
        cookies: Optional list of cookies to send.
        proxy: Optional proxy config.
        session: Optional session ID to reuse a browser instance.
        return_only_cookies: If True, return only cookies without page HTML.
    """
    payload = {
        "cmd": "request.post",
        "url": url,
        "postData": post_data,
        "maxTimeout": max_timeout,
    }
    if cookies:
        payload["cookies"] = cookies
    if proxy:
        payload["proxy"] = proxy
    if session:
        payload["session"] = session
    if return_only_cookies:
        payload["returnOnlyCookies"] = True

    result = await _call_flaresolverr(payload)
    return json.dumps(result, indent=2)


@mcp.tool()
async def create_session(session: str | None = None, proxy: dict | None = None) -> str:
    """Create a persistent browser session in FlareSolverr.

    Sessions keep the browser open between requests, which is faster for
    multiple requests to the same site. Remember to destroy sessions when done.

    Args:
        session: Optional custom session ID. If not provided, one is generated.
        proxy: Optional proxy config for this session.
    """
    payload = {"cmd": "sessions.create"}
    if session:
        payload["session"] = session
    if proxy:
        payload["proxy"] = proxy

    result = await _call_flaresolverr(payload)
    return json.dumps(result, indent=2)


@mcp.tool()
async def list_sessions() -> str:
    """List all active FlareSolverr browser sessions."""
    result = await _call_flaresolverr({"cmd": "sessions.list"})
    return json.dumps(result, indent=2)


@mcp.tool()
async def destroy_session(session: str) -> str:
    """Destroy a FlareSolverr browser session.

    Always destroy sessions when you're done to free memory.

    Args:
        session: The session ID to destroy.
    """
    result = await _call_flaresolverr({"cmd": "sessions.destroy", "session": session})
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    mcp.run(transport="sse")
