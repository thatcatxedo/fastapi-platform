import { useState, useEffect } from 'react'
import { API_URL } from '../config'

function Admin({ user }) {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [settings, setSettings] = useState({ allow_signups: true, allowed_imports: [] })
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createUserData, setCreateUserData] = useState({ username: '', email: '', password: '' })
  const [createError, setCreateError] = useState('')
  const [createLoading, setCreateLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(null)
  const [adminToggleLoading, setAdminToggleLoading] = useState(null)
  const [allowedImportsText, setAllowedImportsText] = useState('')
  const [allowedImportsSaving, setAllowedImportsSaving] = useState(false)
  const [allowedImportsError, setAllowedImportsError] = useState('')
  const [adminTemplates, setAdminTemplates] = useState([])
  const [templatesLoading, setTemplatesLoading] = useState(true)

  useEffect(() => {
    fetchStats()
    fetchUsers()
    fetchSettings()
    fetchAdminTemplates()
  }, [])

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchUsers = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setUsers(data)
      }
    } catch (err) {
      console.error('Failed to fetch users:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/settings`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
        setAllowedImportsText((data.allowed_imports || []).join('\n'))
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    }
  }

  const fetchAdminTemplates = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        setAdminTemplates(await response.json())
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    } finally {
      setTemplatesLoading(false)
    }
  }

  const handleToggleTemplateVisibility = async (template) => {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_URL}/api/admin/templates/${template.id}`, {
      method: 'PUT',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ is_hidden: !template.is_hidden })
    })
    if (response.ok) {
      fetchAdminTemplates()
    }
  }

  const handleDeleteTemplate = async (template) => {
    if (!confirm(`Delete template "${template.name}"? This cannot be undone.`)) return
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_URL}/api/admin/templates/${template.id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (response.ok) {
      fetchAdminTemplates()
      fetchStats()
    }
  }

  const updateSettings = async (payload) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
      })
      if (response.ok) {
        setSettings(payload)
        if (payload.allowed_imports) {
          setAllowedImportsText(payload.allowed_imports.join('\n'))
        }
        return true
      } else {
        const data = await response.json()
        alert(data.detail?.message || 'Failed to update settings')
        return false
      }
    } catch (err) {
      alert('Failed to update settings')
      return false
    }
  }

  const handleCreateUser = async (e) => {
    e.preventDefault()
    setCreateError('')
    setCreateLoading(true)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/users`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(createUserData)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to create user')
      }

      setCreateUserData({ username: '', email: '', password: '' })
      setShowCreateForm(false)
      fetchUsers()
      fetchStats()
    } catch (err) {
      setCreateError(err.message)
    } finally {
      setCreateLoading(false)
    }
  }

  const handleDeleteUser = async (userId) => {
    if (!confirm('Are you sure you want to delete this user? This will delete all their apps and data.')) {
      return
    }

    setDeleteLoading(userId)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail?.message || 'Failed to delete user')
      }

      fetchUsers()
      fetchStats()
    } catch (err) {
      alert(err.message || 'Failed to delete user')
    } finally {
      setDeleteLoading(null)
    }
  }

  const handleToggleAdmin = async (userId, currentIsAdmin) => {
    const action = currentIsAdmin ? 'remove admin privileges from' : 'grant admin privileges to'
    if (!confirm(`Are you sure you want to ${action} this user?`)) {
      return
    }

    setAdminToggleLoading(userId)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/users/${userId}/admin`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ is_admin: !currentIsAdmin })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail?.message || 'Failed to update admin status')
      }

      fetchUsers()
    } catch (err) {
      alert(err.message || 'Failed to update admin status')
    } finally {
      setAdminToggleLoading(null)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString()
  }

  const parseAllowedImports = (value) => {
    const entries = value
      .split('\n')
      .map((line) => line.trim().toLowerCase())
      .filter(Boolean)
    return Array.from(new Set(entries))
  }

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ margin: 0, fontWeight: '400' }}>Admin Dashboard</h1>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', fontSize: '0.9rem' }}>
          <input
            type="checkbox"
            checked={settings.allow_signups}
            onChange={(e) => updateSettings({
              allow_signups: e.target.checked,
              allowed_imports: parseAllowedImports(allowedImportsText)
            })}
          />
          <span>Allow Signups</span>
        </label>
      </div>

      <div className="card" style={{ padding: '1rem', marginBottom: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.05rem', fontWeight: '500' }}>Allowed Imports</h2>
          <button
            className="btn btn-primary"
            disabled={allowedImportsSaving}
            onClick={async () => {
              setAllowedImportsError('')
              const allowedImports = parseAllowedImports(allowedImportsText)
              if (allowedImports.length === 0) {
                setAllowedImportsError('Provide at least one module name.')
                return
              }
              setAllowedImportsSaving(true)
              const ok = await updateSettings({
                allow_signups: settings.allow_signups,
                allowed_imports: allowedImports
              })
              if (!ok) {
                setAllowedImportsError('Failed to update allowed imports.')
              }
              setAllowedImportsSaving(false)
            }}
          >
            {allowedImportsSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
        <textarea
          rows={6}
          value={allowedImportsText}
          onChange={(e) => setAllowedImportsText(e.target.value)}
          placeholder="one.module.per.line"
          style={{ width: '100%', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace', fontSize: '0.85rem' }}
        />
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          One module per line. Changes apply to all new validations.
        </div>
        {allowedImportsError && (
          <div className="error" style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>
            {allowedImportsError}
          </div>
        )}
      </div>

      {/* Stats Row - All in one line */}
      {stats && (
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
          <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: '600' }}>{stats.users}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Users</div>
          </div>
          <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: '500' }}>{stats.apps}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Apps</div>
          </div>
          <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: '600', color: 'var(--success)' }}>{stats.running_apps}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Running</div>
          </div>
          <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.75rem', fontWeight: '500' }}>{stats.templates}</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Templates</div>
          </div>
          {stats.mongo && !stats.mongo.error && (
            <>
              <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.75rem', fontWeight: '600' }}>{stats.mongo.user_databases}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>User DBs</div>
              </div>
              <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.75rem', fontWeight: '500' }}>{stats.mongo.total_storage_mb}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>User MB</div>
              </div>
              <div className="card" style={{ flex: '1', minWidth: '120px', padding: '1rem', textAlign: 'center' }}>
                <div style={{ fontSize: '1.75rem', fontWeight: '600' }}>{stats.mongo.total_documents}</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Documents</div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Two column layout: Users table + Activity sidebar */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '1.5rem' }}>
        {/* Users Table */}
        <div className="card" style={{ padding: '1rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>Users ({users.length})</h2>
            {!settings.allow_signups && (
              <button
                className="btn btn-secondary"
                onClick={() => setShowCreateForm(!showCreateForm)}
                style={{ fontSize: '0.8rem', padding: '0.25rem 0.75rem' }}
              >
                {showCreateForm ? 'Cancel' : '+ Add User'}
              </button>
            )}
          </div>

          {showCreateForm && (
            <form onSubmit={handleCreateUser} style={{ marginBottom: '1rem', padding: '0.75rem', background: 'var(--bg-light)', borderRadius: '0', border: '1px solid var(--border)' }}>
              {createError && <div className="error" style={{ marginBottom: '0.5rem', fontSize: '0.85rem' }}>{createError}</div>}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '0.5rem', alignItems: 'end' }}>
                <input
                  type="text"
                  placeholder="Username"
                  value={createUserData.username}
                  onChange={(e) => setCreateUserData({ ...createUserData, username: e.target.value })}
                  required
                  style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                />
                <input
                  type="email"
                  placeholder="Email"
                  value={createUserData.email}
                  onChange={(e) => setCreateUserData({ ...createUserData, email: e.target.value })}
                  required
                  style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={createUserData.password}
                  onChange={(e) => setCreateUserData({ ...createUserData, password: e.target.value })}
                  required
                  style={{ padding: '0.4rem', fontSize: '0.85rem' }}
                />
                <button type="submit" className="btn btn-primary" disabled={createLoading} style={{ padding: '0.4rem 0.75rem', fontSize: '0.85rem' }}>
                  {createLoading ? '...' : 'Create'}
                </button>
              </div>
            </form>
          )}

          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: '600' }}>Username</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: '600' }}>Email</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Apps</th>
                  <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: '600' }}>Created</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Role</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '0.5rem' }}>
                      {u.username}
                      {u.id === user.id && <span style={{ marginLeft: '0.4rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>(you)</span>}
                    </td>
                    <td style={{ padding: '0.5rem', color: 'var(--text-muted)' }}>{u.email}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      {u.app_count}
                      {u.running_app_count > 0 && <span style={{ color: 'var(--success)', marginLeft: '0.25rem' }}>({u.running_app_count})</span>}
                    </td>
                    <td style={{ padding: '0.5rem', color: 'var(--text-muted)' }}>{formatDate(u.created_at)}</td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      {u.id !== user.id ? (
                        <button
                          onClick={() => handleToggleAdmin(u.id, u.is_admin)}
                          disabled={adminToggleLoading === u.id}
                          title={u.is_admin ? 'Remove admin privileges' : 'Grant admin privileges'}
                          style={{
                            background: 'none',
                            border: '1px solid var(--border)',
                            borderRadius: '0',
                            padding: '0.15rem 0.4rem',
                            cursor: 'pointer',
                            fontSize: '0.75rem',
                            color: u.is_admin ? 'var(--primary)' : 'var(--text-muted)'
                          }}
                        >
                          {adminToggleLoading === u.id ? '...' : (u.is_admin ? 'Admin' : 'User')}
                        </button>
                      ) : (
                        <span style={{ padding: '0.15rem 0.4rem', background: 'var(--primary)', color: 'white', borderRadius: '0', fontSize: '0.75rem' }}>Admin</span>
                      )}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      {u.id !== user.id && (
                        <button
                          onClick={() => handleDeleteUser(u.id)}
                          disabled={deleteLoading === u.id}
                          title="Delete user"
                          style={{ background: 'none', border: 'none', color: 'var(--error)', cursor: 'pointer', fontSize: '0.8rem' }}
                        >
                          {deleteLoading === u.id ? '...' : '✕'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Activity Sidebar */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {stats?.recent_signups?.length > 0 && (
            <div className="card" style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: '500' }}>Recent Signups</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem' }}>
                {stats.recent_signups.slice(0, 5).map((signup, idx) => (
                  <li key={idx} style={{ padding: '0.35rem 0', borderBottom: idx < Math.min(stats.recent_signups.length, 5) - 1 ? '1px solid var(--border)' : 'none' }}>
                    <strong>{signup.username}</strong>
                    <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.8rem' }}>{formatDate(signup.created_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {stats?.recent_deploys?.length > 0 && (
            <div className="card" style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: '500' }}>Recent Deploys</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: '0.85rem' }}>
                {stats.recent_deploys.slice(0, 5).map((deploy, idx) => (
                  <li key={idx} style={{ padding: '0.35rem 0', borderBottom: idx < Math.min(stats.recent_deploys.length, 5) - 1 ? '1px solid var(--border)' : 'none' }}>
                    <strong style={{ wordBreak: 'break-all', fontWeight: '500' }}>{deploy.name}</strong>
                    <span style={{ color: 'var(--text-muted)', marginLeft: '0.5rem', fontSize: '0.8rem' }}>{formatDate(deploy.created_at)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {stats?.mongo && !stats.mongo.error && (
            <div className="card" style={{ padding: '1rem' }}>
              <h3 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: '500' }}>MongoDB</h3>
              <div style={{ fontSize: '0.85rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Platform DB</span>
                  <span>{stats.mongo.platform_storage_mb} MB</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                  <span style={{ color: 'var(--text-muted)' }}>User Data</span>
                  <span>{stats.mongo.total_storage_mb} MB</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.25rem 0' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Collections</span>
                  <span>{stats.mongo.total_collections}</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Templates Management */}
      <div className="card" style={{ padding: '1rem', marginTop: '1.5rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>
            Templates ({adminTemplates.length})
          </h2>
        </div>

        {templatesLoading ? (
          <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>Loading templates...</div>
        ) : adminTemplates.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--text-muted)' }}>No templates found.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid var(--border)' }}>
                  <th style={{ textAlign: 'left', padding: '0.5rem', fontWeight: '600' }}>Name</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Type</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Mode</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Complexity</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}>Visible</th>
                  <th style={{ textAlign: 'center', padding: '0.5rem', fontWeight: '600' }}></th>
                </tr>
              </thead>
              <tbody>
                {adminTemplates.map((t) => (
                  <tr key={t.id} style={{ borderBottom: '1px solid var(--border)', opacity: t.is_hidden ? 0.5 : 1 }}>
                    <td style={{ padding: '0.5rem' }}>
                      <div style={{ fontWeight: '500' }}>{t.name}</div>
                      {t.description && (
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {t.description}
                        </div>
                      )}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '0.25rem',
                        background: t.is_global ? 'rgba(59, 130, 246, 0.1)' : 'var(--bg-light)',
                        color: t.is_global ? '#3b82f6' : 'var(--text-muted)',
                        border: `1px solid ${t.is_global ? 'rgba(59, 130, 246, 0.3)' : 'var(--border)'}`
                      }}>
                        {t.is_global ? 'Global' : 'User'}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {t.mode === 'multi' ? `Multi (${t.framework || '?'})` : 'Single'}
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.1rem 0.4rem',
                        borderRadius: '0.25rem',
                        background: t.complexity === 'simple' ? '#10b981' : t.complexity === 'medium' ? '#f59e0b' : '#ef4444',
                        color: 'white'
                      }}>
                        {t.complexity}
                      </span>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <button
                        onClick={() => handleToggleTemplateVisibility(t)}
                        style={{
                          background: 'none',
                          border: '1px solid var(--border)',
                          borderRadius: '0',
                          padding: '0.15rem 0.5rem',
                          cursor: 'pointer',
                          fontSize: '0.75rem',
                          color: t.is_hidden ? 'var(--error)' : 'var(--success)'
                        }}
                        title={t.is_hidden ? 'Show template' : 'Hide template'}
                      >
                        {t.is_hidden ? 'Hidden' : 'Visible'}
                      </button>
                    </td>
                    <td style={{ padding: '0.5rem', textAlign: 'center' }}>
                      <button
                        onClick={() => handleDeleteTemplate(t)}
                        title="Delete template"
                        style={{ background: 'none', border: 'none', color: 'var(--error)', cursor: 'pointer', fontSize: '0.8rem' }}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Admin
