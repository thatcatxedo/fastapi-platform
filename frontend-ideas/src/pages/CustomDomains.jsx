import React, { useState } from 'react'
import './CustomDomains.css'

const CustomDomains = () => {
  const [domains] = useState([
    {
      id: 'domain-1',
      domain: 'api.example.com',
      app: 'todo-api',
      status: 'active',
      ssl: 'valid',
      verified: true
    },
    {
      id: 'domain-2',
      domain: 'dashboard.example.com',
      app: 'weather-dashboard',
      status: 'pending',
      ssl: 'pending',
      verified: false
    }
  ])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Custom Domains</h1>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          + Add Domain
        </button>
      </div>

      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Domain</th>
                <th>App</th>
                <th>Status</th>
                <th>SSL</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {domains.map(domain => (
                <tr key={domain.id}>
                  <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {domain.domain}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {domain.app}
                  </td>
                  <td>
                    <span className="status-badge" style={{ 
                      backgroundColor: domain.status === 'active' ? 'var(--success)' : 'var(--warning)'
                    }}>
                      {domain.status}
                    </span>
                  </td>
                  <td>
                    <span className="status-badge" style={{ 
                      backgroundColor: domain.ssl === 'valid' ? 'var(--success)' : 'var(--warning)'
                    }}>
                      {domain.ssl}
                    </span>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      {!domain.verified && (
                        <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                          Verify
                        </button>
                      )}
                      <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                        Configure
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>DNS Configuration</h2>
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
          To connect a custom domain, add the following DNS records:
        </div>
        <div style={{ padding: '1rem', background: 'var(--bg-light)', border: '1px solid var(--border)', borderRadius: '0', fontFamily: 'monospace', fontSize: '0.875rem' }}>
          <div style={{ marginBottom: '0.5rem' }}>
            <strong>Type:</strong> CNAME
          </div>
          <div style={{ marginBottom: '0.5rem' }}>
            <strong>Name:</strong> api.example.com
          </div>
          <div>
            <strong>Value:</strong> app-abc123.gatorlunch.com
          </div>
        </div>
      </div>
    </div>
  )
}

export default CustomDomains
