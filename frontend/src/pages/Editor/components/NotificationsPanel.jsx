import { useState } from 'react'
import { Link } from 'react-router-dom'
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
  const [copiedUrl, setCopiedUrl] = useState(false)

  const copyToClipboard = async (text, type = 'curl') => {
    try {
      await navigator.clipboard.writeText(text)
      if (type === 'url') {
        setCopiedUrl(true)
        setTimeout(() => setCopiedUrl(false), 2000)
      } else {
        setCopiedCurl(true)
        setTimeout(() => setCopiedCurl(false), 2000)
      }
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const isDeploying = deploymentStatus && deploymentStatus.status === 'deploying'
  const isDeploySuccess = deployingAppId && deploymentStatus?.status === 'running' && success

  return (
    <div style={{ flexShrink: 0, marginBottom: '0.75rem' }}>
      {error && (
        <div className="error" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <strong>Error:</strong> {error}
        </div>
      )}
      {isDeploySuccess ? (
        <div className="success" style={{ marginBottom: '0.5rem', padding: '1rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '1.125rem', fontWeight: '600', marginBottom: '0.25rem' }}>
              Deployment Successful!
              {deployDuration && (
                <span style={{ marginLeft: '0.5rem', fontSize: '0.875rem', fontWeight: '400', opacity: 0.9 }}>
                  ({deployDuration}s)
                </span>
              )}
            </div>
            <div style={{ fontSize: '0.875rem', opacity: 0.9 }}>
              Your app is now live and ready to use.
            </div>
          </div>
          
          <div style={{ 
            display: 'flex', 
            gap: '0.75rem', 
            alignItems: 'center', 
            flexWrap: 'wrap',
            marginBottom: '0.75rem' 
          }}>
            <a
              href={getAppUrl(deployingAppId)}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              Open App
            </a>
            <a
              href={`${getAppUrl(deployingAppId)}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              API Docs
            </a>
            <Link
              to="/dashboard"
              className="btn btn-secondary"
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              View in Dashboard
            </Link>
          </div>

          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            background: 'rgba(0, 0, 0, 0.2)',
            borderRadius: '0.25rem',
            fontSize: '0.75rem'
          }}>
            <code style={{ flex: 1, color: 'var(--text)' }}>{getAppUrl(deployingAppId)}</code>
            <button
              onClick={() => copyToClipboard(getAppUrl(deployingAppId), 'url')}
              className="btn btn-secondary"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
            >
              {copiedUrl ? 'Copied!' : 'Copy URL'}
            </button>
            <button
              onClick={() => copyToClipboard(getCurlSnippet(getAppUrl(deployingAppId)), 'curl')}
              className="btn btn-secondary"
              style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
            >
              {copiedCurl ? 'Copied!' : 'Copy curl'}
            </button>
          </div>
        </div>
      ) : success && (
        <div className="success" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <strong>Success!</strong> {success}
        </div>
      )}
      {validationMessage && (
        <div className="success" style={{ marginBottom: '0.5rem', padding: '0.75rem' }}>
          <strong>Validation:</strong> {validationMessage}
        </div>
      )}
      {(loading || isDeploying) && deploymentStatus?.deploy_phase && (
        <EventsTimeline
          events={deploymentStatus?.events || []}
          phase={deploymentStatus?.deploy_phase || 'validating'}
        />
      )}
    </div>
  )
}

export default NotificationsPanel
