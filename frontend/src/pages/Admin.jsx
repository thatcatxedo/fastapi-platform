import { useState, useEffect } from 'react'
import { API_URL } from '../App'

function Admin({ user }) {
  const [stats, setStats] = useState(null)
  const [users, setUsers] = useState([])
  const [settings, setSettings] = useState({ allow_signups: true })
  const [loading, setLoading] = useState(true)
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [createUserData, setCreateUserData] = useState({ username: '', email: '', password: '' })
  const [createError, setCreateError] = useState('')
  const [createLoading, setCreateLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(null)

  useEffect(() => {
    fetchStats()
    fetchUsers()
    fetchSettings()
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
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err)
    }
  }

  const updateSettings = async (allowSignups) => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/admin/settings`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ allow_signups: allowSignups })
      })
      if (response.ok) {
        setSettings({ allow_signups: allowSignups })
      } else {
        const data = await response.json()
        alert(data.detail?.message || 'Failed to update settings')
      }
    } catch (err) {
      alert('Failed to update settings')
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

      // Reset form and refresh users list
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

      // Refresh users and stats
      fetchUsers()
      fetchStats()
    } catch (err) {
      alert(err.message || 'Failed to delete user')
    } finally {
      setDeleteLoading(null)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  if (loading) {
    return <div className="loading">Loading...</div>
  }

  return (
    <div className="container" style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
      <h1 style={{ marginBottom: '2rem' }}>Admin Dashboard</h1>

      {/* Settings Card */}
      <div className="card" style={{ marginBottom: '2rem' }}>
        <h2>Platform Settings</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={settings.allow_signups}
              onChange={(e) => updateSettings(e.target.checked)}
            />
            <span>Allow Public Signups</span>
          </label>
        </div>
        {!settings.allow_signups && (
          <div style={{ marginTop: '1rem' }}>
            <button
              className="btn btn-secondary"
              onClick={() => setShowCreateForm(!showCreateForm)}
              style={{ fontSize: '0.875rem' }}
            >
              {showCreateForm ? 'Hide' : 'Create User Manually'}
            </button>
            {showCreateForm && (
              <form onSubmit={handleCreateUser} style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-secondary)', borderRadius: '4px' }}>
                {createError && <div className="error" style={{ marginBottom: '1rem' }}>{createError}</div>}
                <div className="form-group">
                  <label>Username</label>
                  <input
                    type="text"
                    value={createUserData.username}
                    onChange={(e) => setCreateUserData({ ...createUserData, username: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Email</label>
                  <input
                    type="email"
                    value={createUserData.email}
                    onChange={(e) => setCreateUserData({ ...createUserData, email: e.target.value })}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    value={createUserData.password}
                    onChange={(e) => setCreateUserData({ ...createUserData, password: e.target.value })}
                    required
                  />
                </div>
                <button type="submit" className="btn btn-primary" disabled={createLoading}>
                  {createLoading ? 'Creating...' : 'Create User'}
                </button>
              </form>
            )}
          </div>
        )}
      </div>

      {/* Stats Cards */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          <div className="card">
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem' }}>{stats.users}</h3>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>Total Users</p>
          </div>
          <div className="card">
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem' }}>{stats.apps}</h3>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>Total Apps</p>
          </div>
          <div className="card">
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem' }}>{stats.running_apps}</h3>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>Running Apps</p>
          </div>
          <div className="card">
            <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem' }}>{stats.templates}</h3>
            <p style={{ margin: 0, color: 'var(--text-muted)' }}>Templates</p>
          </div>
        </div>
      )}

      {/* Recent Activity */}
      {stats && (stats.recent_signups.length > 0 || stats.recent_deploys.length > 0) && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
          {stats.recent_signups.length > 0 && (
            <div className="card">
              <h3>Recent Signups</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {stats.recent_signups.map((signup, idx) => (
                  <li key={idx} style={{ padding: '0.5rem 0', borderBottom: idx < stats.recent_signups.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <strong>{signup.username}</strong>
                    <br />
                    <small style={{ color: 'var(--text-muted)' }}>{formatDate(signup.created_at)}</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {stats.recent_deploys.length > 0 && (
            <div className="card">
              <h3>Recent Deploys</h3>
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {stats.recent_deploys.map((deploy, idx) => (
                  <li key={idx} style={{ padding: '0.5rem 0', borderBottom: idx < stats.recent_deploys.length - 1 ? '1px solid var(--border)' : 'none' }}>
                    <strong>{deploy.name}</strong>
                    <br />
                    <small style={{ color: 'var(--text-muted)' }}>{formatDate(deploy.created_at)}</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Users Table */}
      <div className="card">
        <h2>Users</h2>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--border)' }}>
                <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: '600' }}>Username</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: '600' }}>Email</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: '600' }}>Apps (Running)</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: '600' }}>Created</th>
                <th style={{ textAlign: 'left', padding: '0.75rem', fontWeight: '600' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid var(--border)' }}>
                  <td style={{ padding: '0.75rem' }}>
                    {u.username}
                    {u.is_admin && <span style={{ marginLeft: '0.5rem', padding: '0.125rem 0.5rem', background: 'var(--primary)', color: 'white', borderRadius: '4px', fontSize: '0.75rem' }}>Admin</span>}
                  </td>
                  <td style={{ padding: '0.75rem' }}>{u.email}</td>
                  <td style={{ padding: '0.75rem' }}>{u.app_count} <span style={{ color: 'var(--text-muted)' }}>({u.running_app_count} running)</span></td>
                  <td style={{ padding: '0.75rem', color: 'var(--text-muted)' }}>{formatDate(u.created_at)}</td>
                  <td style={{ padding: '0.75rem' }}>
                    {u.id !== user.id ? (
                      <button
                        className="btn btn-secondary"
                        onClick={() => handleDeleteUser(u.id)}
                        disabled={deleteLoading === u.id}
                        style={{ fontSize: '0.875rem', padding: '0.25rem 0.75rem' }}
                      >
                        {deleteLoading === u.id ? 'Deleting...' : 'Delete'}
                      </button>
                    ) : (
                      <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>You</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Admin
