import { useState, useEffect, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_URL } from '../../../App'

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

function useAppState(appId) {
  const navigate = useNavigate()
  
  // Core state
  const [code, setCode] = useState(DEFAULT_TEMPLATE)
  const [name, setName] = useState('')
  const [envVars, setEnvVars] = useState([])
  const [isEditing, setIsEditing] = useState(false)
  
  // Draft/Version tracking state
  const [deployedCode, setDeployedCode] = useState(null)
  const [hasUnpublishedChanges, setHasUnpublishedChanges] = useState(false)
  const [lastSavedCode, setLastSavedCode] = useState(null)
  const [savingDraft, setSavingDraft] = useState(false)
  const [draftSaved, setDraftSaved] = useState(false)
  
  // UI state
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [validationMessage, setValidationMessage] = useState('')
  
  // Deployment state
  const [deploymentStatus, setDeploymentStatus] = useState(null)
  const [deployingAppId, setDeployingAppId] = useState(null)
  const [deployStage, setDeployStage] = useState('draft')
  const [deployStartTime, setDeployStartTime] = useState(null)
  const [deployDuration, setDeployDuration] = useState(null)
  
  // Refs for editor
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const decorationsRef = useRef([])

  // Fetch app data if editing
  useEffect(() => {
    if (appId) {
      fetchApp()
    }
  }, [appId])

  const parseApiError = (data, fallback) => {
    if (!data) return fallback
    if (typeof data.detail === 'string') return data.detail
    if (data.detail?.message) return data.detail.message
    if (data.message) return data.message
    return fallback
  }

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
      }
      
      // Track deployed code for change detection
      setDeployedCode(app.deployed_code || app.code)
      setLastSavedCode(app.code)
      setHasUnpublishedChanges(app.has_unpublished_changes || false)
    } catch (err) {
      setError(err.message)
    }
  }

  const pollDeploymentStatus = useCallback(async (targetAppId) => {
    const maxAttempts = 30
    let attempts = 0

    const checkStatus = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`${API_URL}/api/apps/${targetAppId}/deploy-status`, {
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
            // Reset change tracking after successful deploy
            setDeployedCode(code)
            setLastSavedCode(code)
            setHasUnpublishedChanges(false)
            
            setSuccess('App deployed successfully!')
            setTimeout(() => {
              navigate('/dashboard')
            }, 3000)
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
        setTimeout(checkStatus, 2000)
      } else {
        setError('Deployment is taking longer than expected. Check the dashboard for status.')
        setLoading(false)
      }
      return false
    }

    checkStatus()
  }, [deployStartTime, navigate, code])

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

      navigate('/dashboard')
    } catch (err) {
      setError(err.message)
      setSuccess('')
    }
  }

  const handleSaveDraft = useCallback(async () => {
    if (!appId || !isEditing) return
    
    // Don't save if code hasn't changed from last save
    if (code === lastSavedCode) {
      setSuccess('No changes to save')
      setTimeout(() => setSuccess(''), 2000)
      return
    }

    setError('')
    setSavingDraft(true)
    setDraftSaved(false)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/apps/${appId}/draft`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
      })

      const data = await response.json()

      if (!response.ok) {
        const message = parseApiError(data, 'Failed to save draft')
        throw new Error(message)
      }

      setLastSavedCode(code)
      setHasUnpublishedChanges(data.has_unpublished_changes)
      setDraftSaved(true)
      setSuccess('Draft saved')
      
      // Clear the "saved" message after a short delay
      setTimeout(() => {
        setDraftSaved(false)
        setSuccess('')
      }, 2000)
    } catch (err) {
      setError(err.message)
    } finally {
      setSavingDraft(false)
    }
  }, [appId, isEditing, code, lastSavedCode])

  // Editor helpers
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

  const setEditorRefs = (editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
  }

  // Compute if there are unsaved local changes (editor differs from last save)
  const hasLocalChanges = code !== lastSavedCode && lastSavedCode !== null

  return {
    // Core state
    code,
    setCode,
    name,
    setName,
    envVars,
    setEnvVars,
    isEditing,
    
    // Draft/Version tracking
    deployedCode,
    hasUnpublishedChanges,
    hasLocalChanges,
    savingDraft,
    draftSaved,
    
    // UI state
    loading,
    validating,
    error,
    setError,
    success,
    setSuccess,
    validationMessage,
    
    // Deployment state
    deploymentStatus,
    deployingAppId,
    deployStage,
    deployDuration,
    
    // Actions
    handleValidate,
    handleDeploy,
    handleDelete,
    handleSaveDraft,
    
    // Editor helpers
    setEditorRefs,
    clearErrorHighlight,
    
    // Refs (exposed for keyboard shortcuts)
    editorRef,
    monacoRef
  }
}

export { DEFAULT_TEMPLATE }
export default useAppState
