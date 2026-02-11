import { useState, useEffect, useRef } from 'react'
import styles from '../Editor.module.css'

const isValidEnvVarKey = (key) => /^[A-Z_][A-Z0-9_]*$/i.test(key)

function SettingsDrawer({
  databaseId,
  onDatabaseChange,
  databases,
  autoSelectDefault,
  disabled,
  envVars,
  onEnvVarsChange,
  expanded,
  onToggleExpanded,
  codeUsesMongo
}) {
  const [showEnvValues, setShowEnvValues] = useState({})
  const autoSelectDone = useRef(false)

  // Auto-select default database when template requires it
  useEffect(() => {
    if (autoSelectDefault && !autoSelectDone.current && databases.length > 0 && !databaseId) {
      const defaultDb = databases.find(db => db.is_default)
      if (defaultDb) {
        onDatabaseChange(defaultDb.id)
        autoSelectDone.current = true
      }
    }
  }, [autoSelectDefault, databases, databaseId, onDatabaseChange])

  const addEnvVar = () => {
    onEnvVarsChange([...envVars, { key: '', value: '' }])
    if (!expanded) onToggleExpanded()
  }

  const removeEnvVar = (index) => {
    onEnvVarsChange(envVars.filter((_, i) => i !== index))
    const newShowValues = { ...showEnvValues }
    delete newShowValues[index]
    setShowEnvValues(newShowValues)
  }

  const updateEnvVar = (index, field, value) => {
    const newEnvVars = [...envVars]
    newEnvVars[index][field] = value
    onEnvVarsChange(newEnvVars)
  }

  const toggleShowValue = (index) => {
    setShowEnvValues({ ...showEnvValues, [index]: !showEnvValues[index] })
  }

  // Build summary text for collapsed header
  const dbName = databases.find(db => db.id === databaseId)?.name
    || (databaseId ? 'selected' : 'default')
  const parts = []
  if (envVars.length > 0) parts.push(`${envVars.length} env var${envVars.length > 1 ? 's' : ''}`)
  if (databases.length > 0) parts.push(`DB: ${dbName}`)
  const summary = parts.length > 0 ? `(${parts.join(' \u00B7 ')})` : ''

  return (
    <div className={styles.settingsDrawer}>
      <div className={styles.settingsHeader} onClick={onToggleExpanded}>
        <div className={styles.settingsHeaderLeft}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {expanded ? '\u25BC' : '\u25B6'}
          </span>
          <label style={{
            margin: 0,
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            fontWeight: '500',
            cursor: 'pointer'
          }}>
            Settings
          </label>
          {summary && <span className={styles.settingsSummary}>{summary}</span>}
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); addEnvVar() }}
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
        >
          + Add Env Var
        </button>
      </div>

      {expanded && (
        <div className={styles.settingsContent}>
          {/* Database section */}
          {databases.length > 0 && (
            <>
              <div className={styles.settingsSection}>
                <label className={styles.settingsSectionLabel}>Database:</label>
                <select
                  value={databaseId || ''}
                  onChange={(e) => onDatabaseChange(e.target.value || null)}
                  disabled={disabled}
                  className={styles.settingsSelect}
                >
                  <option value="">Use Default</option>
                  {databases.map(db => (
                    <option key={db.id} value={db.id}>
                      {db.name}{db.is_default ? ' (Default)' : ''} - {db.total_size_mb} MB
                    </option>
                  ))}
                </select>
              </div>
              {codeUsesMongo && !databaseId && (
                <div className={styles.settingsWarningNote}>
                  This code uses MongoDB. The default database will be used.
                </div>
              )}
              <div className={styles.settingsSeparator} />
            </>
          )}

          {/* Environment variables section */}
          <label className={styles.settingsEnvLabel}>Environment Variables</label>
          {envVars.length === 0 ? (
            <div style={{
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              padding: '0.5rem',
              textAlign: 'center'
            }}>
              No environment variables. Click "+ Add Env Var" to add one.
              <br />
              <span style={{ fontSize: '0.7rem' }}>
                Access in code: <code>import os; os.environ.get("KEY")</code>
              </span>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {envVars.map((env, index) => (
                <div key={index} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    type="text"
                    value={env.key}
                    onChange={(e) => updateEnvVar(index, 'key', e.target.value.toUpperCase())}
                    placeholder="KEY_NAME"
                    style={{
                      flex: 1,
                      padding: '0.375rem 0.5rem',
                      fontSize: '0.8rem',
                      background: 'var(--bg)',
                      border: `1px solid ${env.key && !isValidEnvVarKey(env.key) ? 'var(--error)' : 'var(--border)'}`,
                      borderRadius: '0.375rem',
                      color: 'var(--text)',
                      fontFamily: 'monospace'
                    }}
                  />
                  <div style={{ flex: 2, display: 'flex', gap: '0.25rem' }}>
                    <input
                      type={showEnvValues[index] ? 'text' : 'password'}
                      value={env.value}
                      onChange={(e) => updateEnvVar(index, 'value', e.target.value)}
                      placeholder="value"
                      style={{
                        flex: 1,
                        padding: '0.375rem 0.5rem',
                        fontSize: '0.8rem',
                        background: 'var(--bg)',
                        border: '1px solid var(--border)',
                        borderRadius: '0.375rem',
                        color: 'var(--text)',
                        fontFamily: 'monospace'
                      }}
                    />
                    <button
                      type="button"
                      onClick={() => toggleShowValue(index)}
                      style={{
                        padding: '0.25rem 0.5rem',
                        fontSize: '0.7rem',
                        background: 'var(--bg)',
                        border: '1px solid var(--border)',
                        borderRadius: '0.375rem',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        minWidth: '45px'
                      }}
                      title={showEnvValues[index] ? 'Hide value' : 'Show value'}
                    >
                      {showEnvValues[index] ? 'Hide' : 'Show'}
                    </button>
                  </div>
                  <button
                    type="button"
                    onClick={() => removeEnvVar(index)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.8rem',
                      background: 'transparent',
                      border: '1px solid var(--border)',
                      borderRadius: '0.375rem',
                      color: 'var(--error)',
                      cursor: 'pointer'
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default SettingsDrawer
