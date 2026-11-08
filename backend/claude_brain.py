"""
claude_brain.py
Gemini as the brain — schema-only context (~300 tokens) — via LangChain.

Connects to the 3 local MCP servers (neo4j, sqlite, chromadb) as a real MCP
client for every chat call using langchain-mcp-adapters, binds their tools to
a LangChain chat model (Gemini), and runs a manual tool-calling loop so
Gemini actually queries live data through those servers rather than
bypassing them.

Using LangChain here (rather than the google-genai SDK directly) is mainly
for LangSmith tracing: with LANGSMITH_TRACING=true set, every model/tool call
below is traced automatically — no manual wrapping needed, unlike Anthropic's
wrap_anthropic. Set LANGSMITH_API_KEY / LANGSMITH_PROJECT / LANGSMITH_TRACING
in .env to see traces at smith.langchain.com.

(Historical note: this previously called Anthropic's Claude directly, then
Gemini directly via google-genai. Swapped to Claude->Gemini because
Anthropic's remote MCP connector requires servers reachable from Anthropic's
own cloud — these run on localhost, which can never satisfy that. Swapped
google-genai->LangChain for LangSmith tracing.)
"""
import os

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage

MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

# ── MCP server registry ──────────────────────────────────────────
MCP_SERVERS = {
    "neo4j-mainframe":    {"transport": "streamable_http", "url": "http://localhost:8081/mcp"},
    "sqlite-smf":         {"transport": "streamable_http", "url": "http://localhost:8082/mcp"},
    "chromadb-runbooks":  {"transport": "streamable_http", "url": "http://localhost:8083/mcp"},
}

# ── Schema-only context — ~300 tokens ────────────────────────────
# Gemini gets the schema (what exists) NOT the data (actual values).
# Gemini writes its own Cypher and SQL to query live data via MCP.
SCHEMA = """\
You are MAIA — Mainframe Agentic Intelligence Assistant.

You have 3 MCP tools. Write your own queries. Never assume data — always query.

━━━ NEO4J  (neo4j_query(cypher: str)) ━━━
Node labels:
  Program(name, complexity, lines, description, author)
  Job(name, schedule, sla, lpar, owner)
  Dataset(name)
  LPAR(name, label)
Relationships:
  (Program)-[:CALLS]->(Program)
  (Job)-[:EXECUTES]->(Program)
  (Job)-[:TRIGGERS]->(Job)
  (Job)-[:RUNS_ON]->(LPAR)
  (Program)-[:READS]->(Dataset)
  (Program)-[:WRITES]->(Dataset)
Known entities:
  Programs: PAYROLL BILLING TAXCALC CREDITVAL CUSTMGMT REPORTING
  Jobs: PAYJOB BILLJOB NIGHTLY
  LPARs: LPAR-1 LPAR-2 LPAR-3

━━━ SQLITE  (sqlite_query(sql: str)) ━━━
Tables:
  job_history(id,job,lpar,date,start_time,end_time,
              elapsed_mins,mips,cpu_secs,rc,status,error,note,ts)
  lpar_performance(id,lpar,label,date,hour,ts,
                   avg_mips,peak_mips,cpu_pct)
ts is ISO timestamp. Use datetime('now','-N minutes') for recent data.
R4HA = rolling 4-reading average of peak_mips. Tier boundary ~10,000 MSU.

━━━ CHROMADB  (chromadb_search(query: str, n_results: int = 4)) ━━━
Contains: runbooks, ADRs, incident post-mortems, SOPs.
Use natural language — finds by meaning not exact keywords.

━━━ RULES ━━━
1. Query before answering. Never invent names, numbers, or return codes.
2. Cite specific values from results (MIPS, RC, elapsed minutes, dates).
3. Call multiple tools when question spans domains.
4. For impact: MATCH (n)-[:CALLS|EXECUTES|TRIGGERS*1..6]->(p:Program {name:$x})
5. For billing: AVG(peak_mips) across recent lpar_performance rows.
6. End with a clear, actionable recommendation.
"""


def mcp_status() -> dict:
    import requests
    out = {}
    for name, s in MCP_SERVERS.items():
        try:
            requests.get(s["url"], timeout=0.8)
            out[name] = {"running": True,  "url": s["url"]}
        except Exception:
            out[name] = {"running": False, "url": s["url"]}
    return out


async def chat(message: str, history: list[dict]) -> str:
    """
    Send message to Gemini (via LangChain), which calls the 3 MCP servers as
    real MCP tools.

    Args:
        message: User question
        history: [{role: "user"|"assistant", content: str}, ...]

    Returns:
        Gemini's final answer as a string
    """
    messages = [SystemMessage(content=SCHEMA)]
    for h in history:
        if h.get("role") == "user":
            messages.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            messages.append(AIMessage(content=h["content"]))
    messages.append(HumanMessage(content=message))

    mcp_client = MultiServerMCPClient(MCP_SERVERS)
    tools = await mcp_client.get_tools()
    tool_map = {t.name: t for t in tools}

    llm = ChatGoogleGenerativeAI(model=MODEL, api_key=os.getenv("GEMINI_API_KEY"))
    llm_with_tools = llm.bind_tools(tools)

    for _ in range(10):
        resp = await llm_with_tools.ainvoke(messages)
        messages.append(resp)

        if not resp.tool_calls:
            # .text normalizes content that some models (e.g. thinking-enabled
            # ones) return as a list of content blocks instead of a plain
            # string — using .content directly would leak raw block dicts
            # into the chat UI.
            return resp.text or "No response."

        for tc in resp.tool_calls:
            tool = tool_map.get(tc["name"])
            if tool is None:
                result_text = f'{{"error": "unknown tool: {tc["name"]}"}}'
            else:
                result_text = str(await tool.ainvoke(tc["args"]))
            messages.append(ToolMessage(content=result_text, tool_call_id=tc["id"]))

    return "Reached tool call limit — try rephrasing your question."
