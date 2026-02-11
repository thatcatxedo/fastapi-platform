import { useState, useEffect, useRef, useCallback } from 'react'
import { API_URL } from '../config'

// Derive WebSocket URL from API_URL
const WS_URL = API_URL
  ? API_URL.replace(/^http/, 'ws')
  : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`

function LogsPanel({ appId, isOpen, onClose, embedded = false }) {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const [connectionMode, setConnectionMode] = useState(null) // 'ws' or 'poll'
  const logsEndRef = useRef(null)
  const pollIntervalRef = useRef(null)
  const wsRef = useRef(null)

  const fetchLogs = useCallback(async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(
        `${API_URL}/api/apps/${appId}/logs?tail_lines=200`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (response.ok) {
        const data = await response.json()
        setLogs(data.logs || [])
        setError(data.error)
      }
    } catch (err) {
      setError('Failed to fetch logs')
    } finally {
      setLoading(false)
    }
  }, [appId])

  const startPolling = useCallback(() => {
    setConnectionMode('poll')
    fetchLogs()
    pollIntervalRef.current = setInterval(fetchLogs, 3000)
  }, [fetchLogs])

  const connectWebSocket = useCallback(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      startPolling()
      return
    }

    let ws
    try {
      ws = new WebSocket(
        `${WS_URL}/api/apps/${appId}/logs/stream?token=${token}`
      )
    } catch {
      // WebSocket construction can throw (e.g. mixed content)
      startPolling()
      return
    }
    wsRef.current = ws

    ws.onopen = () => {
      setConnectionMode('ws')
      setLoading(false)
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'log') {
          setLogs(prev => [
            ...prev.slice(-499),
            { timestamp: data.timestamp, message: data.message }
          ])
        } else if (data.type === 'error') {
          setError(data.message)
        } else if (data.type === 'connected') {
          setError(null)
        }
      } catch {
        // Ignore malformed messages
      }
    }

    ws.onerror = () => {
      // Fall back to polling on any WebSocket error
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      startPolling()
    }

    ws.onclose = (event) => {
      wsRef.current = null
      // Only fall back to polling if we haven't already started
      if (event.code === 4001 || event.code === 4004) {
        if (!pollIntervalRef.current) {
          startPolling()
        }
      }
    }
  }, [appId, startPolling])

  useEffect(() => {
    if (isOpen && appId) {
      connectWebSocket()
    }
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
        pollIntervalRef.current = null
      }
      setConnectionMode(null)
    }
  }, [isOpen, appId, connectWebSocket])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  if (!isOpen) return null

  return (
    <div className={`logs-panel ${embedded ? 'logs-panel-embedded' : ''}`}>
      {/* Header */}
      <div className="logs-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Logs: {appId.slice(0, 8)}...</h3>
          {connectionMode && (
            <span style={{
              fontSize: '0.65rem',
              color: connectionMode === 'ws' ? 'var(--success)' : 'var(--text-muted)',
              opacity: 0.7
            }}>
              {connectionMode === 'ws' ? 'live' : 'polling'}
            </span>
          )}
          {error && (
            <span style={{ color: 'var(--warning)', fontSize: '0.75rem' }}>
              {error}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label style={{ fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
            />
            Auto-scroll
          </label>
          <button onClick={fetchLogs} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Refresh
          </button>
          {!embedded && (
            <button onClick={onClose} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
              Close
            </button>
          )}
        </div>
      </div>

      {/* Logs content */}
      <div className="logs-panel-content">
        {loading ? (
          <div style={{ color: 'var(--text-muted)' }}>Loading logs...</div>
        ) : logs.length === 0 ? (
          <div style={{ color: 'var(--text-muted)' }}>No logs available</div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="log-line">
              {log.timestamp && (
                <span className="log-timestamp">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
              )}
              <span className="log-message">{log.message}</span>
            </div>
          ))
        )}
        <div ref={logsEndRef} />
      </div>
    </div>
  )
}

export default LogsPanel
