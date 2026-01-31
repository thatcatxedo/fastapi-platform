import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../App'
import { useApps } from '../context/AppsContext'
import LogsPanel from '../components/LogsPanel'
import ErrorsPanel from '../components/ErrorsPanel'
import { useToast } from '../components/Toast'

function Dashboard({ user }) {
  const { apps, loading, stats, fetchApps } = useApps()
  const [logsAppId, setLogsAppId] = useState(null)
  const [errorsAppId, setErrorsAppId] = useState(null)
  const [appMetrics, setAppMetrics] = useState({})
  const [loadingMetrics, setLoadingMetrics] = useState(false)
  const toast = useToast()

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

  // Calculate aggregate metrics
  const totalRequests = Object.values(appMetrics).reduce((sum, m) => sum + (m?.request_count || 0), 0)
  const totalErrors = Object.values(appMetrics).reduce((sum, m) => sum + (m?.error_count || 0), 0)
  const avgResponseTime = Object.values(appMetrics).length > 0
    ? Math.round(Object.values(appMetrics).reduce((sum, m) => sum + (m?.avg_response_time_ms || 0), 0) / Object.values(appMetrics).length)
    : 0

  const runningApps = apps.filter(app => app.status === 'running')

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>Dashboard</h1>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="card" style={{ padding: '1.25rem' }}>
              <div style={{ height: '1rem', width: '60%', background: 'var(--bg-lighter)', borderRadius: '0.25rem', marginBottom: '0.5rem' }} />
              <div style={{ height: '2rem', width: '40%', background: 'var(--bg-lighter)', borderRadius: '0.25rem' }} />
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1>Dashboard</h1>
        <button 
          className="btn btn-secondary" 
          onClick={fetchApps}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          Refresh
        </button>
      </div>

      {/* Stats Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            Total Apps
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '600', color: 'var(--text)' }}>
            {stats.total}
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            Running
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '600', color: 'var(--success)' }}>
            {stats.running}
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            Deploying
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '600', color: 'var(--warning)' }}>
            {stats.deploying}
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
            Errors
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '600', color: stats.error > 0 ? 'var(--error)' : 'var(--text)' }}>
            {stats.error}
          </div>
        </div>
      </div>

      {/* Metrics Summary */}
      {stats.running > 0 && (
        <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
          <h2 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text)' }}>
            Aggregate Metrics (24h)
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1.5rem' }}>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Total Requests
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text)' }}>
                {loadingMetrics ? '...' : totalRequests.toLocaleString()}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Total Errors
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: totalErrors > 0 ? 'var(--error)' : 'var(--text)' }}>
                {loadingMetrics ? '...' : totalErrors.toLocaleString()}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Avg Response Time
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: '600', color: 'var(--text)' }}>
                {loadingMetrics ? '...' : `${avgResponseTime}ms`}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Running Apps Quick Access */}
      {runningApps.length > 0 ? (
        <div>
          <h2 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text)' }}>
            Running Apps
          </h2>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1rem' }}>
            {runningApps.map(app => (
              <div key={app.app_id} className="card" style={{ padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <div>
                    <Link 
                      to={`/editor/${app.app_id}`}
                      style={{ 
                        fontWeight: '500', 
                        color: 'var(--text)', 
                        textDecoration: 'none',
                        display: 'block',
                        marginBottom: '0.25rem'
                      }}
                    >
                      {app.name}
                    </Link>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {app.app_id}
                    </span>
                  </div>
                  <span className="status-badge status-running">● running</span>
                </div>
                
                {appMetrics[app.app_id] && (
                  <div style={{ 
                    display: 'flex', 
                    gap: '1rem', 
                    fontSize: '0.75rem', 
                    color: 'var(--text-muted)',
                    marginBottom: '0.75rem'
                  }}>
                    <span>{appMetrics[app.app_id].request_count} req</span>
                    <span style={{ color: appMetrics[app.app_id].error_count > 0 ? 'var(--error)' : undefined }}>
                      {appMetrics[app.app_id].error_count} err
                    </span>
                    <span>{appMetrics[app.app_id].avg_response_time_ms}ms avg</span>
                  </div>
                )}

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <a
                    href={app.deployment_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                  >
                    Open App
                  </a>
                  <a
                    href={`${app.deployment_url}/docs`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary"
                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                  >
                    API Docs
                  </a>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setLogsAppId(app.app_id)}
                    style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                  >
                    Logs
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => setErrorsAppId(app.app_id)}
                    style={{ 
                      padding: '0.375rem 0.75rem', 
                      fontSize: '0.75rem',
                      color: appMetrics[app.app_id]?.error_count > 0 ? 'var(--error)' : undefined
                    }}
                  >
                    Errors
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : stats.total === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem', opacity: 0.3 }}>🚀</div>
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
          <p style={{ color: 'var(--text-muted)' }}>
            No apps currently running. Select an app from the sidebar to deploy it.
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
