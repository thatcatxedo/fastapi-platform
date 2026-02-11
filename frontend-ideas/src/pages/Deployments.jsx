import React, { useState } from 'react'
import DeploymentCard from '../components/DeploymentCard'
import GitIntegration from '../components/GitIntegration'
import { generateDeployments } from '../utils/mockData'
import './Deployments.css'

const Deployments = () => {
  const [deployments] = useState(generateDeployments(20))
  const [showGitModal, setShowGitModal] = useState(false)
  const [gitConnected, setGitConnected] = useState({
    provider: 'github',
    repo: 'thatcatxedo/fastapi-platform',
    branch: 'main'
  })

  const successCount = deployments.filter(d => d.status === 'success').length
  const failedCount = deployments.filter(d => d.status === 'failed').length
  const deployingCount = deployments.filter(d => d.status === 'deploying').length

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Deployments</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            className="btn btn-secondary" 
            onClick={() => setShowGitModal(true)}
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            {gitConnected ? 'Manage Git' : 'Connect Git'}
          </button>
          <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Deploy Now
          </button>
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Successful
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--success)' }}>
            {successCount}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Failed
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--error)' }}>
            {failedCount}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Deploying
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--warning)' }}>
            {deployingCount}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Total
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {deployments.length}
          </div>
        </div>
      </div>

      {/* Git Status */}
      {gitConnected && (
        <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>Git Repository Connected</div>
              <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                {gitConnected.provider} • {gitConnected.repo} • {gitConnected.branch}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <span className="status-badge status-running">Auto-deploy enabled</span>
              <button className="btn btn-secondary" onClick={() => setShowGitModal(true)} style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Configure
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Deployment History */}
      <div>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Recent Deployments</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '1rem' }}>
          {deployments.slice(0, 12).map(deployment => (
            <DeploymentCard key={deployment.id} deployment={deployment} />
          ))}
        </div>
      </div>

      {showGitModal && (
        <div className="modal-overlay" onClick={() => setShowGitModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <GitIntegration 
              onConnect={(config) => {
                if (config) {
                  setGitConnected(config)
                }
                setShowGitModal(false)
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

export default Deployments
