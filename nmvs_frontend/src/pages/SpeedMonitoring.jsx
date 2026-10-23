import { useCallback, useState } from 'react'
import { ArrowDownToLine, ArrowUpFromLine, Gauge, Trash2, Zap } from 'lucide-react'
import { deleteSpeedHistory, getSpeedHistory, runSpeedTest } from '../api/speedMonitoring'
import { getApiError } from '../api/axios'
import { useRemote } from '../hooks/useRemote'
import { Button, DataTable, ErrorState, MetricCard, Notice, PageHeader, RefreshButton, Spinner } from '../components/common'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

function Speedometer({ speed, loading }) {
  const numericSpeed = Number(speed)
  const hasSpeed = speed != null && Number.isFinite(numericSpeed) && numericSpeed >= 0
  const thresholds = [10, 25, 50, 100, 250, 500, 1000]
  const maximum = thresholds.find((threshold) => numericSpeed <= threshold) || thresholds[thresholds.length - 1]
  const progress = hasSpeed ? Math.min(numericSpeed / maximum, 1) : 0
  const needleAngle = progress * 180
  const ticks = Array.from({ length: 81 }, (_, index) => {
    const angle = 180 - index * 2.25
    const radians = angle * Math.PI / 180
    const major = index % 10 === 0
    const medium = index % 5 === 0
    const innerRadius = major ? 194 : medium ? 198 : 202
    const outerRadius = 216
    return {
      angle,
      major,
      medium,
      x1: 280 + Math.cos(radians) * innerRadius,
      y1: 300 - Math.sin(radians) * innerRadius,
      x2: 280 + Math.cos(radians) * outerRadius,
      y2: 300 - Math.sin(radians) * outerRadius,
    }
  })
  const labels = Array.from({ length: 9 }, (_, index) => {
    const angle = (180 - index * 22.5) * Math.PI / 180
    return {
      value: index,
      x: 280 + Math.cos(angle) * 179,
      y: 300 - Math.sin(angle) * 179,
    }
  })

  return (
    <div className={`speedometer-card ${loading ? 'speedometer-testing' : ''} ${!loading && !hasSpeed ? 'speedometer-ready' : ''}`} role="img" aria-label={loading ? 'Speed test in progress' : `Download speed ${hasSpeed ? `${numericSpeed} megabits per second` : 'not measured'}`}>
      <div className="speedometer-topline"><span className="speedometer-live-dot" /><span>LATEST DOWNLOAD</span><strong>{loading ? '…' : hasSpeed ? `${numericSpeed.toLocaleString(undefined, { maximumFractionDigits: 1 })} Mbps` : '— Mbps'}</strong></div>
      <svg className="speedometer-dial" viewBox="0 0 560 360" aria-hidden="true">
        <defs>
          <linearGradient id="speedometer-fill" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#148bff" />
            <stop offset="82%" stopColor="#08b9ff" />
            <stop offset="100%" stopColor="#72ddff" />
          </linearGradient>
          <filter id="speedometer-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <path d="M 64 300 A 216 216 0 0 0 496 300" className="speedometer-outer-orbit" />
        <path d="M 64 300 A 216 216 0 0 0 496 300" className="speedometer-track" />
        <path d="M 64 300 A 216 216 0 0 0 496 300" className="speedometer-value-track" pathLength="100" strokeDasharray={`${progress * 100} 100`} filter="url(#speedometer-glow)" />
        <path d="M 153 300 A 127 127 0 0 0 407 300" className="speedometer-inner-track" />
        <path d="M 171 300 A 109 109 0 0 0 389 300" className="speedometer-inner-track speedometer-inner-track-accent" />
        {ticks.map((tick) => <line key={tick.angle} x1={tick.x1} y1={tick.y1} x2={tick.x2} y2={tick.y2} className={`speedometer-tick ${tick.major ? 'speedometer-tick-major' : tick.medium ? 'speedometer-tick-medium' : ''}`} />)}
        {labels.map((label) => <text key={label.value} x={label.x} y={label.y} className="speedometer-label">{label.value}</text>)}
        <text x="280" y="150" className="speedometer-unit">Mbps</text>
        <g className="speedometer-needle" transform={`rotate(${needleAngle} 280 300)`}>
          <path d="M 280 300 L 125 300" className="speedometer-needle-trail" />
          <path d="M 280 300 L 125 300" />
        </g>
        <circle cx="280" cy="300" r="12" className="speedometer-hub-ring" />
        <circle cx="280" cy="300" r="6" className="speedometer-hub" />
      </svg>
    </div>
  )
}

