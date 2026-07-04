/**
 * Extended API client — new endpoints for menu, orders, reservations, AI, QR
 * Drop this into src/api/extensions.ts and import in your existing client.ts
 */

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function humanizeStatus(status: number, detail?: string): string {
  if (status === 401) return 'Your session has expired. Please log in again.'
  if (status === 403) return 'You do not have permission to do this.'
  if (status === 404) return 'The requested item was not found.'
  if (status === 500) return 'Something went wrong. Please try again.'
  return detail ?? 'Something went wrong. Please try again.'
}

function getToken(): string | null {
  return localStorage.getItem('foh_access_token')
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401) {
    localStorage.removeItem('foh_access_token')
    localStorage.removeItem('foh_token_expires')
    sessionStorage.setItem('foh_session_expired', '1')
    window.location.href = '/login'
    throw new Error('Your session has expired. Please log in again.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : undefined
    throw new Error(humanizeStatus(res.status, detail))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ─── Menu ────────────────────────────────────────────────────────────────────

export interface MenuItem {
  id: string
  name: string
  description?: string
  price: number
  category: string
  available: boolean
  displayOrder: number
}

export const menuApi = {
  list: () => apiFetch<MenuItem[]>('/menu/all'),
  listPublic: () => apiFetch<MenuItem[]>('/menu'),
  create: (data: Omit<MenuItem, 'id'>) =>
    apiFetch<MenuItem>('/menu/items', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<MenuItem>) =>
    apiFetch<MenuItem>(`/menu/items/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  remove: (id: string) =>
    apiFetch<void>(`/menu/items/${id}`, { method: 'DELETE' }),
  toggle: (id: string, _available: boolean) =>
    apiFetch<MenuItem>(`/menu/items/${id}/toggle`, { method: 'PATCH' }),
}

// ─── Orders ──────────────────────────────────────────────────────────────────

export interface OrderItem { id: string; itemName: string; unitPrice: number; quantity: number }
export interface Order {
  id: string; sessionId: string; tableId: string
  placedAt: string; status: string; items: OrderItem[]
}

export const ordersApi = {
  list: (params?: { tableId?: string; sessionId?: string }) => {
    const q = new URLSearchParams()
    if (params?.tableId) q.set('table_id', params.tableId)
    if (params?.sessionId) q.set('session_id', params.sessionId)
    return apiFetch<Order[]>(`/orders?${q}`)
  },
  place: (tableId: string, items: { menuItemId: string; quantity: number }[], sessionId?: string) =>
    apiFetch<Order>('/orders', {
      method: 'POST',
      body: JSON.stringify({ tableId, items, sessionId }),
    }),
}

// ─── Billing ─────────────────────────────────────────────────────────────────

export interface BillItem { itemName: string; unitPrice: number; quantity: number; lineTotal: number }
export interface Bill {
  id: string; sessionId: string; subtotal: number; total: number
  status: string; generatedAt: string; paidAt?: string; items: BillItem[]
}

export const billingApi = {
  requestBill: (sessionId: string) =>
    apiFetch<Bill>(`/sessions/${sessionId}/request-bill`, { method: 'POST' }),
  getBill: (sessionId: string) =>
    apiFetch<Bill>(`/sessions/${sessionId}/bill`),
  markPaid: (sessionId: string) =>
    apiFetch<Bill>(`/sessions/${sessionId}/mark-paid`, { method: 'POST' }),
}

// ─── Reservations ─────────────────────────────────────────────────────────────

export interface Reservation {
  id: string; tableId: string; guestName: string
  partySize: number; reservedFor: string; reservedUntil: string
  status: string; notes?: string
}

export const reservationsApi = {
  list: () => apiFetch<Reservation[]>('/reservations'),
  create: (data: {
    tableId: string; guestName: string; partySize: number
    reservedFor: string; reservedUntil: string; notes?: string
  }) => apiFetch<Reservation>('/reservations', { method: 'POST', body: JSON.stringify(data) }),
  release: (id: string) =>
    apiFetch<Reservation>(`/reservations/${id}/release`, { method: 'POST' }),
}

// ─── AI ───────────────────────────────────────────────────────────────────────

export interface AIEvent {
  id: string; tableId?: string; eventType: string
  message: string; targetRole?: string; createdAt: string; resolved: boolean
}
export interface SeatingResponse { suggestion: string; partySize: number }
export interface ShiftReport { reportDate: string; content: string; stats: Record<string, unknown> }

export const aiApi = {
  suggestSeating: (partySize: number) =>
    apiFetch<SeatingResponse>('/ai/seating-suggest', {
      method: 'POST', body: JSON.stringify({ partySize }),
    }),
  getAlerts: (resolved = false) =>
    apiFetch<AIEvent[]>(`/ai/events?resolved=${resolved}`),
  resolveAlert: (id: string) =>
    apiFetch<{ id: string; resolved: boolean }>(`/ai/events/${id}/resolve`, { method: 'PATCH' }),
  getShiftReport: (date?: string) =>
    apiFetch<ShiftReport>(`/ai/reports/shift${date ? `?date=${date}` : ''}`),
}

// ─── QR ───────────────────────────────────────────────────────────────────────

export const qrApi = {
  printUrl: (tableId: string) => `${API_URL}/tables/${tableId}/qr`,
  rotate: (tableId: string) =>
    apiFetch<{ token: string; message: string }>(`/tables/${tableId}/qr/rotate`, { method: 'POST' }),
}
