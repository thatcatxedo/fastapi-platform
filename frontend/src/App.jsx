import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Database from './pages/Database'
import Editor from './pages/Editor/index'
import AppView from './pages/AppView'
import Admin from './pages/Admin'
import Sidebar from './components/Sidebar'
import { ToastProvider } from './components/Toast'
import { AppsProvider } from './context/AppsContext'
import './index.css'

const API_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:8000' 
  : ''

export { API_URL }

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkAuth()
  }, [])

  const checkAuth = async () => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }

    try {
      const response = await fetch(`${API_URL}/api/auth/me`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      })
      if (response.ok) {
        const userData = await response.json()
        setUser(userData)
      } else {
        localStorage.removeItem('token')
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      localStorage.removeItem('token')
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
  }

  if (loading) {
    return (
      <div className="app">
        <div className="loading">Loading...</div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <ToastProvider>
        {user ? (
          // Authenticated: IDE layout with sidebar
          <AppsProvider user={user}>
            <div className="ide-layout">
              <Sidebar user={user} onLogout={logout} />
              <main className="ide-main">
                <Routes>
                  <Route path="/" element={<Navigate to="/editor" replace />} />
                  <Route path="/editor" element={<Editor user={user} />} />
                  <Route path="/editor/:appId" element={<Editor user={user} />} />
                  <Route path="/dashboard" element={<Dashboard user={user} />} />
                  <Route path="/database" element={<Database user={user} />} />
                  <Route path="/app/:appId" element={<AppView user={user} />} />
                  <Route path="/admin" element={user.is_admin ? <Admin user={user} /> : <Navigate to="/editor" replace />} />
                  <Route path="/login" element={<Navigate to="/editor" replace />} />
                  <Route path="/signup" element={<Navigate to="/editor" replace />} />
                </Routes>
              </main>
            </div>
          </AppsProvider>
        ) : (
          // Unauthenticated: Full-page auth screens
          <div className="auth-page">
            <div className="auth-container">
              <Routes>
                <Route path="/" element={<Navigate to="/login" replace />} />
                <Route path="/login" element={<Login onLogin={setUser} />} />
                <Route path="/signup" element={<Signup onSignup={setUser} />} />
                <Route path="*" element={<Navigate to="/login" replace />} />
              </Routes>
            </div>
          </div>
        )}
      </ToastProvider>
    </BrowserRouter>
  )
}

export default App
