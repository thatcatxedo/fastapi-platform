import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { API_URL } from '../App'
import { useToast } from '../components/Toast'

// Helper to get app URL using subdomain routing
const getAppUrl = (appId) => {
  const appDomain = import.meta.env.VITE_APP_DOMAIN ||
    window.location.hostname.replace(/^platform\./, '')
  return `https://app-${appId}.${appDomain}`
}

function AppView({ user }) {
  const { appId } = useParams()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [app, setApp] = useState(null)
  const [iframeLoaded, setIframeLoaded] = useState(false)
  const [copiedUrl, setCopiedUrl] = useState(false)

  useEffect(() => {
    fetchAppStatus()
    recordActivity()
  }, [appId])

  const fetchAppStatus = async () => {
    setLoading(true)
    setError('')
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('App not found')
        }
        throw new Error('Failed to fetch app status')
      }

      const data = await response.json()
      setApp(data)

      if (data.status !== 'running') {
        if (data.status === 'deploying') {
          setError('App is still deploying. Please wait...')
        } else if (data.status === 'error') {
          setError(data.error_message || 'App failed to deploy')
        } else {
          setError(`App is not running (status: ${data.status})`)
        }
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

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

  const copyUrl = async () => {
    try {
      await navigator.clipboard.writeText(appUrl)
      setCopiedUrl(true)
      toast.success('URL copied to clipboard')
      setTimeout(() => setCopiedUrl(false), 2000)
    } catch (err) {
      toast.error('Failed to copy URL')
    }
  }

  const appUrl = getAppUrl(appId)
  const isRunning = app?.status === 'running'

  if (loading) {
    return (
      <div>
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between', 
          marginBottom: '1.5rem' 
        }}>
          <h1 style={{ fontWeight: '400' }}>App Preview</h1>
        </div>
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ 
            display: 'inline-block',
            animation: 'spin 1s linear infinite',
            fontSize: '1.5rem',
            marginBottom: '1rem'
          }}>○</div>
          <p style={{ color: 'var(--text-muted)' }}>Checking app status...</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      {/* Header with actions */}
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between', 
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '1rem'
      }}>
        <div>
          <h1 style={{ marginBottom: '0.25rem' }}>{app?.name || 'App Preview'}</h1>
          {isRunning && (
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              <code>{appUrl}</code>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          <Link 
            to={`/editor/${appId}`} 
            className="btn btn-secondary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Edit Code
          </Link>
          {isRunning && (
            <>
              <button
                onClick={copyUrl}
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              >
                {copiedUrl ? 'Copied!' : 'Copy URL'}
              </button>
              <a
                href={appUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              >
                Open in New Tab
              </a>
              <a
                href={`${appUrl}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
                style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              >
                API Docs
              </a>
            </>
          )}
          <Link 
            to="/dashboard" 
            className="btn btn-secondary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Back to Dashboard
          </Link>
        </div>
      </div>

      {error && (
        <div className="error" style={{ marginBottom: '1rem', padding: '1rem' }}>
          <div style={{ marginBottom: '0.75rem' }}>{error}</div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button 
              onClick={fetchAppStatus} 
              className="btn btn-secondary"
              style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
            >
              Retry
            </button>
            <Link 
              to={`/editor/${appId}`} 
              className="btn btn-primary"
              style={{ padding: '0.375rem 0.75rem', fontSize: '0.75rem' }}
            >
              Go to Editor
            </Link>
          </div>
        </div>
      )}

      {isRunning && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          {/* Iframe loading indicator */}
          {!iframeLoaded && (
            <div style={{ 
              padding: '3rem', 
              textAlign: 'center',
              background: 'var(--bg)'
            }}>
              <div style={{ 
                display: 'inline-block',
                animation: 'spin 1s linear infinite',
                fontSize: '1.5rem',
                marginBottom: '1rem'
              }}>○</div>
              <p style={{ color: 'var(--text-muted)' }}>Loading app...</p>
            </div>
          )}
          <iframe
            src={appUrl}
            style={{
              width: '100%',
              height: iframeLoaded ? '600px' : '0',
              border: 'none',
              display: 'block'
            }}
            title="App Preview"
            onLoad={() => setIframeLoaded(true)}
          />
        </div>
      )}

      {!isRunning && !error && (
        <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '1rem', opacity: 0.5 }}>⚠</div>
          <h2 style={{ marginBottom: '0.5rem', color: 'var(--text)', fontWeight: '500' }}>App Not Available</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }}>
            This app is not currently running. You may need to deploy it first.
          </p>
          <Link 
            to={`/editor/${appId}`} 
            className="btn btn-primary"
            style={{ padding: '0.75rem 1.5rem' }}
          >
            Go to Editor
          </Link>
        </div>
      )}
    </div>
  )
}

export default AppView
