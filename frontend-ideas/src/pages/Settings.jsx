import React, { useState } from 'react'
import './Settings.css'

const Settings = () => {
  const [settings, setSettings] = useState({
    appName: 'todo-api',
    framework: 'fastapi',
    pythonVersion: '3.11',
    autoDeploy: true,
    healthCheck: true,
    healthCheckPath: '/health'
  })

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>App Settings</h1>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          Save Changes
        </button>
      </div>

      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>General</h2>
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>App Name</label>
            <input
              type="text"
              value={settings.appName}
              onChange={(e) => setSettings({ ...settings, appName: e.target.value })}
              style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Framework</label>
            <select
              value={settings.framework}
              onChange={(e) => setSettings({ ...settings, framework: e.target.value })}
              style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
            >
              <option value="fastapi">FastAPI</option>
              <option value="fasthtml">FastHTML</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Python Version</label>
            <select
              value={settings.pythonVersion}
              onChange={(e) => setSettings({ ...settings, pythonVersion: e.target.value })}
              style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
            >
              <option value="3.11">3.11</option>
              <option value="3.10">3.10</option>
              <option value="3.9">3.9</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Deployment</h2>
        <div style={{ display: 'grid', gap: '1rem' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={settings.autoDeploy}
              onChange={(e) => setSettings({ ...settings, autoDeploy: e.target.checked })}
            />
            <span style={{ fontSize: '0.875rem' }}>Auto-deploy on push</span>
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={settings.healthCheck}
              onChange={(e) => setSettings({ ...settings, healthCheck: e.target.checked })}
            />
            <span style={{ fontSize: '0.875rem' }}>Enable health checks</span>
          </label>
          {settings.healthCheck && (
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Health Check Path</label>
              <input
                type="text"
                value={settings.healthCheckPath}
                onChange={(e) => setSettings({ ...settings, healthCheckPath: e.target.value })}
                style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
              />
            </div>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Danger Zone</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ padding: '1rem', border: '1px solid var(--error)', borderRadius: '0' }}>
            <div style={{ fontWeight: '500', marginBottom: '0.5rem' }}>Delete App</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.75rem' }}>
              Permanently delete this app and all its data. This action cannot be undone.
            </div>
            <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem', color: 'var(--error)' }}>
              Delete App
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Settings
