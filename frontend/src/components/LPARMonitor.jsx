import { useState, useEffect } from 'react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const COLORS = { 'LPAR-1':'#00BDCF', 'LPAR-2':'#F5A020', 'LPAR-3':'#E04040' }

function buildChartData(rows) {
  // Group by timestamp, one row per time point
  const byTs = {}
  for (const r of rows) {
    const ts = r.ts?.slice(11,16) || r.hour || ''  // HH:MM
    if (!byTs[ts]) byTs[ts] = { ts }
    byTs[ts][r.lpar] = r.peak_mips
    byTs[ts][r.lpar + '_cpu'] = r.cpu_pct
  }
  return Object.values(byTs).sort((a,b)=>a.ts.localeCompare(b.ts)).slice(-30)
}

export default function LPARMonitor() {
  const [rows, setRows]   = useState([])
  const [last, setLast]   = useState(null)
  const [view, setView]   = useState('mips')  // mips | cpu

  const load = async () => {
    try {
      const r = await fetch('/api/lpar')
      const d = await r.json()
      setRows(d.data || [])
      setLast(new Date())
    } catch(e) { console.error(e) }
  }

  useEffect(() => { load(); const t = setInterval(load, 10000); return ()=>clearInterval(t) }, [])

  const chartData = buildChartData(rows)
  const lpars = ['LPAR-1','LPAR-2','LPAR-3']

  // Latest values per LPAR
  const latest = {}
  for (const lpar of lpars) {
    const relevant = rows.filter(r=>r.lpar===lpar).slice(-3)
    if (relevant.length) {
      latest[lpar] = relevant[relevant.length-1]
    }
  }

  return (
    <div className="space-y-6">

      {/* LPAR stat cards */}
      <div className="grid grid-cols-3 gap-4">
        {lpars.map(lpar => {
          const d = latest[lpar]
          const cpu = d?.cpu_pct ?? 0
          const cpuColor = cpu > 90 ? 'text-red-400' : cpu > 75 ? 'text-orange-400' : 'text-green-400'
          return (
            <div key={lpar} className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] p-5">
              <div className="flex justify-between items-start mb-3">
                <div>
                  <p className="font-bold text-white">{lpar}</p>
                  <p className="text-xs text-[#7A9FBF]">{
                    {'LPAR-1':'Production-Payments','LPAR-2':'Batch-Processing','LPAR-3':'Customer-Reporting'}[lpar]
                  }</p>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  cpu > 90 ? 'bg-red-500/20 text-red-400' :
                  cpu > 75 ? 'bg-orange-500/20 text-orange-400' :
                             'bg-green-500/20 text-green-400'
                }`}>
                  {cpu.toFixed(1)}% CPU
                </span>
              </div>
              <div style={{color:COLORS[lpar]}} className="text-3xl font-bold">
                {d?.peak_mips?.toLocaleString() ?? '—'}
              </div>
              <div className="text-xs text-[#7A9FBF] mt-1">peak MIPS</div>
              <div className="mt-3 h-1.5 bg-[#1A2C47] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100,cpu)}%`,
                    background: cpu>90?'#ef4444':cpu>75?'#f97316':'#22c55e'
                  }}
                />
              </div>
            </div>
          )
        })}
      </div>

      {/* Chart */}
      <div className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] p-5">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-white font-bold">Live Performance Chart</h2>
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg border border-[#1A2C47] overflow-hidden text-xs">
              {['mips','cpu'].map(v => (
                <button key={v}
                  onClick={()=>setView(v)}
                  className={`px-3 py-1.5 font-medium transition-colors ${
                    view===v ? 'bg-[#00BDCF] text-[#0D1828]' : 'text-[#7A9FBF] hover:text-white'
                  }`}
                >
                  {v === 'mips' ? 'Peak MIPS' : 'CPU %'}
                </button>
              ))}
            </div>
            {last && <span className="text-xs text-[#7A9FBF]">{last.toLocaleTimeString()}</span>}
          </div>
        </div>

        {chartData.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-[#7A9FBF]">
            Waiting for data…
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={chartData} margin={{top:5,right:20,bottom:5,left:10}}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1A2C47" />
              <XAxis dataKey="ts" tick={{fill:'#7A9FBF',fontSize:11}} />
              <YAxis tick={{fill:'#7A9FBF',fontSize:11}}
                     label={{value: view==='mips'?'MIPS':'CPU %',
                             angle:-90, position:'insideLeft',
                             fill:'#7A9FBF', fontSize:11}} />
              <Tooltip
                contentStyle={{background:'#0F1C2E',border:'1px solid #1A2C47',borderRadius:'8px'}}
                labelStyle={{color:'#D2E4F2'}}
                itemStyle={{color:'#D2E4F2'}}
              />
              <Legend wrapperStyle={{color:'#7A9FBF',fontSize:12}} />
              {lpars.map(lpar => (
                <Line
                  key={lpar}
                  type="monotone"
                  dataKey={view==='mips' ? lpar : lpar+'_cpu'}
                  name={lpar}
                  stroke={COLORS[lpar]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{r:4}}
                  connectNulls
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <p className="text-xs text-[#7A9FBF] text-center">
        Chart auto-refreshes every 10 seconds · Simulator injects new readings every 10s
      </p>
    </div>
  )
}
