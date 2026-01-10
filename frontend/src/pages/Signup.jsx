import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../App'

function Signup({ onSignup }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Signup failed')
      }

      // Auto-login after signup
      const loginResponse = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      const loginData = await loginResponse.json()
      localStorage.setItem('token', loginData.access_token)
      
      // Fetch user info
      const userResponse = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${loginData.access_token}` }
      })
      const user = await userResponse.json()
      
      onSignup(user)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Sign Up</h1>
      
      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Signing up...' : 'Sign Up'}
        </button>
      </form>

      <p style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Already have an account? <a href="/login" style={{ color: 'var(--primary)' }}>Log in</a>
      </p>
    </div>
  )
}

export default Signup
