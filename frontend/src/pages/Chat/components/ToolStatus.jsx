import styles from '../Chat.module.css'

const TOOL_INFO = {
  create_app: { label: 'Creating app', icon: '🚀' },
  update_app: { label: 'Updating app', icon: '✏️' },
  get_app: { label: 'Fetching app details', icon: '📋' },
  get_app_logs: { label: 'Reading logs', icon: '📜' },
  list_apps: { label: 'Listing apps', icon: '📂' },
  delete_app: { label: 'Deleting app', icon: '🗑️' },
  list_databases: { label: 'Listing databases', icon: '🗄️' }
}

export function ToolStatus({ status }) {
  if (!status) return null

  const { tool, tool_input, result } = status
  const info = TOOL_INFO[tool] || { label: tool, icon: '⚙️' }
  const isComplete = result !== null
  const isSuccess = result?.success !== false

  return (
    <div className={styles.toolStatus}>
      <div className={styles.toolStatusHeader}>
        {!isComplete ? (
          // Show spinning icon while in progress
          <span className={`${styles.toolStatusIcon} ${styles.spinning}`}>⏳</span>
        ) : isSuccess ? (
          <span className={styles.toolStatusIcon}>✓</span>
        ) : (
          <span className={styles.toolStatusIcon} style={{ color: 'var(--error)' }}>✗</span>
        )}
        <span>{info.icon}</span>
        <span>{info.label}{!isComplete ? '...' : ''}</span>
      </div>

      {result && (
        <div className={`${styles.toolStatusResult} ${isSuccess ? styles.success : styles.error}`}>
          {isSuccess ? '✓' : '✗'} {result.message || 'Done'}
          {result.url && (
            <a href={result.url} target="_blank" rel="noopener noreferrer">
              Open →
            </a>
          )}
          {!result.message && !result.url && (
            <pre style={{ margin: '0.5rem 0 0', whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
