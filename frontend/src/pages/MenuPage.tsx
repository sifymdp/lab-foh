import { useCallback, useEffect, useState } from 'react'
import { menuApi, type MenuItem } from '../api/extensions'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { EmptyState } from '../components/ui/EmptyState'
import { humanizeApiError } from '../lib/apiErrors'

const CATEGORIES = ['Starters', 'Mains', 'Drinks', 'Desserts']

interface FormState {
  name: string; description: string; price: string
  category: string; available: boolean; displayOrder: string
}

const EMPTY_FORM: FormState = {
  name: '', description: '', price: '', category: 'Mains', available: true, displayOrder: '0'
}

export function MenuPage() {
  const [items, setItems] = useState<MenuItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [filterCat, setFilterCat] = useState<string>('All')
  const [toast, setToast] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await menuApi.list()
      setItems(data)
    } catch (e) {
      setError(humanizeApiError(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  const openAdd = () => {
    setEditingId(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (item: MenuItem) => {
    setEditingId(item.id)
    setForm({
      name: item.name,
      description: item.description ?? '',
      price: String(item.price),
      category: item.category,
      available: item.available,
      displayOrder: String(item.displayOrder),
    })
    setShowForm(true)
  }

  const handleSave = async () => {
    if (!form.name.trim() || !form.price) return
    setSaving(true)
    setError('')
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description.trim() || undefined,
        price: parseFloat(form.price),
        category: form.category,
        available: form.available,
        displayOrder: parseInt(form.displayOrder) || 0,
      }
      if (editingId) {
        await menuApi.update(editingId, payload)
        setToast('Menu item updated')
      } else {
        await menuApi.create(payload)
        setToast('Menu item added')
      }
      setShowForm(false)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await menuApi.remove(id)
      setItems((prev) => prev.filter((i) => i.id !== id))
      setDeleteTarget(null)
    } catch (e) {
      setError(humanizeApiError(e))
    }
  }

  const handleToggle = async (item: MenuItem) => {
    try {
      const updated = await menuApi.toggle(item.id, !item.available)
      setItems((prev) => prev.map((i) => (i.id === item.id ? updated : i)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Toggle failed')
    }
  }

  const filtered = filterCat === 'All' ? items : items.filter((i) => i.category === filterCat)

  const grouped = CATEGORIES.reduce<Record<string, MenuItem[]>>((acc, cat) => {
    const catItems = filtered.filter((i) => i.category === cat)
    if (catItems.length) acc[cat] = catItems
    return acc
  }, {})

  if (loading) return <div className="page-loading"><div className="spinner" /></div>

  return (
    <div className="menu-page" style={{ padding: '0 24px 40px' }}>
      {toast && (
        <div style={{
          position: 'fixed', top: 16, right: 16, zIndex: 1000,
          padding: '12px 16px', background: '#1e6b3c', color: '#fff',
          borderRadius: 8, boxShadow: '0 4px 12px rgba(0,0,0,0.2)', fontSize: 14,
        }}>
          {toast}
        </div>
      )}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '24px 0 20px' }}>
        <div>
          <h2 style={{ margin: 0 }}>Menu</h2>
          <p className="muted" style={{ margin: '4px 0 0' }}>Manage items — changes appear on guest QR pages instantly</p>
        </div>
        <button className="btn btn-primary" onClick={openAdd}>+ Add item</button>
      </div>

      {error && (
        <div style={{ background: '#fee', border: '1px solid #fcc', borderRadius: 8, padding: '10px 16px', marginBottom: 16, color: '#c00' }}>
          {error} <button style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer' }} onClick={() => setError('')}>✕</button>
        </div>
      )}

      {/* Category filter */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 20, flexWrap: 'wrap' }}>
        {['All', ...CATEGORIES].map((cat) => (
          <button
            key={cat}
            type="button"
            className={`filter-chip ${filterCat === cat ? 'active' : ''}`}
            onClick={() => setFilterCat(cat)}
          >
            {cat} {cat !== 'All' && `(${items.filter((i) => i.category === cat).length})`}
          </button>
        ))}
      </div>

      {/* Menu items grouped by category */}
      {Object.entries(grouped).map(([cat, catItems]) => (
        <div key={cat} style={{ marginBottom: 32 }}>
          <h3 style={{ fontSize: 13, fontWeight: 600, color: '#888', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 12 }}>{cat}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {catItems.sort((a, b) => a.displayOrder - b.displayOrder).map((item) => (
              <div key={item.id} style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                background: item.available ? '#fff' : '#fafafa',
                border: '1px solid #eee', borderRadius: 8,
                opacity: item.available ? 1 : 0.6,
              }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 500, fontSize: 14 }}>{item.name}</span>
                    {!item.available && (
                      <span style={{ fontSize: 11, background: '#fee', color: '#c00', padding: '2px 6px', borderRadius: 4 }}>86'd</span>
                    )}
                  </div>
                  {item.description && (
                    <p style={{ margin: '2px 0 0', fontSize: 12, color: '#888' }}>{item.description}</p>
                  )}
                </div>
                <span style={{ fontWeight: 600, color: '#1a1a1a', minWidth: 60, textAlign: 'right' }}>
                  ₹{Number(item.price).toFixed(2)}
                </span>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    type="button"
                    onClick={() => handleToggle(item)}
                    style={{
                      padding: '4px 10px', borderRadius: 6, border: '1px solid #ddd',
                      background: item.available ? '#e6f4ea' : '#fff',
                      color: item.available ? '#1e6b3c' : '#666',
                      fontSize: 12, cursor: 'pointer', fontWeight: 500,
                    }}
                  >
                    {item.available ? 'Available' : 'Off'}
                  </button>
                  <button type="button" onClick={() => openEdit(item)} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #ddd', background: '#fff', fontSize: 12, cursor: 'pointer' }}>Edit</button>
                  <button type="button" onClick={() => setDeleteTarget(item.id)} style={{ padding: '4px 10px', borderRadius: 6, border: '1px solid #fcc', background: '#fff', color: '#c00', fontSize: 12, cursor: 'pointer' }}>Remove</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {filtered.length === 0 && !loading && (
        <EmptyState icon="🍽" title="No menu items yet." message='Click "Add item" to create your first menu item.' />
      )}

      <ConfirmDialog
        open={!!deleteTarget}
        message="Remove this item from the menu?"
        confirmLabel="Remove"
        onConfirm={() => deleteTarget && handleDelete(deleteTarget)}
        onCancel={() => setDeleteTarget(null)}
      />

      {showForm && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ background: '#fff', borderRadius: 12, padding: 24, width: '100%', maxWidth: 460, boxShadow: '0 20px 60px rgba(0,0,0,0.2)' }}>
            <h3 style={{ margin: '0 0 20px', fontSize: 18 }}>{editingId ? 'Edit item' : 'Add menu item'}</h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Name *</label>
                <input className="input" value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="e.g. Grilled Salmon" style={{ width: '100%' }} />
              </div>
              <div>
                <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Description</label>
                <input className="input" value={form.description} onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))} placeholder="Optional description" style={{ width: '100%' }} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Price (₹) *</label>
                  <input className="input" type="number" step="0.01" min="0" value={form.price} onChange={(e) => setForm((f) => ({ ...f, price: e.target.value }))} placeholder="0.00" style={{ width: '100%' }} />
                </div>
                <div>
                  <label style={{ fontSize: 13, fontWeight: 500, display: 'block', marginBottom: 4 }}>Category</label>
                  <select className="input" value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} style={{ width: '100%' }}>
                    {CATEGORIES.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <input type="checkbox" id="avail" checked={form.available} onChange={(e) => setForm((f) => ({ ...f, available: e.target.checked }))} />
                <label htmlFor="avail" style={{ fontSize: 13 }}>Available on menu</label>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
              <button className="btn btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave} disabled={saving || !form.name || !form.price}>
                {saving ? 'Saving…' : editingId ? 'Save changes' : 'Add item'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
