import { useState } from 'react'
import { Activity, ArrowUpRight, Network, Radio, Search, Signal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDiscoveryTopology } from '../api/topology'
import { createLocalDetection, getLocalDetectionResult } from '../api/devices'
import { getApiError } from '../api/axios'
import { Button, DataTable, Notice, PageHeader, StatusBadge } from '../components/common'

export default function Discovery() {
  const [network, setNetwork] = useState('')
  const [ip, setIp] = useState('')
  const [results, setResults] = useState(null)
  const [pingResult, setPingResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const [pingBusy, setPingBusy] = useState(false)
  const [error, setError] = useState('')
  const [pingError, setPingError] = useState('')
  async function scan(event) {
    event.preventDefault(); setBusy(true); setError(''); setResults(null)
    try {
      const cidr = network.trim()
      const topology = await getDiscoveryTopology(cidr, true)
      localStorage.setItem('nmvs_topology_grouping_network', cidr)
      setResults({ network: cidr, count: topology.nodes.length, devices: topology.nodes })
    } catch (e) { setError(getApiError(e)) } finally { setBusy(false) }
  }
  async function ping(event) {
    event.preventDefault(); setPingBusy(true); setPingError(''); setPingResult(null)
    try {
      const created = await createLocalDetection(ip.trim())
      const startedAt = Date.now()
      let result = created
      while (Date.now() - startedAt < 35000 && ['pending', 'running'].includes(result.status)) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500))
        result = await getLocalDetectionResult(created.job_id)
      }
      if (['pending', 'running'].includes(result.status)) {
        throw new Error('Local Agent did not respond. Check that it is running and connected to this backend.')
      }
      if (result.status !== 'completed') {
        throw new Error(result.error_message || `Ping job ${result.status}.`)
      }
      setPingResult({
        ip: result.ip,
        status: result.result_status,
        latency_ms: result.latency_ms,
      })
    } catch (e) {
      setPingError(e.message && !e.response ? e.message : getApiError(e))
    } finally {
      setPingBusy(false)
    }
  }
  return <>
    <PageHeader eyebrow="NETWORK VISIBILITY" title="Network discovery" description="Scan a CIDR network from the backend, or ping one IP from the connected Local Agent." />
    <div className="discovery-grid">
      <section className="panel discovery-card"><div className="panel-heading"><div className="feature-title"><span className="feature-icon"><Network size={18} /></span><div><h2>Scan network range</h2><p>Scans up to 4,096 addresses, identifies reachable devices, and adds them to Topology inventory.</p></div></div></div><form className="inline-form" onSubmit={scan}><label>CIDR network<input required placeholder="192.168.1.0/24" value={network} onChange={(e) => setNetwork(e.target.value)} /></label><Button disabled={busy}>{busy ? <><span className="button-loader" />Scanning…</> : <><Search size={16} /> Start scan</>}</Button></form>{busy && <Notice>Scanning and identifying reachable devices. Duration depends on network size and response time.</Notice>}{error && <Notice type="error">{error}</Notice>}{results && <div className="scan-result-summary"><span className="live-dot" /> Scan complete · {results.count} reachable {results.count === 1 ? 'device' : 'devices'} · {results.network}<Link className="text-link" to="/topology">View in Topology <ArrowUpRight size={14} /></Link></div>}</section>
      <section className="panel discovery-card"><div className="panel-heading"><div className="feature-title"><span className="feature-icon feature-purple"><Radio size={18} /></span><div><h2>Ping test via Local Agent</h2><p>Ping one IPv4 or IPv6 address from the computer running the Local Agent.</p></div></div></div><form className="inline-form" onSubmit={ping}><label>IP address<input required placeholder="192.168.1.1" value={ip} onChange={(e) => setIp(e.target.value)} /></label><Button variant="secondary" disabled={pingBusy}>{pingBusy ? 'Waiting for agent…' : <><Activity size={16} /> Ping address</>}</Button></form>{pingError && <Notice type="error">{pingError}</Notice>}{pingResult && <div className="ping-result"><Signal size={18} /><strong>{pingResult.ip}</strong><StatusBadge status={pingResult.status} />{pingResult.latency_ms != null && <span>{pingResult.latency_ms} ms</span>}</div>}</section>
    </div>
    <section className="panel table-panel"><div className="panel-heading"><div><h2>Discovered devices</h2><p>Detected devices are saved to inventory and shown in the Topology module by the scanned CIDR.</p></div></div>{results ? <DataTable rows={results.devices || []} empty="No reachable hosts returned by scan" columns={[{ key: 'name', label: 'Device' }, { key: 'ip', label: 'IP address' }, { key: 'device_type', label: 'Device type' }, { key: 'status', label: 'Status', render: (row) => <StatusBadge status={row.status} /> }]} /> : <div className="chart-empty">Enter a network CIDR and run a scan to discover devices.</div>}</section>
  </>
}
