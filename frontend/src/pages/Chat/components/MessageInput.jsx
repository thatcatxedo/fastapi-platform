import { useState } from 'react'
import styles from '../Chat.module.css'

export function MessageInput({ onSend, disabled, isSending, isStreaming }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (value.trim() && !disabled) {
      onSend(value.trim())
      setValue('')
    }
  }

  const handleKeyDown = (e) => {
    // Submit on Enter (without Shift)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Determine button state
  const getButtonContent = () => {
    if (isSending) {
      return (
        <>
          <span className={styles.sendButtonSpinner}></span>
          Sending
        </>
      )
    }
    if (isStreaming) {
      return 'Responding...'
    }
    return 'Send'
  }

  return (
    <form className={styles.inputArea} onSubmit={handleSubmit}>
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask me to create an app... (Enter to send, Shift+Enter for new line)"
        disabled={disabled}
        rows={2}
      />
      <button
        type="submit"
        className={`btn btn-primary ${styles.sendButton} ${isSending ? styles.sending : ''}`}
        disabled={disabled || !value.trim()}
      >
        {getButtonContent()}
      </button>
    </form>
  )
}
