import React, { useState } from 'react'
import Editor from '@monaco-editor/react'
import { FileText, X } from 'lucide-react'
import './CodeEditor.css'

const CodeEditor = ({ mode, files, onFileChange, framework }) => {
  const [activeFile, setActiveFile] = useState(Object.keys(files)[0] || 'app.py')
  const [fileTabs, setFileTabs] = useState(Object.keys(files))

  const defaultFiles = {
    'app.py': `from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI!"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
`,
    'models.py': `from pydantic import BaseModel
from typing import Optional

class Item(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
`,
    'database.py': `from pymongo import MongoClient
import os

client = MongoClient(os.getenv("MONGO_URI"))
db = client.get_default_database()
`,
    'utils.py': `def format_response(data):
    return {"status": "success", "data": data}
`,
    'config.py': `import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
APP_NAME = os.getenv("APP_NAME", "My App")
`
  }

  const currentFiles = mode === 'multi' 
    ? { ...defaultFiles, ...files }
    : files

  const handleEditorChange = (value) => {
    onFileChange(activeFile, value || '')
  }

  const handleTabClick = (filename) => {
    setActiveFile(filename)
    if (!fileTabs.includes(filename)) {
      setFileTabs([...fileTabs, filename])
    }
  }

  const handleTabClose = (e, filename) => {
    e.stopPropagation()
    if (fileTabs.length > 1) {
      const newTabs = fileTabs.filter(f => f !== filename)
      setFileTabs(newTabs)
      if (activeFile === filename) {
        setActiveFile(newTabs[0])
      }
    }
  }

  const addNewFile = () => {
    const newFilename = `file_${fileTabs.length + 1}.py`
    onFileChange(newFilename, '')
    setFileTabs([...fileTabs, newFilename])
    setActiveFile(newFilename)
  }

  return (
    <div className="code-editor-container">
      {mode === 'multi' && (
        <div className="file-tabs">
          <div className="tabs-scroll">
            {fileTabs.map(filename => (
              <div
                key={filename}
                className={`file-tab ${activeFile === filename ? 'active' : ''}`}
                onClick={() => handleTabClick(filename)}
              >
                <FileText size={14} />
                <span>{filename}</span>
                {fileTabs.length > 1 && (
                  <button
                    className="tab-close"
                    onClick={(e) => handleTabClose(e, filename)}
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
          <button className="add-file-btn" onClick={addNewFile}>
            +
          </button>
        </div>
      )}
      
      <div className="editor-wrapper">
        <Editor
          height="100%"
          language="python"
          theme="vs-dark"
          value={currentFiles[activeFile] || ''}
          onChange={handleEditorChange}
          options={{
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            roundedSelection: false,
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            formatOnPaste: true,
            formatOnType: true,
          }}
        />
      </div>

      <div className="editor-footer">
        <div className="footer-info">
          <span>{framework || 'FastAPI'}</span>
          <span>•</span>
          <span>{mode === 'single' ? 'Single file mode' : 'Multi-file mode'}</span>
          <span>•</span>
          <span>{activeFile}</span>
        </div>
        <div className="footer-actions">
          <button className="footer-btn">Format</button>
          <button className="footer-btn">Save</button>
        </div>
      </div>
    </div>
  )
}

export default CodeEditor
