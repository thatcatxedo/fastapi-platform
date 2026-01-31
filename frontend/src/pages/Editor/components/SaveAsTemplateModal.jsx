import { useState } from 'react'
import { API_URL } from '../../../App'

function SaveAsTemplateModal({ isOpen, onClose, code, files, mode, framework, onSuccess }) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [complexity, setComplexity] = useState('simple')
  const [tags, setTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSaving(true)

    try {
      const token = localStorage.getItem('token')
      const payload = {
        name: name.trim(),
        description: description.trim(),
        complexity,
        tags: tags.split(',').map(t => t.trim()).filter(t => t),
        mode: mode || 'single',
      }

      if (mode === 'multi' && files) {
        payload.files = files
        payload.framework = framework || 'fastapi'
        payload.entrypoint = 'app.py'
      } else {
        payload.code = code
      }

      const response = await fetch(`${API_URL}/api/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to save template')
      }

      onSuccess(data)
      handleClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    setName('')
    setDescription('')
    setComplexity('simple')
    setTags('')
    setError('')
    onClose()
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem'
      }}
      onClick={handleClose}
    >
      <div
        style={{
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: '0.75rem',
          width: '100%',
          maxWidth: '500px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1.25rem 1.5rem',
          borderBottom: '1px solid var(--border)'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.125rem' }}>Save as Template</h2>
          <button
            onClick={handleClose}
            style={{
              padding: '0.5rem',
              background: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              lineHeight: 1
            }}
            title="Close"
          >
            ×
          </button>
        </div>

        {/* Modal Content */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem' }}>
          {error && (
            <div style={{
              padding: '0.75rem',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '0.5rem',
              color: '#ef4444',
              marginBottom: '1rem',
              fontSize: '0.875rem'
            }}>
              {error}
            </div>
          )}

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.875rem' }}>
              Template Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Custom Template"
              required
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text)',
                fontSize: '0.875rem'
              }}
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.875rem' }}>
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="A brief description of what this template does..."
              rows={3}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text)',
                fontSize: '0.875rem',
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.875rem' }}>
              Complexity
            </label>
            <select
              value={complexity}
              onChange={(e) => setComplexity(e.target.value)}
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text)',
                fontSize: '0.875rem'
              }}
            >
              <option value="simple">Simple</option>
              <option value="medium">Medium</option>
              <option value="complex">Complex</option>
            </select>
          </div>

          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500', fontSize: '0.875rem' }}>
              Tags (comma-separated)
            </label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="api, crud, mongodb"
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                background: 'var(--bg-secondary)',
                color: 'var(--text)',
                fontSize: '0.875rem'
              }}
            />
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-secondary"
              style={{ padding: '0.75rem 1.5rem' }}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={saving || !name.trim()}
              style={{ padding: '0.75rem 1.5rem' }}
            >
              {saving ? 'Saving...' : 'Save Template'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default SaveAsTemplateModal
