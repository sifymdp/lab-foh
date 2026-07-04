import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { DEMO_PASSWORD } from '../mock/data'

const DEMO_ACCOUNTS = [
  { email: 'owner@foh.demo', role: 'Owner' },
  { email: 'manager@foh.demo', role: 'Manager' },
  { email: 'host@foh.demo', role: 'Host' },
  { email: 'waiter@foh.demo', role: 'Waiter' },
]

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('host@foh.demo')
  const [password, setPassword] = useState(DEMO_PASSWORD)
  const [error, setError] = useState<string | null>(
    sessionStorage.getItem('foh_session_expired') ? 'Your session expired. Please log in.' : null,
  )
  const [loading, setLoading] = useState(false)

  if (user) return <Navigate to="/floor" replace />

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    sessionStorage.removeItem('foh_session_expired')
    try {
      await login(email, password)
      navigate('/floor')
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  function quickLogin(demoEmail: string) {
    setEmail(demoEmail)
    setPassword(DEMO_PASSWORD)
  }

  return (
    <div className="login-page">
      <div className="login-hero">
        <span className="brand-mark lg">FOH</span>
        <h2>Your host stand, digital</h2>
        <p>
          Visualize the floor in real time, seat guests faster, and keep every table status in
          sync — like leading table management tools built for busy dining rooms.
        </p>
        <ul>
          <li>Live floor plan with color-coded tables</li>
          <li>One-tap seating and status updates</li>
          <li>Shift overview at a glance</li>
        </ul>
      </div>

      <div className="login-panel">
        <div className="login-card">
          <div className="login-brand">
            <span className="brand-mark">FOH</span>
            <h1>Sign in</h1>
            <p>Host stand · Table management</p>
          </div>

          <form onSubmit={handleSubmit} className="login-form">
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                className="input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="username"
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
                autoComplete="current-password"
                required
              />
            </label>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="btn btn-primary btn-block" disabled={loading}>
              {loading ? 'Signing in…' : 'Continue to floor plan'}
            </button>
          </form>

          <div className="demo-accounts">
            <p className="demo-label">Quick demo · password {DEMO_PASSWORD}</p>
            <div className="demo-grid">
              {DEMO_ACCOUNTS.map((a) => (
                <button
                  key={a.email}
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => quickLogin(a.email)}
                >
                  {a.role}
                </button>
              ))}
            </div>
          </div>

          <p className="mock-banner">Preview mode · mock data until backend is connected</p>
        </div>
      </div>
    </div>
  )
}
