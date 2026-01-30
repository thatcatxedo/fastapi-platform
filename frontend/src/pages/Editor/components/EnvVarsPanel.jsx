import { useState } from 'react'

const isValidEnvVarKey = (key) => {
  return /^[A-Z_][A-Z0-9_]*$/i.test(key)
}

function EnvVarsPanel({ envVars, onChange, expanded, onToggleExpanded }) {
  const [showEnvValues, setShowEnvValues] = useState({})

  const addEnvVar = () => {
    onChange([...envVars, { key: '', value: '' }])
    if (!expanded) {
      onToggleExpanded()
    }
  }

  const removeEnvVar = (index) => {
    onChange(envVars.filter((_, i) => i !== index))
    const newShowValues = { ...showEnvValues }
    delete newShowValues[index]
    setShowEnvValues(newShowValues)
  }

  const updateEnvVar = (index, field, value) => {
    const newEnvVars = [...envVars]
    newEnvVars[index][field] = value
    onChange(newEnvVars)
  }

  const toggleShowValue = (index) => {
    setShowEnvValues({ ...showEnvValues, [index]: !showEnvValues[index] })
  }

  return (
    <div style={{
      marginBottom: '0.75rem',
      background: 'var(--bg-light)',
      border: '1px solid var(--border)',
      borderRadius: '0.5rem',
      flexShrink: 0
    }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '0.5rem 0.75rem',
          cursor: 'pointer'
        }}
        onClick={onToggleExpanded}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {expanded ? '▼' : '▶'}
          </span>
          <label style={{
            margin: 0,
            fontSize: '0.75rem',
            color: 'var(--text-muted)',
            fontWeight: '500',
            cursor: 'pointer'
          }}>
            Environment Variables {envVars.length > 0 && `(${envVars.length})`}
          </label>
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); addEnvVar(); }}
          className="btn btn-secondary"
          style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
        >
          + Add
        </button>
      </div>

      {expanded && (
        <div style={{ padding: '0 0.75rem 0.75rem 0.75rem' }}>
          {envVars.length === 0 ? (
            <div style={{
              color: 'var(--text-muted)',
              fontSize: '0.75rem',
              padding: '0.5rem',
              textAlign: 'center'
            }}>
              No environment variables. Click "+ Add" to add one.
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

export default EnvVarsPanel
