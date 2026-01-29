import { useState, useEffect, useRef } from 'react'
import { API_URL } from '../App'

function LogsPanel({ appId, isOpen, onClose }) {
  const [logs, setLogs] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [autoScroll, setAutoScroll] = useState(true)
  const logsEndRef = useRef(null)
  const pollIntervalRef = useRef(null)

  useEffect(() => {
    if (isOpen && appId) {
      fetchLogs()
      // Poll every 3 seconds
      pollIntervalRef.current = setInterval(fetchLogs, 3000)
    }
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current)
      }
    }
  }, [isOpen, appId])

  useEffect(() => {
    if (autoScroll && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [logs, autoScroll])

  const fetchLogs = async () => {
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
  }

  if (!isOpen) return null

  return (
    <div className="logs-panel">
      {/* Header */}
      <div className="logs-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Logs: {appId.slice(0, 8)}...</h3>
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
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Close
          </button>
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
