import { useState, useEffect, useCallback, useRef } from 'react'
import { API_URL } from '../../../config'

function DatabaseSelector({ value, onChange, disabled, autoSelectDefault }) {
  const [databases, setDatabases] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const autoSelectDone = useRef(false)

  useEffect(() => {
    fetchDatabases()
  }, [])

  // Auto-select default database when autoSelectDefault is true and no value is set
  useEffect(() => {
    if (autoSelectDefault && !autoSelectDone.current && databases.length > 0 && !value) {
      const defaultDb = databases.find(db => db.is_default)
      if (defaultDb) {
        onChange(defaultDb.id)
        autoSelectDone.current = true
      }
    }
  }, [autoSelectDefault, databases, value, onChange])

  const fetchDatabases = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/databases`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (response.ok) {
        const data = await response.json()
        setDatabases(data.databases || [])
      }
    } catch (err) {
      setError('Failed to load databases')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{
        marginBottom: '0.75rem',
        background: 'var(--bg-light)',
        border: '1px solid var(--border)',
        borderRadius: '0.5rem',
        padding: '0.5rem 0.75rem',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <label style={{
            margin: 0,
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            fontWeight: '500'
          }}>
            Database
          </label>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Loading...</span>
        </div>
      </div>
    )
  }

  if (databases.length === 0) {
    return null // Don't show selector if no databases
  }

  return (
    <div style={{
      marginBottom: '0.75rem',
      background: 'var(--bg-light)',
      border: '1px solid var(--border)',
      borderRadius: '0.5rem',
      padding: '0.5rem 0.75rem',
      flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
        <label style={{
          margin: 0,
          fontSize: '0.75rem',
          color: 'var(--text-muted)',
          fontWeight: '500',
          whiteSpace: 'nowrap'
        }}>
          Database:
        </label>
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value || null)}
          disabled={disabled}
          style={{
            flex: 1,
            minWidth: '150px',
            padding: '0.375rem 0.5rem',
            fontSize: '0.8rem',
            background: 'var(--bg)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            color: 'var(--text)',
            cursor: disabled ? 'not-allowed' : 'pointer'
          }}
        >
          <option value="">Use Default</option>
          {databases.map(db => (
            <option key={db.id} value={db.id}>
              {db.name}{db.is_default ? ' (Default)' : ''} - {db.total_size_mb} MB
            </option>
          ))}
        </select>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          Select which database this app connects to
        </span>
      </div>
      {error && (
        <div style={{ marginTop: '0.25rem', fontSize: '0.7rem', color: 'var(--error)' }}>
          {error}
        </div>
      )}
    </div>
  )
}

export default DatabaseSelector
