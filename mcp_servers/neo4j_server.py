"""mcp_servers/neo4j_server.py — Claude writes Cypher, this executes it."""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()
from fastmcp import FastMCP
from backend.stores.graph import run as neo4j_run

mcp = FastMCP("neo4j-mainframe",
              instructions="Execute Cypher queries against the mainframe knowledge graph.")

@mcp.tool()
def neo4j_query(cypher: str) -> str:
    """Execute any Cypher query against the Neo4j mainframe knowledge graph.
    Returns results as JSON. Write MATCH/RETURN/WHERE/ORDER BY as needed."""
    try:
        rows = neo4j_run(cypher)
        return json.dumps(rows, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print("🌐  Neo4j MCP Server → http://localhost:8081")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8081)
