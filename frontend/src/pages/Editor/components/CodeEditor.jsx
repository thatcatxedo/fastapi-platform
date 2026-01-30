import { useState, useEffect, useRef } from 'react'
import Editor from '@monaco-editor/react'

function CodeEditor({
  code,
  onChange,
  onMount,
  onDeploy,
  onValidate
}) {
  const [editorHeight, setEditorHeight] = useState(500)
  const editorContainerRef = useRef(null)

  useEffect(() => {
    const updateEditorHeight = () => {
      if (editorContainerRef.current) {
        const rect = editorContainerRef.current.getBoundingClientRect()
        setEditorHeight(Math.max(300, rect.height))
      }
    }

    updateEditorHeight()

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
  }, [])

  const handleEditorMount = (editor, monaco) => {
    // Keyboard shortcuts
    // Ctrl/Cmd + S = Prevent browser save dialog
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      // Future: save draft. For now, just prevent default.
    })

    // Ctrl/Cmd + Enter = Deploy
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onDeploy()
    })

    // Ctrl/Cmd + Shift + V = Validate
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.KeyV,
      () => onValidate()
    )

    // Pass refs to parent
    if (onMount) {
      onMount(editor, monaco)
    }
  }

  return (
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
          onChange={(value) => onChange(value || '')}
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
  )
}

export default CodeEditor
