/**
 * API client — uses mock store until FastAPI backend is connected.
 * Set VITE_USE_MOCK=false and VITE_API_URL when backend is ready.
 */
import type {
  AuthUser,
  CameraRoiSuggestion,
  CameraSnapshotAnalysis,
  CreateTablePayload,
  CreateUserPayload,
  DiningSession,
  Floor,
  LoginResponse,
  RectBounds,
  SeatGuestPayload,
  Table,
  TableStatus,
  User,
} from '../types'
import { humanizeApiError } from '../lib/apiErrors'
import * as mock from '../mock/store'

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true'
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type ApiSection = {
  id: string
  name: string
  color: string
  bounds?: RectBounds
  points?: { x: number; y: number }[]
  description?: string
  outdoors?: boolean
  smokingAllowed?: boolean
}

type ApiFloorLabel = Floor['labels'][number]

type ApiFloorPayload = Omit<Floor, 'sections'> & {
  sections: Array<{
    id: string
    name: string
    color: string
    points: { x: number; y: number }[]
    description?: string
    outdoors?: boolean
    smokingAllowed?: boolean
  }>
  labels: ApiFloorLabel[]
}

function pointsToBounds(points: { x: number; y: number }[]): RectBounds {
  const xs = points.map((p) => p.x)
  const ys = points.map((p) => p.y)
  const minX = Math.min(...xs)
  const minY = Math.min(...ys)
  return {
    x: minX,
    y: minY,
    width: Math.max(...xs) - minX,
    height: Math.max(...ys) - minY,
  }
}

function boundsToPoints(bounds: RectBounds): { x: number; y: number }[] {
  const { x, y, width, height } = bounds
  return [
    { x, y },
    { x: x + width, y },
    { x: x + width, y: y + height },
    { x, y: y + height },
  ]
}

function normalizeFloor(floor: Floor & { sections?: ApiSection[] }): Floor {
  return {
    ...floor,
    sections: (floor.sections ?? []).map((s) => {
      const sec = s as ApiSection
      return {
        id: sec.id,
        name: sec.name,
        color: sec.color,
        bounds: sec.bounds ?? (sec.points?.length ? pointsToBounds(sec.points) : { x: 0, y: 0, width: 100, height: 100 }),
        description: sec.description,
        outdoors: sec.outdoors,
        smokingAllowed: sec.smokingAllowed,
      }
    }),
  }
}

function toApiFloorPayload(floor: Floor): ApiFloorPayload {
  return {
    ...floor,
    sections: floor.sections.map((section) => ({
      id: section.id,
      name: section.name,
      color: section.color,
      points: boundsToPoints(section.bounds),
      description: section.description,
      outdoors: section.outdoors,
      smokingAllowed: section.smokingAllowed,
    })),
    labels: floor.labels,
  }
}

