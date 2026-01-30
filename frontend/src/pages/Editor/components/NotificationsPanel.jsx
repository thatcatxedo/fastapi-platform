import { useState } from 'react'
import EventsTimeline from '../../../components/EventsTimeline'

// Helper to get app URL using subdomain routing
const getAppUrl = (appId) => {
  const appDomain = import.meta.env.VITE_APP_DOMAIN ||
    window.location.hostname.replace(/^platform\./, '')
  return `https://app-${appId}.${appDomain}`
}

const getCurlSnippet = (url) => {
  return `curl ${url}`
}

function NotificationsPanel({
  error,
  success,
  validationMessage,
  deploymentStatus,
  deployingAppId,
  deployDuration,
  loading
}) {
  const [copiedCurl, setCopiedCurl] = useState(false)

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedCurl(true)
      setTimeout(() => setCopiedCurl(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const isDeploying = deploymentStatus && deploymentStatus.status === 'deploying'

  return (
    <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
      {error && (
        <div className="error" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {success && (
        <div className="success" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.5rem' }}>
            <div>
              <strong>Success!</strong> {success}
              {deployDuration && (
                <span style={{ marginLeft: '0.5rem', color: 'var(--success)', fontWeight: '600' }}>
                  ({deployDuration}s)
                </span>
              )}
            </div>
            {deployingAppId && deploymentStatus?.status === 'running' && (
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <a
                  href={getAppUrl(deployingAppId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                >
                  Open App
                </a>
                <a
                  href={`${getAppUrl(deployingAppId)}/docs`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-secondary"
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                >
                  API Docs
                </a>
                <button
                  onClick={() => copyToClipboard(getCurlSnippet(getAppUrl(deployingAppId)))}
                  className="btn btn-secondary"
                  style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                >
                  {copiedCurl ? 'Copied!' : 'Copy curl'}
                </button>
              </div>
            )}
          </div>
          {deployingAppId && (
            <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              URL: <code>{getAppUrl(deployingAppId)}</code>
            </div>
          )}
        </div>
      )}
      {validationMessage && (
        <div className="success" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <strong>Validation:</strong> {validationMessage}
        </div>
      )}
      {isDeploying && (
        <div style={{
          background: 'rgba(245, 158, 11, 0.1)',
          border: '1px solid var(--warning)',
          color: 'var(--warning)',
          padding: '0.75rem',
          borderRadius: '0.5rem',
          marginBottom: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.875rem'
        }}>
          <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>○</span>
          <span>Deploying your app... This may take a minute.</span>
          {deploymentStatus.pod_status && (
            <span style={{ fontSize: '0.75rem', opacity: 0.8 }}>
              (Pod: {deploymentStatus.pod_status})
            </span>
          )}
        </div>
      )}
      {deployingAppId && (loading || isDeploying) && (
        <EventsTimeline
          appId={deployingAppId}
          isDeploying={true}
        />
      )}
    </div>
  )
}

export default NotificationsPanel
