import { useState, useEffect } from 'react'
import { API_URL } from '../App'

function Database({ user }) {
  const [databases, setDatabases] = useState([])
  const [totalSize, setTotalSize] = useState(0)
  const [defaultDatabaseId, setDefaultDatabaseId] = useState('default')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // Create database modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newDbName, setNewDbName] = useState('')
  const [newDbDescription, setNewDbDescription] = useState('')
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState('')

  // Viewer state
  const [viewerInfo, setViewerInfo] = useState(null)
  const [viewerLoading, setViewerLoading] = useState(null) // database_id being loaded
  const [viewerError, setViewerError] = useState('')

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState(null) // database_id to delete
  const [deleteLoading, setDeleteLoading] = useState(false)

  useEffect(() => {
    fetchDatabases()
  }, [])

  const fetchDatabases = async () => {
    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.message || 'Failed to fetch databases')
      }

      const data = await response.json()
      setDatabases(data.databases || [])
      setTotalSize(data.total_size_mb || 0)
      setDefaultDatabaseId(data.default_database_id || 'default')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const createDatabase = async (e) => {
    e.preventDefault()
    setCreateLoading(true)
    setCreateError('')
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: newDbName,
          description: newDbDescription || null
        })
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail?.message || data.message || 'Failed to create database')
      }

      // Refresh list and close modal
      await fetchDatabases()
      setShowCreateModal(false)
      setNewDbName('')
      setNewDbDescription('')
    } catch (err) {
      setCreateError(err.message)
    } finally {
      setCreateLoading(false)
    }
  }

  const setAsDefault = async (databaseId) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases/${databaseId}`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_default: true })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.message || 'Failed to set default')
      }

      await fetchDatabases()
    } catch (err) {
      setError(err.message)
    }
  }

  const deleteDatabase = async (databaseId) => {
    setDeleteLoading(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases/${databaseId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.message || 'Failed to delete database')
      }

      setDeleteConfirm(null)
      await fetchDatabases()
    } catch (err) {
      setError(err.message)
      setDeleteConfirm(null)
    } finally {
      setDeleteLoading(false)
    }
  }

  const launchViewer = async (databaseId) => {
    setViewerLoading(databaseId)
    setViewerError('')
    setViewerInfo(null)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases/${databaseId}/viewer`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail?.message || data.message || 'Failed to open viewer')
      }

      setViewerInfo(data)
      if (data.ready === undefined || data.ready) {
        window.open(data.url, '_blank', 'noopener,noreferrer')
      }
    } catch (err) {
      setViewerError(err.message)
    } finally {
      setViewerLoading(null)
    }
  }

  if (loading) {
    return (
      <div>
        <h1 style={{ marginBottom: '1.5rem' }}>Databases</h1>
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>Loading databases...</div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1>Databases</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            className="btn btn-secondary"
            onClick={fetchDatabases}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Refresh
          </button>
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateModal(true)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            + New Database
          </button>
        </div>
      </div>

      {error && <div className="error" style={{ marginBottom: '1rem' }}>{error}</div>}
      {viewerError && <div className="error" style={{ marginBottom: '1rem' }}>{viewerError}</div>}

      {/* Viewer Info Banner */}
      {viewerInfo && (
        <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-light)' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', fontSize: '0.875rem' }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Viewer URL:</span>{' '}
              <a href={viewerInfo.url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)' }}>
                {viewerInfo.url}
              </a>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Username:</span> <code>{viewerInfo.username}</code>
            </div>
            {viewerInfo.password_provided && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Password:</span> <code>{viewerInfo.password}</code>
              </div>
            )}
            <button
              onClick={() => setViewerInfo(null)}
              style={{ marginLeft: 'auto', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
            >
              ×
            </button>
          </div>
          {viewerInfo.ready === false && (
            <div style={{ marginTop: '0.5rem', color: 'var(--warning)', fontSize: '0.8rem' }}>
              Viewer is starting up... Please wait a moment and try again.
            </div>
          )}
        </div>
      )}

      {/* Total Size Summary */}
      <div style={{ marginBottom: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        {databases.length} database{databases.length !== 1 ? 's' : ''} · {totalSize} MB total
      </div>

      {/* Database Cards */}
      {databases.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <h2 style={{ marginBottom: '0.5rem' }}>No Databases</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Create your first database to get started.
          </p>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            + New Database
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {databases.map((db) => (
            <div key={db.id} className="card" style={{ padding: '1rem 1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    {db.is_default && <span style={{ color: 'var(--warning)' }}>★</span>}
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>{db.name}</h3>
                    {db.is_default && (
                      <span style={{ fontSize: '0.75rem', padding: '0.125rem 0.5rem', background: 'var(--bg-light)', borderRadius: '0', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                        Default
                      </span>
                    )}
                  </div>
                  {db.description && (
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                      {db.description}
                    </p>
                  )}
                  <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    {db.total_collections} collection{db.total_collections !== 1 ? 's' : ''} · {db.total_documents.toLocaleString()} documents · {db.total_size_mb} MB
                  </div>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {db.mongo_database}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-primary"
                    onClick={() => launchViewer(db.id)}
                    disabled={viewerLoading === db.id}
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    {viewerLoading === db.id ? 'Opening...' : 'View'}
                  </button>
                  {!db.is_default && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => setAsDefault(db.id)}
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                    >
                      Set Default
                    </button>
                  )}
                  {!db.is_default && databases.length > 1 && (
                    <button
                      className="btn btn-secondary"
                      onClick={() => setDeleteConfirm(db.id)}
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', color: 'var(--error)' }}
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>

              {/* Delete Confirmation */}
              {deleteConfirm === db.id && (
                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '0', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
                  <span style={{ fontSize: '0.875rem' }}>Delete "{db.name}"? This cannot be undone.</span>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => setDeleteConfirm(null)}
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                    >
                      Cancel
                    </button>
                    <button
                      className="btn"
                      onClick={() => deleteDatabase(db.id)}
                      disabled={deleteLoading}
                      style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem', background: 'var(--error)', color: 'white' }}
                    >
                      {deleteLoading ? 'Deleting...' : 'Delete'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Create Database Modal */}
      {showCreateModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div className="card" style={{ width: '100%', maxWidth: '400px', margin: '1rem', padding: '1.5rem' }}>
            <h2 style={{ margin: '0 0 1rem 0', fontSize: '1.25rem', fontWeight: '500' }}>New Database</h2>
            {createError && <div className="error" style={{ marginBottom: '1rem' }}>{createError}</div>}
            <form onSubmit={createDatabase}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem', fontWeight: '500' }}>
                  Name
                </label>
                <input
                  type="text"
                  value={newDbName}
                  onChange={(e) => setNewDbName(e.target.value)}
                  placeholder="e.g., Production"
                  required
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0', border: '1px solid var(--border)' }}
                />
              </div>
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.25rem', fontSize: '0.875rem', fontWeight: '400' }}>
                  Description (optional)
                </label>
                <input
                  type="text"
                  value={newDbDescription}
                  onChange={(e) => setNewDbDescription(e.target.value)}
                  placeholder="e.g., Production database for live apps"
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0', border: '1px solid var(--border)' }}
                />
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => {
                    setShowCreateModal(false)
                    setNewDbName('')
                    setNewDbDescription('')
                    setCreateError('')
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createLoading || !newDbName.trim()}
                >
                  {createLoading ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Database
