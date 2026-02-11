import React from 'react'
import { NavLink } from 'react-router-dom'
import { Sun, Moon, Search, LayoutDashboard, Database, Activity, Rocket, Settings, Shield, BarChart3, Zap, TestTube, BookOpen, CreditCard, Globe, Users, User } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'
import NotificationCenter from './NotificationCenter'

const Sidebar = ({ user, apps = [], onOpenCommandPalette }) => {
  const { theme, toggleTheme } = useTheme()

  const getStatusColor = (status) => {
    switch (status) {
      case 'running': return 'var(--success)'
      case 'deploying': return 'var(--warning)'
      case 'error': return 'var(--error)'
      default: return 'var(--text-muted)'
    }
  }

  const navSections = [
    {
      title: 'Navigation',
      items: [
        { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
        { to: '/database', icon: Database, label: 'Database' },
      ]
    },
    {
      title: 'Monitoring',
      items: [
        { to: '/activity', icon: Activity, label: 'Activity' },
        { to: '/deployments', icon: Rocket, label: 'Deployments' },
      ]
    },
    {
      title: 'Analytics',
      items: [
        { to: '/analytics', icon: BarChart3, label: 'Usage' },
        { to: '/performance', icon: Zap, label: 'Performance' },
      ]
    },
    {
      title: 'Settings',
      items: [
        { to: '/settings', icon: Settings, label: 'Settings' },
        { to: '/security', icon: Shield, label: 'Security' },
      ]
    },
  ]

  return (
    <aside className="ide-sidebar">
      <div className="sidebar-header">
        <NavLink to="/dashboard" className="sidebar-logo">
          FastAPI Platform
        </NavLink>
        <div style={{ display: 'flex', gap: '0.25rem' }}>
          <NotificationCenter />
          <button className="theme-toggle" onClick={toggleTheme} aria-label="Toggle theme">
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
        </div>
      </div>

      <div className="sidebar-section">
        <NavLink to="/editor" className="btn btn-primary sidebar-new-app">
          + New App
        </NavLink>
      </div>

      <div className="sidebar-section sidebar-apps">
        <div className="sidebar-section-title">Your Apps</div>
        <div className="sidebar-apps-list">
          {apps.length === 0 ? (
            <div className="sidebar-empty">No apps yet</div>
          ) : (
            apps.map(app => (
              <NavLink
                key={app.app_id}
                to={'/editor/' + app.app_id}
                className={({ isActive }) => 'sidebar-app-item' + (isActive ? ' active' : '')}
              >
                {app.status === 'running' ? (
                  <span className="status-indicator" style={{ color: getStatusColor(app.status) }}>
                    <span className="pulse-ring"></span>
                    <span className="pulse-dot"></span>
                  </span>
                ) : (
                  <span className="sidebar-app-status" style={{ backgroundColor: getStatusColor(app.status) }} />
                )}
                <span className="sidebar-app-name">{app.name}</span>
              </NavLink>
            ))
          )}
        </div>
      </div>

      <div className="sidebar-scrollable">
        {navSections.map(section => (
          <div key={section.title} className="sidebar-section sidebar-nav">
            <div className="sidebar-section-title">{section.title}</div>
            {section.items.map(item => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => 'sidebar-nav-item' + (isActive ? ' active' : '')}
              >
                <item.icon size={18} className="sidebar-nav-icon" />
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="sidebar-footer">
        <button className="sidebar-search-trigger" onClick={onOpenCommandPalette}>
          <Search size={14} />
          <span>Search...</span>
          <kbd>⌘K</kbd>
        </button>
      </div>

      <div className="sidebar-user">
        <div className="sidebar-user-info">
          <span className="sidebar-user-name">{user?.username || 'demo'}</span>
          {user?.is_admin && <span className="sidebar-user-badge">Admin</span>}
        </div>
        <button className="btn btn-secondary sidebar-logout">Logout</button>
      </div>
    </aside>
  )
}

export default Sidebar
