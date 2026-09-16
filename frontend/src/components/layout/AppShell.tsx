import { useCallback, useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { aiApi, type AIEvent } from '../../api/extensions'
import { AIChatWidget } from '../ui/AIChatWidget'
import { ToastStack } from '../ui/ToastStack'
import { useAuth } from '../../context/AuthContext'
import { useSocket } from '../../context/SocketContext'
import { shouldCountAlertBadge, shouldShowAlertToast } from '../../lib/alertRules'
import { canEditFloor, canManageUsers } from '../../lib/permissions'
import type { Role } from '../../types'

function canManageMenu(role: Role) { return role === 'OWNER' || role === 'MANAGER' }
function canViewReports(role: Role) { return role === 'OWNER' || role === 'MANAGER' }

const NAV: Array<{
  to: string
  label: string
  icon: string
  ownerOnly?: boolean
  menuOnly?: boolean
  reportsOnly?: boolean
  floorEditorOnly?: boolean
}> = [
  { to: '/floor',        label: 'Floor plan',    icon: '◫' },
  { to: '/sessions',     label: 'Sessions',      icon: '☰' },
  { to: '/reservations', label: 'Reservations',  icon: '📅' },
  { to: '/menu',         label: 'Menu',          icon: '🍽',  menuOnly: true },
  { to: '/camera-setup', label: 'Camera Setup',  icon: '📷',  floorEditorOnly: true },
  { to: '/alerts',       label: 'AI Alerts',     icon: '🔔' },
  { to: '/reports',      label: 'Reports',       icon: '📊',  reportsOnly: true },
  { to: '/users',        label: 'Team',          icon: '◎',  ownerOnly: true },
]

function AlertBadge({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <span
      style={{
        position: 'absolute',
        top: -4,
        right: -8,
        minWidth: 18,
        height: 18,
        padding: '0 5px',
        borderRadius: 9,
        background: '#dc2626',
        color: '#fff',
        fontSize: 11,
        fontWeight: 700,
        lineHeight: '18px',
        textAlign: 'center',
      }}
    >
      {count > 99 ? '99+' : count}
    </span>
  )
}

interface ToastItem { id: string; message: string; variant?: 'default' | 'error' }

export function AppShell() {
  const { user, logout } = useAuth()
  const { connected, on } = useSocket()
  const [alertCount, setAlertCount] = useState(0)
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const pushToast = useCallback((message: string, ms = 5000, variant: 'default' | 'error' = 'default') => {
    const id = crypto.randomUUID()
    setToasts((prev) => [...prev, { id, message, variant }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), ms)
  }, [])

  const refreshAlertCount = useCallback(async () => {
    if (!user) return
    try {
      const alerts = await aiApi.getAlerts(false)
      setAlertCount(alerts.length)
    } catch {
      /* keep last count */
    }
  }, [user])

  useEffect(() => { refreshAlertCount() }, [refreshAlertCount])

  useEffect(() => {
    if (!user) return
    const unsubAlert = on('ai_alert', (payload) => {
      const alert = payload as AIEvent
      if (!shouldShowAlertToast(alert.eventType, user.role)) return
      if (shouldCountAlertBadge(alert.eventType, user.role)) {
        setAlertCount((c) => c + 1)
      }
      pushToast(alert.message, 5000)
      window.dispatchEvent(new CustomEvent('foh:ai-alert', { detail: alert }))
    })
    const unsubOrder = on('order_placed', (payload) => {
      const data = payload as { tableNumber?: string; itemCount?: number }
      if (user.role !== 'WAITER' && user.role !== 'HOST') return
      const num = data.tableNumber ?? '?'
      const count = data.itemCount ?? 0
      pushToast(`New order at Table ${num} — ${count} items`, 6000)
    })
    return () => { unsubAlert(); unsubOrder() }
  }, [on, user, pushToast])

  useEffect(() => {
    const onDismissed = () => setAlertCount((c) => Math.max(0, c - 1))
    const onRestored = () => setAlertCount((c) => c + 1)
    window.addEventListener('foh:alert-dismissed', onDismissed)
    window.addEventListener('foh:alert-restored', onRestored)
    return () => {
      window.removeEventListener('foh:alert-dismissed', onDismissed)
      window.removeEventListener('foh:alert-restored', onRestored)
    }
  }, [])

  const showNavItem = (item: typeof NAV[number]) => {
    if (!user) return false
    if (item.ownerOnly && !canManageUsers(user.role)) return false
    if (item.menuOnly && !canManageMenu(user.role)) return false
    if (item.reportsOnly && !canViewReports(user.role)) return false
    if (item.floorEditorOnly && !canEditFloor(user.role)) return false
    return true
  }

  return (
    <div className="app-shell">
      <ToastStack toasts={toasts} />
      <aside className="app-sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">FOH</span>
          <div>
            <strong>Host Stand</strong>
            <span className="brand-sub">Table management</span>
          </div>
        </div>

        <nav className="app-nav" aria-label="Main">
          {NAV.filter(showNavItem).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span
                className="nav-item__icon"
                aria-hidden
                style={item.to === '/alerts' ? { position: 'relative' } : undefined}
              >
                {item.icon}
                {item.to === '/alerts' && <AlertBadge count={alertCount} />}
              </span>
              {item.label}
            </NavLink>
          ))}
        </nav>

        {user && canEditFloor(user.role) && (
          <p className="sidebar-hint">Layout edit enabled</p>
        )}

        <div className="sidebar-footer">
          <span className={`socket-indicator ${connected ? 'socket-indicator--live' : ''}`}>
            <span className="socket-indicator__dot" />
            {connected ? 'Live sync' : 'Offline'}
          </span>
        </div>
      </aside>

      <div className="app-content">
        <nav className="mobile-nav" aria-label="Mobile">
          {NAV.filter(showNavItem).map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'active' : '')}
            >
              {item.label}
              {item.to === '/alerts' && alertCount > 0 ? ` (${alertCount})` : ''}
            </NavLink>
          ))}
        </nav>
        <header className="app-topbar">
          <div className="topbar-title">
            <h1>Main Dining</h1>
            <p className="muted">Tonight&apos;s service</p>
          </div>
          <div className="topbar-user">
            <span className={`role-badge role-${user?.role.toLowerCase()}`}>{user?.role}</span>
            <span className="user-name">{user?.name}</span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={logout}>Sign out</button>
          </div>
        </header>
        <main className="app-main">
          <Outlet />
        </main>
      </div>
      {user && (user.role === 'OWNER' || user.role === 'MANAGER') && <AIChatWidget />}
    </div>
  )
}
