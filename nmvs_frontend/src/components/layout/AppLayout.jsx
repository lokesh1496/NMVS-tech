import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import {
  Activity, Bell, Boxes, ChevronLeft, ChevronRight, CircleGauge, Compass, Gauge,
  LayoutDashboard, LogOut, Menu, Network, Settings, Shield, X,
} from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { Notice } from '../common'

const navigation = [
  { label: 'Overview', to: '/', icon: LayoutDashboard },
  { label: 'Inventory', to: '/devices', icon: Boxes },
  { label: 'Discovery', to: '/discovery', icon: Compass },
  { label: 'Monitoring', to: '/monitoring', icon: Activity },
  { label: 'Topology', to: '/topology', icon: Network },
  { label: 'Speed tests', to: '/speed', icon: Gauge },
  { label: 'Alerts', to: '/alerts', icon: Bell },
  { label: 'Reports', to: '/reports', icon: CircleGauge },
  { label: 'Metrics', to: '/metrics', icon: Shield },
  { label: 'Settings', to: '/settings', icon: Settings },
]

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const { user, signOut, sessionError } = useAuth()
  const location = useLocation()
  const current = navigation.find((item) => item.to === location.pathname)
  return (
    <div className={`app-shell ${collapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      {mobileOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark"><Network size={21} /></div>
          <div className="brand-copy"><strong>NMVS</strong><span>NETWORK OPERATIONS</span></div>
          <button className="mobile-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={18} /></button>
        </div>
        <div className="nav-section-label">WORKSPACE</div>
        <nav className="side-nav">
          {navigation.map(({ label, to, icon: Icon }) => (
            <NavLink key={to} end={to === '/'} to={to} title={collapsed ? label : undefined} onClick={() => setMobileOpen(false)}>
              <Icon size={18} /><span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="connection-state"><span className="configured-dot" /><span>API endpoint configured</span></div>
          <button className="user-card" onClick={signOut} title="Sign out">
            <span className="avatar">{(user?.username || 'U').slice(0, 1).toUpperCase()}</span>
            <span className="user-copy"><strong>{user?.username || 'Operator'}</strong><small>Sign out</small></span>
            <LogOut size={16} className="logout-icon" />
          </button>
          <button className="collapse-button" onClick={() => setCollapsed(!collapsed)} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
            {collapsed ? <ChevronRight size={17} /> : <><ChevronLeft size={17} /> Collapse navigation</>}
          </button>
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <button className="mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={21} /></button>
          <div className="breadcrumb"><span>NMVS</span><span className="crumb-separator">/</span><strong>{current?.label || 'Workspace'}</strong></div>
          <div className="topbar-right"><span className="topbar-status"><i />Monitoring console</span><span className="top-avatar">{(user?.username || 'U').slice(0, 1).toUpperCase()}</span></div>
        </header>
        <div className="page-content">{sessionError && <Notice type="error">{sessionError}</Notice>}<Outlet /></div>
      </main>
    </div>
  )
}
