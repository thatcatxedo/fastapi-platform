import { useEffect, useCallback, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useChat } from '../../hooks/useChat'
import { useApps } from '../../context/AppsContext'
import { ConversationList } from './components/ConversationList'
import { MessageList } from './components/MessageList'
import { MessageInput } from './components/MessageInput'
import { AppSelector } from './components/AppSelector'
import styles from './Chat.module.css'

export default function Chat({ user }) {
  const { conversationId } = useParams()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { apps } = useApps()
  const [selectedAppId, setSelectedAppId] = useState(null)

  const {
    conversations,
    messages,
    isStreaming,
    streamingContent,
    toolStatus,
    error,
    loading,
    // UX feedback states
    isSending,
    isThinking,
    connectionStatus,
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

  // Read app from URL params (from editor "Chat about this app" button)
  useEffect(() => {
    const appFromUrl = searchParams.get('app')
    if (appFromUrl && apps.find(a => a.app_id === appFromUrl)) {
      setSelectedAppId(appFromUrl)
    }
  }, [searchParams, apps])

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

  // Send message with app context
  const handleSendMessage = useCallback((content) => {
    if (conversationId) {
      sendMessage(conversationId, content, selectedAppId)
    }
  }, [conversationId, sendMessage, selectedAppId])

  // Get status bar content
  const getStatusBarContent = () => {
    if (connectionStatus === 'connecting') {
      return { className: styles.statusConnecting, text: 'Connecting...' }
    }
    if (connectionStatus === 'streaming') {
      return { className: styles.statusStreaming, text: 'Claude is responding' }
    }
    if (connectionStatus === 'error') {
      return { className: styles.statusError, text: 'Connection error' }
    }
    return { className: styles.statusIdle, text: 'Ready' }
  }

  const statusInfo = getStatusBarContent()

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
        {/* App context bar */}
        <div className={styles.contextBar}>
          <AppSelector
            apps={apps}
            selected={selectedAppId}
            onSelect={setSelectedAppId}
          />
        </div>

        {/* Connection status bar */}
        {conversationId && (
          <div className={`${styles.statusBar} ${statusInfo.className}`}>
            <span className={styles.statusDot}></span>
            <span className={styles.statusText}>{statusInfo.text}</span>
          </div>
        )}

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
              isThinking={isThinking}
            />
            <MessageInput
              onSend={handleSendMessage}
              disabled={isStreaming}
              isSending={isSending}
              isStreaming={isStreaming}
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
