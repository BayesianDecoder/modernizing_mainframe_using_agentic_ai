"""mcp_servers/chromadb_server.py — semantic search over runbooks."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
from fastmcp import FastMCP
from backend.stores.vector_store import search

mcp = FastMCP("chromadb-runbooks",
              instructions="Semantic search over runbooks, ADRs, and incident records.")

@mcp.tool()
def chromadb_search(query: str, n_results: int = 4) -> str:
    """Search institutional knowledge by meaning (runbooks, ADRs, incidents).
    Use natural language — exact keyword match not required."""
    results = search(query, n_results)
    return json.dumps(results, indent=2)

if __name__ == "__main__":
    print("🔍  ChromaDB MCP Server → http://localhost:8083")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8083)
