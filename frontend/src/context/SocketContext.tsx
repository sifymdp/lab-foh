import {
  createContext, useCallback, useContext, useEffect,
  useMemo, useRef, useState, type ReactNode,
} from 'react'

type EventHandler = (payload: unknown) => void
interface SocketContextValue {
  connected: boolean
  joinFloor: (floorId: string) => void
  on: (event: string, handler: EventHandler) => () => void
}

const SocketContext = createContext<SocketContextValue | null>(null)
const USE_MOCK = import.meta.env.VITE_USE_MOCK !== 'false'
const SOCKET_URL = (import.meta.env.VITE_SOCKET_URL ?? 'http://localhost:8000').replace('http', 'ws')

export function SocketProvider({ children }: { children: ReactNode }) {
  const [connected, setConnected] = useState(USE_MOCK)
  const listeners = useMemo(() => new Map<string, Set<EventHandler>>(), [])
  const wsRef = useRef<WebSocket | null>(null)
  const floorIdRef = useRef<string>('floor-1')

  const emit = useCallback((event: string, payload: unknown) => {
    listeners.get(event)?.forEach((h) => h(payload))
  }, [listeners])

  const connect = useCallback((floorId: string) => {
    if (USE_MOCK) { setConnected(true); return }
    const token = localStorage.getItem('foh_access_token')
    const url = `${SOCKET_URL}/ws/${floorId}${token ? `?token=${token}` : ''}`
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onopen = () => { console.log('[WS] connected to', url); setConnected(true) }
    ws.onclose = () => {
      setConnected(false)
      setTimeout(() => connect(floorIdRef.current), 3000)
    }
    ws.onerror = () => setConnected(false)
    ws.onmessage = (e) => {
      console.log('[WS] message received:', e.data)
      try { const { event, data } = JSON.parse(e.data); emit(event, data) } catch { /* ignore */ }
    }
  }, [emit])

  useEffect(() => {
    if (USE_MOCK) return
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send('ping')
    }, 30_000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => () => { wsRef.current?.close() }, [])

  const joinFloor = useCallback((floorId: string) => {
    floorIdRef.current = floorId
    wsRef.current?.close()
    connect(floorId)
  }, [connect])

  const on = useCallback((event: string, handler: EventHandler) => {
    if (!listeners.has(event)) listeners.set(event, new Set())
    listeners.get(event)!.add(handler)
    return () => listeners.get(event)?.delete(handler)
  }, [listeners])

  const value = useMemo(() => ({ connected, joinFloor, on }), [connected, joinFloor, on])
  return <SocketContext.Provider value={value}>{children}</SocketContext.Provider>
}

export function useSocket() {
  const ctx = useContext(SocketContext)
  if (!ctx) throw new Error('useSocket must be used within SocketProvider')
  return ctx
}
