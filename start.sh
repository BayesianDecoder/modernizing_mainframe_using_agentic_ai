#!/bin/bash
# MAIA Live — start everything

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo ""
echo "═══════════════════════════════════════════"
echo "  MAIA Live — Starting"
echo "═══════════════════════════════════════════"

# 1. Load .env
[ -f .env ] && export $(grep -v '^#' .env | xargs) || { echo "⚠️  Copy .env.example to .env first"; exit 1; }

# 2. Run ingestion (seeds data)
echo ""
echo "📦  Running ingestion pipeline..."
python -m backend.ingestion 2>&1 | tail -15

# 3. Start MCP servers in background
echo ""
echo "🔌  Starting MCP servers..."
python mcp_servers/neo4j_server.py    &  MCP1=$!
python mcp_servers/sqlite_server.py   &  MCP2=$!
python mcp_servers/chromadb_server.py &  MCP3=$!
sleep 3
echo "    ✅  MCP servers started (pids $MCP1 $MCP2 $MCP3)"

# 4. Start FastAPI
echo ""
echo "🚀  Starting FastAPI backend on http://localhost:8000..."
uvicorn backend.main:app --reload --port 8000 &
BACK=$!
sleep 2

# 5. Start React frontend
echo ""
echo "⚛️   Starting React frontend on http://localhost:5173..."
cd frontend
npm run dev &
FRONT=$!
cd ..

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅  All services running"
echo ""
echo "  Dashboard:  http://localhost:5173"
echo "  API docs:   http://localhost:8000/docs"
echo "  Neo4j MCP:  http://localhost:8081"
echo "  SQLite MCP: http://localhost:8082"
echo "  Chroma MCP: http://localhost:8083"
echo ""
echo "  Press Ctrl+C to stop all"
echo "═══════════════════════════════════════════"

# Wait and clean up on Ctrl+C
trap "echo ''; echo 'Stopping...'; kill $MCP1 $MCP2 $MCP3 $BACK $FRONT 2>/dev/null; exit 0" INT
wait
