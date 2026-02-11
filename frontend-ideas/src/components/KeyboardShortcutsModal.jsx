import React from 'react'
import { X } from 'lucide-react'

const shortcuts = {
  'General': [
    { label: 'Open Command Palette', keys: ['Cmd', 'K'] },
    { label: 'Toggle Dark Mode', keys: ['Cmd', 'Shift', 'D'] },
    { label: 'Show Keyboard Shortcuts', keys: ['Cmd', '/'] },
    { label: 'Close Modal / Panel', keys: ['Esc'] },
  ],
  'Editor': [
    { label: 'Save File', keys: ['Cmd', 'S'] },
    { label: 'Deploy App', keys: ['Cmd', 'Enter'] },
    { label: 'New App', keys: ['Cmd', 'N'] },
  ],
}

const KeyboardShortcutsModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content shortcuts-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Keyboard Shortcuts</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="modal-body">
          {Object.entries(shortcuts).map(([group, items]) => (
            <div key={group} className="shortcuts-group">
              <div className="shortcuts-group-title">{group}</div>
              {items.map((shortcut, i) => (
                <div key={i} className="shortcut-row">
                  <span className="shortcut-label">{shortcut.label}</span>
                  <div className="shortcut-keys">
                    {shortcut.keys.map((key, j) => <kbd key={j}>{key}</kbd>)}
                  </div>
                </div>
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default KeyboardShortcutsModal
