import React from 'react'
import './DeploymentCard.css'

const DeploymentCard = ({ deployment }) => {
  const getStatusColor = (status) => {
    switch (status) {
      case 'success': return 'var(--success)'
      case 'failed': return 'var(--error)'
      case 'deploying': return 'var(--warning)'
      case 'rolled_back': return 'var(--text-muted)'
      default: return 'var(--text-muted)'
    }
  }

  const formatDuration = (seconds) => {
    if (seconds < 60) return `${seconds}s`
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`
  }

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    const now = Date.now()
    const diff = now - timestamp
    const hours = Math.floor(diff / (1000 * 60 * 60))
    
    if (hours === 0) return 'Just now'
    if (hours === 1) return '1 hour ago'
    return `${hours} hours ago`
  }

  return (
    <div className="deployment-card">
      <div className="deployment-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
            <span style={{ fontWeight: '500' }}>{deployment.appName}</span>
            <span className="status-badge" style={{ backgroundColor: getStatusColor(deployment.status) }}>
              {deployment.status}
            </span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {deployment.branch} • {deployment.commit.slice(0, 7)}
          </div>
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          {formatTimestamp(deployment.timestamp)}
        </div>
      </div>
      <div className="deployment-footer">
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Deployed by {deployment.deployedBy} • {formatDuration(deployment.duration)}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <a href={deployment.url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
            View
          </a>
          {deployment.status === 'success' && (
            <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
              Rollback
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default DeploymentCard
