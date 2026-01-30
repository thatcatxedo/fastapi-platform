import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Database from './pages/Database'
import Editor from './pages/Editor'
import AppView from './pages/AppView'
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
      <div className="app">
        <header className="app-header">
          <div className="container">
            <h1><a href="/">FastAPI Platform</a></h1>
            <nav>
              {user ? (
                <>
                  <a href="/dashboard">Dashboard</a>
                  <a href="/database">Database</a>
                  <a href="/editor">New App</a>
                  <span style={{ color: 'var(--text-muted)' }}>{user.username}</span>
                  <button className="btn btn-secondary" onClick={logout} style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <a href="/login">Login</a>
                  <a href="/signup">Signup</a>
                </>
              )}
            </nav>
          </div>
        </header>

        <main className="app-main">
          <Routes>
            <Route path="/" element={user ? <Navigate to="/dashboard" /> : <Navigate to="/login" />} />
            <Route path="/login" element={user ? <Navigate to="/dashboard" /> : <Login onLogin={setUser} />} />
            <Route path="/signup" element={user ? <Navigate to="/dashboard" /> : <Signup onSignup={setUser} />} />
            <Route path="/dashboard" element={user ? <Dashboard user={user} /> : <Navigate to="/login" />} />
            <Route path="/database" element={user ? <Database user={user} /> : <Navigate to="/login" />} />
            <Route path="/editor" element={user ? <Editor user={user} /> : <Navigate to="/login" />} />
            <Route path="/editor/:appId" element={user ? <Editor user={user} /> : <Navigate to="/login" />} />
            <Route path="/app/:appId" element={user ? <AppView user={user} /> : <Navigate to="/login" />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
