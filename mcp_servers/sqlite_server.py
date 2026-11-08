"""mcp_servers/sqlite_server.py — Claude writes SQL, this executes it."""
import sys, json, sqlite3
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
from fastmcp import FastMCP
from backend.stores.smf_store import DB_PATH

mcp = FastMCP("sqlite-smf",
              instructions="Execute SQL queries against the SMF performance database.")

@mcp.tool()
def sqlite_query(sql: str) -> str:
    """Execute a SQL SELECT against the SMF database.
    Tables: job_history, lpar_performance. Returns JSON rows.
    Use datetime('now','-N minutes') for recent data."""
    try:
        with sqlite3.connect(DB_PATH) as c:
            c.row_factory = sqlite3.Row
            rows = [dict(r) for r in c.execute(sql).fetchall()]
        return json.dumps(rows, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print("📊  SQLite MCP Server → http://localhost:8082")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8082)
