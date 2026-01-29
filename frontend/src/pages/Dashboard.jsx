import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { API_URL } from '../App'
import LogsPanel from '../components/LogsPanel'

function Dashboard({ user }) {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [logsAppId, setLogsAppId] = useState(null)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const deployingAppId = searchParams.get('deploying')

  useEffect(() => {
    fetchApps()
    // If we have a deploying app, start polling its status
    if (deployingAppId) {
      pollDeploymentStatus(deployingAppId)
      // Remove query param after starting poll
      navigate('/dashboard', { replace: true })
    }
  }, [deployingAppId])

  const pollDeploymentStatus = async (appId) => {
    const maxAttempts = 60 // 2 minutes max (2 second intervals)
    let attempts = 0
    
    const checkStatus = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`${API_URL}/api/apps/${appId}/deploy-status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const status = await response.json()
          
          // Update the app in the list
          setApps(prevApps => 
            prevApps.map(app => 
              app.app_id === appId 
                ? { 
                    ...app, 
                    status: status.status, 
                    deploy_stage: status.deploy_stage,
                    last_error: status.last_error,
                    error_message: status.last_error || status.error_message 
                  }
                : app
            )
          )
          
          if (status.status === 'running' && status.deployment_ready) {
            // Success! Refresh the full list to get latest data
            fetchApps()
            return true
          } else if (status.status === 'error') {
            // Error - stop polling
            fetchApps()
            return true
          }
        }
      } catch (err) {
        console.error('Error checking status:', err)
      }
      
      attempts++
      if (attempts < maxAttempts) {
        setTimeout(checkStatus, 2000) // Check every 2 seconds
      } else {
        // Timeout - refresh to get latest status
        fetchApps()
      }
      return false
    }
    
    checkStatus()
  }

  const fetchApps = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch apps')
      }

      const data = await response.json()
      setApps(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const deleteApp = async (appId) => {
    if (!window.confirm('Are you sure you want to delete this app?')) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to delete app')
      }

      fetchApps()
    } catch (err) {
      alert(err.message)
    }
  }

  if (loading) {
    return <div className="loading">Loading your apps...</div>
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1>Applications</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={fetchApps}
            disabled={loading}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            {loading ? '...' : 'Refresh'}
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/editor')}>
            New Application
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {apps.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
            No applications found. Create your first FastAPI application.
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/editor')}>
            Create Application
          </button>
        </div>
      ) : (
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>App ID</th>
                <th>Status</th>
                <th>Last Activity</th>
                <th>Links</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {apps.map((app) => (
                <tr key={app.id}>
                  <td>
                    <div style={{ fontWeight: '500' }}>{app.name}</div>
                    {app.status === 'error' && (app.last_error || app.error_message) && (
                      <div className="error" style={{ marginTop: '0.5rem', padding: '0.5rem', fontSize: '0.75rem' }}>
                        {app.last_error || app.error_message}
                      </div>
                    )}
                  </td>
                  <td>
                    <code style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>{app.app_id}</code>
                  </td>
                  <td>
                    <span className={`status-badge status-${app.status}`}>
                      {app.status === 'running' && '●'}
                      {app.status === 'deploying' && (
                        <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>○</span>
                      )}
                      {app.status === 'error' && '●'}
                      {' '}{app.status}
                    </span>
                    {app.deploy_stage && app.deploy_stage !== app.status && (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
                        Stage: {app.deploy_stage}
                      </div>
                    )}
                    {app.status === 'deploying' && (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '0.25rem', fontStyle: 'italic' }}>
                        Deploying...
                      </div>
                    )}
                  </td>
                  <td>
                    {app.last_activity && app.status !== 'deploying' ? (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                        {new Date(app.last_activity).toLocaleString()}
                      </span>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>—</span>
                    )}
                  </td>
                  <td>
                    {app.status === 'running' ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                        <a
                          href={app.deployment_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem' }}
                        >
                          View App
                        </a>
                        <a
                          href={`${app.deployment_url}/docs`}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem' }}
                        >
                          API Docs
                        </a>
                      </div>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>—</span>
                    )}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                      {app.status === 'error' && (
                        <button
                          className="btn btn-secondary"
                          onClick={() => navigate(`/editor/${app.app_id}`)}
                          style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                        >
                          Retry
                        </button>
                      )}
                      {app.status === 'running' && (
                        <button
                          className="btn btn-secondary"
                          onClick={() => setLogsAppId(app.app_id)}
                          style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                        >
                          Logs
                        </button>
                      )}
                      <button
                        className="btn btn-secondary"
                        onClick={() => navigate(`/editor/${app.app_id}`)}
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                      >
                        Edit
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => deleteApp(app.app_id)}
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                      >
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <LogsPanel
        appId={logsAppId}
        isOpen={!!logsAppId}
        onClose={() => setLogsAppId(null)}
      />
    </div>
  )
}

export default Dashboard
