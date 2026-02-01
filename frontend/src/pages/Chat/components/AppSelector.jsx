import styles from '../Chat.module.css'

export function AppSelector({ apps, selected, onSelect }) {
  const selectedApp = apps.find(a => a.app_id === selected)

  return (
    <div className={styles.appSelector}>
      <label className={styles.appSelectorLabel}>App context:</label>
      <select
        value={selected || ''}
        onChange={(e) => onSelect(e.target.value || null)}
        className={styles.appSelectorSelect}
      >
        <option value="">None - General chat</option>
        {apps.map(app => (
          <option key={app.app_id} value={app.app_id}>
            {app.name} ({app.status || 'unknown'})
          </option>
        ))}
      </select>
      {selected && (
        <button
          onClick={() => onSelect(null)}
          className={styles.appSelectorClear}
          title="Clear app context"
        >
          &times;
        </button>
      )}
      {selectedApp && selectedApp.deployment_url && (
        <a
          href={selectedApp.deployment_url}
          target="_blank"
          rel="noopener noreferrer"
          className={styles.appSelectorLink}
          title="Open app"
        >
          &#8599;
        </a>
      )}
    </div>
  )
}
