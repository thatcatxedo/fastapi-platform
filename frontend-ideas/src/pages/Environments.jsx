import React, { useState } from 'react'
import './Environments.css'

const Environments = () => {
  const [environments] = useState([
    {
      id: 'env-1',
      name: 'Production',
      branch: 'main',
      url: 'https://app-1.gatorlunch.com',
      status: 'running',
      lastDeployed: '2 hours ago'
    },
    {
      id: 'env-2',
      name: 'Staging',
      branch: 'develop',
      url: 'https://staging-app-1.gatorlunch.com',
      status: 'running',
      lastDeployed: '1 day ago'
    },
    {
      id: 'env-3',
      name: 'Preview (PR #42)',
      branch: 'feature/auth',
      url: 'https://pr-42-app-1.gatorlunch.com',
      status: 'running',
      lastDeployed: '3 hours ago'
    }
  ])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Environments</h1>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          + Create Environment
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {environments.map(env => (
          <div key={env.id} className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <div>
                <h2 style={{ fontSize: '1.1rem', fontWeight: '500', marginBottom: '0.25rem' }}>{env.name}</h2>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Branch: {env.branch}
                </div>
              </div>
              <span className="status-badge status-running">{env.status}</span>
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <a 
                href={env.url} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.875rem' }}
              >
                {env.url}
              </a>
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Last deployed: {env.lastDeployed}
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <a href={env.url} target="_blank" rel="noopener noreferrer" className="btn btn-primary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
                Open
              </a>
              <button className="btn btn-secondary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
                Configure
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Environment Types</h2>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Type</th>
                <th>Purpose</th>
                <th>Auto-deploy</th>
                <th>Cost</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ fontWeight: '500' }}>Production</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Live user traffic</td>
                <td><span className="status-badge status-running">Enabled</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Full</td>
              </tr>
              <tr>
                <td style={{ fontWeight: '500' }}>Staging</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Pre-production testing</td>
                <td><span className="status-badge status-running">Enabled</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Full</td>
              </tr>
              <tr>
                <td style={{ fontWeight: '500' }}>Preview</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Pull request previews</td>
                <td><span className="status-badge status-running">Enabled</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Reduced</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Environments
