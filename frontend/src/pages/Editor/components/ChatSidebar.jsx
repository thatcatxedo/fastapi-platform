import { useState, useEffect, useRef, useCallback } from 'react'
import { useChat } from '../../../hooks/useChat'
import styles from './ChatSidebar.module.css'

const TOOL_INFO = {
  create_app: { label: 'Creating app', icon: '🚀' },
  update_app: { label: 'Updating app', icon: '✏️' },
  get_app: { label: 'Fetching app details', icon: '📋' },
  get_app_logs: { label: 'Reading logs', icon: '📜' },
  list_apps: { label: 'Listing apps', icon: '📂' },
  delete_app: { label: 'Deleting app', icon: '🗑️' },
  list_databases: { label: 'Listing databases', icon: '🗄️' }
}

export function ChatSidebar({ appId, onClose }) {
  const {
    messages,
    isStreaming,
    streamingContent,
    toolStatus,
    error,
    isSending,
    isThinking,
    loadConversation,
    createConversation,
    sendMessage,
    clearError
  } = useChat()

  const [conversationId, setConversationId] = useState(null)
  const [initializing, setInitializing] = useState(true)

  // Load or create conversation for this app
  useEffect(() => {
    const initConversation = async () => {
      setInitializing(true)
      const storageKey = `chatSidebar_${appId}`
      const storedId = localStorage.getItem(storageKey)

      if (storedId) {
        // Try to load existing conversation
        const conv = await loadConversation(storedId)
        if (conv) {
          setConversationId(storedId)
          setInitializing(false)
          return
        }
        // Conversation was deleted, remove from storage
        localStorage.removeItem(storageKey)
      }

      // Create new conversation
      const newConv = await createConversation(`App: ${appId}`)
      if (newConv) {
        setConversationId(newConv.id)
        localStorage.setItem(storageKey, newConv.id)
      }
      setInitializing(false)
    }

    if (appId) {
      initConversation()
    }
  }, [appId])

  const handleSend = async (content) => {
    if (!conversationId || !content.trim()) return
    await sendMessage(conversationId, content, appId)
  }

  const handleNewChat = async () => {
    const storageKey = `chatSidebar_${appId}`
    const newConv = await createConversation(`App: ${appId}`)
    if (newConv) {
      setConversationId(newConv.id)
      localStorage.setItem(storageKey, newConv.id)
    }
  }

  return (
    <div className={styles.chatSidebar}>
      <div className={styles.header}>
        <span className={styles.headerTitle}>💬 Chat</span>
        <button
          className={styles.headerBtn}
          onClick={handleNewChat}
          disabled={initializing || isStreaming}
          title="Start new conversation"
        >
          New
        </button>
        <button className={styles.closeBtn} onClick={onClose} title="Close chat">
          ×
        </button>
      </div>

      {error && (
        <div className={styles.errorMessage}>
          {error}
          <button onClick={clearError} style={{ marginLeft: '0.5rem', cursor: 'pointer' }}>×</button>
        </div>
      )}

      <MessageList
        messages={messages}
        isStreaming={isStreaming}
        streamingContent={streamingContent}
        toolStatus={toolStatus}
        isThinking={isThinking}
        initializing={initializing}
      />

      <MessageInput
        onSend={handleSend}
        disabled={!conversationId || initializing}
        isSending={isSending}
        isStreaming={isStreaming}
      />
    </div>
  )
}

function MessageList({ messages, isStreaming, streamingContent, toolStatus, isThinking, initializing }) {
  const messagesEndRef = useRef(null)
  const containerRef = useRef(null)
  const [showScrollButton, setShowScrollButton] = useState(false)

  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
    setShowScrollButton(!isNearBottom)
  }, [])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    if (!showScrollButton) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent, showScrollButton])

  if (initializing) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.thinkingDots}>
          <span></span>
          <span></span>
          <span></span>
        </div>
        <p style={{ marginTop: '0.5rem', fontSize: '0.85rem' }}>Loading...</p>
      </div>
    )
  }

  if (messages.length === 0 && !isStreaming && !isThinking) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>💬</div>
        <div className={styles.emptyTitle}>Chat about this app</div>
        <p className={styles.emptyText}>
          Ask me to help you debug, add features, or explain your code.
        </p>
      </div>
    )
  }

  return (
    <div className={styles.messageListContainer}>
      <div
        ref={containerRef}
        className={styles.messageList}
        onScroll={handleScroll}
      >
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}

        {isThinking && !streamingContent && !toolStatus && (
          <div className={styles.thinking}>
            <div className={styles.thinkingDots}>
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className={styles.thinkingText}>Thinking...</span>
          </div>
        )}

        {toolStatus && <ToolStatus status={toolStatus} />}

        {isStreaming && streamingContent && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingContent }}
            isStreaming
          />
        )}

        <div ref={messagesEndRef} />
      </div>

      {showScrollButton && (
        <button className={styles.scrollToBottom} onClick={scrollToBottom}>
          ↓ New
        </button>
      )}
    </div>
  )
}

function MessageBubble({ message, isStreaming }) {
  const isUser = message.role === 'user'

  return (
    <div className={`${styles.message} ${isUser ? styles.user : styles.assistant}`}>
      <div className={styles.messageContent}>
        {message.content}
        {isStreaming && <span className={styles.cursor}>|</span>}
      </div>

      {message.tool_calls && message.tool_calls.length > 0 && (
        <div className={styles.toolCalls}>
          {message.tool_calls.map((tc) => (
            <ToolCallDisplay key={tc.id} toolCall={tc} />
          ))}
        </div>
      )}
    </div>
  )
}

function ToolCallDisplay({ toolCall }) {
  const { name, result } = toolCall
  const isSuccess = result?.success !== false

  return (
    <div className={styles.toolCall}>
      <div className={styles.toolCallHeader}>
        {isSuccess ? (
          <span style={{ color: 'var(--success)' }}>✓</span>
        ) : (
          <span style={{ color: 'var(--error)' }}>✗</span>
        )}
        <span>{name}</span>
      </div>
      {result && (
        <div className={`${styles.toolCallResult} ${isSuccess ? styles.success : styles.error}`}>
          {result.message || result.url || (
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.75rem' }}>
              {JSON.stringify(result, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

function ToolStatus({ status }) {
  if (!status) return null

  const { tool, result } = status
  const info = TOOL_INFO[tool] || { label: tool, icon: '⚙️' }
  const isComplete = result !== null
  const isSuccess = result?.success !== false

  return (
    <div className={styles.toolStatus}>
      <div className={styles.toolStatusHeader}>
        {!isComplete ? (
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
        </div>
      )}
    </div>
  )
}

function MessageInput({ onSend, disabled, isSending, isStreaming }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (value.trim() && !disabled && !isSending && !isStreaming) {
      onSend(value.trim())
      setValue('')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const getButtonContent = () => {
    if (isSending) {
      return (
        <>
          <span className={styles.sendButtonSpinner}></span>
        </>
      )
    }
    if (isStreaming) {
      return '...'
    }
    return 'Send'
  }

  return (
    <form className={styles.inputArea} onSubmit={handleSubmit}>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about this app..."
        disabled={disabled || isStreaming}
        rows={2}
      />
      <button
        type="submit"
        className={`btn btn-primary ${styles.sendButton} ${isSending ? styles.sending : ''}`}
        disabled={disabled || !value.trim() || isStreaming}
      >
        {getButtonContent()}
      </button>
    </form>
  )
}

export default ChatSidebar
