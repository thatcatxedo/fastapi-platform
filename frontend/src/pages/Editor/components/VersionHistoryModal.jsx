import { useState, useEffect } from 'react'
import { API_URL } from '../../../App'

function VersionHistoryModal({ isOpen, onClose, appId, onRollbackSuccess }) {
  const [versions, setVersions] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [rollingBack, setRollingBack] = useState(false)
  const [selectedVersion, setSelectedVersion] = useState(null)
  const [previewCode, setPreviewCode] = useState(null)

  useEffect(() => {
    if (isOpen && appId) {
      fetchVersions()
    }
  }, [isOpen, appId])

  const fetchVersions = async () => {
    setLoading(true)
    setError('')
    
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}/versions`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch version history')
      }

      const data = await response.json()
      setVersions(data.versions || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleRollback = async (versionIndex) => {
    if (!window.confirm('Are you sure you want to rollback to this version? This will deploy the selected version.')) {
      return
    }

    setRollingBack(true)
    setError('')

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}/rollback/${versionIndex}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail?.message || data.detail || 'Rollback failed')
      }

      onRollbackSuccess()
    } catch (err) {
      setError(err.message)
    } finally {
      setRollingBack(false)
    }
  }

  const formatDate = (dateString) => {
    try {
      const date = new Date(dateString)
      return date.toLocaleString()
    } catch {
      return dateString
    }
  }

  const togglePreview = (index) => {
    if (selectedVersion === index) {
      setSelectedVersion(null)
      setPreviewCode(null)
    } else {
      setSelectedVersion(index)
      setPreviewCode(versions[index].code)
    }
  }

  if (!isOpen) return null

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000
    }}>
      <div style={{
        backgroundColor: 'var(--bg-secondary, #1a1a1a)',
        borderRadius: '0.75rem',
        width: '90%',
        maxWidth: previewCode ? '1200px' : '600px',
        maxHeight: '80vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid var(--border)'
      }}>
        {/* Header */}
        <div style={{
          padding: '1rem 1.5rem',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Version History</h2>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.5rem',
              cursor: 'pointer',
              padding: '0.25rem'
            }}
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          display: 'flex'
        }}>
          {/* Version list */}
          <div style={{
            flex: previewCode ? '0 0 350px' : 1,
            padding: '1rem 1.5rem',
            overflowY: 'auto',
            borderRight: previewCode ? '1px solid var(--border)' : 'none'
          }}>
            {error && (
              <div style={{
                padding: '0.75rem',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: '0.5rem',
                color: '#ef4444',
                marginBottom: '1rem'
              }}>
                {error}
              </div>
            )}

            {loading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                Loading versions...
              </div>
            ) : versions.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                No version history yet. Deploy changes to start building history.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {versions.map((version, index) => (
                  <div
                    key={index}
                    style={{
                      padding: '1rem',
                      background: selectedVersion === index 
                        ? 'var(--bg-hover, rgba(255,255,255,0.1))' 
                        : 'var(--bg, rgba(255,255,255,0.05))',
                      borderRadius: '0.5rem',
                      border: selectedVersion === index 
                        ? '1px solid var(--primary, #3b82f6)' 
                        : '1px solid var(--border)'
                    }}
                  >
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '0.5rem'
                    }}>
                      <div>
                        <div style={{ fontWeight: 500, marginBottom: '0.25rem' }}>
                          Version {versions.length - index}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {formatDate(version.deployed_at)}
                        </div>
                      </div>
                      <div style={{ 
                        fontSize: '0.7rem', 
                        color: 'var(--text-muted)',
                        fontFamily: 'monospace',
                        background: 'var(--bg)',
                        padding: '0.125rem 0.375rem',
                        borderRadius: '0.25rem'
                      }}>
                        {version.code_hash.substring(0, 8)}
                      </div>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.75rem' }}>
                      <button
                        onClick={() => togglePreview(index)}
                        className="btn btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '0.375rem 0.75rem' }}
                      >
                        {selectedVersion === index ? 'Hide' : 'Preview'}
                      </button>
                      <button
                        onClick={() => handleRollback(index)}
                        disabled={rollingBack}
                        className="btn btn-primary"
                        style={{ fontSize: '0.75rem', padding: '0.375rem 0.75rem' }}
                      >
                        {rollingBack ? 'Rolling back...' : 'Rollback'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Code preview */}
          {previewCode && (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              overflow: 'hidden'
            }}>
              <div style={{
                padding: '0.75rem 1rem',
                borderBottom: '1px solid var(--border)',
                fontSize: '0.875rem',
                color: 'var(--text-muted)'
              }}>
                Code Preview - Version {versions.length - selectedVersion}
              </div>
              <pre style={{
                flex: 1,
                margin: 0,
                padding: '1rem',
                overflow: 'auto',
                fontSize: '0.8rem',
                fontFamily: 'monospace',
                background: 'var(--bg)',
                color: 'var(--text)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word'
              }}>
                {previewCode}
              </pre>
            </div>
          )}
        </div>

        {/* Footer */}
        <div style={{
          padding: '1rem 1.5rem',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'flex-end'
        }}>
          <button
            onClick={onClose}
            className="btn btn-secondary"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default VersionHistoryModal
