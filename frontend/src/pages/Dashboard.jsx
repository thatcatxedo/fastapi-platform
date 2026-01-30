import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { API_URL } from '../App'
import LogsPanel from '../components/LogsPanel'

function Dashboard({ user }) {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [logsAppId, setLogsAppId] = useState(null)
  const [copiedUrl, setCopiedUrl] = useState(null)
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

  const cloneApp = async (appId) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}/clone`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.message || 'Failed to clone app')
      }

      const clonedApp = await response.json()
      // Refresh apps list and navigate to show the new cloned app
      await fetchApps()
      // Navigate to editor for the cloned app
      navigate(`/editor/${clonedApp.app_id}?deploying=${clonedApp.app_id}`)
    } catch (err) {
      alert(err.message)
    }
  }

  const copyAppUrl = async (app) => {
    const fullUrl = `${window.location.origin}${app.deployment_url}`
    try {
      await navigator.clipboard.writeText(fullUrl)
      setCopiedUrl(app.app_id)
      setTimeout(() => setCopiedUrl(null), 2000)
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = fullUrl
      document.body.appendChild(textArea)
      textArea.select()
      try {
        document.execCommand('copy')
        setCopiedUrl(app.app_id)
        setTimeout(() => setCopiedUrl(null), 2000)
      } catch (e) {
        alert('Failed to copy URL')
      }
      document.body.removeChild(textArea)
    }
  }

  if (loading) {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
          <h1>Applications</h1>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              className="btn btn-secondary" 
              disabled
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', opacity: 0.5 }}
            >
              Refresh
            </button>
            <button className="btn btn-primary" disabled style={{ opacity: 0.5 }}>
              New Application
            </button>
          </div>
        </div>
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
              {[1, 2, 3].map((i) => (
                <tr key={i}>
                  <td>
                    <div style={{ 
                      height: '1.25rem', 
                      width: '60%', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                  <td>
                    <div style={{ 
                      height: '1rem', 
                      width: '80px', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                  <td>
                    <div style={{ 
                      height: '1.25rem', 
                      width: '70px', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                  <td>
                    <div style={{ 
                      height: '1rem', 
                      width: '120px', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                  <td>
                    <div style={{ 
                      height: '1rem', 
                      width: '100px', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                  <td>
                    <div style={{ 
                      height: '1.5rem', 
                      width: '200px', 
                      background: 'var(--bg-light)', 
                      borderRadius: '0.25rem',
                      animation: 'pulse 1.5s ease-in-out infinite'
                    }} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}</style>
      </div>
    )
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
        <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem' }}>
          <div style={{ fontSize: '3rem', marginBottom: '1rem', opacity: 0.3 }}>🚀</div>
          <h2 style={{ marginBottom: '0.5rem', color: 'var(--text)' }}>No Applications Yet</h2>
          <p style={{ marginBottom: '2rem', color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto 2rem' }}>
            Get started by creating your first FastAPI application. Write Python code, deploy instantly, and share your API with the world.
          </p>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={() => navigate('/editor')} style={{ padding: '0.75rem 1.5rem' }}>
              Create Your First App
            </button>
            <button className="btn btn-secondary" onClick={fetchApps} style={{ padding: '0.75rem 1.5rem' }}>
              Refresh
            </button>
          </div>
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
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <a
                            href={app.deployment_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem' }}
                          >
                            View App
                          </a>
                          <button
                            onClick={() => copyAppUrl(app)}
                            style={{
                              padding: '0.125rem 0.375rem',
                              fontSize: '0.7rem',
                              background: copiedUrl === app.app_id ? 'var(--success)' : 'var(--bg-light)',
                              border: '1px solid var(--border)',
                              borderRadius: '0.25rem',
                              cursor: 'pointer',
                              color: copiedUrl === app.app_id ? 'white' : 'var(--text-muted)',
                              transition: 'all 0.2s'
                            }}
                            title="Copy app URL"
                          >
                            {copiedUrl === app.app_id ? '✓ Copied' : '📋'}
                          </button>
                        </div>
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
                        className="btn btn-secondary"
                        onClick={() => cloneApp(app.app_id)}
                        style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
                        title="Clone this app"
                      >
                        Clone
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
