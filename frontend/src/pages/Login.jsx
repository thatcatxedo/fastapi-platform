import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { API_URL } from '../App'

function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [touched, setTouched] = useState({})
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const validateField = (name, value) => {
    switch (name) {
      case 'username':
        if (!value.trim()) return 'Username is required'
        if (value.length < 3) return 'Username must be at least 3 characters'
        return ''
      case 'password':
        if (!value) return 'Password is required'
        return ''
      default:
        return ''
    }
  }

  const handleBlur = (name, value) => {
    setTouched(prev => ({ ...prev, [name]: true }))
    setFieldErrors(prev => ({ ...prev, [name]: validateField(name, value) }))
  }

  const handleChange = (name, value, setter) => {
    setter(value)
    // Clear error when user starts typing again
    if (touched[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: validateField(name, value) }))
    }
    // Clear server error when user makes changes
    if (error) setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    // Validate all fields
    const usernameError = validateField('username', username)
    const passwordError = validateField('password', password)
    
    setFieldErrors({ username: usernameError, password: passwordError })
    setTouched({ username: true, password: true })
    
    if (usernameError || passwordError) {
      return
    }

    setError('')
    setLoading(true)

    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Login failed')
      }

      localStorage.setItem('token', data.access_token)
      
      // Fetch user info
      const userResponse = await fetch(`${API_URL}/api/auth/me`, {
        headers: { 'Authorization': `Bearer ${data.access_token}` }
      })
      const user = await userResponse.json()
      
      onLogin(user)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const getInputStyle = (fieldName) => ({
    borderColor: touched[fieldName] && fieldErrors[fieldName] ? 'var(--error)' : undefined
  })

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem' }}>Login</h1>
      
      {error && <div className="error">{error}</div>}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => handleChange('username', e.target.value, setUsername)}
            onBlur={(e) => handleBlur('username', e.target.value)}
            style={getInputStyle('username')}
            autoFocus
          />
          {touched.username && fieldErrors.username && (
            <div style={{ color: 'var(--error)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {fieldErrors.username}
            </div>
          )}
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => handleChange('password', e.target.value, setPassword)}
            onBlur={(e) => handleBlur('password', e.target.value)}
            style={getInputStyle('password')}
          />
          {touched.password && fieldErrors.password && (
            <div style={{ color: 'var(--error)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {fieldErrors.password}
            </div>
          )}
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Logging in...' : 'Login'}
        </button>
      </form>

      <p style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Don't have an account? <Link to="/signup" style={{ color: 'var(--primary)' }}>Sign up</Link>
      </p>
    </div>
  )
}

export default Login
