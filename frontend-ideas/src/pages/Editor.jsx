import React, { useState } from 'react'
import CodeEditor from '../components/CodeEditor'
import AIChat from '../components/AIChat'
import AppConfig from '../components/AppConfig'
import { FileCode, Settings, MessageSquare, X } from 'lucide-react'
import './Editor.css'

const Editor = ({ app }) => {
  const [mode, setMode] = useState(app?.mode || 'single')
  const [showChat, setShowChat] = useState(false)
  const [showConfig, setShowConfig] = useState(false)
  const [name, setName] = useState(app?.name || 'new-app')
  const [files, setFiles] = useState({
    'app.py': `from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
`
  })

  const handleFileChange = (filename, content) => {
    setFiles(prev => ({
      ...prev,
      [filename]: content
    }))
  }

  return (
    <div className="editor-layout">
      <div className="editor-header">
        <div className="editor-header-left">
          <div className="editor-app-info">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              style={{
                fontSize: '16px',
                fontWeight: '400',
                padding: '4px 8px',
                border: '1px solid var(--border)',
                borderRadius: '0',
                background: 'var(--bg)',
                color: 'var(--text)'
              }}
            />
            <span className="app-status running">● Running</span>
          </div>
        </div>
        <div className="editor-header-center">
          {!app && (
            <div className="mode-toggle">
              <button
                className={`mode-btn ${mode === 'single' ? 'active' : ''}`}
                onClick={() => setMode('single')}
              >
                <FileCode size={16} />
                Single File
              </button>
              <button
                className={`mode-btn ${mode === 'multi' ? 'active' : ''}`}
                onClick={() => setMode('multi')}
              >
                <FileCode size={16} />
                Multi-File
              </button>
            </div>
          )}
        </div>
        <div className="editor-header-right">
          <button
            className={`header-btn ${showChat ? 'active' : ''}`}
            onClick={() => setShowChat(!showChat)}
          >
            <MessageSquare size={18} />
            AI Assistant
          </button>
          <button
            className={`header-btn ${showConfig ? 'active' : ''}`}
            onClick={() => setShowConfig(!showConfig)}
          >
            <Settings size={18} />
            Config
          </button>
          <button className="btn-deploy">Deploy</button>
        </div>
      </div>

      <div className="editor-content">
        <div className="editor-main">
          <CodeEditor
            mode={mode}
            files={files}
            onFileChange={handleFileChange}
            framework={app?.framework || 'fastapi'}
          />
        </div>

        {showChat && (
          <div className="editor-sidebar chat-sidebar">
            <div className="sidebar-header">
              <h3>AI Assistant</h3>
              <button
                className="sidebar-close"
                onClick={() => setShowChat(false)}
              >
                <X size={18} />
              </button>
            </div>
            <AIChat appName={name} />
          </div>
        )}

        {showConfig && (
          <div className="editor-sidebar config-sidebar">
            <div className="sidebar-header">
              <h3>App Configuration</h3>
              <button
                className="sidebar-close"
                onClick={() => setShowConfig(false)}
              >
                <X size={18} />
              </button>
            </div>
            <AppConfig app={app || { name, url: `https://app-${name}.gatorlunch.com`, framework: 'fastapi', mode }} />
          </div>
        )}
      </div>
    </div>
  )
}

export default Editor
