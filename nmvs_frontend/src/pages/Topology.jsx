import { useCallback, useMemo, useState } from 'react'
import { Network, RefreshCw } from 'lucide-react'
import { getApiError } from '../api/axios'
import { getTopology } from '../api/topology'
import { useRemote } from '../hooks/useRemote'
import { Button, ErrorState, Notice, PageHeader, Spinner } from '../components/common'

function buildSubnetLayout(nodes, edges) {
  const sortedNodes = [...nodes].sort((first, second) => {
    const firstGateway = first.role === 'gateway' || first.is_gateway
    const secondGateway = second.role === 'gateway' || second.is_gateway
    return Number(secondGateway) - Number(firstGateway)
  })
  const gateway = sortedNodes[0]
  const downstream = sortedNodes.slice(1)
  const width = Math.max(900, downstream.length * 190 + 100)
  const height = downstream.length ? 250 : 210
  const positions = new Map()
  if (gateway) positions.set(gateway.id, { x: width / 2, y: 55 })
  const spacing = Math.min(205, (width - 140) / Math.max(downstream.length, 1))
  const rowWidth = spacing * Math.max(downstream.length - 1, 0)
  downstream.forEach((node, index) => {
    positions.set(node.id, {
      x: width / 2 - rowWidth / 2 + index * spacing,
      y: 190,
    })
  })

  const nodeIds = new Set(nodes.map((node) => node.id))
  const visibleEdges = edges.filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  const inferredEdges = gateway
    ? downstream
      .filter((node) => !visibleEdges.some((edge) =>
        (edge.source === gateway.id && edge.target === node.id)
        || (edge.target === gateway.id && edge.source === node.id),
      ))
      .map((node) => ({
        id: `inferred-${gateway.id}-${node.id}`,
        source: gateway.id,
        target: node.id,
        status: gateway.status === 'Offline' || node.status === 'Offline' ? 'down' : 'active',
        link_type: 'inferred',
      }))
    : []
  return {
    width,
    height,
    positions,
    edges: [...visibleEdges, ...inferredEdges],
    isInferred: visibleEdges.length === 0 && inferredEdges.length > 0,
  }
}

