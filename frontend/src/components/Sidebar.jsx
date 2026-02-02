import { NavLink, useParams } from 'react-router-dom'
import { useApps } from '../context/AppsContext'

function Sidebar({ user, onLogout }) {
  const { apps, loading } = useApps()
  const { appId: currentAppId } = useParams()

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'var(--success)'
      case 'deploying': return 'var(--warning)'
      case 'error': return 'var(--error)'
      default: return 'var(--text-muted)'
    }
  }

  return (
    <aside className="ide-sidebar">
      {/* Logo/Brand */}
      <div className="sidebar-header">
        <NavLink to="/editor" className="sidebar-logo">
          FastAPI Platform
        </NavLink>
      </div>

      {/* New App Button */}
      <div className="sidebar-section">
        <NavLink to="/editor" className="btn btn-primary sidebar-new-app">
          + New App
        </NavLink>
      </div>

      {/* Apps List */}
      <div className="sidebar-section sidebar-apps">
        <div className="sidebar-section-title">Your Apps</div>
        <div className="sidebar-apps-list">
          {loading ? (
            <div className="sidebar-loading">Loading...</div>
          ) : apps.length === 0 ? (
            <div className="sidebar-empty">No apps yet</div>
          ) : (
            apps.map(app => (
              <NavLink
                key={app.app_id}
                to={`/editor/${app.app_id}`}
                className={({ isActive }) => 
                  `sidebar-app-item ${isActive ? 'active' : ''}`
                }
              >
                <span 
                  className="sidebar-app-status"
                  style={{ backgroundColor: getStatusColor(app.status) }}
                  title={app.status}
                />
                <span className="sidebar-app-name">{app.name}</span>
              </NavLink>
            ))
          )}
        </div>
      </div>

      {/* Navigation Links */}
      <div className="sidebar-section sidebar-nav">
        <div className="sidebar-section-title">Navigation</div>
        <NavLink
          to="/dashboard"
          className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
        >
          <span className="sidebar-nav-icon">📊</span>
          Dashboard
        </NavLink>
        <NavLink
          to="/database"
          className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
        >
          <span className="sidebar-nav-icon">🗄️</span>
          Database
        </NavLink>
        {user?.is_admin && (
          <NavLink 
            to="/admin" 
            className={({ isActive }) => `sidebar-nav-item ${isActive ? 'active' : ''}`}
          >
            <span className="sidebar-nav-icon">⚙️</span>
            Admin
          </NavLink>
        )}
      </div>

      {/* User Section */}
      <div className="sidebar-user">
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{user?.username}</span>
          {user?.is_admin && <span className="sidebar-user-badge">Admin</span>}
        </div>
        <button 
          className="btn btn-secondary sidebar-logout"
          onClick={onLogout}
        >
          Logout
        </button>
      </div>
    </aside>
  )
}

export default Sidebar
