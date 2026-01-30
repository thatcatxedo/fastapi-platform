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

// Default multi-file templates
const DEFAULT_FASTAPI_FILES = {
  'app.py': `from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import router

app = FastAPI(title="My API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}
`,
  'routes.py': `from fastapi import APIRouter, HTTPException
from models import Item, ItemCreate
from services import get_items, get_item, create_item, delete_item

router = APIRouter(prefix="/api")

@router.get("/items")
def list_items():
    return get_items()

@router.get("/items/{item_id}")
def read_item(item_id: str):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.post("/items")
def add_item(item: ItemCreate):
    return create_item(item)

@router.delete("/items/{item_id}")
def remove_item(item_id: str):
    return delete_item(item_id)
`,
  'models.py': `from pydantic import BaseModel
from typing import Optional

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None

class Item(ItemCreate):
    id: str
`,
  'services.py': `from pymongo import MongoClient
from bson import ObjectId
import os

db = MongoClient(os.environ["PLATFORM_MONGO_URI"]).get_default_database()

def get_items():
    items = list(db.items.find())
    return [{"id": str(item["_id"]), **{k: v for k, v in item.items() if k != "_id"}} for item in items]

def get_item(item_id: str):
    item = db.items.find_one({"_id": ObjectId(item_id)})
    if item:
        return {"id": str(item["_id"]), **{k: v for k, v in item.items() if k != "_id"}}
    return None

def create_item(item):
    result = db.items.insert_one(item.model_dump())
    return {"id": str(result.inserted_id), **item.model_dump()}

def delete_item(item_id: str):
    db.items.delete_one({"_id": ObjectId(item_id)})
    return {"success": True}
`,
  'helpers.py': `"""Utility functions for the app."""

def format_id(obj_id) -> str:
    """Convert ObjectId to string."""
    return str(obj_id)
`
}

const DEFAULT_FASTHTML_FILES = {
  'app.py': `from fasthtml.common import *
from routes import setup_routes

app, rt = fast_app()
setup_routes(rt)

@rt("/health")
def health():
    return {"status": "ok"}
`,
  'routes.py': `from fasthtml.common import *
from services import get_items, create_item, delete_item
from components import item_list, item_form, page_layout

def setup_routes(rt):
    @rt("/")
    def home():
        items = get_items()
        return page_layout(
            H1("My Items"),
            item_form(),
            item_list(items)
        )

    @rt("/items", methods=["POST"])
    def add_item(name: str):
        create_item(name)
        items = get_items()
        return item_list(items)

    @rt("/items/{item_id}", methods=["DELETE"])
    def remove_item(item_id: str):
        delete_item(item_id)
        items = get_items()
        return item_list(items)
`,
  'models.py': `"""Data models for the app."""
from dataclasses import dataclass
from typing import Optional

@dataclass
class Item:
    id: str
    name: str
    description: Optional[str] = None
`,
  'services.py': `from pymongo import MongoClient
from bson import ObjectId
import os

db = MongoClient(os.environ["PLATFORM_MONGO_URI"]).get_default_database()

def get_items():
    items = list(db.items.find())
    return [{"id": str(item["_id"]), "name": item["name"]} for item in items]

def create_item(name: str):
    db.items.insert_one({"name": name})

def delete_item(item_id: str):
    db.items.delete_one({"_id": ObjectId(item_id)})
`,
  'components.py': `from fasthtml.common import *

def page_layout(*children):
    return Titled("FastHTML App", *children)

def item_form():
    return Form(
        Input(name="name", placeholder="Item name", required=True),
        Button("Add Item"),
        hx_post="/items",
        hx_target="#item-list",
        hx_swap="outerHTML"
    )

def item_list(items):
    return Ul(
        *[item_row(item) for item in items],
        id="item-list"
    )

def item_row(item):
    return Li(
        Span(item["name"]),
        Button("x",
            hx_delete=f"/items/{item['id']}",
            hx_target="#item-list",
            hx_swap="outerHTML"
        )
    )
`
}

