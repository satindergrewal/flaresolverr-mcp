# FlareSolverr MCP Server

MCP (Model Context Protocol) server that wraps [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) to bypass Cloudflare and DDoS-GUARD protection.

Any MCP-compatible client (OpenClaw, Claude Desktop, Ollama, etc.) can connect and use these tools via SSE transport.

## Tools

| Tool | Description |
|------|-------------|
| `fetch_url` | GET a URL through FlareSolverr, bypassing Cloudflare. Returns HTML + cookies. |
| `post_url` | POST form data to a URL through FlareSolverr. |
| `create_session` | Create a persistent browser session (faster for multiple requests to the same site). |
| `list_sessions` | List all active browser sessions. |
| `destroy_session` | Destroy a session to free memory. |

## Prerequisites

A running [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) instance. The easiest way:

```bash
docker run -d --name=flaresolverr -p 8191:8191 --restart unless-stopped \
  ghcr.io/flaresolverr/flaresolverr:latest
```

## Setup

### Option 1: Docker Compose (recommended)

Runs both FlareSolverr and the MCP server together:

```bash
git clone https://github.com/satindergrewal/flaresolverr-mcp.git
cd flaresolverr-mcp
docker compose up -d
```

- FlareSolverr: `http://localhost:8191`
- MCP Server (SSE): `http://localhost:8192/sse`

### Option 2: Standalone Python

If FlareSolverr is already running:

```bash
git clone https://github.com/satindergrewal/flaresolverr-mcp.git
cd flaresolverr-mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python server.py
```

The MCP server starts on `http://0.0.0.0:8192/sse`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLARESOLVERR_URL` | `http://localhost:8191` | FlareSolverr instance URL |
| `FLARESOLVERR_TIMEOUT` | `60000` | Default max timeout in ms for challenge solving |
| `MCP_HOST` | `0.0.0.0` | Host the MCP server binds to |
| `MCP_PORT` | `8192` | Port the MCP server listens on |

## MCP Client Configuration

### OpenClaw

1. Add to `~/.openclaw/openclaw.json`:

```json
{
  "mcp": {
    "servers": {
      "flaresolverr": {
        "url": "http://localhost:8192/sse",
        "transport": "sse",
        "timeout": 120
      }
    }
  }
}
```

2. Include all tools and add `mcp` to the allowed tool categories:

```bash
openclaw mcp tools flaresolverr --include '*'
openclaw mcp reload
```

3. Add `"mcp"` to your `tools.allow` list in `openclaw.json` (under the `tools` section):

```json
{
  "tools": {
    "allow": [
      "...your existing tools...",
      "mcp"
    ]
  }
}
```

4. Verify:

```bash
openclaw mcp probe        # should show: flaresolverr: 5 tools
openclaw mcp doctor       # should show: flaresolverr: ok
```

5. Start a **new session** in OpenClaw for the tools to appear.

### Claude Desktop

Add to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "flaresolverr": {
      "url": "http://localhost:8192/sse"
    }
  }
}
```

### Any MCP Client (generic)

Connect via SSE transport to: `http://<your-server-ip>:8192/sse`

Set timeout to at least 120 seconds — Cloudflare challenges can take 30-60s to solve.

## Testing

### Unit tests (no FlareSolverr needed)

```bash
make install
make test-unit
```

### Integration tests (requires running FlareSolverr)

```bash
make test-integration
```

### Run all tests

```bash
make test-all
```

## License

MIT
