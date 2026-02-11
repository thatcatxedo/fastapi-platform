import React, { useState } from 'react'
import './GitIntegration.css'

const GitIntegration = ({ onConnect }) => {
  const [provider, setProvider] = useState('github')
  const [repoUrl, setRepoUrl] = useState('')
  const [branch, setBranch] = useState('main')

  return (
    <div className="git-integration">
      <h3 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Connect Git Repository</h3>
      
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Provider</label>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['github', 'gitlab'].map(p => (
            <button
              key={p}
              className={`btn ${provider === p ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setProvider(p)}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', textTransform: 'capitalize' }}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: '1rem' }}>
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Repository URL</label>
        <input
          type="text"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          placeholder={`https://${provider}.com/username/repo`}
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
        <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Branch</label>
        <input
          type="text"
          value={branch}
          onChange={(e) => setBranch(e.target.value)}
          placeholder="main"
          style={{
            width: '100%',
            padding: '0.5rem',
            border: '1px solid var(--border)',
            borderRadius: '0',
            fontSize: '0.875rem'
          }}
        />
      </div>

      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
        <button className="btn btn-secondary" onClick={() => onConnect && onConnect(null)}>
          Cancel
        </button>
        <button 
          className="btn btn-primary" 
          onClick={() => onConnect && onConnect({ provider, repoUrl, branch })}
          disabled={!repoUrl}
        >
          Connect
        </button>
      </div>
    </div>
  )
}

export default GitIntegration
