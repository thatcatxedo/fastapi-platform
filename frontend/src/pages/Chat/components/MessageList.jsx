import { useEffect, useRef, useState, useCallback } from 'react'
import styles from '../Chat.module.css'
import { ToolStatus } from './ToolStatus'

export function MessageList({ messages, isStreaming, streamingContent, toolStatus, isThinking }) {
  const messagesEndRef = useRef(null)
  const containerRef = useRef(null)
  const [showScrollButton, setShowScrollButton] = useState(false)

  // Check if user has scrolled up from bottom
  const handleScroll = useCallback(() => {
    if (!containerRef.current) return
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100
    setShowScrollButton(!isNearBottom)
  }, [])

  // Scroll to bottom
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  // Auto-scroll to bottom on new messages or streaming content (if near bottom)
  useEffect(() => {
    if (!showScrollButton) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, streamingContent, showScrollButton])

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

        {/* Thinking indicator - shows before any response arrives */}
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

        {/* Tool execution status */}
        {toolStatus && <ToolStatus status={toolStatus} />}

        {/* Streaming assistant message */}
        {isStreaming && streamingContent && (
          <MessageBubble
            message={{ role: 'assistant', content: streamingContent }}
            isStreaming
          />
        )}

        {/* Scroll anchor */}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && (
        <button className={styles.scrollToBottom} onClick={scrollToBottom}>
          New messages
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

      {/* Tool calls display for assistant messages */}
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
          <span style={{ color: 'var(--success)' }}>&#10003;</span>
        ) : (
          <span style={{ color: 'var(--error)' }}>&#10007;</span>
        )}
        <span>{name}</span>
      </div>
      {result && (
        <div className={`${styles.toolCallResult} ${isSuccess ? styles.success : styles.error}`}>
          {result.message || result.url || (
            <pre>{JSON.stringify(result, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  )
}
