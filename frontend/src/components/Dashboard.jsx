import { useState, useEffect } from 'react'

const SEV_STYLE = {
  CRITICAL: { bg:'bg-red-500/10',    border:'border-red-500',    text:'text-red-400',    badge:'bg-red-500'    },
  HIGH:     { bg:'bg-orange-500/10', border:'border-orange-500', text:'text-orange-400', badge:'bg-orange-500' },
  MEDIUM:   { bg:'bg-yellow-500/10', border:'border-yellow-500', text:'text-yellow-400', badge:'bg-yellow-500' },
  LOW:      { bg:'bg-blue-500/10',   border:'border-blue-500',   text:'text-blue-400',   badge:'bg-blue-500'   },
}

function AlertCard({ alert }) {
  const s = SEV_STYLE[alert.severity] || SEV_STYLE.LOW
  const age = alert.ts
    ? Math.round((Date.now() - new Date(alert.ts).getTime()) / 1000)
    : null

  return (
    <div className={`rounded-lg border ${s.border} ${s.bg} p-4 flex items-start gap-4`}>
      <div className="flex-shrink-0 mt-0.5">
        <span className={`inline-block px-2 py-0.5 text-xs font-bold rounded text-white ${s.badge}`}>
          {alert.severity}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <p className={`font-semibold text-sm ${s.text}`}>{alert.name}</p>
        <p className="text-[#D2E4F2] text-sm mt-0.5 leading-snug">{alert.message}</p>
        {alert.job   && <span className="mt-1 inline-block text-xs text-[#7A9FBF] font-mono">job:{alert.job}</span>}
        {alert.lpar  && <span className="mt-1 inline-block text-xs text-[#7A9FBF] font-mono ml-2">lpar:{alert.lpar}</span>}
        {alert.suggestion && (
          <p className="mt-2 text-xs text-[#F5A020] bg-[#F5A020]/10 border border-[#F5A020]/30 rounded px-2 py-1.5 leading-snug">
            💡 {alert.suggestion}
          </p>
        )}
      </div>
      {age != null && (
        <div className="flex-shrink-0 text-xs text-[#7A9FBF]">
          {age < 60 ? `${age}s ago` : `${Math.round(age/60)}m ago`}
        </div>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [data, setData]       = useState({ alerts:[], count:0, critical:0, high:0 })
  const [lastUpdate, setLast] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const r = await fetch('/api/alerts')
      setData(await r.json())
      setLast(new Date())
    } catch(e) {
      console.error(e)
    }
    setLoading(false)
  }

  useEffect(() => { load(); const t = setInterval(load, 30000); return ()=>clearInterval(t) }, [])

  const { alerts, critical, high } = data
  const medium  = alerts.filter(a=>a.severity==='MEDIUM').length
  const low     = alerts.filter(a=>a.severity==='LOW').length

  return (
    <div className="space-y-6">

      {/* Summary row */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label:'Critical', value:critical,                           color:'text-red-400',    bg:'bg-red-500/10',    border:'border-red-500/30'    },
          { label:'High',     value:high,                               color:'text-orange-400', bg:'bg-orange-500/10', border:'border-orange-500/30' },
          { label:'Medium',   value:medium,                             color:'text-yellow-400', bg:'bg-yellow-500/10', border:'border-yellow-500/30' },
          { label:'Low',      value:low,                                color:'text-blue-400',   bg:'bg-blue-500/10',   border:'border-blue-500/30'   },
        ].map(c => (
          <div key={c.label} className={`rounded-xl border ${c.border} ${c.bg} p-5 text-center`}>
            <div className={`text-4xl font-bold ${c.color}`}>{c.value}</div>
            <div className="text-xs text-[#7A9FBF] uppercase tracking-wide mt-1">{c.label}</div>
          </div>
        ))}
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-white font-bold text-lg">Active Alerts</h2>
        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-xs text-[#7A9FBF]">
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
          )}
          <button
            onClick={load}
            className="px-3 py-1 text-xs bg-[#1A2C47] hover:bg-[#223550] text-[#00BDCF] rounded border border-[#1A2C47] transition-colors"
          >
            {loading ? '⟳ Refreshing…' : '⟳ Refresh'}
          </button>
          <span className="text-xs text-[#7A9FBF]">Auto-refreshes every 30s</span>
        </div>
      </div>

      {/* Alert list */}
      {alerts.length === 0 ? (
        <div className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] p-12 text-center">
          <div className="text-green-400 text-4xl mb-3">✓</div>
          <p className="text-white font-semibold">All systems nominal</p>
          <p className="text-[#7A9FBF] text-sm mt-1">No active alerts</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((a, i) => <AlertCard key={a.id || i} alert={a} />)}
        </div>
      )}

      {/* Alert rule legend */}
      <div className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] p-4">
        <p className="text-xs font-semibold text-[#7A9FBF] uppercase tracking-wide mb-3">
          Alert Rules (pure SQL/Cypher — zero Claude cost)
        </p>
        <div className="grid grid-cols-2 gap-2">
          {[
            ['LPAR CPU > 85%',     'CRITICAL/HIGH', 'Every 30s'],
            ['Job RC ≠ 0 (30min)', 'CRITICAL',      'Every 30s'],
            ['R4HA > 9,000 MSU',   'HIGH',          'Every 30s'],
            ['Job > 150% avg time','MEDIUM',         'Every 30s'],
            ['Jobs share LPAR',    'LOW',            'Every 30s'],
          ].map(([rule, sev, freq]) => (
            <div key={rule} className="flex items-center gap-2 text-xs">
              <span className="text-[#00BDCF]">▸</span>
              <span className="text-[#D2E4F2] flex-1">{rule}</span>
              <span className="text-[#7A9FBF]">{sev}</span>
              <span className="text-[#7A9FBF] font-mono">{freq}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}
