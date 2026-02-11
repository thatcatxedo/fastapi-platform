import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../config'
import { useApps } from '../context/AppsContext'
import LogsPanel from '../components/LogsPanel'
import ErrorsPanel from '../components/ErrorsPanel'

function timeAgo(dateStr) {
  if (!dateStr) return null
  const seconds = Math.floor((Date.now() - new Date(dateStr).getTime()) / 1000)
  if (seconds < 60) return 'just now'
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

const STATUS_PRIORITY = { running: 0, deploying: 1, error: 2 }

function Dashboard({ user }) {
  const { apps, loading, stats, fetchApps } = useApps()
  const [logsAppId, setLogsAppId] = useState(null)
  const [errorsAppId, setErrorsAppId] = useState(null)
  const [appMetrics, setAppMetrics] = useState({})
  const [loadingMetrics, setLoadingMetrics] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  // Fetch metrics for running apps
  useEffect(() => {
    const runningApps = apps.filter(app => app.status === 'running')
    if (runningApps.length > 0) {
      fetchMetrics(runningApps)
    }
  }, [apps])

  const fetchMetrics = async (runningApps) => {
    setLoadingMetrics(true)
    try {
      const token = localStorage.getItem('token')
      const results = await Promise.all(
        runningApps.map(app =>
          fetch(`${API_URL}/api/apps/${app.app_id}/metrics`, {
            headers: { 'Authorization': `Bearer ${token}` }
          }).then(r => r.ok ? r.json() : null).catch(() => null)
        )
      )

      const newMetrics = {}
      runningApps.forEach((app, i) => {
        if (results[i]) {
          newMetrics[app.app_id] = results[i]
        }
      })
      setAppMetrics(newMetrics)
    } catch (err) {
      console.error('Failed to fetch metrics:', err)
    } finally {
      setLoadingMetrics(false)
    }
  }

  // Aggregate metrics
  const totalRequests = Object.values(appMetrics).reduce((sum, m) => sum + (m?.request_count || 0), 0)
  const totalErrors = Object.values(appMetrics).reduce((sum, m) => sum + (m?.error_count || 0), 0)
  const avgResponseTime = Object.values(appMetrics).length > 0
    ? Math.round(Object.values(appMetrics).reduce((sum, m) => sum + (m?.avg_response_time_ms || 0), 0) / Object.values(appMetrics).length)
    : 0

  // Filter and sort apps
  const filteredApps = useMemo(() => {
    return apps
      .filter(app => statusFilter === 'all' || app.status === statusFilter)
      .filter(app => !searchQuery || app.name.toLowerCase().includes(searchQuery.toLowerCase()))
      .sort((a, b) => {
        const pa = STATUS_PRIORITY[a.status] ?? 3
        const pb = STATUS_PRIORITY[b.status] ?? 3
        if (pa !== pb) return pa - pb
        // Within same status, sort by last_activity descending
        const ta = a.last_activity ? new Date(a.last_activity).getTime() : 0
        const tb = b.last_activity ? new Date(b.last_activity).getTime() : 0
        return tb - ta
      })
  }, [apps, statusFilter, searchQuery])

  const handleStatClick = (status) => {
    setStatusFilter(prev => prev === status ? 'all' : status)
  }

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>Dashboard</h1>
        <div className="stats-row">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card stat-card" style={{ padding: '1rem' }}>
              <div style={{ height: '0.75rem', width: '60%', background: 'var(--bg-light)', marginBottom: '0.5rem' }} />
              <div style={{ height: '1.5rem', width: '40%', background: 'var(--bg-light)' }} />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <h1>Dashboard</h1>
        <button
          className="btn btn-secondary"
          onClick={fetchApps}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          Refresh
        </button>
      </div>

      {/* Stats Row */}
      <div className="stats-row">
        <div
          className={`card stat-card stat-card-clickable ${statusFilter === 'all' ? 'stat-card-active' : ''}`}
          onClick={() => handleStatClick('all')}
        >
          <div className="stat-label">Total Apps</div>
          <div className="stat-value">{stats.total}</div>
        </div>
        <div
          className={`card stat-card stat-card-clickable ${statusFilter === 'running' ? 'stat-card-active' : ''}`}
          onClick={() => handleStatClick('running')}
        >
          <div className="stat-label">Running</div>
          <div className="stat-value" style={{ color: 'var(--success)' }}>{stats.running}</div>
        </div>
        <div
          className={`card stat-card stat-card-clickable ${statusFilter === 'deploying' ? 'stat-card-active' : ''}`}
          onClick={() => handleStatClick('deploying')}
        >
          <div className="stat-label">Deploying</div>
          <div className="stat-value" style={{ color: 'var(--warning)' }}>{stats.deploying}</div>
        </div>
        <div
          className={`card stat-card stat-card-clickable ${statusFilter === 'error' ? 'stat-card-active' : ''}`}
          onClick={() => handleStatClick('error')}
        >
          <div className="stat-label">Errors</div>
          <div className="stat-value" style={{ color: stats.error > 0 ? 'var(--error)' : 'var(--text)' }}>{stats.error}</div>
        </div>

        {/* Inline aggregate metrics */}
        {stats.running > 0 && (
          <div className="stat-card stat-card-metrics">
            <div className="stat-label">24h</div>
            <div className="stat-metrics-row">
              <span>{loadingMetrics ? '...' : totalRequests.toLocaleString()} reqs</span>
              <span className="stat-metrics-sep">&middot;</span>
              <span style={{ color: totalErrors > 0 ? 'var(--error)' : undefined }}>{loadingMetrics ? '...' : `${totalErrors} errors (${totalRequests > 0 ? ((totalErrors / totalRequests) * 100).toFixed(1) : '0.0'}%)`}</span>
              <span className="stat-metrics-sep">&middot;</span>
              <span>{loadingMetrics ? '...' : `${avgResponseTime}ms`} avg</span>
            </div>
          </div>
        )}
      </div>

      {/* Search and Filter Bar */}
      <div className="filter-bar">
        <input
          type="text"
          placeholder="Search apps..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="filter-search"
        />
        <div className="filter-pills">
          {['all', 'running', 'deploying', 'error'].map(status => (
            <button
              key={status}
              className={`filter-pill ${statusFilter === status ? 'filter-pill-active' : ''}`}
              onClick={() => setStatusFilter(status)}
            >
              {status === 'all' ? 'All' : status.charAt(0).toUpperCase() + status.slice(1)}
              {status !== 'all' && (
                <span className="filter-pill-count">
                  {status === 'running' ? stats.running : status === 'deploying' ? stats.deploying : stats.error}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* App List */}
      {filteredApps.length > 0 ? (
        <div className="app-list">
          {filteredApps.map(app => {
            const metrics = appMetrics[app.app_id]
            const isRunning = app.status === 'running'
            const isError = app.status === 'error'
            const isDeploying = app.status === 'deploying'
            const activity = timeAgo(app.last_activity)

            return (
              <div key={app.app_id} className="app-row">
                <div className="app-row-header">
                  <div className="app-row-name-group">
                    <Link to={`/editor/${app.app_id}`} className="app-row-name">
                      {app.name}
                    </Link>
                    <span className={`status-badge status-${app.status}`}>
                      {app.status === 'running' && '\u25CF '}
                      {app.status === 'deploying' && '\u25CB '}
                      {app.status === 'error' && '\u25CF '}
                      {app.status}
                    </span>
                  </div>
                  {isRunning && app.deployment_url && (
                    <a
                      href={app.deployment_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="app-row-url"
                    >
                      {app.deployment_url.replace(/^https?:\/\//, '')}
                    </a>
                  )}
                </div>

                <div className="app-row-meta">
                  <div className="app-row-meta-left">
                    {activity && (
                      <span className="app-row-activity">Active {activity}</span>
                    )}
                    {isRunning && metrics && (() => {
                      const errorRate = metrics.request_count > 0
                        ? ((metrics.error_count / metrics.request_count) * 100).toFixed(1)
                        : '0.0'
                      return (
                        <span className="app-row-metrics">
                          {metrics.request_count.toLocaleString()} reqs
                          <span className="stat-metrics-sep">&middot;</span>
                          <span style={{ color: metrics.error_count > 0 ? 'var(--error)' : undefined }}>
                            {metrics.error_count} errors ({errorRate}%)
                          </span>
                          <span className="stat-metrics-sep">&middot;</span>
                          {metrics.avg_response_time_ms}ms
                        </span>
                      )
                    })()}
                    {isError && app.error_message && (
                      <span className="app-row-error">{app.error_message}</span>
                    )}
                    {isDeploying && app.deploy_stage && (
                      <span className="app-row-deploying">{app.deploy_stage}...</span>
                    )}
                  </div>

                  <div className="app-row-actions">
                    <Link
                      to={`/editor/${app.app_id}`}
                      className="btn btn-secondary app-row-btn"
                    >
                      Edit
                    </Link>
                    {isRunning && app.deployment_url && (
                      <>
                        <a
                          href={app.deployment_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary app-row-btn"
                        >
                          Open
                        </a>
                        <a
                          href={`${app.deployment_url}/docs`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn btn-secondary app-row-btn"
                        >
                          Docs
                        </a>
                      </>
                    )}
                    <button
                      className="btn btn-secondary app-row-btn"
                      onClick={() => setLogsAppId(app.app_id)}
                    >
                      Logs
                    </button>
                    {isRunning && (
                      <button
                        className="btn btn-secondary app-row-btn"
                        onClick={() => setErrorsAppId(app.app_id)}
                        style={{ color: metrics?.error_count > 0 ? 'var(--error)' : undefined }}
                      >
                        Errors
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      ) : stats.total === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <h2 style={{ marginBottom: '0.5rem', color: 'var(--text)' }}>No Apps Yet</h2>
          <p style={{ marginBottom: '1.5rem', color: 'var(--text-muted)' }}>
            Create your first app to get started!
          </p>
          <Link to="/editor" className="btn btn-primary" style={{ padding: '0.75rem 1.5rem' }}>
            Create New App
          </Link>
        </div>
      ) : (
        <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            No apps match{searchQuery ? ` "${searchQuery}"` : ''}{statusFilter !== 'all' ? ` with status "${statusFilter}"` : ''}.
          </p>
        </div>
      )}

      <LogsPanel
        appId={logsAppId}
        isOpen={!!logsAppId}
        onClose={() => setLogsAppId(null)}
      />

      <ErrorsPanel
        appId={errorsAppId}
        isOpen={!!errorsAppId}
        onClose={() => setErrorsAppId(null)}
      />
    </div>
  )
}

export default Dashboard
