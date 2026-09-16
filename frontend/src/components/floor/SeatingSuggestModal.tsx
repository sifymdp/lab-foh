import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { aiApi } from '../../api/extensions'
import { STATUS_CONFIG } from '../../services/tableConfig'
import type { Table } from '../../types'

interface Props {
  onClose: () => void
  /** Called when a host picks one of the found tables — selects it on the floor. */
  onPick?: (tableId: string) => void
}

export function SeatingSuggestModal({ onClose, onPick }: Props) {
  const [partySize, setPartySize] = useState(2)
  const [tables, setTables] = useState<Table[] | null>(null)
  const [suggestion, setSuggestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const handleFind = async () => {
    setLoading(true)
    setError('')
    setSuggestion('')
    setTables(null)
    try {
      // The finder (actual best-fit tables) is the source of truth; the AI note
      // is a bonus and must never block showing the tables.
      const found = await api.findAvailableTables(partySize)
      setTables(found)
      aiApi.suggestSeating(partySize)
        .then((res) => setSuggestion(res.suggestion))
        .catch(() => { /* AI note is optional */ })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not find tables')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      role="presentation"
      onClick={onClose}
      style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}
    >
      <div
        role="dialog"
        aria-modal="true"
        onClick={(e) => e.stopPropagation()}
        style={{ background: '#fff', borderRadius: 12, padding: 24, width: '100%', maxWidth: 480, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}
      >
        <h3 style={{ margin: '0 0 4px', fontSize: 18 }}>Find a table</h3>
        <p className="muted" style={{ margin: '0 0 16px', fontSize: 13 }}>Available tables that fit the party, best fit first.</p>
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
          <div style={{ flex: 1 }}>
            <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Party size</label>
            <input
              className="input"
              type="number"
              min={1}
              max={20}
              value={partySize}
              onChange={(e) => setPartySize(parseInt(e.target.value) || 1)}
              style={{ width: '100%' }}
            />
          </div>
          <button type="button" className="btn btn-primary" onClick={handleFind} disabled={loading}>
            {loading ? 'Finding…' : 'Find tables'}
          </button>
        </div>

        {error && <p className="form-error">{error}</p>}

        {tables && (
          tables.length === 0 ? (
            <p style={{ fontSize: 14, color: '#b91c1c', margin: '0 0 16px' }}>
              No available table seats {partySize}. Try combining tables or waitlisting the party.
            </p>
          ) : (
            <ul style={{ listStyle: 'none', margin: '0 0 16px', padding: 0, display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 280, overflowY: 'auto' }}>
              {tables.map((t, i) => {
                const cfg = STATUS_CONFIG[t.status]
                return (
                  <li key={t.id}>
                    <button
                      type="button"
                      onClick={() => { onPick?.(t.id); onClose() }}
                      style={{
                        width: '100%', display: 'flex', alignItems: 'center', gap: 12, textAlign: 'left',
                        padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
                        border: `1px solid ${i === 0 ? '#86efac' : '#e2e8f0'}`,
                        background: i === 0 ? '#f0fdf4' : '#fff',
                      }}
                    >
                      <span style={{ width: 10, height: 10, borderRadius: '50%', background: cfg.border }} />
                      <span style={{ fontWeight: 700, fontSize: 15 }}>Table {t.number}</span>
                      <span style={{ fontSize: 13, color: '#64748b' }}>
                        seats {t.capacity} · {t.type.toLowerCase()}
                      </span>
                      {i === 0 && (
                        <span style={{ marginLeft: 'auto', fontSize: 11, fontWeight: 700, color: '#166534', background: '#dcfce7', padding: '2px 8px', borderRadius: 999 }}>
                          Best fit
                        </span>
                      )}
                    </button>
                  </li>
                )
              })}
            </ul>
          )
        )}

        {suggestion && (
          <p style={{ margin: '0 0 16px', fontSize: 13, lineHeight: 1.6, color: '#64748b', whiteSpace: 'pre-wrap', borderLeft: '3px solid #e2e8f0', paddingLeft: 12 }}>
            {suggestion}
          </p>
        )}

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
