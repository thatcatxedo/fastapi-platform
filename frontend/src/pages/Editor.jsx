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
  const [templates, setTemplates] = useState([])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [selectedComplexity, setSelectedComplexity] = useState('all')
  const [loadingTemplates, setLoadingTemplates] = useState(false)

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
    setSidebarOpen(false)
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
            setSuccess('App deployed successfully!')
            setTimeout(() => {
              navigate('/dashboard')
            }, 2000)
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
        return
      }

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

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          name: name.trim(),
          code: code
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
          {!isEditing && (
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              style={{
                padding: '0.5rem',
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                fontSize: '1.2rem'
              }}
              title="Toggle Templates"
            >
              {sidebarOpen ? 'Templates' : 'Show'}
            </button>
          )}
          <h1 style={{ margin: 0 }}>
            {isEditing ? 'Edit Application' : 'Create Application'}
          </h1>
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
            <strong>Success!</strong> {success}
            {deployingAppId && (
              <div style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                Your app will be available at: <code>{window.location.origin}/user/{user.id}/app/{deployingAppId}</code>
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

      {/* Main content area with sidebar */}
      <div style={{ 
        display: 'flex', 
        gap: '1rem', 
        flex: 1, 
        overflow: 'hidden',
        minHeight: 0
      }}>
        {/* Templates Sidebar */}
        {!isEditing && sidebarOpen && (
          <div style={{
            width: '300px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '0.5rem',
            padding: '1rem',
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0
          }}>
            <div style={{ marginBottom: '1rem' }}>
              <h2 style={{ margin: '0 0 0.75rem 0', fontSize: '1.1rem' }}>Application Templates</h2>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {['all', 'simple', 'medium', 'complex'].map(comp => (
                  <button
                    key={comp}
                    onClick={() => setSelectedComplexity(comp)}
                    style={{
                      padding: '0.25rem 0.5rem',
                      fontSize: '0.75rem',
                      background: selectedComplexity === comp ? 'var(--primary)' : 'var(--bg)',
                      color: selectedComplexity === comp ? 'white' : 'var(--text)',
                      border: '1px solid var(--border)',
                      borderRadius: '0.25rem',
                      cursor: 'pointer',
                      textTransform: 'capitalize'
                    }}
                  >
                    {comp}
                  </button>
                ))}
              </div>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {loadingTemplates ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  Loading templates...
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                  No templates found
                </div>
              ) : (
                filteredTemplates.map(template => (
                  <div
                    key={template.id}
                    style={{
                      background: 'var(--bg)',
                      border: '1px solid var(--border)',
                      borderRadius: '0.5rem',
                      padding: '0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--primary)'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.5rem' }}>
                      <h3 style={{ margin: 0, fontSize: '0.9rem', fontWeight: '600' }}>{template.name}</h3>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.15rem 0.4rem',
                        background: template.complexity === 'simple' ? '#10b981' : template.complexity === 'medium' ? '#f59e0b' : '#ef4444',
                        color: 'white',
                        borderRadius: '0.25rem',
                        textTransform: 'capitalize'
                      }}>
                        {template.complexity}
                      </span>
                    </div>
                    <p style={{ 
                      margin: '0 0 0.75rem 0', 
                      fontSize: '0.75rem', 
                      color: 'var(--text-muted)',
                      lineHeight: '1.4'
                    }}>
                      {template.description}
                    </p>
                    <button
                      onClick={() => handleUseTemplate(template)}
                      className="btn btn-primary"
                      style={{ 
                        width: '100%', 
                        padding: '0.5rem', 
                        fontSize: '0.75rem' 
                      }}
                    >
                      Load Template
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Main editor area */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minHeight: 0 }}>
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
            onChange={(value) => setCode(value || '')}
            theme="vs-dark"
            options={{
              minimap: { enabled: true },
              fontSize: 14,
              lineNumbers: 'on',
              roundedSelection: false,
              scrollBeyondLastLine: false,
              automaticLayout: true,
            }}
          />
        </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default EditorPage
