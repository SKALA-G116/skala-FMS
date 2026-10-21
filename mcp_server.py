"""Food-domain MCP stdio entry point; --host exposes trusted host tools only."""
from backend.app.infrastructure.database import init, pool
from backend.app.mcp.server import mcp

if __name__ == '__main__':
    init()
    try:
        mcp.run(transport='stdio', show_banner=False)
    finally:
        pool.close()
