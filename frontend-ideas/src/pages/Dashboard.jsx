import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, ExternalLink, FileText, TrendingUp, TrendingDown, Minus, Rocket, Box, AlertCircle, RefreshCw } from 'lucide-react'

const Sparkline = ({ data, color = 'var(--primary)' }) => {
  const max = Math.max(...data)
  return (
    <div className="sparkline">
      {data.map((value, i) => (
        <div
          key={i}
          className="sparkline-bar"
          style={{
            height: (value / max * 100) + '%',
            background: i === data.length - 1 ? color : undefined
          }}
        />
      ))}
    </div>
  )
}

const StatCard = ({ label, value, change, changeType, sparkData, color }) => (
  <div className="card" style={{ padding: '1.25rem' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
      <div>
        <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>{label}</div>
        <div style={{ fontSize: 'var(--font-2xl)', fontWeight: '600', color: color || 'var(--text)' }}>{value}</div>
      </div>
      {sparkData && <Sparkline data={sparkData} color={color} />}
    </div>
    {change !== undefined && (
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', fontSize: 'var(--font-xs)' }}>
        {changeType === 'up' && <TrendingUp size={12} style={{ color: 'var(--success)' }} />}
        {changeType === 'down' && <TrendingDown size={12} style={{ color: 'var(--error)' }} />}
        {changeType === 'neutral' && <Minus size={12} style={{ color: 'var(--text-muted)' }} />}
        <span style={{ color: changeType === 'up' ? 'var(--success)' : changeType === 'down' ? 'var(--error)' : 'var(--text-muted)' }}>
          {change}
        </span>
        <span style={{ color: 'var(--text-muted)' }}>vs last week</span>
      </div>
    )}
  </div>
)

const Dashboard = () => {
  const [apps] = useState([
    { app_id: 'app-1', name: 'todo-api', framework: 'FastAPI', status: 'running', deployment_url: 'https://app-1.gatorlunch.com', lastDeployed: '2 hours ago' },
    { app_id: 'app-2', name: 'weather-dashboard', framework: 'FastHTML', status: 'running', deployment_url: 'https://app-2.gatorlunch.com', lastDeployed: '1 day ago' },
    { app_id: 'app-3', name: 'kanban-board', framework: 'FastHTML', status: 'stopped', deployment_url: 'https://app-3.gatorlunch.com', lastDeployed: '3 days ago' },
  ])

  const stats = {
    total: apps.length,
    running: apps.filter(a => a.status === 'running').length,
    deploying: 0,
    error: 0
  }

  const runningApps = apps.filter(app => app.status === 'running')
  const sparkData = [3, 5, 4, 7, 6, 8, 7, 9, 8, 10, 9, 12]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '600', fontSize: 'var(--font-xl)' }}>Dashboard</h1>
        <button className="btn btn-secondary">
          <RefreshCw size={14} />
          Refresh
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <StatCard label="Total Apps" value={stats.total} sparkData={sparkData} />
        <StatCard label="Running" value={stats.running} color="var(--success)" change="+2" changeType="up" />
        <StatCard label="Deploying" value={stats.deploying} color="var(--warning)" change="0" changeType="neutral" />
        <StatCard label="Errors" value={stats.error} color={stats.error > 0 ? 'var(--error)' : undefined} change="-1" changeType="down" />
      </div>

      {runningApps.length > 0 ? (
        <div>
          <h2 style={{ fontSize: 'var(--font-md)', marginBottom: '1rem', fontWeight: '600' }}>Running Apps</h2>
          <div className="table-container">
            <table className="apps-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>URL</th>
                  <th>Last Deployed</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {runningApps.map(app => (
                  <tr key={app.app_id}>
                    <td>
                      <Link to={'/editor/' + app.app_id} style={{ fontWeight: '500', color: 'var(--text)', textDecoration: 'none' }}>
                        {app.name}
                      </Link>
                      <div style={{ fontSize: 'var(--font-xs)', color: 'var(--text-muted)' }}>{app.app_id}</div>
                    </td>
                    <td>
                      <span className="status-badge status-running">
                        <span className="status-indicator" style={{ color: 'var(--success)' }}>
                          <span className="pulse-ring"></span>
                          <span className="pulse-dot"></span>
                        </span>
                        running
                      </span>
                    </td>
                    <td>
                      <a href={app.deployment_url} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: 'var(--font-sm)' }}>
                        {app.deployment_url}
                      </a>
                    </td>
                    <td style={{ color: 'var(--text-muted)', fontSize: 'var(--font-sm)' }}>{app.lastDeployed}</td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <a href={app.deployment_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
                          <ExternalLink size={12} /> Open
                        </a>
                        <button className="btn btn-secondary btn-sm"><FileText size={12} /> Logs</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon"><Rocket size={28} /></div>
            <h3 className="empty-state-title">No Apps Running</h3>
            <p className="empty-state-description">Create your first FastAPI or FastHTML app to get started with the platform.</p>
            <Link to="/editor" className="btn btn-primary"><Plus size={16} /> Create New App</Link>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
