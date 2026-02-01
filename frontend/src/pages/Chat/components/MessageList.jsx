import { useEffect, useRef } from 'react'
import styles from '../Chat.module.css'
import { ToolStatus } from './ToolStatus'

export function MessageList({ messages, isStreaming, streamingContent, toolStatus }) {
  const messagesEndRef = useRef(null)

  // Auto-scroll to bottom on new messages or streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamingContent])

  return (
    <div className={styles.messageList}>
      {messages.map((msg) => (
        <MessageBubble key={msg.id} message={msg} />
      ))}

      {/* Streaming assistant message */}
      {isStreaming && streamingContent && (
        <MessageBubble
          message={{ role: 'assistant', content: streamingContent }}
          isStreaming
        />
      )}

      {/* Tool execution status */}
      {toolStatus && <ToolStatus status={toolStatus} />}

      {/* Scroll anchor */}
      <div ref={messagesEndRef} />
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
