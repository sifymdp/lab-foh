import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Role, User } from '../types'

const ROLES: Role[] = ['OWNER', 'MANAGER', 'HOST', 'WAITER']

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<Role>('WAITER')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setUsers(await api.getUsers())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load users')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    try {
      await api.createUser({ name, email, password, role })
      setShowForm(false)
      setName('')
      setEmail('')
      setPassword('')
      setRole('WAITER')
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user')
    }
  }

  async function toggleActive(user: User) {
    try {
      await api.setUserActive(user.id, !user.isActive)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user')
    }
  }

  return (
    <div className="users-page">
      <div className="page-header">
        <div>
          <h2>Users</h2>
          <p className="muted">Owner only — create and activate staff accounts</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={() => setShowForm(true)}>
          Add user
        </button>
      </div>

      {error && <p className="form-error">{error}</p>}

      {loading ? (
        <div className="page-loading inline">
          <div className="spinner" />
        </div>
      ) : (
        <div className="users-table-wrap">
          <table className="users-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={!u.isActive ? 'inactive' : ''}>
                  <td>{u.name}</td>
                  <td>{u.email}</td>
                  <td>
                    <span className={`role-badge role-${u.role.toLowerCase()}`}>
                      {u.role}
                    </span>
                  </td>
                  <td>{u.isActive ? 'Active' : 'Inactive'}</td>
                  <td>
                    {u.role !== 'OWNER' && (
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        onClick={() => toggleActive(u)}
                      >
                        {u.isActive ? 'Deactivate' : 'Activate'}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal">
            <h3>Add staff user</h3>
            <form onSubmit={handleCreate}>
              <label className="field">
                <span>Name</span>
                <input
                  className="input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Email</span>
                <input
                  type="email"
                  className="input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </label>
              <label className="field">
                <span>Password</span>
                <input
                  type="password"
                  className="input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                />
              </label>
              <label className="field">
                <span>Role</span>
                <select
                  className="input"
                  value={role}
                  onChange={(e) => setRole(e.target.value as Role)}
                >
                  {ROLES.filter((r) => r !== 'OWNER').map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
              </label>
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
