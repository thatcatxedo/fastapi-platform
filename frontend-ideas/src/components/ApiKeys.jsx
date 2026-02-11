import React, { useState } from 'react'
import { mockApiKeys } from '../utils/mockData'
import './ApiKeys.css'

const ApiKeys = () => {
  const [keys] = useState(mockApiKeys)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showKey, setShowKey] = useState({})

  const toggleShowKey = (keyId) => {
    setShowKey(prev => ({ ...prev, [keyId]: !prev[keyId] }))
  }

  const copyToClipboard = (text) => {
    navigator.clipboard.writeText(text)
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '500' }}>API Keys</h3>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowAddModal(true)}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          + Create API Key
        </button>
      </div>

      <div className="table-container">
        <table className="apps-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Key</th>
              <th>Scopes</th>
              <th>Last Used</th>
              <th>Expires</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {keys.map(key => (
              <tr key={key.id}>
                <td style={{ fontWeight: '500' }}>{key.name}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <code style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {showKey[key.id] ? key.key : `${key.key.slice(0, 15)}...`}
                    </code>
                    <button
                      onClick={() => toggleShowKey(key.id)}
                      className="btn btn-secondary"
                      style={{ padding: '0.125rem 0.25rem', fontSize: '0.65rem' }}
                    >
                      {showKey[key.id] ? 'Hide' : 'Show'}
                    </button>
                    <button
                      onClick={() => copyToClipboard(key.key)}
                      className="btn btn-secondary"
                      style={{ padding: '0.125rem 0.25rem', fontSize: '0.65rem' }}
                    >
                      Copy
                    </button>
                  </div>
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  {key.scopes.join(', ')}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  {key.lastUsed}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  {key.expiresAt || 'Never'}
                </td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--error)' }}>
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: '1rem', fontWeight: '500' }}>Create API Key</h2>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Name</label>
              <input
                type="text"
                placeholder="My API Key"
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid var(--border)',
                  borderRadius: '0',
                  fontSize: '0.875rem'
                }}
              />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Scopes</label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {['read:apps', 'write:apps', 'read:metrics', 'write:deployments'].map(scope => (
                  <label key={scope} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input type="checkbox" defaultChecked={scope.startsWith('read')} />
                    <span style={{ fontSize: '0.875rem' }}>{scope}</span>
                  </label>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={() => setShowAddModal(false)}>
                Create Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ApiKeys
