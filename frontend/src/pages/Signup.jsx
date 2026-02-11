import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { API_URL } from '../config'

function Signup({ onSignup }) {
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
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
        if (!/^[a-zA-Z0-9_-]+$/.test(value)) return 'Username can only contain letters, numbers, hyphens, and underscores'
        return ''
      case 'email':
        if (!value.trim()) return 'Email is required'
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'Please enter a valid email address'
        return ''
      case 'password':
        if (!value) return 'Password is required'
        if (value.length < 6) return 'Password must be at least 6 characters'
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
    const emailError = validateField('email', email)
    const passwordError = validateField('password', password)
    
    setFieldErrors({ username: usernameError, email: emailError, password: passwordError })
    setTouched({ username: true, email: true, password: true })
    
    if (usernameError || emailError || passwordError) {
      return
    }

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

  const getInputStyle = (fieldName) => ({
    borderColor: touched[fieldName] && fieldErrors[fieldName] ? 'var(--error)' : undefined
  })

  // Password strength indicator
  const getPasswordStrength = () => {
    if (password.length === 0) return null
    if (password.length < 6) return { label: 'Too short', color: 'var(--error)' }
    if (password.length < 8) return { label: 'Weak', color: 'var(--warning)' }
    if (password.length < 12) return { label: 'Good', color: 'var(--success)' }
    return { label: 'Strong', color: 'var(--success)' }
  }

  const passwordStrength = getPasswordStrength()

  return (
    <div style={{ maxWidth: '400px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '2rem', fontWeight: '400' }}>Sign Up</h1>
      
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
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => handleChange('email', e.target.value, setEmail)}
            onBlur={(e) => handleBlur('email', e.target.value)}
            style={getInputStyle('email')}
          />
          {touched.email && fieldErrors.email && (
            <div style={{ color: 'var(--error)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {fieldErrors.email}
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
          {touched.password && fieldErrors.password ? (
            <div style={{ color: 'var(--error)', fontSize: '0.75rem', marginTop: '0.25rem' }}>
              {fieldErrors.password}
            </div>
          ) : passwordStrength && (
            <div style={{ 
              color: passwordStrength.color, 
              fontSize: '0.75rem', 
              marginTop: '0.25rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span>Password strength: {passwordStrength.label}</span>
            </div>
          )}
        </div>

        <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Signing up...' : 'Sign Up'}
        </button>
      </form>

      <p style={{ marginTop: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
        Already have an account? <Link to="/login" style={{ color: 'var(--primary)' }}>Log in</Link>
      </p>
    </div>
  )
}

export default Signup
