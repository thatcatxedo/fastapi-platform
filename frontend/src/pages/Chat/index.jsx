import { useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useChat } from '../../hooks/useChat'
import { ConversationList } from './components/ConversationList'
import { MessageList } from './components/MessageList'
import { MessageInput } from './components/MessageInput'
import styles from './Chat.module.css'

export default function Chat({ user }) {
  const { conversationId } = useParams()
  const navigate = useNavigate()

  const {
    conversations,
    messages,
    isStreaming,
    streamingContent,
    toolStatus,
    error,
    loading,
    loadConversations,
    loadConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    clearError
  } = useChat()

  // Load conversations on mount
  useEffect(() => {
    loadConversations()
  }, [loadConversations])

  // Load conversation when ID changes
  useEffect(() => {
    if (conversationId) {
      loadConversation(conversationId)
    }
  }, [conversationId, loadConversation])

  // Create new conversation
  const handleNewConversation = useCallback(async () => {
    const conv = await createConversation()
    if (conv) {
      navigate(`/chat/${conv.id}`)
    }
  }, [createConversation, navigate])

  // Select conversation
  const handleSelectConversation = useCallback((id) => {
    navigate(`/chat/${id}`)
  }, [navigate])

  // Delete conversation
  const handleDeleteConversation = useCallback(async (id) => {
    const confirmed = window.confirm('Delete this conversation?')
    if (!confirmed) return

    const success = await deleteConversation(id)
    if (success && id === conversationId) {
      navigate('/chat')
    }
  }, [deleteConversation, conversationId, navigate])

  // Send message
  const handleSendMessage = useCallback((content) => {
    if (conversationId) {
      sendMessage(conversationId, content)
    }
  }, [conversationId, sendMessage])

  return (
    <div className={styles.chatLayout}>
      <ConversationList
        conversations={conversations}
        activeId={conversationId}
        onNew={handleNewConversation}
        onSelect={handleSelectConversation}
        onDelete={handleDeleteConversation}
        loading={loading && !conversationId}
      />

      <div className={styles.chatMain}>
        {error && (
          <div className={styles.errorMessage}>
            {error}
            <button
              onClick={clearError}
              style={{ marginLeft: '1rem', background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}
            >
              &times;
            </button>
          </div>
        )}

        {conversationId ? (
          <>
            <MessageList
              messages={messages}
              isStreaming={isStreaming}
              streamingContent={streamingContent}
              toolStatus={toolStatus}
            />
            <MessageInput
              onSend={handleSendMessage}
              disabled={isStreaming}
            />
          </>
        ) : (
          <WelcomeScreen onNewChat={handleNewConversation} />
        )}
      </div>
    </div>
  )
}

function WelcomeScreen({ onNewChat }) {
  return (
    <div className={styles.welcomeScreen}>
      <div className={styles.welcomeIcon}>&#128172;</div>
      <h2 className={styles.welcomeTitle}>AI App Builder</h2>
      <p className={styles.welcomeText}>
        I can help you create, update, and debug FastAPI and FastHTML applications.
        Just describe what you want to build!
      </p>
      <button className="btn btn-primary" onClick={onNewChat}>
        Start a New Chat
      </button>
    </div>
  )
}
