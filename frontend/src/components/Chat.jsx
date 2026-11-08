import { useState, useRef, useEffect } from 'react'

const QUICK = [
  'What breaks if CREDITVAL changes?',
  'Why does BILLJOB keep failing?',
  'Which LPAR has the highest CPU?',
  'Show me the modernisation strategy for PAYROLL',
  'What is our current R4HA billing risk?',
  'Which jobs depend on PAYJOB completing?',
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div className={`max-w-3xl rounded-xl px-4 py-3 ${
        isUser
          ? 'bg-[#00BDCF]/10 border border-[#00BDCF]/30 text-[#D2E4F2]'
          : 'bg-[#0F1C2E] border border-[#1A2C47] text-[#D2E4F2]'
      }`}>
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 pb-2 border-b border-[#1A2C47]">
            <span className="text-[#00BDCF] text-xs font-bold">🤖 MAIA (Gemini + MCP)</span>
          </div>
        )}
        <div className="text-sm whitespace-pre-wrap leading-relaxed">
          {msg.content}
        </div>
      </div>
    </div>
  )
}

export default function Chat() {
  const [history, setHistory]   = useState([])
  const [input,   setInput]     = useState('')
  const [loading, setLoading]   = useState(false)
  const bottomRef               = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({behavior:'smooth'}) }, [history])

  const send = async (msg) => {
    const message = msg || input.trim()
    if (!message || loading) return
    setInput('')

    const newHistory = [...history, {role:'user', content:message}]
    setHistory(newHistory)
    setLoading(true)

    try {
      const r = await fetch('/api/chat', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ message, history }),
      })
      const d = await r.json()
      setHistory([...newHistory, {role:'assistant', content:d.reply}])
    } catch(e) {
      setHistory([...newHistory, {role:'assistant', content:`❌ Error: ${e.message}`}])
    }
    setLoading(false)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-200px)] gap-4">

      {/* How it works banner */}
      <div className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] p-3">
        <div className="flex items-center gap-6 text-xs text-[#7A9FBF]">
          <span>🧠 <strong className="text-[#00BDCF]">Gemini</strong> reads schema only (~300 tokens)</span>
          <span>→</span>
          <span>✍️ Gemini <strong className="text-white">writes its own</strong> Cypher + SQL queries</span>
          <span>→</span>
          <span>🔌 <strong className="text-[#F5A020]">MCP servers</strong> execute against live data</span>
          <span>→</span>
          <span>💬 Gemini synthesises from real results</span>
        </div>
      </div>

      {/* Quick questions */}
      <div className="flex flex-wrap gap-2">
        {QUICK.map(q => (
          <button
            key={q}
            onClick={() => send(q)}
            disabled={loading}
            className="text-xs px-3 py-1.5 rounded-full border border-[#1A2C47] bg-[#0F1C2E] text-[#7A9FBF] hover:border-[#00BDCF] hover:text-[#00BDCF] transition-colors disabled:opacity-40"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Message list */}
      <div className="flex-1 overflow-y-auto rounded-xl border border-[#1A2C47] bg-[#0D1828] p-4">
        {history.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center gap-3">
            <span className="text-5xl">🖥️</span>
            <p className="text-white font-semibold">Ask MAIA anything about your mainframe</p>
            <p className="text-[#7A9FBF] text-sm max-w-md">
              Gemini writes Cypher and SQL queries itself — no pre-written tools.
              It queries live Neo4j, SQLite, and ChromaDB via MCP servers.
            </p>
          </div>
        ) : (
          <>
            {history.map((m,i) => <Message key={i} msg={m} />)}
            {loading && (
              <div className="flex justify-start mb-4">
                <div className="bg-[#0F1C2E] border border-[#1A2C47] rounded-xl px-4 py-3">
                  <div className="flex items-center gap-2 text-xs text-[#7A9FBF]">
                    <span className="animate-spin">⟳</span>
                    Gemini writing queries + querying live data…
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="flex gap-3">
        <input
          value={input}
          onChange={e=>setInput(e.target.value)}
          onKeyDown={e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}}}
          placeholder="Ask about programs, jobs, costs, dependencies, modernisation…"
          disabled={loading}
          className="flex-1 bg-[#0F1C2E] border border-[#1A2C47] rounded-xl px-4 py-3 text-sm text-[#D2E4F2] placeholder-[#7A9FBF] focus:outline-none focus:border-[#00BDCF] disabled:opacity-50"
        />
        <button
          onClick={()=>send()}
          disabled={loading || !input.trim()}
          className="px-5 py-3 bg-[#00BDCF] hover:bg-[#00A8C0] text-[#0D1828] font-bold rounded-xl text-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? '…' : '↑ Send'}
        </button>
        {history.length > 0 && (
          <button
            onClick={()=>setHistory([])}
            className="px-3 py-3 border border-[#1A2C47] rounded-xl text-xs text-[#7A9FBF] hover:text-white transition-colors"
          >
            Clear
          </button>
        )}
      </div>

    </div>
  )
}