export default function SpeedMonitoring() {
  const loader = useCallback(() => getSpeedHistory(100), [])
  const { data, loading, error, reload } = useRemote(loader)
  const [targetIp, setTargetIp] = useState('')
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)
  const [notice, setNotice] = useState('')
  const [noticeType, setNoticeType] = useState('success')
  async function startTest(event) {
    event.preventDefault(); setBusy(true); setNotice(''); setResult(null)
    try { const record = await runSpeedTest(targetIp.trim()); setResult(record); setNoticeType('success'); setNotice('Speed test completed and saved to history.'); reload() }
    catch (e) { setNoticeType('error'); setNotice(getApiError(e)) }
    finally { setBusy(false) }
  }
  async function remove(id) {
    if (!window.confirm('Delete this saved speed test record?')) return
    try { await deleteSpeedHistory(id); setNoticeType('success'); setNotice('Speed test record deleted.'); reload() }
    catch (e) { setNoticeType('error'); setNotice(getApiError(e)) }
  }
  const chartData = (data || []).slice().reverse().map((item) => ({ date: item.tested_at ? new Date(item.tested_at).toLocaleDateString() : '', Download: item.download_mbps, Upload: item.upload_mbps }))
  const displayedResult = busy ? null : result || data?.[0]
  return <>
    <PageHeader eyebrow="PERFORMANCE" title="Speed monitoring" description="Run a backend speed test and review saved download, upload and ping results." actions={<RefreshButton onClick={reload} loading={loading} />} />
    {notice && <Notice type={noticeType} onClose={() => setNotice('')}>{notice}</Notice>}
    <section className="panel speed-run-panel"><div className="speed-run-copy"><span className="eyebrow">ON-DEMAND TEST</span><h2>Measure network performance</h2><p>Enter an IP address or host name to label this speed test in your history.</p><form className="speed-run-form" onSubmit={startTest}><label>Target IP or name<input required value={targetIp} onChange={(e) => setTargetIp(e.target.value)} placeholder="e.g. 192.168.1.1" /></label><Button disabled={busy}>{busy ? <><span className="button-loader" />Testing…</> : <><Zap size={16} /> Run speed test</>}</Button></form></div><Speedometer speed={displayedResult?.download_mbps} loading={busy} /></section>
    {result && <div className="metrics-grid metrics-grid-small result-metrics"><MetricCard label="Download" value={result.download_mbps != null ? `${result.download_mbps} Mbps` : '—'} icon={ArrowDownToLine} tone="cyan" /><MetricCard label="Upload" value={result.upload_mbps != null ? `${result.upload_mbps} Mbps` : '—'} icon={ArrowUpFromLine} tone="purple" /><MetricCard label="Latency" value={result.ping_ms != null ? `${result.ping_ms} ms` : '—'} icon={Zap} tone="amber" /><MetricCard label="Target" value={result.ip || '—'} icon={Gauge} tone="green" />{result.error && <div className="error-detail">{result.error}</div>}</div>}
    {loading && !data ? <Spinner /> : error ? <ErrorState error={error} retry={reload} /> : <>
      <section className="panel chart-panel"><div className="panel-heading"><div><h2>Performance over time</h2><p>Historical results returned by the backend. Values in Mbps.</p></div></div>{chartData.length ? <div className="chart-area chart-area-short"><ResponsiveContainer width="100%" height="100%"><LineChart data={chartData}><CartesianGrid stroke="var(--border-soft)" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="date" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false} /><Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)' }} /><Line dataKey="Download" stroke="var(--cyan)" strokeWidth={2} dot={{ r: 3 }} connectNulls /><Line dataKey="Upload" stroke="var(--teal)" strokeWidth={2} dot={{ r: 3 }} connectNulls /></LineChart></ResponsiveContainer></div> : <div className="chart-empty">No saved speed test history.</div>}</section>
      <section className="panel table-panel"><div className="panel-heading"><div><h2>Test history</h2><p>{data?.length || 0} records returned</p></div></div><DataTable rows={data || []} columns={[{ key: 'ip', label: 'Target' }, { key: 'download_mbps', label: 'Download', render: (r) => r.download_mbps == null ? '—' : `${r.download_mbps} Mbps` }, { key: 'upload_mbps', label: 'Upload', render: (r) => r.upload_mbps == null ? '—' : `${r.upload_mbps} Mbps` }, { key: 'ping_ms', label: 'Ping', render: (r) => r.ping_ms == null ? '—' : `${r.ping_ms} ms` }, { key: 'tested_at', label: 'Tested at', render: (r) => r.tested_at ? new Date(r.tested_at).toLocaleString() : '—' }, { key: 'actions', label: '', render: (r) => <button className="table-icon-action danger-action" title="Delete record" onClick={() => remove(r.id)}><Trash2 size={15} /></button> }]} empty="No speed tests recorded" /></section>
    </>}
  </>
}
