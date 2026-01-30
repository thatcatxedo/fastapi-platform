import { useState, useEffect } from 'react'
import { API_URL } from '../App'

function Database({ user }) {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [viewerInfo, setViewerInfo] = useState(null)
  const [viewerLoading, setViewerLoading] = useState(false)
  const [viewerError, setViewerError] = useState('')

  useEffect(() => {
    fetchStats()
  }, [])

  const fetchStats = async () => {
    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/database/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.message || 'Failed to fetch database stats')
      }

      const data = await response.json()
      setStats(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const requestViewer = async (endpoint) => {
    setViewerLoading(true)
    setViewerError('')
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail?.message || data.message || 'Failed to open MongoDB viewer')
      }

      setViewerInfo(data)
      if (data.ready === undefined || data.ready) {
        window.open(data.url, '_blank', 'noopener,noreferrer')
      }
    } catch (err) {
      setViewerError(err.message)
    } finally {
      setViewerLoading(false)
    }
  }

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>Database</h1>
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>Loading database statistics...</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1>Database</h1>
        <button
          className="btn btn-secondary"
          onClick={fetchStats}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          Refresh
        </button>
      </div>

      {error && <div className="error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {/* Database Viewer Card */}
      <div className="card" style={{ marginBottom: '1.5rem', padding: '1rem 1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>MongoDB Viewer</h3>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              Browse and manage your database with mongo-express
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              className="btn btn-primary"
              onClick={() => requestViewer('/api/viewer')}
              disabled={viewerLoading}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              {viewerLoading ? 'Opening...' : 'Open Viewer'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => requestViewer('/api/viewer/rotate')}
              disabled={viewerLoading}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              Rotate Credentials
            </button>
          </div>
        </div>
        {viewerError && (
          <div className="error" style={{ marginTop: '0.75rem', padding: '0.5rem' }}>
            {viewerError}
          </div>
        )}
        {viewerInfo && (
          <div style={{ marginTop: '0.75rem', padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '0.375rem', fontSize: '0.875rem' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>URL:</span>{' '}
                <a href={viewerInfo.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)' }}>
                  {viewerInfo.url}
                </a>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Username:</span>{' '}
                <code>{viewerInfo.username}</code>
              </div>
              {viewerInfo.password_provided && (
                <div>
                  <span style={{ color: 'var(--text-muted)' }}>Password:</span>{' '}
                  <code>{viewerInfo.password}</code>
                </div>
              )}
            </div>
            {viewerInfo.ready === false && (
              <div style={{ marginTop: '0.5rem', color: 'var(--warning)', fontSize: '0.8rem' }}>
                Viewer is starting up... Please wait a moment and try again.
              </div>
            )}
          </div>
        )}
      </div>

      {/* Database Stats Overview */}
      {stats && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--primary)' }}>
                {stats.total_collections}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Collections</div>
            </div>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--success)' }}>
                {stats.total_documents.toLocaleString()}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Documents</div>
            </div>
            <div className="card" style={{ padding: '1.25rem', textAlign: 'center' }}>
              <div style={{ fontSize: '2rem', fontWeight: '700', color: 'var(--warning)' }}>
                {stats.total_size_mb < 1 ? formatBytes(stats.total_size_bytes) : `${stats.total_size_mb} MB`}
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Total Size</div>
            </div>
          </div>

          {/* Collections Table */}
          <div className="card" style={{ padding: '1rem' }}>
            <h3 style={{ margin: '0 0 1rem 0', fontSize: '1rem' }}>Collections</h3>
            {stats.collections.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                <p>No collections yet. Create data in your apps to see collections here.</p>
              </div>
            ) : (
              <div className="table-container">
                <table className="apps-table">
                  <thead>
                    <tr>
                      <th>Collection Name</th>
                      <th>Documents</th>
                      <th>Size</th>
                      <th>Avg Doc Size</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.collections.map((coll) => (
                      <tr key={coll.name}>
                        <td>
                          <code style={{ fontSize: '0.875rem' }}>{coll.name}</code>
                        </td>
                        <td>{coll.document_count.toLocaleString()}</td>
                        <td>{formatBytes(coll.size_bytes)}</td>
                        <td>{coll.avg_doc_size ? formatBytes(coll.avg_doc_size) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty State */}
      {!stats && !error && !loading && (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <h2 style={{ marginBottom: '0.5rem' }}>No Database Found</h2>
          <p style={{ color: 'var(--text-muted)' }}>
            Your database will be created when you deploy an app that uses MongoDB.
          </p>
        </div>
      )}
    </div>
  )
}

export default Database
