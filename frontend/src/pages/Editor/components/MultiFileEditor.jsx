import { useState, useCallback, useRef, useEffect } from 'react'
import Editor from '@monaco-editor/react'
import styles from './MultiFileEditor.module.css'

const FASTAPI_FILES = ['app.py', 'routes.py', 'models.py', 'services.py', 'helpers.py']
const FASTHTML_FILES = ['app.py', 'routes.py', 'models.py', 'services.py', 'components.py']

const EXTENSION_TO_LANGUAGE = {
  '.py': 'python',
  '.css': 'css',
  '.js': 'javascript',
  '.html': 'html',
  '.json': 'json',
  '.txt': 'plaintext',
  '.svg': 'xml'
}

const ADD_FILE_TEMPLATES = [
  { label: 'Python', ext: '.py', defaultName: 'module.py', content: '# ' },
  { label: 'CSS', ext: '.css', defaultName: 'static/styles.css', content: '/*  */' },
  { label: 'JavaScript', ext: '.js', defaultName: 'static/script.js', content: '// ' },
  { label: 'HTML', ext: '.html', defaultName: 'static/index.html', content: '<!DOCTYPE html>\n<html>\n<head><meta charset="utf-8"><title></title></head>\n<body></body>\n</html>' },
  { label: 'JSON', ext: '.json', defaultName: 'static/data.json', content: '{}' },
  { label: 'SVG', ext: '.svg', defaultName: 'static/icon.svg', content: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="currentColor" d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>' },
  { label: 'Text', ext: '.txt', defaultName: 'static/readme.txt', content: '' }
]

function getLanguage(filename) {
  const ext = filename.includes('.') ? '.' + filename.split('.').pop().toLowerCase() : ''
  return EXTENSION_TO_LANGUAGE[ext] || 'plaintext'
}

function getUniqueFilename(files, baseName) {
  if (!files || !(baseName in files)) return baseName
  const lastDot = baseName.lastIndexOf('.')
  const base = lastDot >= 0 ? baseName.slice(0, lastDot) : baseName
  const ext = lastDot >= 0 ? baseName.slice(lastDot) : '.py'
  let i = 1
  while (`${base}${i}${ext}` in files) i++
  return `${base}${i}${ext}`
}

function sortFileList(files, entrypoint) {
  const keys = Object.keys(files || {})
  return [...keys].sort((a, b) => {
    if (a === entrypoint) return -1
    if (b === entrypoint) return 1
    return a.localeCompare(b)
  })
}

export default function MultiFileEditor({
  files,
  framework = 'fastapi',
  entrypoint = 'app.py',
  onChange,
  onMount,
  readOnly = false,
  errorLine = null,
  errorFile = null
}) {
  const [activeFile, setActiveFile] = useState('app.py')
  const [showAddMenu, setShowAddMenu] = useState(false)
  const [editingRename, setEditingRename] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const editorRef = useRef(null)
  const monacoRef = useRef(null)
  const decorationsRef = useRef([])
  const containerRef = useRef(null)
  const addMenuRef = useRef(null)
  const [editorHeight, setEditorHeight] = useState(400)

  const fileList = sortFileList(files, entrypoint)

  // Ensure activeFile exists when files change
  useEffect(() => {
    if (files && !(activeFile in files) && fileList.length > 0) {
      setActiveFile(fileList[0])
    }
  }, [files, activeFile, fileList])

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

  // Close add menu on outside click
  useEffect(() => {
    if (!showAddMenu) return
    const handleClick = (e) => {
      if (addMenuRef.current && !addMenuRef.current.contains(e.target)) {
        setShowAddMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showAddMenu])

  // Handle error highlighting
  useEffect(() => {
    if (!editorRef.current || !monacoRef.current) return
    decorationsRef.current = editorRef.current.deltaDecorations(decorationsRef.current, [])
    if (errorLine && errorFile === activeFile) {
      decorationsRef.current = editorRef.current.deltaDecorations([], [{
        range: new monacoRef.current.Range(errorLine, 1, errorLine, 1),
        options: {
          isWholeLine: true,
          glyphMarginClassName: styles.errorGlyphMargin,
          className: styles.errorLineHighlight
        }
      }])
      editorRef.current.revealLineInCenter(errorLine)
    }
  }, [errorLine, errorFile, activeFile])

  const handleEditorMount = useCallback((editor, monaco) => {
    editorRef.current = editor
    monacoRef.current = monaco
    if (onMount) onMount({ editorRef, monacoRef, decorationsRef })
  }, [onMount])

  const handleFileChange = useCallback((value) => {
    if (onChange && files) {
      onChange({ ...files, [activeFile]: value || '' })
    }
  }, [onChange, files, activeFile])

  const handleAddFile = (template) => {
    if (!onChange || !files) return
    const newName = getUniqueFilename(files, template.defaultName)
    onChange({ ...files, [newName]: template.content })
    setActiveFile(newName)
    setShowAddMenu(false)
  }

  const handleRename = (oldName) => {
    setEditingRename(oldName)
    setRenameValue(oldName)
  }

  const handleRenameSubmit = () => {
    if (!onChange || !files || !editingRename) return
    if (editingRename === entrypoint) return
    const trimmed = renameValue.trim()
    if (!trimmed || trimmed === editingRename) {
      setEditingRename(null)
      return
    }
    if (trimmed in files) {
      setEditingRename(null)
      return
    }
    const newFiles = { ...files }
    newFiles[trimmed] = newFiles[editingRename]
    delete newFiles[editingRename]
    onChange(newFiles)
    if (activeFile === editingRename) setActiveFile(trimmed)
    setEditingRename(null)
  }

  const handleDelete = (filename) => {
    if (!onChange || !files || filename === entrypoint) return
    const newFiles = { ...files }
    delete newFiles[filename]
    onChange(newFiles)
    if (activeFile === filename && fileList.length > 1) {
      const idx = fileList.indexOf(filename)
      const next = idx > 0 ? fileList[idx - 1] : fileList[idx + 1]
      setActiveFile(next)
    }
  }

  const handleKeyDown = useCallback((e) => {
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

  const handleRenameKeyDown = (e) => {
    if (e.key === 'Enter') handleRenameSubmit()
    if (e.key === 'Escape') setEditingRename(null)
  }

  return (
    <div className={styles.multifileEditor} ref={containerRef}>
      <div className={styles.fileListSidebar}>
        <div className={styles.fileListHeader}>
          <span className={styles.fileListTitle}>Files</span>
          <div className={styles.addFileDropdown} ref={addMenuRef}>
            <button
              type="button"
              className={styles.addFileBtn}
              onClick={() => setShowAddMenu(!showAddMenu)}
              disabled={readOnly}
              title="Add file"
            >
              + Add
            </button>
            {showAddMenu && (
              <div className={styles.addFileMenu}>
                {ADD_FILE_TEMPLATES.map((t) => (
                  <button
                    key={t.ext}
                    type="button"
                    className={styles.addFileMenuItem}
                    onClick={() => handleAddFile(t)}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <div className={styles.fileList}>
          {fileList.map((filename) => {
            const isEntrypoint = filename === entrypoint
            const isActive = activeFile === filename
            const hasError = errorFile === filename

            if (editingRename === filename) {
              return (
                <div key={filename} className={styles.fileItem} style={{ flexDirection: 'column', alignItems: 'stretch' }}>
                  <input
                    type="text"
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onKeyDown={handleRenameKeyDown}
                    onBlur={handleRenameSubmit}
                    autoFocus
                    className={styles.fileItemName}
                    style={{ background: '#2d2d2d', border: '1px solid #444', color: '#fff', padding: '4px' }}
                  />
                </div>
              )
            }

            return (
              <div
                key={filename}
                className={`${styles.fileItem} ${isActive ? styles.active : ''} ${hasError ? styles.hasError : ''}`}
                onClick={() => setActiveFile(filename)}
              >
                <span className={styles.fileItemName} title={filename}>
                  {isEntrypoint && <span className={styles.entrypointBadge}>app</span>}
                  {filename}
                </span>
                {hasError && <span className={styles.errorIndicator}>!</span>}
                <div className={styles.fileItemActions} onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className={styles.fileActionBtn}
                    onClick={() => handleRename(filename)}
                    disabled={isEntrypoint}
                    title="Rename"
                  >
                    ✎
                  </button>
                  <button
                    type="button"
                    className={styles.fileActionBtn}
                    onClick={() => handleDelete(filename)}
                    disabled={isEntrypoint}
                    title="Delete"
                  >
                    ×
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <div className={styles.editorWrapper}>
        <div
          className={styles.editorContainer}
          onKeyDown={handleKeyDown}
          style={{ height: editorHeight }}
        >
          <Editor
            height="100%"
            language={getLanguage(activeFile)}
            theme="vs-dark"
            value={files?.[activeFile] ?? ''}
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
      </div>
    </div>
  )
}

export { FASTAPI_FILES, FASTHTML_FILES }
