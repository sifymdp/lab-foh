import { useEffect, useState } from 'react'
import { billingApi, ordersApi, type Bill, type Order } from '../../api/extensions'
import { useAuth } from '../../context/AuthContext'
import { useFloor } from '../../context/FloorContext'
import { ConfirmDialog } from '../ui/ConfirmDialog'
import { canEditFloor, canSeatGuests } from '../../lib/permissions'
import { STATUS_CONFIG } from '../../services/tableConfig'
import type { Floor, Table, TableType } from '../../types'
import { OccupancyTimer } from './OccupancyTimer'
import { PrintQRButton } from './PrintQRButton'
import { StatusActions } from './StatusActions'

interface TableDetailPanelProps {
  floor: Floor
  table: Table
  onClose: () => void
  onSeatGuests: () => void
}

function aggregateItems(orders: Order[]) {
  const map = new Map<string, { name: string; price: number; qty: number }>()
  for (const order of orders) {
    for (const item of order.items) {
      const key = `${item.itemName}-${item.unitPrice}`
      const existing = map.get(key)
      if (existing) existing.qty += item.quantity
      else map.set(key, { name: item.itemName, price: item.unitPrice, qty: item.quantity })
    }
  }
  return [...map.values()]
}

export function TableDetailPanel({ floor, table, onClose, onSeatGuests }: TableDetailPanelProps) {
  const { user } = useAuth()
  const { sessions, changeStatus, closeSession, updateTable, deleteTable } = useFloor()
  const [statusLoading, setStatusLoading] = useState(false)
  const [statusError, setStatusError] = useState<string | null>(null)
  const [layoutError, setLayoutError] = useState<string | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [bill, setBill] = useState<Bill | null>(null)
  const [showBill, setShowBill] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [confirmPaid, setConfirmPaid] = useState(false)
  const [billingLoading, setBillingLoading] = useState(false)

  const session = sessions.find(
    (s) => s.tableId === table.id && ['SEATED', 'ACTIVE', 'BILLING', 'PAID'].includes(s.status),
  )
  const section = floor.sections.find((s) => s.id === table.sectionId)
  const editable = user ? canEditFloor(user.role) : false
  const canSeat = user ? canSeatGuests(user.role) : false
  const showOrders = ['ACTIVE', 'BILLING', 'PAID'].includes(table.status)

  useEffect(() => {
    if (!showOrders) return
    let cancelled = false
    setOrdersLoading(true)
    ordersApi.list({ tableId: table.id })
      .then((data) => { if (!cancelled) setOrders(data) })
      .catch(() => { if (!cancelled) setOrders([]) })
      .finally(() => { if (!cancelled) setOrdersLoading(false) })
    return () => { cancelled = true }
  }, [table.id, showOrders])

  const items = aggregateItems(orders)
  const runningTotal = items.reduce((sum, i) => sum + i.price * i.qty, 0)

  async function handleStatus(next: typeof table.status) {
    setStatusLoading(true)
    setStatusError(null)
    try {
      await changeStatus(table.id, next)
    } catch (e) {
      setStatusError(e instanceof Error ? e.message : 'Status update failed')
    } finally {
      setStatusLoading(false)
    }
  }

  const handleViewBill = async () => {
    if (!session) return
    setBillingLoading(true)
    try {
      const b = await billingApi.getBill(session.id)
      setBill(b)
      setShowBill(true)
    } catch {
      const b = await billingApi.requestBill(session.id)
      setBill(b)
      setShowBill(true)
    } finally {
      setBillingLoading(false)
    }
  }

  const handleMarkPaid = async () => {
    if (!session) return
    setBillingLoading(true)
    try {
      await billingApi.markPaid(session.id)
      setConfirmPaid(false)
      setShowBill(false)
    } finally {
      setBillingLoading(false)
    }
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setShowBill(false)
        setConfirmDelete(false)
        setConfirmPaid(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <aside className="table-panel">
      <div className="panel-header">
        <div>
          <p className="panel-eyebrow">{section?.name ?? 'Floor'}</p>
          <h2>Table {table.number}</h2>
        </div>
        <button type="button" className="btn-icon" onClick={onClose} aria-label="Close">×</button>
      </div>

      <div
        className="status-banner"
        style={{
          backgroundColor: STATUS_CONFIG[table.status].bg,
          borderColor: STATUS_CONFIG[table.status].border,
          color: STATUS_CONFIG[table.status].text,
        }}
      >
        {STATUS_CONFIG[table.status].label}
        {session && (
          <span className="status-banner__timer">
            <OccupancyTimer seatedAt={session.seatedAt} />
          </span>
        )}
      </div>

      <dl className="detail-list">
        <div>
          <dt>Capacity</dt>
          <dd>
            {editable ? (
              <input type="number" min={1} max={20} className="input input-sm" value={table.capacity}
                onChange={(e) => updateTable(table.id, { capacity: Number(e.target.value) })} />
            ) : `${table.capacity} guests`}
          </dd>
        </div>
        {editable && (
          <>
            <div>
              <dt>Type</dt>
              <dd>
                <select className="input" value={table.type}
                  onChange={(e) => updateTable(table.id, { type: e.target.value as TableType })}>
                  <option value="STANDARD">Standard</option>
                  <option value="BOOTH">Booth</option>
                  <option value="BAR">Bar</option>
                  <option value="VIP">VIP</option>
                </select>
              </dd>
            </div>
            <div>
              <dt>Rotation</dt>
              <dd>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <button
                    type="button" className="btn btn-secondary btn-sm" title="Rotate 15° left"
                    onClick={() => updateTable(table.id, { rotation: (((table.rotation - 15) % 360) + 360) % 360 })}
                  >⟲</button>
                  <span style={{ minWidth: 46, textAlign: 'center', fontVariantNumeric: 'tabular-nums', fontSize: 13 }}>
                    {Math.round(table.rotation)}°
                  </span>
                  <button
                    type="button" className="btn btn-secondary btn-sm" title="Rotate 15° right"
                    onClick={() => updateTable(table.id, { rotation: (((table.rotation + 15) % 360) + 360) % 360 })}
                  >⟳</button>
                  {table.rotation !== 0 && (
                    <button
                      type="button" className="btn btn-ghost btn-sm"
                      onClick={() => updateTable(table.id, { rotation: 0 })}
                    >Reset</button>
                  )}
                </div>
              </dd>
            </div>
          </>
        )}
        {session && (
          <>
            {session.guestName && <div><dt>Guest</dt><dd>{session.guestName}</dd></div>}
            <div><dt>Party size</dt><dd>{session.partySize} guests</dd></div>
          </>
        )}
      </dl>

      {showOrders && (
        <div className="panel-section">
          <h3>Order summary</h3>
          {ordersLoading ? (
            <p className="muted" style={{ fontSize: 13 }}>Loading orders…</p>
          ) : items.length === 0 ? (
            <p className="muted" style={{ fontSize: 13 }}>No orders placed yet.</p>
          ) : (
            <ul style={{ margin: 0, padding: 0, listStyle: 'none', fontSize: 13 }}>
              {items.map((i) => (
                <li key={i.name} style={{ padding: '4px 0', color: '#475569' }}>
                  {i.qty}× {i.name} — £{(i.price * i.qty).toFixed(2)}
                </li>
              ))}
              <li style={{ fontWeight: 700, marginTop: 6, color: '#0f172a' }}>
                Running total: £{runningTotal.toFixed(2)}
              </li>
            </ul>
          )}
        </div>
      )}

      {statusError && <p className="form-error">{statusError}</p>}

      <div className="panel-section">
        <h3>Update status</h3>
        <StatusActions current={table.status} onSelect={handleStatus} loading={statusLoading} />
      </div>

      {editable && (
        <div className="panel-section">
          <a href="/camera-setup" className="btn btn-secondary btn-block" style={{ textAlign: 'center', textDecoration: 'none' }}>
            Configure camera / ROI
          </a>
          <button
            type="button"
            className="btn btn-ghost btn-block layout-delete-btn"
            style={{ marginTop: 8 }}
            onClick={() => setConfirmDelete(true)}
          >
            Remove table from layout
          </button>
          {layoutError && <p className="form-error">{layoutError}</p>}
        </div>
      )}

      <div className="panel-actions">
        {['AVAILABLE', 'SEATED'].includes(table.status) && (
          <PrintQRButton tableId={table.id} tableNumber={table.number} />
        )}
        {table.status === 'BILLING' && session && (
          <button type="button" className="btn btn-secondary btn-block" onClick={handleViewBill} disabled={billingLoading}>
            View Bill
          </button>
        )}
        {canSeat && ['AVAILABLE', 'RESERVED'].includes(table.status) && (
          <button type="button" className="btn btn-primary btn-block" onClick={onSeatGuests}>
            Seat guests here
          </button>
        )}
        {session && (
          <button type="button" className="btn btn-secondary btn-block" onClick={() => closeSession(session.id)}>
            Release table
          </button>
        )}
      </div>

      {showBill && bill && (
        <div role="presentation" onClick={() => setShowBill(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.45)', zIndex: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}
            style={{ background: '#fff', borderRadius: 12, padding: 24, maxWidth: 420, width: '90%' }}>
            <h3 style={{ margin: '0 0 12px' }}>Bill — Table {table.number}</h3>
            <ul style={{ margin: '0 0 12px', padding: 0, listStyle: 'none', fontSize: 14 }}>
              {bill.items.map((i) => (
                <li key={`${i.itemName}-${i.quantity}`} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0' }}>
                  <span>{i.quantity}× {i.itemName}</span>
                  <span>£{i.lineTotal.toFixed(2)}</span>
                </li>
              ))}
            </ul>
            <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: 8, fontSize: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Subtotal</span><span>£{bill.subtotal.toFixed(2)}</span></div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, marginTop: 4 }}><span>Total</span><span>£{bill.total.toFixed(2)}</span></div>
            </div>
            <div style={{ display: 'flex', gap: 8, marginTop: 16, justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn-ghost" onClick={() => setShowBill(false)}>Close</button>
              {bill.status !== 'PAID' && (
                <button type="button" className="btn btn-primary" onClick={() => setConfirmPaid(true)} disabled={billingLoading}>
                  Mark Paid
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <ConfirmDialog
        open={confirmDelete}
        message={`Remove table ${table.number} from the floor plan?`}
        confirmLabel="Remove"
        onConfirm={async () => {
          setLayoutError(null)
          try {
            await deleteTable(table.id)
            setConfirmDelete(false)
            onClose()
          } catch (e) {
            setLayoutError(e instanceof Error ? e.message : 'Could not remove table')
            setConfirmDelete(false)
          }
        }}
        onCancel={() => setConfirmDelete(false)}
      />
      <ConfirmDialog
        open={confirmPaid}
        message={`Mark Table ${table.number} as paid?`}
        confirmLabel="Mark paid"
        onConfirm={handleMarkPaid}
        onCancel={() => setConfirmPaid(false)}
      />
    </aside>
  )
}
