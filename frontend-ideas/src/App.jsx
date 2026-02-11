import React, { useState, useMemo } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider, useTheme } from './context/ThemeContext'
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts'
import Dashboard from './pages/Dashboard'
import Databases from './pages/Databases'
import Activity from './pages/Activity'
import Settings from './pages/Settings'
import Sidebar from './components/Sidebar'
import CommandPalette from './components/CommandPalette'
import KeyboardShortcutsModal from './components/KeyboardShortcutsModal'
import './App.css'

function AppContent() {
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)
  const [shortcutsModalOpen, setShortcutsModalOpen] = useState(false)
  const { toggleTheme } = useTheme()

  const [user] = useState({ username: 'demo', is_admin: false })
  const [apps] = useState([
    { app_id: 'app-1', name: 'todo-api', status: 'running' },
    { app_id: 'app-2', name: 'weather-dashboard', status: 'running' },
    { app_id: 'app-3', name: 'kanban-board', status: 'stopped' },
  ])

  const shortcuts = useMemo(() => [
    { key: 'k', ctrl: true, action: () => setCommandPaletteOpen(true) },
    { key: '/', ctrl: true, action: () => setShortcutsModalOpen(true) },
    { key: 'd', ctrl: true, shift: true, action: toggleTheme },
    { key: 'Escape', ctrl: false, action: () => { setCommandPaletteOpen(false); setShortcutsModalOpen(false) } },
  ], [toggleTheme])

  useKeyboardShortcuts(shortcuts)

  return (
    <BrowserRouter>
      <div className="ide-layout">
        <Sidebar
          user={user}
          apps={apps}
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
        />
        <main className="ide-main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/editor" element={<Dashboard />} />
            <Route path="/editor/:appId" element={<Dashboard />} />
            <Route path="/database" element={<Databases />} />
            <Route path="/activity" element={<Activity />} />
            <Route path="/deployments" element={<Activity />} />
            <Route path="/analytics" element={<Dashboard />} />
            <Route path="/performance" element={<Dashboard />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/security" element={<Settings />} />
          </Routes>
        </main>
      </div>

      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        apps={apps}
      />

      <KeyboardShortcutsModal
        isOpen={shortcutsModalOpen}
        onClose={() => setShortcutsModalOpen(false)}
      />
    </BrowserRouter>
  )
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  )
}

export default App
