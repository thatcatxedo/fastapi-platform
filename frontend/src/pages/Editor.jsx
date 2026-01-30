import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { API_URL } from '../App'
import EventsTimeline from '../components/EventsTimeline'

const DEFAULT_TEMPLATE = `from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# Your code here - create models, routes, and logic!
# Example:
# class Item(BaseModel):
#     name: str
#     price: float
#
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}
`

// Helper to get app URL using subdomain routing
const getAppUrl = (appId) => {
  const appDomain = import.meta.env.VITE_APP_DOMAIN ||
    window.location.hostname.replace(/^platform\./, '')
  return `https://app-${appId}.${appDomain}`
}

function EditorPage({ user }) {
  const { appId } = useParams()
  const navigate = useNavigate()
  const [code, setCode] = useState(DEFAULT_TEMPLATE)
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [isEditing, setIsEditing] = useState(false)
  const [deploymentStatus, setDeploymentStatus] = useState(null)
  const [deployingAppId, setDeployingAppId] = useState(null)
  const [deployStage, setDeployStage] = useState('draft')
  const [validationMessage, setValidationMessage] = useState('')
  const [editorHeight, setEditorHeight] = useState(500)
  const editorContainerRef = useRef(null)
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const decorationsRef = useRef([])
  const [templates, setTemplates] = useState([])
  const [templatesModalOpen, setTemplatesModalOpen] = useState(false)
  const [selectedComplexity, setSelectedComplexity] = useState('all')
  const [loadingTemplates, setLoadingTemplates] = useState(false)
  const [envVars, setEnvVars] = useState([])  // [{key: '', value: ''}]
  const [showEnvValues, setShowEnvValues] = useState({})  // {index: true/false}
  const [envVarsExpanded, setEnvVarsExpanded] = useState(false)
  const [deployStartTime, setDeployStartTime] = useState(null)
  const [deployDuration, setDeployDuration] = useState(null)
  const [copiedCurl, setCopiedCurl] = useState(false)

  useEffect(() => {
    if (appId) {
      fetchApp()
    } else {
      fetchTemplates()
    }
  }, [appId])

  const fetchTemplates = async () => {
    setLoadingTemplates(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setTemplates(data)
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    } finally {
      setLoadingTemplates(false)
    }
  }

  const handleUseTemplate = (template) => {
    setCode(template.code)
    setName(template.name)
    setSuccess(`Template "${template.name}" loaded. Edit the code before deployment.`)
    setError('')
    setTemplatesModalOpen(false)
  }

  const filteredTemplates = templates.filter(t => 
    selectedComplexity === 'all' || t.complexity === selectedComplexity
  )

  useEffect(() => {
    const updateEditorHeight = () => {
      if (editorContainerRef.current) {
        const rect = editorContainerRef.current.getBoundingClientRect()
        setEditorHeight(Math.max(300, rect.height))
      }
    }

    updateEditorHeight()
    
    // Use ResizeObserver for more accurate updates
    const resizeObserver = new ResizeObserver(() => {
      updateEditorHeight()
    })
    
    if (editorContainerRef.current) {
      resizeObserver.observe(editorContainerRef.current)
    }
    
    window.addEventListener('resize', updateEditorHeight)
    
    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateEditorHeight)
    }
  }, [error, success, deploymentStatus, name])

  const fetchApp = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        throw new Error('Failed to fetch app')
      }

      const app = await response.json()
      setCode(app.code)
      setName(app.name)
      setIsEditing(true)
      setDeployStage(app.deploy_stage || app.status || 'draft')
      if (app.error_message) {
        setError(app.error_message)
      }
      // Load existing env vars
      if (app.env_vars && Object.keys(app.env_vars).length > 0) {
        const envVarsList = Object.entries(app.env_vars).map(([key, value]) => ({ key, value }))
        setEnvVars(envVarsList)
        setEnvVarsExpanded(true)
      }
    } catch (err) {
      setError(err.message)
    }
  }

  const parseApiError = (data, fallback) => {
    if (!data) return fallback
    if (typeof data.detail === 'string') return data.detail
    if (data.detail?.message) return data.detail.message
    if (data.message) return data.message
    return fallback
  }

  const pollDeploymentStatus = async (appId) => {
    const maxAttempts = 30
    let attempts = 0
    
    const checkStatus = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`${API_URL}/api/apps/${appId}/deploy-status`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
        
        if (response.ok) {
          const status = await response.json()
          setDeploymentStatus(status)
          setDeployStage(status.deploy_stage || status.status || 'deploying')
          
          if (status.status === 'running' && status.deployment_ready) {
            // Calculate deploy duration
            if (deployStartTime) {
              const duration = ((Date.now() - deployStartTime) / 1000).toFixed(1)
              setDeployDuration(duration)
            }
            setSuccess('App deployed successfully!')
            setTimeout(() => {
              navigate('/dashboard')
            }, 3000)  // Give a bit more time to see the duration
            return true
          } else if (status.status === 'error') {
            setError(status.last_error || status.error_message || 'Deployment failed')
            setLoading(false)
            return true
          }
        }
      } catch (err) {
        console.error('Error checking status:', err)
      }
      
      attempts++
      if (attempts < maxAttempts) {
        setTimeout(checkStatus, 2000) // Check every 2 seconds
      } else {
        setError('Deployment is taking longer than expected. Check the dashboard for status.')
        setLoading(false)
      }
      return false
    }
    
    checkStatus()
  }

  const handleValidate = async () => {
    if (!name.trim()) {
      setError('App name is required')
      return
    }
    setError('')
    setSuccess('')
    setValidating(true)
    setDeployStage('validating')
    setValidationMessage('')

    try {
      const token = localStorage.getItem('token')
      const url = isEditing
        ? `${API_URL}/api/apps/${appId}/validate`
        : `${API_URL}/api/apps/validate`

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      })

      const data = await response.json()
      if (!response.ok) {
        const message = parseApiError(data, 'Validation failed')
        throw new Error(message)
      }

      if (!data.valid) {
        setDeployStage('error')
        setError(data.message || 'Validation failed')
        if (data.line) {
          highlightErrorLine(data.line)
        }
        return
      }
      clearErrorHighlight()

      setValidationMessage(data.message || 'Code validation passed')
      setDeployStage('validated')
      setSuccess('Validation passed. Ready to deploy.')
    } catch (err) {
      setDeployStage('error')
      setError(err.message)
    } finally {
      setValidating(false)
    }
  }

  const handleDeploy = async () => {
    if (!name.trim()) {
      setError('App name is required')
      return
    }

    setError('')
    setSuccess('')
    setLoading(true)
    setDeployStage('deploying')
    setValidationMessage('')
    setDeployDuration(null)

    if (!window.confirm(`Deploy "${name.trim()}" now?`)) {
      setLoading(false)
      setDeployStage('draft')
      return
    }

    try {
      const token = localStorage.getItem('token')
      const url = isEditing
        ? `${API_URL}/api/apps/${appId}`
        : `${API_URL}/api/apps`

      const method = isEditing ? 'PUT' : 'POST'
      setDeployStartTime(Date.now())

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name.trim(),
          code: code,
          env_vars: envVars.reduce((acc, { key, value }) => {
            if (key.trim()) acc[key.trim()] = value
            return acc
          }, {})
        })
      })

      const data = await response.json()

      if (!response.ok) {
        const message = parseApiError(data, 'Deployment failed')
        throw new Error(message)
      }

      setDeployingAppId(data.app_id)
      pollDeploymentStatus(data.app_id)
    } catch (err) {
      setError(err.message)
      setLoading(false)
      setDeploymentStatus(null)
    }
  }

  const handleDelete = async () => {
    if (!appId) return

    if (!window.confirm(`Are you sure you want to delete "${name.trim() || 'this app'}"? This action cannot be undone.`)) {
      return
    }

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        const errorMsg = parseApiError(data, 'Failed to delete app')
        throw new Error(errorMsg)
      }

      // Navigate to dashboard after successful deletion
      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
      setSuccess('')
    }
  }

  // Env vars helpers
  const addEnvVar = () => {
    setEnvVars([...envVars, { key: '', value: '' }])
    setEnvVarsExpanded(true)
  }

  const removeEnvVar = (index) => {
    setEnvVars(envVars.filter((_, i) => i !== index))
    const newShowValues = { ...showEnvValues }
    delete newShowValues[index]
    setShowEnvValues(newShowValues)
  }

  const updateEnvVar = (index, field, value) => {
    const newEnvVars = [...envVars]
    newEnvVars[index][field] = value
    setEnvVars(newEnvVars)
  }

  const toggleShowValue = (index) => {
    setShowEnvValues({ ...showEnvValues, [index]: !showEnvValues[index] })
  }

  const isValidEnvVarKey = (key) => {
    return /^[A-Z_][A-Z0-9_]*$/i.test(key)
  }

  // Monaco editor handlers
  const handleEditorMount = (editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco

    // Keyboard shortcuts
    // Ctrl/Cmd + S = Prevent browser save dialog
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Future: save draft. For now, just prevent default.
    })

    // Ctrl/Cmd + Enter = Deploy
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      handleDeploy()
    })

    // Ctrl/Cmd + Shift + V = Validate
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyV,
      () => handleValidate()
    )
  }

  // Copy to clipboard helper
  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedCurl(true)
      setTimeout(() => setCopiedCurl(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const getCurlSnippet = (url) => {
    return `curl ${url}`
  }

  const highlightErrorLine = (lineNumber) => {
    if (!editorRef.current || !monacoRef.current || !lineNumber) return

    decorationsRef.current = editorRef.current.deltaDecorations(
      decorationsRef.current,
      [{
        range: new monacoRef.current.Range(lineNumber, 1, lineNumber, 1),
        options: {
          isWholeLine: true,
          className: 'error-line-highlight',
          glyphMarginClassName: 'error-line-glyph'
        }
      }]
    )

    // Scroll to error line
    editorRef.current.revealLineInCenter(lineNumber)
  }

  const clearErrorHighlight = () => {
    if (editorRef.current) {
      decorationsRef.current = editorRef.current.deltaDecorations(
        decorationsRef.current,
        []
      )
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: 'calc(100vh - 140px)',
      minHeight: 0,
      overflow: 'hidden'
    }}>
      {/* Header with title and action buttons */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        marginBottom: '1rem',
        flexShrink: 0
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <h1 style={{ margin: 0 }}>
            {isEditing ? 'Edit Application' : 'Create Application'}
          </h1>
          {!isEditing && (
            <button
              onClick={() => setTemplatesModalOpen(true)}
              className="btn btn-secondary"
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              Browse Templates
            </button>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button
            className="btn btn-secondary"
            onClick={handleValidate}
            disabled={validating || loading}
          >
            {validating ? 'Validating...' : 'Validate'}
          </button>
          <button
            className="btn btn-primary"
            onClick={handleDeploy}
            disabled={loading || validating || (deploymentStatus && deploymentStatus.status === 'deploying')}
            style={{ position: 'relative' }}
          >
            {loading || (deploymentStatus && deploymentStatus.status === 'deploying') ? (
              <>
                <span style={{ marginRight: '0.5rem' }}>•••</span>
                {isEditing ? 'Updating...' : 'Deploying...'}
              </>
            ) : (
              isEditing ? 'Update Application' : 'Deploy Application'
            )}
          </button>
          <button
            className="btn btn-secondary"
            onClick={() => navigate('/dashboard')}
          >
            Cancel
          </button>
          {isEditing && (
            <button
              className="btn btn-danger"
              onClick={handleDelete}
              disabled={loading || validating}
              style={{ padding: '0.5rem 1rem' }}
            >
              Delete App
            </button>
          )}
        </div>
      </div>

      {/* Messages section - compact */}
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
        {deploymentStatus && deploymentStatus.status === 'deploying' && (
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
        {deployingAppId && (loading || (deploymentStatus && deploymentStatus.status === 'deploying')) && (
          <EventsTimeline
            appId={deployingAppId}
            isDeploying={true}
          />
        )}
      </div>

      {/* Main content area */}
      <div style={{ 
        flex: 1, 
        overflow: 'hidden',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column'
      }}>
          {/* App Name input - compact */}
          <div style={{
            marginBottom: '0.75rem',
            padding: '0.5rem 0.75rem',
            background: 'var(--bg-light)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            flexShrink: 0
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <label style={{
                margin: 0,
                fontSize: '0.75rem',
                color: 'var(--text-muted)',
                whiteSpace: 'nowrap',
                fontWeight: '500'
              }}>
                App Name:
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="fastapi-application"
                required
                style={{
                  flex: 1,
                  padding: '0.375rem 0.5rem',
                  fontSize: '0.875rem',
                  background: 'var(--bg)',
                  border: '1px solid var(--border)',
                  borderRadius: '0.375rem',
                  color: 'var(--text)',
                  outline: 'none'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--primary)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
              />
            </div>
          </div>

          {/* Environment Variables - collapsible */}
          <div style={{
            marginBottom: '0.75rem',
            background: 'var(--bg-light)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            flexShrink: 0
          }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '0.5rem 0.75rem',
                cursor: 'pointer'
              }}
              onClick={() => setEnvVarsExpanded(!envVarsExpanded)}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {envVarsExpanded ? '▼' : '▶'}
                </span>
                <label style={{
                  margin: 0,
                  fontSize: '0.75rem',
                  color: 'var(--text-muted)',
                  fontWeight: '500',
                  cursor: 'pointer'
                }}>
                  Environment Variables {envVars.length > 0 && `(${envVars.length})`}
                </label>
              </div>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); addEnvVar(); }}
                className="btn btn-secondary"
                style={{ padding: '0.25rem 0.5rem', fontSize: '0.7rem' }}
              >
                + Add
              </button>
            </div>

            {envVarsExpanded && (
              <div style={{ padding: '0 0.75rem 0.75rem 0.75rem' }}>
                {envVars.length === 0 ? (
                  <div style={{
                    color: 'var(--text-muted)',
                    fontSize: '0.75rem',
                    padding: '0.5rem',
                    textAlign: 'center'
                  }}>
                    No environment variables. Click "+ Add" to add one.
                    <br />
                    <span style={{ fontSize: '0.7rem' }}>
                      Access in code: <code>import os; os.environ.get("KEY")</code>
                    </span>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {envVars.map((env, index) => (
                      <div key={index} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                        <input
                          type="text"
                          value={env.key}
                          onChange={(e) => updateEnvVar(index, 'key', e.target.value.toUpperCase())}
                          placeholder="KEY_NAME"
                          style={{
                            flex: 1,
                            padding: '0.375rem 0.5rem',
                            fontSize: '0.8rem',
                            background: 'var(--bg)',
                            border: `1px solid ${env.key && !isValidEnvVarKey(env.key) ? 'var(--error)' : 'var(--border)'}`,
                            borderRadius: '0.375rem',
                            color: 'var(--text)',
                            fontFamily: 'monospace'
                          }}
                        />
                        <div style={{ flex: 2, display: 'flex', gap: '0.25rem' }}>
                          <input
                            type={showEnvValues[index] ? 'text' : 'password'}
                            value={env.value}
                            onChange={(e) => updateEnvVar(index, 'value', e.target.value)}
                            placeholder="value"
                            style={{
                              flex: 1,
                              padding: '0.375rem 0.5rem',
                              fontSize: '0.8rem',
                              background: 'var(--bg)',
                              border: '1px solid var(--border)',
                              borderRadius: '0.375rem',
                              color: 'var(--text)',
                              fontFamily: 'monospace'
                            }}
                          />
                          <button
                            type="button"
                            onClick={() => toggleShowValue(index)}
                            style={{
                              padding: '0.25rem 0.5rem',
                              fontSize: '0.7rem',
                              background: 'var(--bg)',
                              border: '1px solid var(--border)',
                              borderRadius: '0.375rem',
                              color: 'var(--text-muted)',
                              cursor: 'pointer',
                              minWidth: '45px'
                            }}
                            title={showEnvValues[index] ? 'Hide value' : 'Show value'}
                          >
                            {showEnvValues[index] ? 'Hide' : 'Show'}
                          </button>
                        </div>
                        <button
                          type="button"
                          onClick={() => removeEnvVar(index)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            fontSize: '0.8rem',
                            background: 'transparent',
                            border: '1px solid var(--border)',
                            borderRadius: '0.375rem',
                            color: 'var(--error)',
                            cursor: 'pointer'
                          }}
                          title="Remove"
                        >
                          ×
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Code Editor - takes remaining space */}
          <div className="card" style={{ 
            padding: '1rem', 
            flex: 1, 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'hidden',
            minHeight: 0
          }}>
        <div style={{ marginBottom: '0.75rem', flexShrink: 0 }}>
          <h2 style={{ marginBottom: '0.25rem', fontSize: '1rem' }}>Code Editor</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', margin: 0 }}>
            Write FastAPI code. Ensure app = FastAPI() is defined.
          </p>
        </div>

        <div 
          ref={editorContainerRef}
          style={{ 
            border: '1px solid var(--border)', 
            borderRadius: '0.5rem', 
            overflow: 'hidden',
            flex: 1,
            minHeight: 0
          }}
        >
          <Editor
            height={editorHeight}
            defaultLanguage="python"
            value={code}
            onChange={(value) => {
              setCode(value || '')
              clearErrorHighlight()
            }}
            onMount={handleEditorMount}
            theme="vs-dark"
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              automaticLayout: true,
              glyphMargin: true,
            }}
          />
        </div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.5rem', textAlign: 'right' }}>
          <kbd style={{ padding: '0.1rem 0.3rem', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.2rem' }}>Ctrl+Enter</kbd> Deploy
          {' • '}
          <kbd style={{ padding: '0.1rem 0.3rem', background: 'var(--bg)', border: '1px solid var(--border)', borderRadius: '0.2rem' }}>Ctrl+Shift+V</kbd> Validate
        </div>
        </div>
      </div>

      {/* Templates Modal */}
      {templatesModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem'
          }}
          onClick={() => setTemplatesModalOpen(false)}
        >
          <div
            style={{
              background: 'var(--bg)',
              border: '1px solid var(--border)',
              borderRadius: '0.75rem',
              width: '100%',
              maxWidth: '800px',
              maxHeight: '90vh',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              padding: '1.5rem',
              borderBottom: '1px solid var(--border)'
            }}>
              <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Application Templates</h2>
              <button
                onClick={() => setTemplatesModalOpen(false)}
                style={{
                  padding: '0.5rem',
                  background: 'transparent',
                  border: 'none',
                  fontSize: '1.5rem',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  lineHeight: 1
                }}
                title="Close"
              >
                ×
              </button>
            </div>

            {/* Modal Content */}
            <div style={{
              padding: '1.5rem',
              overflowY: 'auto',
              flex: 1
            }}>
              {/* Complexity Filter */}
              <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {['all', 'simple', 'medium', 'complex'].map(comp => (
                    <button
                      key={comp}
                      onClick={() => setSelectedComplexity(comp)}
                      style={{
                        padding: '0.5rem 1rem',
                        fontSize: '0.875rem',
                        background: selectedComplexity === comp ? 'var(--primary)' : 'var(--bg-light)',
                        color: selectedComplexity === comp ? 'white' : 'var(--text)',
                        border: '1px solid var(--border)',
                        borderRadius: '0.5rem',
                        cursor: 'pointer',
                        textTransform: 'capitalize',
                        fontWeight: selectedComplexity === comp ? '600' : '400'
                      }}
                    >
                      {comp}
                    </button>
                  ))}
                </div>
              </div>

              {/* Templates Grid */}
              {loadingTemplates ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  Loading templates...
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                  No templates found
                </div>
              ) : (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
                  gap: '1rem'
                }}>
                  {filteredTemplates.map(template => (
                    <div
                      key={template.id}
                      style={{
                        background: 'var(--bg-light)',
                        border: '1px solid var(--border)',
                        borderRadius: '0.5rem',
                        padding: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        transition: 'all 0.2s',
                        cursor: 'pointer'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.borderColor = 'var(--primary)'
                        e.currentTarget.style.transform = 'translateY(-2px)'
                        e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.borderColor = 'var(--border)'
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.boxShadow = 'none'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
                        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>{template.name}</h3>
                        <span style={{
                          fontSize: '0.7rem',
                          padding: '0.2rem 0.5rem',
                          background: template.complexity === 'simple' ? '#10b981' : template.complexity === 'medium' ? '#f59e0b' : '#ef4444',
                          color: 'white',
                          borderRadius: '0.25rem',
                          textTransform: 'capitalize',
                          fontWeight: '500'
                        }}>
                          {template.complexity}
                        </span>
                      </div>
                      <p style={{ 
                        margin: '0 0 1rem 0', 
                        fontSize: '0.875rem', 
                        color: 'var(--text-muted)',
                        lineHeight: '1.5',
                        flex: 1
                      }}>
                        {template.description}
                      </p>
                      <button
                        onClick={() => handleUseTemplate(template)}
                        className="btn btn-primary"
                        style={{ 
                          width: '100%', 
                          padding: '0.625rem', 
                          fontSize: '0.875rem',
                          fontWeight: '500'
                        }}
                      >
                        Load Template
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EditorPage
