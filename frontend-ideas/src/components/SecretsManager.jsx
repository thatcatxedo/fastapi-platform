import React, { useState } from 'react'
import { mockSecrets } from '../utils/mockData'
import './SecretsManager.css'

const SecretsManager = () => {
  const [secrets] = useState(mockSecrets)
  const [showAddModal, setShowAddModal] = useState(false)
  const [selectedSecret, setSelectedSecret] = useState(null)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '500' }}>Secrets</h3>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowAddModal(true)}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          + Add Secret
        </button>
      </div>

      <div className="table-container">
        <table className="apps-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Apps</th>
              <th>Last Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {secrets.map(secret => (
              <tr key={secret.id}>
                <td style={{ fontWeight: '500' }}>{secret.name}</td>
                <td>
                  <span className="status-badge status-running" style={{ fontSize: '0.75rem' }}>
                    Encrypted
                  </span>
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  {secret.apps.join(', ')}
                </td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                  {secret.lastUpdated} by {secret.updatedBy}
                </td>
                <td>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button 
                      className="btn btn-secondary" 
                      onClick={() => setSelectedSecret(secret)}
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                    >
                      View
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                      Edit
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: '1rem', fontWeight: '500' }}>Add Secret</h2>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Name</label>
              <input
                type="text"
                placeholder="SECRET_NAME"
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
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Value</label>
              <textarea
                placeholder="Secret value (will be encrypted)"
                rows={4}
                style={{
                  width: '100%',
                  padding: '0.5rem',
                  border: '1px solid var(--border)',
                  borderRadius: '0',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace'
                }}
              />
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={() => setShowAddModal(false)}>
                Save Secret
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default SecretsManager
