import { useState, useEffect, useCallback } from 'react'
import { API_URL } from '../config'
import { useToast } from '../components/Toast'

// =============================================================================
// Helpers
// =============================================================================

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function authHeaders() {
  return { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: { ...authHeaders(), ...options.headers },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail?.message || data.message || 'Request failed')
  }
  return data
}

// =============================================================================
// Sub-components
// =============================================================================

function Breadcrumb({ items }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
      {items.map((item, i) => (
        <span key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {i > 0 && <span style={{ color: 'var(--border)' }}>›</span>}
          {item.onClick ? (
            <button
              onClick={item.onClick}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0, color: 'var(--primary)', fontSize: 'inherit' }}
            >
              {item.label}
            </button>
          ) : (
            <span style={{ color: 'var(--text)' }}>{item.label}</span>
          )}
        </span>
      ))}
    </div>
  )
}

function CollectionsView({ database, onBack, onSelectCollection }) {
  const [collections, setCollections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [stats, setStats] = useState({ total_collections: 0, total_documents: 0, total_size_mb: 0 })

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      setError('')
      try {
        const data = await apiFetch(`/api/databases/${database.id}/collections`)
        if (cancelled) return
        setCollections(data.collections || [])
        setStats({
          total_collections: data.total_collections,
          total_documents: data.total_documents,
          total_size_mb: data.total_size_mb,
        })
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [database.id])

  return (
    <div>
      <Breadcrumb items={[
        { label: 'Databases', onClick: onBack },
        { label: database.name },
      ]} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h1 style={{ margin: 0 }}>{database.name}</h1>
        <button className="btn btn-secondary" onClick={() => { setLoading(true); setError(''); apiFetch(`/api/databases/${database.id}/collections`).then(data => { setCollections(data.collections || []); setStats({ total_collections: data.total_collections, total_documents: data.total_documents, total_size_mb: data.total_size_mb }); }).catch(err => setError(err.message)).finally(() => setLoading(false)) }} style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
          Refresh
        </button>
      </div>

      {!loading && !error && (
        <div style={{ marginBottom: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          {stats.total_collections} collection{stats.total_collections !== 1 ? 's' : ''} · {stats.total_documents.toLocaleString()} documents · {stats.total_size_mb} MB
        </div>
      )}

      {error && <div className="error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>Loading collections...</div>
        </div>
      ) : collections.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem', opacity: 0.3 }}>📭</div>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>No collections yet. Deploy an app that writes data to see collections here.</p>
        </div>
      ) : (
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Collection</th>
                <th style={{ textAlign: 'right' }}>Documents</th>
                <th style={{ textAlign: 'right' }}>Size</th>
                <th style={{ textAlign: 'right' }}>Avg Doc Size</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {collections.map(coll => (
                <tr key={coll.name}>
                  <td>
                    <code style={{ fontSize: '0.875rem' }}>{coll.name}</code>
                  </td>
                  <td style={{ textAlign: 'right' }}>{coll.document_count.toLocaleString()}</td>
                  <td style={{ textAlign: 'right' }}>{formatBytes(coll.size_bytes)}</td>
                  <td style={{ textAlign: 'right' }}>{coll.avg_doc_size != null ? formatBytes(coll.avg_doc_size) : '—'}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-secondary"
                      onClick={() => onSelectCollection(coll.name)}
                      style={{ padding: '0.25rem 0.6rem', fontSize: '0.8rem' }}
                    >
                      Browse
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function DocumentsView({ database, collection, onBack, onBackToList }) {
  const [documents, setDocuments] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [hasMore, setHasMore] = useState(false)
  const [sortDir, setSortDir] = useState(-1)
  const [filterText, setFilterText] = useState('')
  const [activeFilter, setActiveFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expandedDocs, setExpandedDocs] = useState(new Set())

  const fetchDocuments = useCallback(async (p, ps, sd, filt) => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({
        page: String(p),
        page_size: String(ps),
        sort_field: '_id',
        sort_dir: String(sd),
      })
      if (filt) params.set('filter', filt)

      const data = await apiFetch(
        `/api/databases/${database.id}/${encodeURIComponent(collection)}/documents?${params}`
      )
      setDocuments(data.documents || [])
      setTotal(data.total)
      setHasMore(data.has_more)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [database.id, collection])

  useEffect(() => {
    fetchDocuments(page, pageSize, sortDir, activeFilter)
  }, [page, pageSize, sortDir, activeFilter, fetchDocuments])

  const applyFilter = () => {
    setPage(1)
    setActiveFilter(filterText)
  }

  const clearFilter = () => {
    setFilterText('')
    setPage(1)
    setActiveFilter('')
  }

  const toggleDoc = (idx) => {
    setExpandedDocs(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <div>
      <Breadcrumb items={[
        { label: 'Databases', onClick: onBackToList },
        { label: database.name, onClick: onBack },
        { label: collection },
      ]} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <h1 style={{ margin: 0, fontSize: '1.25rem' }}>
          <code>{collection}</code>
          <span style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: '400', marginLeft: '0.75rem' }}>
            {total.toLocaleString()} document{total !== 1 ? 's' : ''}
          </span>
        </h1>
        <button
          className="btn btn-secondary"
          onClick={() => setSortDir(d => d === -1 ? 1 : -1)}
          style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
        >
          Sort: _id {sortDir === -1 ? '↓ newest' : '↑ oldest'}
        </button>
      </div>

      {/* Filter bar */}
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', alignItems: 'flex-start' }}>
        <textarea
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder='Filter (JSON): {"status": "active"}'
          rows={1}
          style={{
            flex: 1,
            padding: '0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '0',
            fontFamily: 'monospace',
            fontSize: '0.8rem',
            resize: 'vertical',
            minHeight: '2rem',
          }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); applyFilter() } }}
        />
        <button className="btn btn-primary" onClick={applyFilter} style={{ padding: '0.5rem 0.75rem', fontSize: '0.8rem' }}>
          Apply
        </button>
        {activeFilter && (
          <button className="btn btn-secondary" onClick={clearFilter} style={{ padding: '0.5rem 0.75rem', fontSize: '0.8rem' }}>
            Clear
          </button>
        )}
      </div>

      {error && <div className="error" style={{ marginBottom: '1rem' }}>{error}</div>}

      {loading ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)' }}>Loading documents...</div>
        </div>
      ) : documents.length === 0 ? (
        <div className="card" style={{ padding: '2rem', textAlign: 'center' }}>
          <p style={{ color: 'var(--text-muted)', margin: 0 }}>
            {activeFilter ? 'No documents match your filter.' : 'This collection is empty.'}
          </p>
        </div>
      ) : (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {documents.map((doc, idx) => {
              const expanded = expandedDocs.has(idx)
              const preview = doc._id ? `_id: ${typeof doc._id === 'object' ? JSON.stringify(doc._id) : doc._id}` : `Document ${(page - 1) * pageSize + idx + 1}`
              const keys = Object.keys(doc).filter(k => k !== '_id').slice(0, 4)
              const summaryParts = keys.map(k => {
                const v = doc[k]
                const display = typeof v === 'string' ? (v.length > 30 ? v.slice(0, 30) + '...' : v)
                  : typeof v === 'object' ? (Array.isArray(v) ? `[${v.length}]` : '{...}')
                  : String(v)
                return `${k}: ${display}`
              })

              return (
                <div key={idx} className="card" style={{ padding: 0, overflow: 'hidden' }}>
                  <button
                    onClick={() => toggleDoc(idx)}
                    style={{
                      width: '100%',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '0.6rem 1rem',
                      background: 'none',
                      border: 'none',
                      cursor: 'pointer',
                      textAlign: 'left',
                      fontSize: '0.8rem',
                      fontFamily: 'monospace',
                      color: 'var(--text)',
                    }}
                  >
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                      <span style={{ color: 'var(--primary)' }}>{preview}</span>
                      {summaryParts.length > 0 && (
                        <span style={{ color: 'var(--text-muted)', marginLeft: '1rem' }}>
                          {summaryParts.join(' · ')}
                        </span>
                      )}
                    </span>
                    <span style={{ marginLeft: '0.5rem', color: 'var(--text-muted)', flexShrink: 0 }}>
                      {expanded ? '▼' : '▶'}
                    </span>
                  </button>
                  {expanded && (
                    <pre style={{
                      margin: 0,
                      padding: '0.75rem 1rem',
                      background: 'var(--bg-light)',
                      borderTop: '1px solid var(--border)',
                      fontSize: '0.8rem',
                      lineHeight: '1.5',
                      overflow: 'auto',
                      maxHeight: '400px',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}>
                      {JSON.stringify(doc, null, 2)}
                    </pre>
                  )}
                </div>
              )
            })}
          </div>

          {/* Pagination */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Showing {(page - 1) * pageSize + 1}–{Math.min(page * pageSize, total)} of {total.toLocaleString()}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                style={{ padding: '0.3rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.8rem' }}
              >
                {[10, 20, 50, 100].map(n => (
                  <option key={n} value={n}>{n} / page</option>
                ))}
              </select>
              <button
                className="btn btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
              >
                ← Prev
              </button>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {page} / {totalPages}
              </span>
              <button
                className="btn btn-secondary"
                disabled={!hasMore}
                onClick={() => setPage(p => p + 1)}
                style={{ padding: '0.3rem 0.6rem', fontSize: '0.8rem' }}
              >
                Next →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

// =============================================================================
// Main Database page
// =============================================================================

function Database({ user }) {
  const toast = useToast()

  // Database list state
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

  // Delete confirmation
  const [deleteConfirm, setDeleteConfirm] = useState(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  // Explorer navigation
  const [selectedDatabase, setSelectedDatabase] = useState(null)
  const [selectedCollection, setSelectedCollection] = useState(null)

  const fetchDatabases = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/databases')
      setDatabases(data.databases || [])
      setTotalSize(data.total_size_mb || 0)
      setDefaultDatabaseId(data.default_database_id || 'default')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchDatabases()
  }, [fetchDatabases])

  const createDatabase = async (e) => {
    e.preventDefault()
    setCreateLoading(true)
    setCreateError('')
    try {
      await apiFetch('/api/databases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newDbName,
          description: newDbDescription || null
        })
      })
      toast.success('Database created')
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
      await apiFetch(`/api/databases/${databaseId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_default: true })
      })
      toast.success('Default database updated')
      await fetchDatabases()
    } catch (err) {
      toast.error(err.message)
    }
  }

  const deleteDatabase = async (databaseId) => {
    setDeleteLoading(true)
    try {
      await apiFetch(`/api/databases/${databaseId}`, { method: 'DELETE' })
      toast.success('Database deleted')
      setDeleteConfirm(null)
      await fetchDatabases()
    } catch (err) {
      toast.error(err.message)
      setDeleteConfirm(null)
    } finally {
      setDeleteLoading(false)
    }
  }

  // ---- Explorer drill-down views ----

  if (selectedDatabase && selectedCollection) {
    return (
      <DocumentsView
        database={selectedDatabase}
        collection={selectedCollection}
        onBack={() => setSelectedCollection(null)}
        onBackToList={() => { setSelectedCollection(null); setSelectedDatabase(null) }}
      />
    )
  }

  if (selectedDatabase) {
    return (
      <CollectionsView
        database={selectedDatabase}
        onBack={() => setSelectedDatabase(null)}
        onSelectCollection={(name) => setSelectedCollection(name)}
      />
    )
  }

  // ---- Databases list (default view) ----

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
                    onClick={() => setSelectedDatabase(db)}
                    style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}
                  >
                    Browse
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
