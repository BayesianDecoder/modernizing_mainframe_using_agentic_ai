import { useState, useEffect } from 'react'
import Dashboard   from './components/Dashboard.jsx'
import LPARMonitor from './components/LPARMonitor.jsx'
import JobHistory  from './components/JobHistory.jsx'
import Chat        from './components/Chat.jsx'

const TABS = [
  { id:'dashboard',  label:'🔔 Dashboard'    },
  { id:'lpar',       label:'📊 LPAR Monitor' },
  { id:'jobs',       label:'📋 Job History'  },
  { id:'chat',       label:'💬 Ask MAIA'     },
]

export default function App() {
  const [tab, setTab]       = useState('dashboard')
  const [stats, setStats]   = useState({})
  const [mcp, setMcp]       = useState({})

  // Header stats — refresh every 30s
  useEffect(() => {
    const load = () => {
      fetch('/api/stats').then(r=>r.json()).then(setStats).catch(()=>{})
      fetch('/api/mcp-status').then(r=>r.json()).then(setMcp).catch(()=>{})
    }
    load()
    const t = setInterval(load, 30000)
    return () => clearInterval(t)
  }, [])

  const mcpRunning = Object.values(mcp).filter(s=>s.running).length
  const mcpTotal   = Object.values(mcp).length

  return (
    <div className="min-h-screen bg-[#0D1828]">

      {/* ── Top bar ─────────────────────────────────────────── */}
      <header className="bg-[#0F1C2E] border-b border-[#1A2C47] px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-2xl font-bold text-white tracking-tight">MAIA</span>
            <span className="text-[#00BDCF] text-sm italic">Mainframe Agentic Intelligence</span>
            <span className="flex items-center gap-1.5 ml-3">
              <span className="w-2 h-2 rounded-full bg-green-400 pulse-red"></span>
              <span className="text-green-400 text-xs font-semibold">LIVE</span>
            </span>
          </div>

          {/* Stat chips */}
          <div className="flex items-center gap-4 text-sm">
            <Chip label="Programs"   value={stats.programs   ?? '—'} color="teal"   />
            <Chip label="Jobs"       value={stats.jobs       ?? '—'} color="blue"   />
            <Chip label="Alerts"     value={stats.alerts     ?? '—'} color={stats.alerts>0?"red":"green"} />
            <Chip label="Peak MIPS"  value={stats.peak_mips?.toLocaleString() ?? '—'} color="orange" />
            <div className="text-xs text-[#7A9FBF] border border-[#1A2C47] rounded px-2 py-1">
              MCP {mcpRunning}/{mcpTotal} 🔌
            </div>
          </div>
        </div>
      </header>

      {/* ── Tabs ─────────────────────────────────────────────── */}
      <nav className="bg-[#0F1C2E] border-b border-[#1A2C47] px-6">
        <div className="max-w-7xl mx-auto flex gap-1">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t.id
                  ? 'border-[#00BDCF] text-[#00BDCF]'
                  : 'border-transparent text-[#7A9FBF] hover:text-white'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </nav>

      {/* ── Page ─────────────────────────────────────────────── */}
      <main className="max-w-7xl mx-auto px-6 py-6">
        {tab === 'dashboard' && <Dashboard />}
        {tab === 'lpar'      && <LPARMonitor />}
        {tab === 'jobs'      && <JobHistory />}
        {tab === 'chat'      && <Chat />}
      </main>

    </div>
  )
}

function Chip({ label, value, color }) {
  const colors = {
    teal:   'text-[#00BDCF]',
    blue:   'text-blue-400',
    orange: 'text-orange-400',
    green:  'text-green-400',
    red:    'text-red-400',
  }
  return (
    <div className="text-center border border-[#1A2C47] rounded px-3 py-1">
      <div className={`font-bold text-base ${colors[color]}`}>{value}</div>
      <div className="text-[10px] text-[#7A9FBF] uppercase tracking-wide">{label}</div>
    </div>
  )
}
