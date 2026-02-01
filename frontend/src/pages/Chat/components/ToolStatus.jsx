import styles from '../Chat.module.css'

const TOOL_LABELS = {
  create_app: 'Creating app',
  update_app: 'Updating app',
  get_app: 'Getting app details',
  get_app_logs: 'Fetching logs',
  list_apps: 'Listing apps',
  delete_app: 'Deleting app',
  list_databases: 'Listing databases'
}

export function ToolStatus({ status }) {
  if (!status) return null

  const { tool, tool_input, result } = status
  const label = TOOL_LABELS[tool] || tool

  return (
    <div className={styles.toolStatus}>
      <div className={styles.toolStatusHeader}>
        {!result && <span className={styles.spinner}>&#10227;</span>}
        {result?.success === true && <span style={{ color: 'var(--success)' }}>&#10003;</span>}
        {result?.success === false && <span style={{ color: 'var(--error)' }}>&#10007;</span>}
        <span>{label}...</span>
      </div>

      {result && (
        <div className={styles.toolStatusResult}>
          {result.message || (result.url && (
            <>
              App deployed: <a href={result.url} target="_blank" rel="noopener noreferrer">{result.url}</a>
            </>
          )) || JSON.stringify(result, null, 2)}
        </div>
      )}
    </div>
  )
}