function useAppState(appId) {
  const navigate = useNavigate()

  // Core state
  const [code, setCode] = useState(DEFAULT_TEMPLATE)
  const [name, setName] = useState('')
  const [envVars, setEnvVars] = useState([])
  const [isEditing, setIsEditing] = useState(false)

  // Multi-file state
  const [mode, setMode] = useState('single')  // 'single' or 'multi'
  const [framework, setFramework] = useState('fastapi')  // 'fastapi' or 'fasthtml'
  const [files, setFiles] = useState(null)
  const [entrypoint, setEntrypoint] = useState('app.py')

  // Draft/Version tracking state
  const [deployedCode, setDeployedCode] = useState(null)
  const [deployedFiles, setDeployedFiles] = useState(null)
  const [hasUnpublishedChanges, setHasUnpublishedChanges] = useState(false)
  const [lastSavedCode, setLastSavedCode] = useState(null)
  const [lastSavedFiles, setLastSavedFiles] = useState(null)
  const [savingDraft, setSavingDraft] = useState(false)
  const [draftSaved, setDraftSaved] = useState(false)

  // UI state
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [validationMessage, setValidationMessage] = useState('')

  // Validation error tracking for multi-file
  const [errorLine, setErrorLine] = useState(null)
  const [errorFile, setErrorFile] = useState(null)

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

      // Handle multi-file vs single-file mode
      const appMode = app.mode || 'single'
      setMode(appMode)

      if (appMode === 'multi') {
        setFramework(app.framework || 'fastapi')
        setEntrypoint(app.entrypoint || 'app.py')
        setFiles(app.files || {})
        setDeployedFiles(app.deployed_files || app.files || {})
        setLastSavedFiles(app.files || {})
      } else {
        setCode(app.code)
        setDeployedCode(app.deployed_code || app.code)
        setLastSavedCode(app.code)
      }

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
            if (mode === 'multi') {
              setDeployedFiles(files)
              setLastSavedFiles(files)
            } else {
              setDeployedCode(code)
              setLastSavedCode(code)
            }
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
  }, [deployStartTime, navigate, code, files, mode])

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
    setErrorLine(null)
    setErrorFile(null)

    try {
      const token = localStorage.getItem('token')
      const url = isEditing
        ? `${API_URL}/api/apps/${appId}/validate`
        : `${API_URL}/api/apps/validate`

      // Build request body based on mode
      const body = mode === 'multi'
        ? { files, entrypoint }
        : { code }

      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
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
          setErrorLine(data.line)
          if (mode === 'multi' && data.file) {
            setErrorFile(data.file)
          } else {
            highlightErrorLine(data.line)
          }
        }
        return
      }
      clearErrorHighlight()
      setErrorLine(null)
      setErrorFile(null)

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

      // Build request body based on mode
      const body = {
        name: name.trim(),
        env_vars: envVars.reduce((acc, { key, value }) => {
          if (key.trim()) acc[key.trim()] = value
          return acc
        }, {})
      }

      if (mode === 'multi') {
        body.files = files
        // Only include these for new apps
        if (!isEditing) {
          body.mode = 'multi'
          body.framework = framework
          body.entrypoint = entrypoint
        }
      } else {
        body.code = code
        if (!isEditing) {
          body.mode = 'single'
        }
      }

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
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

    // Don't save if content hasn't changed from last save
    if (mode === 'multi') {
      if (JSON.stringify(files) === JSON.stringify(lastSavedFiles)) {
        setSuccess('No changes to save')
        setTimeout(() => setSuccess(''), 2000)
        return
      }
    } else {
      if (code === lastSavedCode) {
        setSuccess('No changes to save')
        setTimeout(() => setSuccess(''), 2000)
        return
      }
    }

    setError('')
    setSavingDraft(true)
    setDraftSaved(false)

    try {
      const token = localStorage.getItem('token')

      // Build request body based on mode
      const body = mode === 'multi' ? { files } : { code }

      const response = await fetch(`${API_URL}/api/apps/${appId}/draft`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      })

      const data = await response.json()

      if (!response.ok) {
        const message = parseApiError(data, 'Failed to save draft')
        throw new Error(message)
      }

      if (mode === 'multi') {
        setLastSavedFiles(files)
      } else {
        setLastSavedCode(code)
      }
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
  }, [appId, isEditing, code, lastSavedCode, files, lastSavedFiles, mode])

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
  const hasLocalChanges = mode === 'multi'
    ? (files && lastSavedFiles && JSON.stringify(files) !== JSON.stringify(lastSavedFiles))
    : (code !== lastSavedCode && lastSavedCode !== null)

  // Initialize multi-file mode for new apps
  const initMultiFileMode = useCallback((newFramework = 'fastapi') => {
    setMode('multi')
    setFramework(newFramework)
    setEntrypoint('app.py')
    const defaultFiles = newFramework === 'fasthtml' ? DEFAULT_FASTHTML_FILES : DEFAULT_FASTAPI_FILES
    setFiles({ ...defaultFiles })
    setLastSavedFiles(null)
    setDeployedFiles(null)
  }, [])

  // Switch back to single-file mode for new apps
  const initSingleFileMode = useCallback(() => {
    setMode('single')
    setCode(DEFAULT_TEMPLATE)
    setFiles(null)
    setLastSavedCode(null)
    setDeployedCode(null)
  }, [])

  return {
    // Core state
    code,
    setCode,
    name,
    setName,
    envVars,
    setEnvVars,
    isEditing,

    // Multi-file state
    mode,
    setMode,
    framework,
    setFramework,
    files,
    setFiles,
    entrypoint,

    // Draft/Version tracking
    deployedCode,
    deployedFiles,
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

    // Validation error tracking
    errorLine,
    errorFile,

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
    initMultiFileMode,
    initSingleFileMode,

    // Editor helpers
    setEditorRefs,
    clearErrorHighlight,

    // Refs (exposed for keyboard shortcuts)
    editorRef,
    monacoRef
  }
}

export { DEFAULT_TEMPLATE, DEFAULT_FASTAPI_FILES, DEFAULT_FASTHTML_FILES }
export default useAppState
