import type { Role } from '../types'

export function canEditFloor(role: Role): boolean {
  return role === 'OWNER' || role === 'MANAGER'
}

export function canManageUsers(role: Role): boolean {
  return role === 'OWNER'
}

export function canSeatGuests(_role: Role): boolean {
  return true
}

export function canChangeStatus(_role: Role): boolean {
  return true
}