export default function Topology() {
  const [source, setSource] = useState('all')
  const [groupingNetwork, setGroupingNetwork] = useState(() => localStorage.getItem('nmvs_topology_grouping_network') || '')
  const loader = useCallback(
    () => getTopology({ source, connected_only: false, include_wan: false, grouping_network: groupingNetwork || undefined }),
    [source, groupingNetwork],
  )
  const { data, setData, loading, error, reload } = useRemote(loader, [source, groupingNetwork])
  const [notice, setNotice] = useState('')

  const subnetGroups = useMemo(() => {
    const groups = new Map()
    for (const node of data?.nodes || []) {
      const subnet = node.subnet || 'Unknown subnet'
      if (!groups.has(subnet)) groups.set(subnet, [])
      groups.get(subnet).push(node)
    }
    return [...groups.entries()]
      .sort(([first], [second]) => first.localeCompare(second))
      .map(([subnet, nodes]) => [subnet, nodes.sort((a, b) => a.name.localeCompare(b.name))])
  }, [data])

  async function refreshInventory() {
    setNotice('')
    try {
      const latestScan = localStorage.getItem('nmvs_topology_grouping_network') || ''
      setGroupingNetwork(latestScan)
      setData(await getTopology({ source, connected_only: false, include_wan: false, grouping_network: latestScan || undefined }))
    } catch (requestError) {
      setNotice(getApiError(requestError))
    }
  }

  return <>
    <PageHeader
      eyebrow="NETWORK MAP"
      title="Topology"
      description="Devices discovered from your network scan, grouped into the subnet you entered in Network Discovery."
      actions={<Button onClick={refreshInventory} disabled={loading}><RefreshCw size={16} className={loading ? 'spin' : ''} /> Refresh topology</Button>}
    />
    {notice && <Notice type="error" onClose={() => setNotice('')}>{notice}</Notice>}

    {loading && !data ? <Spinner label="Loading discovered network topology…" /> : error && !data ? <ErrorState error={error} retry={reload} /> : data && <>
      <div className="topology-stats">
        {[['Devices', data.summary?.total_nodes], ['Online', data.summary?.online_nodes], ['Offline', data.summary?.offline_nodes], ['Subnets', subnetGroups.length]].map(([label, value]) => <div key={label}><small>{label}</small><strong>{value ?? '—'}</strong></div>)}
      </div>
      <section className="panel topology-inventory">
        <div className="topology-inventory-heading">
          <div><h2>Discovered network devices</h2><p>{groupingNetwork ? `Grouped by discovery network ${groupingNetwork}` : `${data.nodes.length} devices organized by subnet`} · {data.summary?.total_edges ?? 0} backend links</p></div>
          <label className="topology-source-filter">Show
            <select value={source} onChange={(event) => setSource(event.target.value)}>
              <option value="all">All devices</option>
              <option value="manual">Manual inventory</option>
              <option value="discovery">Discovered</option>
            </select>
          </label>
        </div>
        {subnetGroups.length ? <div className="topology-subnet-groups">
          {subnetGroups.map(([subnet, nodes]) => <section className="topology-subnet-group" key={subnet}>
            <header><div><Network size={16} /><h3>{subnet}</h3></div><span>{nodes.length} {nodes.length === 1 ? 'device' : 'devices'}</span></header>
            {(() => {
              const layout = buildSubnetLayout(nodes, data.edges || [])
              return <>
                <div className="topology-diagram-scroll"><svg className="topology-diagram" width={layout.width} height={layout.height} viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" aria-label={`Network topology for ${subnet}`}>
                  <g className="topology-links">{layout.edges.map((edge) => {
                    const from = layout.positions.get(edge.source)
                    const to = layout.positions.get(edge.target)
                    if (!from || !to) return null
                    return <g key={edge.id}><line x1={from.x} y1={from.y + 34} x2={to.x} y2={to.y - 34} className={`topology-link ${String(edge.status).toLowerCase() === 'down' ? 'topology-link-down' : ''}`} /><text x={(from.x + to.x) / 2 + 6} y={(from.y + to.y) / 2} className="topology-link-label">{edge.link_type === 'inferred' ? 'network link' : edge.link_type || 'link'}</text><title>{edge.link_type || 'network'} link: {edge.source_ip || edge.source} to {edge.target_ip || edge.target}</title></g>
                  })}</g>
                  {nodes.map((node) => {
                    const point = layout.positions.get(node.id)
                    if (!point) return null
                    const state = String(node.status || 'unknown').toLowerCase()
                    return <g key={node.id} className="topology-diagram-node" transform={`translate(${point.x - 78}, ${point.y - 26})`}>
                      <rect width="156" height="76" rx="11" className={`topology-node-card topology-card-${state}`} />
                      <circle cx="15" cy="17" r="4" className={`topology-node-dot topology-dot-${state}`} />
                      <text x="27" y="20" className="topology-node-status">{node.role === 'gateway' || node.is_gateway ? 'Gateway · ' : ''}{node.status || 'Unknown'}</text>
                      <text x="13" y="43" className="topology-node-name">{node.name}</text>
                      <text x="13" y="60" className="topology-node-ip">{node.ip}</text>
                      <title>{node.name} · {node.device_type} · {node.source}</title>
                    </g>
                  })}
                </svg></div>
                <div className="topology-diagram-legend"><span><i className="topology-dot-online" />Online</span><span><i className="topology-dot-offline" />Offline</span><span><i className="topology-dot-unknown" />Unknown</span><small>{layout.isInferred ? 'Links inferred from gateway and discovered devices' : 'Lines show backend-reported network links'}</small></div>
              </>
            })()}
          </section>)}
        </div> : <div className="chart-empty">No devices match this view. Run a scan in Network Discovery to populate Topology.</div>}
      </section>
    </>}
  </>
}
