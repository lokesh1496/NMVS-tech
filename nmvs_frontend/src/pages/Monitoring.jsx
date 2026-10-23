import { useCallback, useEffect, useState } from 'react'
import { Activity, Clock3, RefreshCw, Search } from 'lucide-react'
import { getMonitoringHistory, getDeviceHistory, checkDevice } from '../api/monitoring'
import { getDevices } from '../api/devices'
import { getApiError } from '../api/axios'
import { useRemote } from '../hooks/useRemote'
import { Button, DataTable, ErrorState, Notice, PageHeader, RefreshButton, Spinner, StatusBadge } from '../components/common'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function Monitoring() {
  const [filterIp, setFilterIp] = useState('')
  const [devices, setDevices] = useState([])
  const [notice, setNotice] = useState('')
  const [checking, setChecking] = useState(false)
  const loader = useCallback(() => filterIp ? getDeviceHistory(filterIp, 100) : getMonitoringHistory(100), [filterIp])
  const { data, loading, error, reload } = useRemote(loader, [loader])
  const loadDevices = useCallback(() => getDevices().then((rows) => setDevices(rows)).catch((e) => setNotice(getApiError(e))), [])
  useEffect(() => { loadDevices() }, [loadDevices])
  async function checkNow() {
    if (!filterIp) { setNotice('Select a device before running a live monitoring check.'); return }
    setChecking(true); setNotice('')
    try { const item = await checkDevice(filterIp); setNotice(`Check completed: ${item.status} · ${item.ip}`); reload() }
    catch (e) { setNotice(getApiError(e)) }
    finally { setChecking(false) }
  }
  const chartData = (data || []).slice().reverse().map((row) => ({ time: row.checked_at ? new Date(row.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '', online: String(row.status).toLowerCase() === 'online' ? 1 : 0 }))
  return <>
    <PageHeader eyebrow="AVAILABILITY & LATENCY" title="Monitoring" description="Review monitoring history and trigger an on-demand availability check." actions={<RefreshButton onClick={reload} loading={loading} />} />
    <section className="panel monitoring-controls"><div className="filter-control"><label htmlFor="monitor-device">Device filter</label><div className="select-with-icon"><Search size={15} /><select id="monitor-device" value={filterIp} onChange={(e) => setFilterIp(e.target.value)}><option value="">All devices</option>{devices.map((device) => <option key={device.id} value={device.ip}>{device.name} · {device.ip}</option>)}</select></div></div><Button variant="secondary" onClick={checkNow} disabled={checking || !filterIp}>{checking ? 'Checking…' : <><RefreshCw size={15} /> Check selected now</>}</Button></section>
    {notice && <Notice onClose={() => setNotice('')}>{notice}</Notice>}
    {loading && !data ? <Spinner /> : error ? <ErrorState error={error} retry={reload} /> : <>
      <div className="metrics-grid metrics-grid-small"><article className="metric-card"><div className="metric-icon tone-cyan"><Activity size={18} /></div><div className="metric-label">Checks returned</div><div className="metric-value">{data?.length ?? '—'}</div><div className="metric-detail">Latest 100 records</div></article><article className="metric-card"><div className="metric-icon tone-green"><Clock3 size={18} /></div><div className="metric-label">Online checks</div><div className="metric-value">{data?.filter((item) => String(item.status).toLowerCase() === 'online').length ?? '—'}</div><div className="metric-detail">Within returned history</div></article><article className="metric-card"><div className="metric-icon tone-red"><Activity size={18} /></div><div className="metric-label">Offline checks</div><div className="metric-value">{data?.filter((item) => String(item.status).toLowerCase() === 'offline').length ?? '—'}</div><div className="metric-detail">Within returned history</div></article></div>
      <section className="panel chart-panel"><div className="panel-heading"><div><h2>Availability history</h2><p>Online/offline state from recorded checks. The monitoring API does not expose latency.</p></div><span className="chart-legend"><i /> Reachable</span></div>{chartData.length ? <div className="chart-area chart-area-short"><ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData}><CartesianGrid stroke="var(--border-soft)" strokeDasharray="3 5" vertical={false} /><XAxis dataKey="time" tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false} /><YAxis domain={[0, 1]} ticks={[0, 1]} tickFormatter={(v) => v ? 'Online' : 'Offline'} tick={{ fill: 'var(--muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={56} /><Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, color: 'var(--text)' }} /><Area dataKey="online" type="stepAfter" stroke="var(--cyan)" fill="var(--cyan)" fillOpacity={0.12} /></AreaChart></ResponsiveContainer></div> : <div className="chart-empty">No monitoring history returned by the API.</div>}</section>
      <section className="panel table-panel"><div className="panel-heading"><div><h2>Monitoring records</h2><p>Records in API order, with the latest checks first.</p></div></div><DataTable rows={data || []} columns={[{ key: 'ip', label: 'IP address' }, { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> }, { key: 'checked_at', label: 'Checked at', render: (row) => row.checked_at ? new Date(row.checked_at).toLocaleString() : '—' }]} empty="No monitoring history" /></section>
    </>}
  </>
}
