import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { API_URL } from '../App'

function AppView({ user }) {
  const { appId } = useParams()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    // Record activity when viewing app
    recordActivity()
  }, [appId])

  const recordActivity = async () => {
    try {
      const token = localStorage.getItem('token')
      await fetch(`${API_URL}/api/apps/${appId}/activity`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
    } catch (err) {
      console.error('Failed to record activity:', err)
    }
  }

  const appUrl = `${window.location.origin}/user/${user.id}/app/${appId}`

  return (
    <div>
      <h1 style={{ marginBottom: '2rem' }}>App Preview</h1>
      
      {error && <div className="error">{error}</div>}

      <div className="card">
        <p style={{ marginBottom: '1rem' }}>
          Your app is available at: <a href={appUrl} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)' }}>{appUrl}</a>
        </p>
        <iframe
          src={appUrl}
          style={{
            width: '100%',
            height: '600px',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem'
          }}
          title="App Preview"
        />
      </div>
    </div>
  )
}

export default AppView
