import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Layout, Database, Settings, Sun, Moon, Rocket, Plus, Activity, FileCode, Command, Keyboard } from 'lucide-react'
import { useTheme } from '../context/ThemeContext'

const CommandPalette = ({ isOpen, onClose, apps = [] }) => {
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef(null)
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()

  const commands = useMemo(() => {
    const items = [
      { id: 'new-app', title: 'New App', description: 'Create a new application', icon: Plus, category: 'Actions', shortcut: ['⌘', 'N'], action: () => navigate('/editor') },
      { id: 'dashboard', title: 'Dashboard', description: 'Go to dashboard', icon: Layout, category: 'Navigation', action: () => navigate('/dashboard') },
      { id: 'database', title: 'Database', description: 'Manage databases', icon: Database, category: 'Navigation', action: () => navigate('/database') },
      { id: 'activity', title: 'Activity Log', description: 'View recent activity', icon: Activity, category: 'Navigation', action: () => navigate('/activity') },
      { id: 'settings', title: 'Settings', description: 'App settings', icon: Settings, category: 'Navigation', action: () => navigate('/settings') },
      { id: 'toggle-theme', title: theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode', description: 'Toggle color theme', icon: theme === 'dark' ? Sun : Moon, category: 'Actions', shortcut: ['⌘', '⇧', 'D'], action: toggleTheme },
      { id: 'shortcuts', title: 'Keyboard Shortcuts', description: 'View all shortcuts', icon: Keyboard, category: 'Help', shortcut: ['⌘', '/'], action: () => {} },
    ]

    apps.forEach(app => {
      items.push({
        id: `app-${app.app_id}`,
        title: app.name,
        description: `Open ${app.name} in editor`,
        icon: FileCode,
        category: 'Apps',
        action: () => navigate(`/editor/${app.app_id}`)
      })
      if (app.status === 'running') {
        items.push({
          id: `deploy-${app.app_id}`,
          title: `Deploy ${app.name}`,
          description: 'Redeploy application',
          icon: Rocket,
          category: 'Actions',
          action: () => navigate(`/editor/${app.app_id}`)
        })
      }
    })

    return items
  }, [apps, theme, navigate, toggleTheme])

  const filteredCommands = useMemo(() => {
    if (!query) return commands
    const q = query.toLowerCase()
    return commands.filter(cmd =>
      cmd.title.toLowerCase().includes(q) ||
      cmd.description.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q)
    )
  }, [commands, query])

  const groupedCommands = useMemo(() => {
    const groups = {}
    filteredCommands.forEach(cmd => {
      if (!groups[cmd.category]) groups[cmd.category] = []
      groups[cmd.category].push(cmd)
    })
    return groups
  }, [filteredCommands])

  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setActiveIndex(0)
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [isOpen])

  useEffect(() => {
    setActiveIndex(0)
  }, [query])

  const handleKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActiveIndex(i => Math.min(i + 1, filteredCommands.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActiveIndex(i => Math.max(i - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      const cmd = filteredCommands[activeIndex]
      if (cmd) {
        cmd.action()
        onClose()
      }
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!isOpen) return null

  let currentIndex = 0

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div className="command-palette" onClick={e => e.stopPropagation()}>
        <div className="command-palette-input-wrapper">
          <Search size={18} />
          <input
            ref={inputRef}
            type="text"
            className="command-palette-input"
            placeholder="Search commands..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
        </div>
        <div className="command-palette-results">
          {filteredCommands.length === 0 ? (
            <div className="command-palette-empty">No results found</div>
          ) : (
            Object.entries(groupedCommands).map(([category, items]) => (
              <div key={category} className="command-palette-group">
                <div className="command-palette-group-title">{category}</div>
                {items.map(cmd => {
                  const isActive = currentIndex === activeIndex
                  const idx = currentIndex
                  currentIndex++
                  const Icon = cmd.icon
                  return (
                    <div
                      key={cmd.id}
                      className={`command-palette-item ${isActive ? 'active' : ''}`}
                      onClick={() => { cmd.action(); onClose() }}
                      onMouseEnter={() => setActiveIndex(idx)}
                    >
                      <div className="command-palette-item-icon">
                        <Icon size={16} />
                      </div>
                      <div className="command-palette-item-content">
                        <div className="command-palette-item-title">{cmd.title}</div>
                        <div className="command-palette-item-description">{cmd.description}</div>
                      </div>
                      {cmd.shortcut && (
                        <div className="command-palette-item-shortcut">
                          {cmd.shortcut.map((key, i) => <kbd key={i}>{key}</kbd>)}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ))
          )}
        </div>
        <div className="command-palette-footer">
          <div className="command-palette-footer-hint">
            <span><kbd>↑</kbd><kbd>↓</kbd> Navigate</span>
            <span><kbd>↵</kbd> Select</span>
            <span><kbd>esc</kbd> Close</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CommandPalette
