import type { TableStatus, TableType } from '../types'

export interface StatusStyle {
  label: string
  bg: string
  border: string
  text: string
}

/** Status colours for canvas tiles (implementation guide §4.2) */
export const STATUS_CONFIG: Record<TableStatus, StatusStyle> = {
  AVAILABLE: {
    label: 'Available',
    bg: '#ecfdf5',
    border: '#22c55e',
    text: '#166534',
  },
  RESERVED: {
    label: 'Reserved',
    bg: '#eff6ff',
    border: '#3b82f6',
    text: '#1e40af',
  },
  SEATED: {
    label: 'Seated',
    bg: '#fff7ed',
    border: '#f97316',
    text: '#9a3412',
  },
  ACTIVE: {
    label: 'Active',
    bg: '#fefce8',
    border: '#eab308',
    text: '#854d0e',
  },
  BILLING: {
    label: 'Billing',
    bg: '#faf5ff',
    border: '#a855f7',
    text: '#6b21a8',
  },
  PAID: {
    label: 'Paid',
    bg: '#f0fdfa',
    border: '#14b8a6',
    text: '#115e59',
  },
  CLEANING: {
    label: 'Cleaning',
    bg: '#f8fafc',
    border: '#94a3b8',
    text: '#475569',
  },
}

export const STATUS_TRANSITIONS: Record<TableStatus, TableStatus[]> = {
  AVAILABLE: ['RESERVED'],
  RESERVED: ['AVAILABLE'],
  SEATED: ['ACTIVE', 'BILLING'],
  ACTIVE: ['BILLING'],
  BILLING: ['PAID'],
  PAID: ['CLEANING'],
  CLEANING: ['AVAILABLE'],
}

export function getNextStatuses(current: TableStatus): TableStatus[] {
  return STATUS_TRANSITIONS[current] ?? []
}

export function isValidTransition(from: TableStatus, to: TableStatus): boolean {
  return getNextStatuses(from).includes(to)
}

export const SECTION_ICONS: Record<string, string> = {
  Indoor: '🏠',
  Outdoor: '☀️',
  Bar: '🍸',
  VIP: '⭐',
}

export const TABLE_TYPE_LABELS: Record<TableType, string> = {
  STANDARD: 'Standard',
  BOOTH: 'Booth',
  BAR: 'Bar',
  VIP: 'VIP',
}

/** Tables in these statuses count as occupied for stats */
export const OCCUPIED_STATUSES: TableStatus[] = [
  'SEATED',
  'ACTIVE',
  'BILLING',
  'PAID',
]
