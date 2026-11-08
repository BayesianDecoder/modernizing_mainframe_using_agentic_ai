import { useState, useEffect } from 'react'

const RC_STYLE = rc =>
  rc === 0 ? 'bg-green-500/20 text-green-400 border-green-500/30'
           : rc <= 4 ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
           : 'bg-red-500/20 text-red-400 border-red-500/30'

export default function JobHistory() {
  const [jobs, setJobs] = useState([])
  const [filter, setFilter] = useState('')

  const load = async () => {
    try {
      const r = await fetch('/api/jobs')
      const d = await r.json()
      setJobs(d.data || [])
    } catch(e) {}
  }

  useEffect(() => { load(); const t = setInterval(load, 30000); return ()=>clearInterval(t) }, [])

  const visible = filter
    ? jobs.filter(j=>j.job?.toLowerCase().includes(filter.toLowerCase()))
    : jobs

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-white font-bold text-lg">Recent Job Runs</h2>
        <input
          value={filter} onChange={e=>setFilter(e.target.value)}
          placeholder="Filter by job name…"
          className="bg-[#0F1C2E] border border-[#1A2C47] rounded-lg px-3 py-1.5 text-sm text-[#D2E4F2] placeholder-[#7A9FBF] focus:outline-none focus:border-[#00BDCF] w-48"
        />
      </div>

      <div className="rounded-xl border border-[#1A2C47] bg-[#0F1C2E] overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-[#0D1828] text-[#7A9FBF] text-xs uppercase tracking-wide">
              {['Job','LPAR','Date','Start','Elapsed (min)','MIPS','RC','Status'].map(h=>(
                <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr><td colSpan={8} className="px-4 py-8 text-center text-[#7A9FBF]">
                No job records yet — simulator generates data every 6-12 minutes
              </td></tr>
            ) : visible.map((j,i) => (
              <tr key={j.id||i} className="border-t border-[#1A2C47] hover:bg-[#1A2C47]/30 transition-colors">
                <td className="px-4 py-3 font-mono font-semibold text-white">{j.job}</td>
                <td className="px-4 py-3 text-[#7A9FBF] font-mono text-xs">{j.lpar}</td>
                <td className="px-4 py-3 text-[#7A9FBF] text-xs">{j.date}</td>
                <td className="px-4 py-3 text-[#D2E4F2] font-mono text-xs">{j.start_time}</td>
                <td className="px-4 py-3">
                  <span className="text-[#D2E4F2]">{j.elapsed_mins?.toFixed(1)}</span>
                </td>
                <td className="px-4 py-3 text-[#00BDCF] font-mono text-xs">
                  {j.mips?.toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-bold border ${RC_STYLE(j.rc)}`}>
                    RC={j.rc}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium ${j.status==='SUCCESS'?'text-green-400':'text-red-400'}`}>
                    {j.status}
                  </span>
                  {j.error && (
                    <p className="text-red-400 text-xs mt-0.5 font-mono truncate max-w-xs" title={j.error}>
                      {j.error.slice(0,50)}…
                    </p>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-[#7A9FBF]">
        Showing last 30 runs · Auto-refreshes every 30s · Simulator runs NIGHTLY every 6min, PAYJOB/BILLJOB every 10-12min
      </p>
    </div>
  )
}
