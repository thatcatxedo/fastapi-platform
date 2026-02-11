import { useState, useEffect } from 'react'
import { API_URL } from '../config'

function ErrorsPanel({ appId, isOpen, onClose }) {
  const [errors, setErrors] = useState([])
  const [totalCount, setTotalCount] = useState(0)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isOpen && appId) {
      fetchErrors()
    }
  }, [isOpen, appId])

  const fetchErrors = async () => {
    setLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(
        `${API_URL}/api/apps/${appId}/errors?limit=50`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (response.ok) {
        const data = await response.json()
        setErrors(data.errors || [])
        setTotalCount(data.total_count || 0)
        setError(null)
      } else {
        setError('Failed to fetch errors')
      }
    } catch (err) {
      setError('Failed to fetch errors')
    } finally {
      setLoading(false)
    }
  }

  if (!isOpen) return null

  return (
    <div className="logs-panel" style={{ maxHeight: '50vh' }}>
      {/* Header */}
      <div className="logs-panel-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h3 style={{ margin: 0, fontSize: '0.9rem' }}>
            Errors: {appId.slice(0, 8)}... 
            <span style={{ fontWeight: 'normal', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
              ({totalCount} total)
            </span>
          </h3>
          {error && (
            <span style={{ color: 'var(--warning)', fontSize: '0.75rem' }}>
              {error}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button onClick={fetchErrors} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Refresh
          </button>
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            Close
          </button>
        </div>
      </div>

      {/* Errors content */}
      <div className="logs-panel-content" style={{ padding: '0.5rem' }}>
        {loading ? (
          <div style={{ color: 'var(--text-muted)', padding: '1rem' }}>Loading errors...</div>
        ) : errors.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.5rem', opacity: 0.5 }}>✓</div>
            No errors in the last 24 hours
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Time</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Status</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Method</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Path</th>
                <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Type</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((err, idx) => (
                <tr 
                  key={idx} 
                  style={{ 
                    borderBottom: '1px solid var(--border)',
                    backgroundColor: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)'
                  }}
                >
                  <td style={{ padding: '0.5rem', whiteSpace: 'nowrap' }}>
                    {err.timestamp ? new Date(err.timestamp).toLocaleString() : '—'}
                  </td>
                  <td style={{ 
                    padding: '0.5rem',
                    color: err.status_code >= 500 ? 'var(--error)' : 'var(--warning, #f59e0b)',
                    fontWeight: '500'
                  }}>
                    {err.status_code}
                  </td>
                  <td style={{ padding: '0.5rem', fontFamily: 'monospace' }}>
                    {err.request_method || '—'}
                  </td>
                  <td style={{ 
                    padding: '0.5rem', 
                    fontFamily: 'monospace',
                    maxWidth: '200px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }} title={err.request_path}>
                    {err.request_path || '—'}
                  </td>
                  <td style={{ padding: '0.5rem' }}>
                    <span style={{
                      padding: '0.125rem 0.375rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.7rem',
                      backgroundColor: err.error_type === 'server_error' 
                        ? 'rgba(239, 68, 68, 0.2)' 
                        : 'rgba(245, 158, 11, 0.2)',
                      color: err.error_type === 'server_error' ? 'var(--error)' : 'var(--warning, #f59e0b)'
                    }}>
                      {err.error_type === 'server_error' ? '5xx' : '4xx'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default ErrorsPanel