function getToken(): string | null {
  return localStorage.getItem('foh_access_token')
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (res.status === 401 && path !== '/auth/login') {
    localStorage.removeItem('foh_access_token')
    localStorage.removeItem('foh_token_expires')
    sessionStorage.setItem('foh_session_expired', '1')
    window.location.href = '/login'
    throw new Error('Your session has expired. Please log in again.')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = typeof body.detail === 'string' ? body.detail : undefined
    const err = new Error(humanizeApiError(null, res.status) || detail || res.statusText)
    ;(err as Error & { status: number }).status = res.status
    throw err
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export const api = {
  login(email: string, password: string): Promise<LoginResponse> {
    if (USE_MOCK) return mock.mockLogin(email, password)
    return apiFetch('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
  },

  getMe(): Promise<AuthUser> {
    const token = getToken()
    if (!token) throw new Error('No token')
    if (USE_MOCK) return mock.mockGetMe(token)
    return apiFetch('/auth/me')
  },

  getFloor(): Promise<Floor> {
    if (USE_MOCK) return mock.mockGetFloor()
    return apiFetch<Floor & { sections?: ApiSection[] }>('/floors/current').then(normalizeFloor)
  },

  updateFloor(floor: Floor): Promise<Floor> {
    if (USE_MOCK) return mock.mockUpdateFloor(floor)
    return apiFetch<Floor & { sections?: ApiSection[] }>('/floors/current', {
      method: 'PUT',
      body: JSON.stringify(toApiFloorPayload(floor)),
    }).then(normalizeFloor)
  },

  updateTable(tableId: string, patch: Partial<Table>): Promise<Table> {
    if (USE_MOCK) return mock.mockUpdateTable(tableId, patch)
    return apiFetch(`/tables/${tableId}`, {
      method: 'PUT',
      body: JSON.stringify(patch),
    })
  },

  patchTableStatus(tableId: string, status: TableStatus): Promise<Table> {
    if (USE_MOCK) return mock.mockPatchTableStatus(tableId, status)
    return apiFetch(`/tables/${tableId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    })
  },

  addTable(payload: CreateTablePayload): Promise<Table> {
    if (USE_MOCK) return mock.mockAddTable(payload)
    return apiFetch('/tables', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  deleteTable(tableId: string): Promise<void> {
    if (USE_MOCK) return mock.mockDeleteTable(tableId)
    return apiFetch(`/tables/${tableId}`, { method: 'DELETE' })
  },

  resetFloorLayout(): Promise<Floor> {
    if (USE_MOCK) return mock.mockResetFloorLayout()
    return apiFetch('/floors/current/reset', { method: 'POST' })
  },

  createSession(payload: SeatGuestPayload): Promise<DiningSession> {
    if (USE_MOCK) return mock.mockCreateSession(payload)
    return apiFetch('/sessions/seat', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  closeSession(sessionId: string): Promise<DiningSession> {
    if (USE_MOCK) return mock.mockCloseSession(sessionId)
    return apiFetch(`/sessions/${sessionId}/close`, { method: 'POST' })
  },

  getSessions(): Promise<DiningSession[]> {
    if (USE_MOCK) return mock.mockGetSessions()
    return apiFetch('/sessions')
  },

  getUsers(): Promise<User[]> {
    if (USE_MOCK) return mock.mockGetUsers()
    return apiFetch('/users')
  },

  createUser(payload: CreateUserPayload): Promise<User> {
    if (USE_MOCK) return mock.mockCreateUser(payload)
    return apiFetch('/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  setUserActive(userId: string, isActive: boolean): Promise<User> {
    if (USE_MOCK) return mock.mockSetUserActive(userId, isActive)
    return apiFetch(`/users/${userId}/active`, {
      method: 'PATCH',
      body: JSON.stringify({ isActive }),
    })
  },

  // Returns a browser-local object URL pointing at one JPEG frame from the
  // table's camera. Caller is responsible for revoking it (URL.revokeObjectURL)
  // when done, to avoid leaking memory.
  async getCameraSnapshot(tableId: string): Promise<string> {
    if (USE_MOCK) return mock.mockGetCameraSnapshot(tableId)
    const token = getToken()
    const res = await fetch(`${API_URL}/tables/${tableId}/camera/snapshot`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || 'Could not load camera snapshot')
    }
    const blob = await res.blob()
    return URL.createObjectURL(blob)
  },

  async uploadCameraVideo(tableId: string, file: File): Promise<{ cameraUrl: string; filename: string }> {
    if (USE_MOCK) {
      return { cameraUrl: `/mock/uploads/${file.name}`, filename: file.name }
    }
    const token = getToken()
    const formData = new FormData()
    formData.append('file', file)
    const res = await fetch(`${API_URL}/tables/${tableId}/camera/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) {
      const body = await res.json().catch(() => ({}))
      throw new Error(body.detail || 'Could not upload video')
    }
    return res.json()
  },

  async autoDetectCameraRoi(tableId: string): Promise<CameraRoiSuggestion> {
    if (USE_MOCK) return mock.mockAutoDetectCameraRoi(tableId)
    return apiFetch<CameraRoiSuggestion>(`/tables/${tableId}/camera/auto-roi`, {
      method: 'POST',
    })
  },

  async analyzeCameraSnapshot(tableId: string, roiCoords?: RectBounds | null): Promise<CameraSnapshotAnalysis> {
    if (USE_MOCK) return mock.mockAnalyzeCameraSnapshot(tableId, roiCoords)
    return apiFetch<CameraSnapshotAnalysis>(`/tables/${tableId}/camera/analyze-snapshot`, {
      method: 'POST',
      body: JSON.stringify({ roiCoords: roiCoords ?? null }),
    })
  },
}
