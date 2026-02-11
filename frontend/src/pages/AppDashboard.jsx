import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { API_URL } from '../config'
import { useToast } from '../components/Toast'
import LogsPanel from '../components/LogsPanel'
import EventsTimeline from '../components/EventsTimeline'

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function authHeaders() {
  return { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
}

function getAppUrl(appId) {
  const domain = import.meta.env.VITE_APP_DOMAIN || window.location.hostname.replace(/^platform\./, '')
  return `https://app-${appId}.${domain}`
}

function AppDashboard({ user }) {
  const { appId } = useParams()
  const toast = useToast()
  const [app, setApp] = useState(null)
  const [metrics, setMetrics] = useState(null)
  const [health, setHealth] = useState(null)
  const [requests, setRequests] = useState([])
  const [events, setEvents] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [selectedRequest, setSelectedRequest] = useState(null)

  const appUrl = appId ? getAppUrl(appId) : ''

  useEffect(() => {
    if (appId) {
      fetchData()
    }
  }, [appId])

  const fetchData = async () => {
    setLoading(true)
    setError('')
    try {
      const headers = authHeaders()
      const [appRes, metricsRes, healthRes, requestsRes, eventsRes] = await Promise.all([
        fetch(`${API_URL}/api/apps/${appId}`, { headers }),
        fetch(`${API_URL}/api/apps/${appId}/metrics?hours=24`, { headers }),
        fetch(`${API_URL}/api/apps/${appId}/health-status`, { headers }),
        fetch(`${API_URL}/api/apps/${appId}/requests?limit=50`, { headers }),
        fetch(`${API_URL}/api/apps/${appId}/events?limit=50`, { headers }),
      ])

      if (!appRes.ok) {
        if (appRes.status === 404) throw new Error('App not found')
        throw new Error('Failed to load app')
      }

      const [appData, metricsData, healthData, requestsData, eventsData] = await Promise.all([
        appRes.json(),
        metricsRes.ok ? metricsRes.json() : null,
        healthRes.ok ? healthRes.json() : null,
        requestsRes.ok ? requestsRes.json() : null,
        eventsRes.ok ? eventsRes.json() : null,
      ])

      setApp(appData)
      setMetrics(metricsData)
      setHealth(healthData)
      setRequests(requestsData?.requests || [])
      setEvents(eventsData)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(appUrl)
      setCopiedUrl(true)
      toast.success('URL copied to clipboard')
      setTimeout(() => setCopiedUrl(false), 2000)
    } catch {
      toast.error('Failed to copy URL')
    }
  }

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>App Dashboard</h1>
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>Loading...</div>
        </div>
      </div>
    )
  }

  if (error || !app) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>App Dashboard</h1>
        <div className="card" style={{ padding: '2rem' }}>
          <div className="error" style={{ marginBottom: '1rem' }}>{error || 'App not found'}</div>
          <Link to="/dashboard" className="btn btn-secondary">Back to Dashboard</Link>
        </div>
      </div>
    )
  }

  const isRunning = app.status === 'running'
  const errorRate = metrics?.request_count > 0
    ? ((metrics.error_count / metrics.request_count) * 100).toFixed(1)
    : '0.0'

  return (
    <div>
      {/* 1. Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem', marginBottom: '1.5rem' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.25rem' }}>
            <h1 style={{ margin: 0 }}>{app.name}</h1>
            <span className={`status-badge status-${app.status}`}>
              {app.status === 'running' && '\u25CF '}
              {app.status === 'deploying' && '\u25CB '}
              {app.status === 'error' && '\u25CF '}
              {app.status}
            </span>
            {health?.health?.status && (
              <span
                style={{
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '0.25rem',
                  background: health.health.status === 'healthy' ? 'rgba(29, 129, 2, 0.2)' :
                    health.health.status === 'degraded' ? 'rgba(255, 153, 0, 0.2)' :
                    health.health.status === 'unhealthy' ? 'rgba(209, 50, 18, 0.2)' : 'rgba(107, 114, 128, 0.2)',
                  color: health.health.status === 'healthy' ? 'var(--success)' :
                    health.health.status === 'degraded' ? 'var(--warning)' :
                    health.health.status === 'unhealthy' ? 'var(--error)' : 'var(--text-muted)',
                }}
              >
                Health: {health.health.status}
              </span>
            )}
          </div>
          {isRunning && appUrl && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.5rem' }}>
              <code style={{ fontSize: '0.875rem' }}>{appUrl}</code>
              <button
                onClick={copyUrl}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
              >
                {copiedUrl ? 'Copied!' : 'Copy'}
              </button>
              <a href={appUrl} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Open
              </a>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Link to={`/editor/${appId}`} className="btn btn-primary" style={{ padding: '0.5rem 1rem' }}>
            Edit
          </Link>
          <Link to="/dashboard" className="btn btn-secondary" style={{ padding: '0.5rem 1rem' }}>
            Back to Apps
          </Link>
        </div>
      </div>

      {/* 2. Stats Row */}
      <div className="stats-row" style={{ marginBottom: '1.5rem' }}>
        {metrics && (
          <>
            <div className="card stat-card">
              <div className="stat-label">Requests (24h)</div>
              <div className="stat-value">{metrics.request_count?.toLocaleString() ?? '—'}</div>
            </div>
            <div className="card stat-card">
              <div className="stat-label">Errors</div>
              <div className="stat-value" style={{ color: (metrics.error_count || 0) > 0 ? 'var(--error)' : undefined }}>
                {metrics.error_count ?? 0} ({errorRate}%)
              </div>
            </div>
            <div className="card stat-card">
              <div className="stat-label">Response time</div>
              <div className="stat-value">
                {metrics.avg_response_time_ms != null ? `${metrics.avg_response_time_ms}ms` : '—'}
                {metrics.min_response_time_ms != null && metrics.max_response_time_ms != null && (
                  <span style={{ fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)', marginLeft: '0.25rem' }}>
                    (min {metrics.min_response_time_ms} / max {metrics.max_response_time_ms})
                  </span>
                )}
              </div>
            </div>
            {health?.health?.uptime_percent != null && (
              <div className="card stat-card">
                <div className="stat-label">Uptime</div>
                <div className="stat-value">{health.health.uptime_percent}%</div>
              </div>
            )}
          </>
        )}
      </div>

      {/* 3. Recent Requests + 4. Logs side by side on larger screens */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}
        className="app-dashboard-grid"
      >
        <div className="card" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Recent Requests</h3>
          </div>
          <div style={{ overflowX: 'auto', maxHeight: '300px' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-light)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Time</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Method</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Path</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', color: 'var(--text-muted)' }}>Status</th>
                  <th style={{ textAlign: 'right', padding: '0.5rem', color: 'var(--text-muted)' }}>Latency</th>
                </tr>
              </thead>
              <tbody>
                {requests.length === 0 ? (
                  <tr><td colSpan={5} style={{ padding: '1.5rem', color: 'var(--text-muted)', textAlign: 'center' }}>No requests yet</td></tr>
                ) : (
                  requests.map((req, idx) => (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid var(--border)',
                        cursor: req.status_code >= 400 ? 'pointer' : undefined,
                        background: selectedRequest === req ? 'rgba(0, 115, 187, 0.1)' : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                      }}
                      onClick={() => req.status_code >= 400 && setSelectedRequest(selectedRequest === req ? null : req)}
                    >
                      <td style={{ padding: '0.5rem', whiteSpace: 'nowrap' }}>
                        {req.timestamp ? new Date(req.timestamp).toLocaleTimeString() : '—'}
                      </td>
                      <td style={{ padding: '0.5rem', fontFamily: 'monospace' }}>{req.method || '—'}</td>
                      <td style={{ padding: '0.5rem', fontFamily: 'monospace', maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={req.path}>{req.path || '—'}</td>
                      <td style={{
                        padding: '0.5rem',
                        color: req.status_code >= 500 ? 'var(--error)' : req.status_code >= 400 ? 'var(--warning)' : undefined,
                        fontWeight: req.status_code >= 400 ? 500 : undefined,
                      }}>
                        {req.status_code}
                      </td>
                      <td style={{ padding: '0.5rem', textAlign: 'right' }}>{req.duration_ms != null ? `${req.duration_ms}ms` : '—'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {selectedRequest && (
            <div style={{ padding: '1rem', borderTop: '1px solid var(--border)', background: 'var(--bg-light)' }}>
              <h4 style={{ margin: '0 0 0.5rem', fontSize: '0.85rem' }}>Failed request details</h4>
              <div style={{ fontSize: '0.8rem', fontFamily: 'monospace' }}>
                <div><strong>Status:</strong> {selectedRequest.status_code}</div>
                <div><strong>Method:</strong> {selectedRequest.method}</div>
                <div><strong>Path:</strong> {selectedRequest.path}</div>
                <div><strong>Duration:</strong> {selectedRequest.duration_ms}ms</div>
                <div><strong>Time:</strong> {selectedRequest.timestamp ? new Date(selectedRequest.timestamp).toLocaleString() : '—'}</div>
              </div>
              <button className="btn btn-secondary" style={{ marginTop: '0.5rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => setSelectedRequest(null)}>Close</button>
            </div>
          )}
        </div>

        {/* 4. Tailing Logs - embedded LogsPanel */}
        <div className="card" style={{ overflow: 'hidden', minHeight: '200px' }}>
          <LogsPanel appId={appId} isOpen={true} onClose={() => {}} embedded />
        </div>
      </div>

      {/* 5. Database + 6. K8s Events */}
      <div className="app-dashboard-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        <div className="card">
          <div style={{ padding: '1rem', borderBottom: '1px solid var(--border)' }}>
            <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Database</h3>
          </div>
          <div style={{ padding: '1rem' }}>
            {app.database_stats?.collections?.length > 0 ? (
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
                  {app.database_stats.total_collections} collection{app.database_stats.total_collections !== 1 ? 's' : ''} · {app.database_stats.total_documents?.toLocaleString() ?? 0} documents · {app.database_stats.total_size_mb ?? 0} MB
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                  {app.database_stats.collections.map((coll, i) => (
                    <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', padding: '0.35rem 0' }}>
                      <span style={{ fontFamily: 'monospace' }}>{coll.name}</span>
                      <span style={{ color: 'var(--text-muted)' }}>{coll.document_count?.toLocaleString() ?? 0} docs · {formatBytes(coll.size_bytes)}</span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                No database or no collections yet.
              </div>
            )}
          </div>
        </div>

        <div className="card">
          <EventsTimeline events={events?.events || []} phase={events?.deployment_phase || 'unknown'} />
        </div>
      </div>
    </div>
  )
}

export default AppDashboard
