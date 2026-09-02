import { useCallback, useEffect, useRef, useState } from 'react'
import { aiApi, type AIEvent } from '../api/extensions'
import { EmptyState } from '../components/ui/EmptyState'
import { shouldShowAlertToast } from '../lib/alertRules'
import { humanizeApiError } from '../lib/apiErrors'
import { useAuth } from '../context/AuthContext'
import { useFloor } from '../context/FloorContext'

export function AIAlertsPage() {
  const { user } = useAuth()
  const { floor } = useFloor()
  const [alerts, setAlerts] = useState<AIEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [showResolved, setShowResolved] = useState(false)
  const [error, setError] = useState('')
  // The most recently dismissed alert, kept briefly so it can be undone.
  const [undo, setUndo] = useState<AIEvent | null>(null)
  const undoTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const load = useCallback(async (resolved = false) => {
    setLoading(true)
    setError('')
    try {
      const data = await aiApi.getAlerts(resolved)
      setAlerts(data)
    } catch (e) {
      setError(humanizeApiError(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(showResolved) }, [load, showResolved])

  useEffect(() => {
    if (!user) return
    const onAlert = (e: Event) => {
      const alert = (e as CustomEvent<AIEvent>).detail
      if (!shouldShowAlertToast(alert.eventType, user.role)) return
      if (showResolved) return
      setAlerts((prev) => {
        if (prev.some((a) => a.id === alert.id)) return prev
        return [alert, ...prev]
      })
    }
    window.addEventListener('foh:ai-alert', onAlert)
    return () => window.removeEventListener('foh:ai-alert', onAlert)
  }, [user, showResolved])

  const handleResolve = async (id: string) => {
    const dismissed = alerts.find((a) => a.id === id) ?? null
    try {
      await aiApi.resolveAlert(id)
      setAlerts((prev) => prev.filter((a) => a.id !== id))
      window.dispatchEvent(new CustomEvent('foh:alert-dismissed'))
      // Offer an undo for a few seconds in case it was an accidental click.
      if (dismissed) {
        setUndo(dismissed)
        if (undoTimer.current) clearTimeout(undoTimer.current)
        undoTimer.current = setTimeout(() => setUndo(null), 8000)
      }
    } catch (e) {
      setError(humanizeApiError(e))
    }
  }

  const restore = useCallback((alert: AIEvent) => {
    setUndo(null)
    if (undoTimer.current) clearTimeout(undoTimer.current)
    aiApi
      .reopenAlert(alert.id)
      .then(() => {
        // Put it back on the active list (only relevant while viewing Active).
        if (!showResolved) {
          setAlerts((prev) =>
            prev.some((a) => a.id === alert.id) ? prev : [{ ...alert, resolved: false }, ...prev],
          )
        } else {
          // On the Resolved tab, it's no longer resolved — drop it from view.
          setAlerts((prev) => prev.filter((a) => a.id !== alert.id))
        }
        window.dispatchEvent(new CustomEvent('foh:alert-restored'))
      })
      .catch((e) => setError(humanizeApiError(e)))
  }, [showResolved])

  useEffect(() => () => { if (undoTimer.current) clearTimeout(undoTimer.current) }, [])

  const eventTypeColor: Record<string, { bg: string; color: string; label: string }> = {
    WAIT_ALERT: { bg: '#fff3cd', color: '#856404', label: 'Wait Alert' },
    DIRTY_ALERT: { bg: '#f8d7da', color: '#721c24', label: 'Dirty Table' },
    DEPARTURE_ALERT: { bg: '#d1ecf1', color: '#0c5460', label: 'Departure' },
    SEATING_SUGGESTION: { bg: '#d4edda', color: '#155724', label: 'Seating' },
    SHIFT_REPORT: { bg: '#e2e3e5', color: '#383d41', label: 'Report' },
  }

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div style={{ padding: '0 24px 40px' }}>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '24px 0 20px' }}>
        <div>
          <h2 style={{ margin: 0 }}>AI Alerts</h2>
          <p className="muted" style={{ margin: '4px 0 0' }}>Real-time alerts for your role</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" className={`filter-chip ${!showResolved ? 'active' : ''}`} onClick={() => setShowResolved(false)}>
            Active ({alerts.filter((a) => !a.resolved).length})
          </button>
          <button type="button" className={`filter-chip ${showResolved ? 'active' : ''}`} onClick={() => setShowResolved(true)}>
            Resolved
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '10px 16px', marginBottom: 16, color: '#c00', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>{error}</span>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => load(showResolved)}>Retry</button>
        </div>
      )}

      {alerts.length === 0 ? (
        <EmptyState
          icon="✓"
          title={showResolved ? 'No resolved alerts' : 'No active alerts. All tables are running smoothly.'}
          message={showResolved ? undefined : 'New alerts appear here in real time.'}
        />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {alerts.map((alert) => {
            const table = floor?.tables.find((t) => t.id === alert.tableId)
            const style = eventTypeColor[alert.eventType] ?? { bg: '#f5f5f5', color: '#444', label: alert.eventType }
            return (
              <div key={alert.id} style={{
                display: 'flex', gap: 14, padding: '14px 16px',
                background: '#fff', border: '1px solid #eee', borderRadius: 10,
                borderLeft: `4px solid ${style.color}`,
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    <span style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: style.bg, color: style.color }}>
                      {style.label}
                    </span>
                    {table && <span style={{ fontSize: 12, color: '#666' }}>Table {table.number}</span>}
                    <span style={{ fontSize: 11, color: '#aaa', marginLeft: 'auto' }}>
                      {new Date(alert.createdAt).toLocaleTimeString()}
                    </span>
                  </div>
                  <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, color: '#333' }}>{alert.message}</p>
                </div>
                {showResolved ? (
                  <button
                    type="button"
                    onClick={() => restore(alert)}
                    style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #bfdbfe', background: '#eff6ff', color: '#1d4ed8', fontSize: 12, fontWeight: 600, cursor: 'pointer', alignSelf: 'flex-start', whiteSpace: 'nowrap' }}
                  >
                    Reopen
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={() => handleResolve(alert.id)}
                    style={{ padding: '6px 12px', borderRadius: 6, border: '1px solid #ddd', background: '#fff', fontSize: 12, cursor: 'pointer', alignSelf: 'flex-start', whiteSpace: 'nowrap' }}
                  >
                    Dismiss
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      {undo && (
        <div
          role="status"
          style={{
            position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
            background: '#0f172a', color: '#fff', padding: '11px 16px', borderRadius: 10,
            display: 'flex', alignItems: 'center', gap: 16, boxShadow: '0 12px 32px rgba(15,23,42,0.28)', zIndex: 2000,
          }}
        >
          <span style={{ fontSize: 13.5 }}>Alert dismissed</span>
          <button
            type="button"
            onClick={() => restore(undo)}
            style={{ background: 'transparent', border: 'none', color: '#7dd3fc', fontSize: 13.5, fontWeight: 700, cursor: 'pointer', padding: 0 }}
          >
            Undo
          </button>
        </div>
      )}
    </div>
  )
}
