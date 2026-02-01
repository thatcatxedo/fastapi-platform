import styles from '../Chat.module.css'

export function ConversationList({ conversations, activeId, onNew, onSelect, onDelete, loading }) {
  return (
    <div className={styles.sidebar}>
      <div className={styles.sidebarHeader}>
        <button
          className={`btn btn-primary ${styles.newChatBtn}`}
          onClick={onNew}
        >
          + New Chat
        </button>
      </div>

      <div className={styles.conversationList}>
        {loading ? (
          <div className={styles.loading}>Loading...</div>
        ) : conversations.length === 0 ? (
          <div className={styles.emptyState}>
            No conversations yet.<br />
            Start a new chat!
          </div>
        ) : (
          conversations.map(conv => (
            <div
              key={conv.id}
              className={`${styles.conversationItem} ${conv.id === activeId ? styles.active : ''}`}
              onClick={() => onSelect(conv.id)}
            >
              <span className={styles.conversationTitle}>
                {conv.title || 'Untitled conversation'}
              </span>
              <button
                className={styles.deleteBtn}
                onClick={(e) => {
                  e.stopPropagation()
                  onDelete(conv.id)
                }}
                title="Delete conversation"
              >
                &times;
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
