import { useState, useCallback } from 'react'
import { API_URL } from '../App'

/**
 * Hook for managing chat conversations and SSE streaming
 */
export function useChat() {
  const [conversations, setConversations] = useState([])
  const [messages, setMessages] = useState([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamingContent, setStreamingContent] = useState('')
  const [toolStatus, setToolStatus] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  // UX feedback states
  const [isSending, setIsSending] = useState(false)      // Message being sent to server
  const [isThinking, setIsThinking] = useState(false)    // Waiting for first token
  const [connectionStatus, setConnectionStatus] = useState('idle') // idle, connecting, streaming, error

  const getAuthHeaders = () => ({
    'Authorization': `Bearer ${localStorage.getItem('token')}`,
    'Content-Type': 'application/json'
  })

  // Load all conversations
  const loadConversations = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations`, {
        headers: getAuthHeaders()
      })
      if (!response.ok) throw new Error('Failed to load conversations')
      const data = await response.json()
      setConversations(data.conversations || [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  // Load a single conversation with messages
  const loadConversation = useCallback(async (conversationId) => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}`, {
        headers: getAuthHeaders()
      })
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Conversation not found')
        }
        throw new Error('Failed to load conversation')
      }
      const data = await response.json()
      setMessages(data.messages || [])
      return data
    } catch (err) {
      setError(err.message)
      setMessages([])
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  // Create a new conversation
  const createConversation = useCallback(async (title = null) => {
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ title })
      })
      if (!response.ok) throw new Error('Failed to create conversation')
      const data = await response.json()
      setConversations(prev => [data, ...prev])
      setMessages([])
      return data
    } catch (err) {
      setError(err.message)
      return null
    }
  }, [])

  // Delete a conversation
  const deleteConversation = useCallback(async (conversationId) => {
    setError(null)
    try {
      const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      })
      if (!response.ok) throw new Error('Failed to delete conversation')
      setConversations(prev => prev.filter(c => c.id !== conversationId))
      return true
    } catch (err) {
      setError(err.message)
      return false
    }
  }, [])

  // Send a message and handle SSE streaming response
  const sendMessage = useCallback(async (conversationId, content, appId = null) => {
    setError(null)
    setIsSending(true)
    setIsThinking(true)
    setConnectionStatus('connecting')
    setIsStreaming(true)
    setStreamingContent('')
    setToolStatus(null)

    // Add user message to UI immediately
    const userMessage = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])

    try {
      const response = await fetch(`${API_URL}/api/chat/conversations/${conversationId}/messages`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ content, app_id: appId })
      })

      // Message sent successfully
      setIsSending(false)

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || 'Failed to send message')
      }

      // Read SSE stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''
      let toolCalls = []
      let receivedFirstEvent = false  // Track locally to avoid stale closure

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          const jsonStr = line.slice(6).trim()
          if (!jsonStr) continue

          try {
            const event = JSON.parse(jsonStr)

            switch (event.type) {
              case 'text':
                // First event received - no longer thinking
                if (!receivedFirstEvent) {
                  receivedFirstEvent = true
                  setIsThinking(false)
                  setConnectionStatus('streaming')
                }
                assistantContent += event.content || ''
                setStreamingContent(assistantContent)
                break

              case 'tool_start':
                // Tool start also means we're no longer waiting
                if (!receivedFirstEvent) {
                  receivedFirstEvent = true
                  setIsThinking(false)
                  setConnectionStatus('streaming')
                }
                setToolStatus({
                  tool: event.tool,
                  tool_input: event.tool_input,
                  result: null
                })
                break

              case 'tool_result':
                setToolStatus(prev => prev ? {
                  ...prev,
                  result: event.result
                } : null)
                toolCalls.push({
                  id: `tool-${toolCalls.length}`,
                  name: event.tool,
                  input: event.tool_input || {},
                  result: event.result
                })
                break

              case 'done':
                // Add final assistant message
                const assistantMessage = {
                  id: `assistant-${Date.now()}`,
                  role: 'assistant',
                  content: assistantContent,
                  tool_calls: toolCalls.length > 0 ? toolCalls : null,
                  created_at: new Date().toISOString()
                }
                setMessages(prev => [...prev, assistantMessage])
                setStreamingContent('')
                setToolStatus(null)
                setConnectionStatus('idle')
                break

              case 'error':
                setConnectionStatus('error')
                throw new Error(event.error || 'Unknown error')
            }
          } catch (parseErr) {
            // Ignore parse errors for malformed chunks
            if (parseErr.message !== 'Unknown error' && !parseErr.message.includes('JSON')) {
              throw parseErr
            }
          }
        }
      }
    } catch (err) {
      setError(err.message)
      setConnectionStatus('error')
      // Remove the optimistic user message on error
      setMessages(prev => prev.filter(m => m.id !== userMessage.id))
    } finally {
      setIsStreaming(false)
      setIsSending(false)
      setIsThinking(false)
      setStreamingContent('')
    }
  }, [])

  // Clear error
  const clearError = useCallback(() => setError(null), [])

  return {
    // State
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
    // Actions
    loadConversations,
    loadConversation,
    createConversation,
    deleteConversation,
    sendMessage,
    clearError
  }
}
