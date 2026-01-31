import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { API_URL } from '../App'

const AppsContext = createContext(null)

export function useApps() {
  const context = useContext(AppsContext)
  if (!context) {
    throw new Error('useApps must be used within an AppsProvider')
  }
  return context
}

export function AppsProvider({ children, user }) {
  const [apps, setApps] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchApps = useCallback(async () => {
    if (!user) {
      setApps([])
      setLoading(false)
      return
    }

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch apps')
      }

      const data = await response.json()
      setApps(data)
      setError('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [user])

  // Fetch apps when user changes
  useEffect(() => {
    fetchApps()
  }, [fetchApps])

  // Update a single app in the list (for real-time status updates)
  const updateApp = useCallback((appId, updates) => {
    setApps(prevApps =>
      prevApps.map(app =>
        app.app_id === appId ? { ...app, ...updates } : app
      )
    )
  }, [])

  // Add a new app to the list
  const addApp = useCallback((newApp) => {
    setApps(prevApps => [newApp, ...prevApps])
  }, [])

  // Remove an app from the list
  const removeApp = useCallback((appId) => {
    setApps(prevApps => prevApps.filter(app => app.app_id !== appId))
  }, [])

  // Get counts for stats
  const stats = {
    total: apps.length,
    running: apps.filter(app => app.status === 'running').length,
    deploying: apps.filter(app => app.status === 'deploying').length,
    error: apps.filter(app => app.status === 'error').length
  }

  const value = {
    apps,
    loading,
    error,
    stats,
    fetchApps,
    updateApp,
    addApp,
    removeApp
  }

  return (
    <AppsContext.Provider value={value}>
      {children}
    </AppsContext.Provider>
  )
}
