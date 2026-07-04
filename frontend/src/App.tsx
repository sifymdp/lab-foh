import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { FloorProvider } from './context/FloorContext'
import { SocketProvider } from './context/SocketContext'
import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { OwnerRoute } from './components/auth/OwnerRoute'
import { ManagerRoute } from './components/auth/ManagerRoute'
import { AppShell } from './components/layout/AppShell'
import { LoginPage } from './pages/LoginPage'
import { FloorPage } from './pages/FloorPage'
import { UsersPage } from './pages/UsersPage'
import { SessionsPage } from './pages/SessionsPage'
import { MenuPage } from './pages/MenuPage'
import { ReservationsPage } from './pages/ReservationsPage'
import { AIAlertsPage } from './pages/AIAlertsPage'
import { ReportsPage } from './pages/ReportsPage'
import { CameraSetupPage } from './pages/CameraSetupPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <SocketProvider>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<ProtectedRoute />}>
              <Route
                element={
                  <FloorProvider>
                    <AppShell />
                  </FloorProvider>
                }
              >
                <Route index element={<Navigate to="/floor" replace />} />
                <Route path="floor" element={<FloorPage />} />
                <Route path="sessions" element={<SessionsPage />} />
                <Route path="reservations" element={<ReservationsPage />} />
                <Route path="menu" element={<MenuPage />} />
                <Route path="alerts" element={<AIAlertsPage />} />
                <Route path="reports" element={<ReportsPage />} />
                <Route element={<OwnerRoute />}>
                  <Route path="users" element={<UsersPage />} />
                </Route>
                <Route element={<ManagerRoute />}>
                  <Route path="camera-setup" element={<CameraSetupPage />} />
                </Route>
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/floor" replace />} />
          </Routes>
        </SocketProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
