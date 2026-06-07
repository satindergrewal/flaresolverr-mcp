# FlareSolverr MCP Server

MCP (Model Context Protocol) server that wraps [FlareSolverr](https://github.com/FlareSolverr/FlareSolverr) to bypass Cloudflare and DDoS-GUARD protection.

Any MCP-compatible client (OpenClaw, Claude Desktop, Ollama, etc.) can connect and use it.

## Tools

| Tool | Description |
|------|-------------|
| `fetch_url` | GET a URL through FlareSolverr, bypassing Cloudflare |
| `post_url` | POST to a URL through FlareSolverr |
| `create_session` | Create a persistent browser session (faster for multiple requests) |
| `list_sessions` | List active browser sessions |
| `destroy_session` | Destroy a session to free memory |

## Quick Start (Docker Compose)

Runs both FlareSolverr and the MCP server together:

```bash
docker compose up -d
```

- FlareSolverr: `http://localhost:8191`
- MCP Server (SSE): `http://localhost:8192`

## Quick Start (Standalone)

If you already have FlareSolverr running:

```bash
pip install -r requirements.txt
FLARESOLVERR_URL=http://localhost:8191 python server.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLARESOLVERR_URL` | `http://localhost:8191` | FlareSolverr instance URL |
| `FLARESOLVERR_TIMEOUT` | `60000` | Default max timeout in ms |

## MCP Client Configuration

### SSE Transport (remote/network)

Connect any MCP client to: `http://<your-server-ip>:8192/sse`

### Example: Claude Desktop / OpenClaw

```json
{
  "mcpServers": {
    "flaresolverr": {
      "url": "http://localhost:8192/sse"
    }
  }
}
```

## License

MIT
