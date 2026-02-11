import { useState, useCallback } from 'react'
import { API_URL } from '../../../config'
import styles from './TestPanel.module.css'

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']
const BODY_METHODS = new Set(['POST', 'PUT', 'PATCH'])

function TestPanel({ appId, deploymentStatus, onClose }) {
  const [method, setMethod] = useState('GET')
  const [path, setPath] = useState('/')
  const [headers, setHeaders] = useState([])
  const [showHeaders, setShowHeaders] = useState(false)
  const [body, setBody] = useState('')
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState(null)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  const isRunning = deploymentStatus?.status === 'running' && deploymentStatus?.deployment_ready

  const getStatusClass = (code) => {
    if (code >= 500) return styles.statusServerError
    if (code >= 400) return styles.statusClientError
    if (code >= 300) return styles.statusRedirect
    return styles.statusSuccess
  }

  const formatBody = (body) => {
    if (body === null || body === undefined) return ''
    if (typeof body === 'object') {
      try {
        return JSON.stringify(body, null, 2)
      } catch {
        return String(body)
      }
    }
    // Try to parse and re-format if it's a JSON string
    if (typeof body === 'string') {
      try {
        return JSON.stringify(JSON.parse(body), null, 2)
      } catch {
        return body
      }
    }
    return String(body)
  }

  const sendRequest = useCallback(async () => {
    if (loading) return

    setLoading(true)
    setError(null)
    setResponse(null)

    const reqPath = path.startsWith('/') ? path : `/${path}`

    // Build headers dict from array
    const headersDict = {}
    for (const h of headers) {
      if (h.key.trim()) {
        headersDict[h.key.trim()] = h.value
      }
    }

    const proxyBody = {
      method,
      path: reqPath,
      headers: Object.keys(headersDict).length > 0 ? headersDict : null,
    }

    // Parse body for methods that support it
    if (BODY_METHODS.has(method) && body.trim()) {
      try {
        proxyBody.body = JSON.parse(body)
      } catch {
        proxyBody.body = body
      }
    }

    try {
      const token = localStorage.getItem('token')
      const res = await fetch(`${API_URL}/api/apps/${appId}/proxy`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(proxyBody),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => null)
        const msg = errData?.detail?.message || errData?.detail || `Request failed (${res.status})`
        setError(msg)
        return
      }

      const data = await res.json()
      setResponse(data)

      // Add to history
      setHistory(prev => [
        {
          method,
          path: reqPath,
          status_code: data.status_code,
          latency_ms: data.latency_ms,
          headers: [...headers],
          body,
        },
        ...prev.slice(0, 19),
      ])
    } catch (err) {
      setError(err.message || 'Request failed')
    } finally {
      setLoading(false)
    }
  }, [appId, method, path, headers, body, loading])

  const loadFromHistory = (entry) => {
    setMethod(entry.method)
    setPath(entry.path)
    setHeaders(entry.headers || [])
    setBody(entry.body || '')
    setShowHistory(false)
  }

  const addHeader = () => {
    setHeaders(prev => [...prev, { key: '', value: '' }])
  }

  const updateHeader = (index, field, value) => {
    setHeaders(prev => prev.map((h, i) => i === index ? { ...h, [field]: value } : h))
  }

  const removeHeader = (index) => {
    setHeaders(prev => prev.filter((_, i) => i !== index))
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendRequest()
    }
  }

  return (
    <div className={styles.testPanel}>
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.headerTitle}>Test API</span>
        {response && (
          <button
            className={styles.headerBtn}
            onClick={() => { setResponse(null); setError(null) }}
          >
            Clear
          </button>
        )}
        <button className={styles.closeBtn} onClick={onClose} title="Close test panel">
          ×
        </button>
      </div>

      {/* Request Builder */}
      <div className={styles.requestSection}>
        <div className={styles.methodAndPath}>
          <select
            className={styles.methodSelect}
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            {METHODS.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <input
            className={styles.pathInput}
            type="text"
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="/endpoint"
          />
        </div>

        {/* Headers (collapsible) */}
        <button
          className={styles.sectionToggle}
          onClick={() => setShowHeaders(!showHeaders)}
        >
          Headers {headers.length > 0 ? `(${headers.length})` : ''} {showHeaders ? '▾' : '▸'}
        </button>

        {showHeaders && (
          <div className={styles.headersSection}>
            {headers.map((h, i) => (
              <div key={i} className={styles.headerRow}>
                <input
                  className={styles.headerKeyInput}
                  type="text"
                  value={h.key}
                  onChange={(e) => updateHeader(i, 'key', e.target.value)}
                  placeholder="Header name"
                />
                <input
                  className={styles.headerValueInput}
                  type="text"
                  value={h.value}
                  onChange={(e) => updateHeader(i, 'value', e.target.value)}
                  placeholder="Value"
                />
                <button className={styles.removeBtn} onClick={() => removeHeader(i)}>×</button>
              </div>
            ))}
            <button className={styles.addBtn} onClick={addHeader}>+ Add Header</button>
          </div>
        )}

        {/* Body (only for POST/PUT/PATCH) */}
        {BODY_METHODS.has(method) && (
          <div className={styles.bodySection}>
            <span className={styles.bodyLabel}>Request Body (JSON)</span>
            <textarea
              className={styles.bodyInput}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder='{"key": "value"}'
            />
          </div>
        )}

        <button
          className={`btn btn-primary ${styles.sendButton}`}
          onClick={sendRequest}
          disabled={loading || !isRunning}
          title={!isRunning ? 'Deploy the app first' : ''}
        >
          {loading ? (
            <>
              <span className={styles.sendSpinner} />
              Sending...
            </>
          ) : (
            'Send Request'
          )}
        </button>

        {!isRunning && (
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center' }}>
            App must be running to send requests
          </span>
        )}
      </div>

      {/* Response Area */}
      <div className={styles.responseSection}>
        {error && (
          <div className={styles.errorDisplay}>{error}</div>
        )}

        {response && (
          <>
            <div className={styles.responseMeta}>
              <span className={`${styles.statusBadge} ${getStatusClass(response.status_code)}`}>
                {response.status_code}
              </span>
              <span className={styles.latency}>{Math.round(response.latency_ms)}ms</span>
              <span className={styles.responseUrl} title={response.url}>{response.url}</span>
            </div>
            <pre className={styles.responseBody}>
              {formatBody(response.body)}
            </pre>
          </>
        )}

        {!response && !error && (
          <div className={styles.emptyState}>
            <div className={styles.emptyText}>
              Send a request to see the response
            </div>
          </div>
        )}
      </div>

      {/* History (collapsible at bottom) */}
      {history.length > 0 && (
        <div className={styles.historySection}>
          <button
            className={styles.sectionToggle}
            onClick={() => setShowHistory(!showHistory)}
            style={{ padding: '0.5rem 0.75rem', borderBottom: showHistory ? '1px solid var(--border)' : 'none' }}
          >
            History ({history.length}) {showHistory ? '▾' : '▸'}
          </button>
          {showHistory && (
            <div className={styles.historyList}>
              {history.map((entry, i) => (
                <div
                  key={i}
                  className={styles.historyItem}
                  onClick={() => loadFromHistory(entry)}
                >
                  <span className={styles.historyMethod}>{entry.method}</span>
                  <span className={styles.historyPath}>{entry.path}</span>
                  <span className={`${styles.historyStatus} ${getStatusClass(entry.status_code)}`}>
                    {entry.status_code}
                  </span>
                  <span className={styles.historyLatency}>{Math.round(entry.latency_ms)}ms</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TestPanel
