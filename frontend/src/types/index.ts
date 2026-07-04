export type Role = 'OWNER' | 'MANAGER' | 'HOST' | 'WAITER'

export type TableStatus =
  | 'AVAILABLE'
  | 'RESERVED'
  | 'SEATED'
  | 'ACTIVE'
  | 'BILLING'
  | 'PAID'
  | 'CLEANING'

export type TableType = 'STANDARD' | 'BOOTH' | 'BAR' | 'VIP'

export type TableShape = 'CIRCLE' | 'RECTANGLE'

export type FloorLabelKind = 'ENTRANCE' | 'KITCHEN' | 'BAR' | 'CUSTOM'

export interface RectBounds {
  x: number
  y: number
  width: number
  height: number
}

export interface User {
  id: string
  name: string
  email: string
  role: Role
  isActive: boolean
}

export interface AuthUser {
  id: string
  name: string
  email: string
  role: Role
}

export interface Section {
  id: string
  name: string
  color: string
  bounds: RectBounds
}

export interface FloorLabel {
  id: string
  kind: FloorLabelKind
  text: string
  bounds: RectBounds
}

export interface Table {
  id: string
  sectionId: string
  number: string
  capacity: number
  type: TableType
  shape: TableShape
  status: TableStatus
  x: number
  y: number
  width: number
  height: number
  rotation: number
  cameraUrl?: string | null
  roiCoords?: RectBounds | null
}

export interface CameraRoiSuggestion {
  frameWidth: number
  frameHeight: number
  sampledFrames: number
  method: string
  confidence: number
  roiCoords: RectBounds
  candidates: RectBounds[]
}

export interface DiningSession {
  id: string
  tableId: string
  guestName?: string
  partySize: number
  seatedAt: string
  status: TableStatus
}

export interface Floor {
  id: string
  name: string
  width: number
  height: number
  sections: Section[]
  labels: FloorLabel[]
  tables: Table[]
}

export interface FloorStats {
  total: number
  available: number
  occupied: number
  reserved: number
  cleaning: number
  occupancyRate: number
  avgOccupiedMinutes: number
}

export interface CreateTablePayload {
  number: string
  capacity: number
  sectionId: string
  type: TableType
  shape: TableShape
  x?: number
  y?: number
  width?: number
  height?: number
}

export interface CreateSectionPayload {
  name: string
  color?: string
  bounds?: RectBounds
}

export interface CreateLabelPayload {
  kind: FloorLabelKind
  text: string
  bounds?: RectBounds
}

export interface LoginResponse {
  accessToken: string
  expiresAt: string
  user: AuthUser
}

export interface SeatGuestPayload {
  tableId: string
  partySize: number
  guestName?: string
}

export interface CreateUserPayload {
  name: string
  email: string
  password: string
  role: Role
}
