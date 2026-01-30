import { useState, useCallback, useRef, useEffect } from 'react'
import Editor from '@monaco-editor/react'

const FASTAPI_FILES = ['app.py', 'routes.py', 'models.py', 'services.py', 'helpers.py']
const FASTHTML_FILES = ['app.py', 'routes.py', 'models.py', 'services.py', 'components.py']

export default function MultiFileEditor({
  files,
  framework = 'fastapi',
  onChange,
  onMount,
  readOnly = false,
  errorLine = null,
  errorFile = null
}) {
  const [activeFile, setActiveFile] = useState('app.py')
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const decorationsRef = useRef([])
  const containerRef = useRef(null)
  const [editorHeight, setEditorHeight] = useState(400)

  const fileOrder = framework === 'fasthtml' ? FASTHTML_FILES : FASTAPI_FILES

  // Calculate editor height based on container
  useEffect(() => {
    if (!containerRef.current) return

    const updateHeight = () => {
      const containerRect = containerRef.current.getBoundingClientRect()
      const availableHeight = window.innerHeight - containerRect.top - 20
      setEditorHeight(Math.max(300, availableHeight))
    }

    updateHeight()
    const resizeObserver = new ResizeObserver(updateHeight)
    resizeObserver.observe(containerRef.current)
    window.addEventListener('resize', updateHeight)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', updateHeight)
    }
  }, [])

  // Handle error highlighting
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return

    // Clear existing decorations
    decorationsRef.current = editorRef.current.deltaDecorations(
      decorationsRef.current,
      []
    )

    // Add error decoration if on active file
    if (errorLine && errorFile === activeFile) {
      decorationsRef.current = editorRef.current.deltaDecorations(
        [],
        [{
          range: new monacoRef.current.Range(errorLine, 1, errorLine, 1),
          options: {
            isWholeLine: true,
            glyphMarginClassName: 'error-glyph-margin',
            className: 'error-line-highlight'
          }
        }]
      )
      // Scroll to error line
      editorRef.current.revealLineInCenter(errorLine)
    }
  }, [errorLine, errorFile, activeFile])

  const handleEditorMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco

    // Forward refs to parent
    if (onMount) {
      onMount({ editorRef, monacoRef, decorationsRef })
    }
  }, [onMount])

  const handleFileChange = useCallback((value) => {
    if (onChange && files) {
      onChange({
        ...files,
        [activeFile]: value || ''
      })
    }
  }, [onChange, files, activeFile])

  const handleTabClick = (filename) => {
    setActiveFile(filename)
  }

  // Handle keyboard shortcuts
  const handleKeyDown = useCallback((e) => {
    // Forward Ctrl+S, Ctrl+Enter, Ctrl+Shift+V to parent via custom events
    if (e.ctrlKey || e.metaKey) {
      if (e.key === 's') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('editor-save-draft'))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('editor-deploy'))
      } else if (e.shiftKey && e.key === 'V') {
        e.preventDefault()
        window.dispatchEvent(new CustomEvent('editor-validate'))
      }
    }
  }, [])

  return (
    <div className="multifile-editor" ref={containerRef}>
      {/* File tabs */}
      <div className="file-tabs">
        {fileOrder.map(filename => (
          <button
            key={filename}
            className={`file-tab ${activeFile === filename ? 'active' : ''} ${errorFile === filename ? 'has-error' : ''}`}
            onClick={() => handleTabClick(filename)}
          >
            {filename}
            {errorFile === filename && <span className="error-indicator">!</span>}
          </button>
        ))}
      </div>

      {/* Monaco Editor */}
      <div
        className="editor-container"
        onKeyDown={handleKeyDown}
        style={{ height: editorHeight }}
      >
        <Editor
          height="100%"
          language="python"
          theme="vs-dark"
          value={files?.[activeFile] || ''}
          onChange={handleFileChange}
          onMount={handleEditorMount}
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            readOnly: readOnly,
            glyphMargin: true,
            folding: true,
            automaticLayout: true
          }}
        />
      </div>

      <style>{`
        .multifile-editor {
          display: flex;
          flex-direction: column;
          height: 100%;
        }

        .file-tabs {
          display: flex;
          gap: 2px;
          padding: 8px 8px 0;
          background: #1e1e1e;
          border-bottom: 1px solid #333;
          overflow-x: auto;
        }

        .file-tab {
          padding: 8px 16px;
          background: #2d2d2d;
          border: none;
          border-radius: 4px 4px 0 0;
          color: #888;
          font-size: 13px;
          cursor: pointer;
          transition: all 0.15s ease;
          position: relative;
          white-space: nowrap;
        }

        .file-tab:hover {
          background: #3d3d3d;
          color: #ccc;
        }

        .file-tab.active {
          background: #1e1e1e;
          color: #fff;
          border-bottom: 2px solid #007acc;
        }

        .file-tab.has-error {
          color: #f48771;
        }

        .file-tab.has-error.active {
          border-bottom-color: #f48771;
        }

        .error-indicator {
          display: inline-block;
          margin-left: 6px;
          width: 16px;
          height: 16px;
          line-height: 16px;
          text-align: center;
          background: #f48771;
          color: #1e1e1e;
          border-radius: 50%;
          font-size: 11px;
          font-weight: bold;
        }

        .editor-container {
          flex: 1;
          min-height: 300px;
        }

        .error-glyph-margin {
          background: #f48771;
          width: 4px !important;
          margin-left: 3px;
        }

        .error-line-highlight {
          background: rgba(244, 135, 113, 0.15);
        }
      `}</style>
    </div>
  )
}

export { FASTAPI_FILES, FASTHTML_FILES }
