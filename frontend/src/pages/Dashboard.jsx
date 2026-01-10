import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../App'

function Dashboard({ user }) {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    fetchApps()
  }, [])

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
        <h1>My Apps</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={fetchApps}
            disabled={loading}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            {loading ? '⏳' : '🔄'} Refresh
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/editor')}>
            + New App
          </button>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {apps.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <p style={{ marginBottom: '1rem', color: 'var(--text-muted)' }}>
            You don't have any apps yet. Create your first FastAPI app!
          </p>
          <button className="btn btn-primary" onClick={() => navigate('/editor')}>
            Create Your First App
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {apps.map((app) => (
            <div key={app.id} className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <h2 style={{ marginBottom: '0.5rem' }}>{app.name}</h2>
                  <p style={{ color: 'var(--text-muted)', marginBottom: '1rem', fontSize: '0.875rem' }}>
                    ID: {app.app_id}
                  </p>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap' }}>
                    <span className={`status-badge status-${app.status}`}>
                      {app.status === 'running' && '✅'}
                      {app.status === 'deploying' && '⏳'}
                      {app.status === 'error' && '❌'}
                      {' '}{app.status}
                    </span>
                    {app.last_activity && (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                        Last active: {new Date(app.last_activity).toLocaleString()}
                      </span>
                    )}
                  </div>
                  {app.status === 'error' && app.error_message && (
                    <div className="error" style={{ marginBottom: '1rem', padding: '0.75rem', fontSize: '0.875rem' }}>
                      <strong>Error:</strong> {app.error_message}
                    </div>
                  )}
                  {app.status === 'running' && (
                    <a
                      href={app.deployment_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: 'var(--primary)', textDecoration: 'none' }}
                    >
                      {window.location.origin}{app.deployment_url} →
                    </a>
                  )}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {app.status === 'error' && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => navigate(`/editor/${app.app_id}`)}
                      style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                    >
                      🔄 Retry
                    </button>
                  )}
                  <button
                    className="btn btn-secondary"
                    onClick={() => navigate(`/editor/${app.app_id}`)}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                  >
                    Edit
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => deleteApp(app.app_id)}
                    style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Dashboard
