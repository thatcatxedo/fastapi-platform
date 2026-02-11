import React, { useState } from 'react'
import { Database, Key, Globe, Save } from 'lucide-react'
import './AppConfig.css'

const AppConfig = ({ app }) => {
  const [selectedDatabase, setSelectedDatabase] = useState('db-1')
  const [envVars, setEnvVars] = useState({
    'MONGO_URI': 'mongodb://localhost:27017',
    'API_KEY': '••••••••',
    'DEBUG': 'false'
  })

  const databases = [
    { id: 'db-1', name: 'my-app-db', status: 'connected' },
    { id: 'db-2', name: 'analytics-db', status: 'available' },
    { id: 'db-3', name: 'user-data-db', status: 'available' }
  ]

  const handleEnvVarChange = (key, value) => {
    setEnvVars(prev => ({
      ...prev,
      [key]: value
    }))
  }

  const handleAddEnvVar = () => {
    const key = prompt('Environment variable name:')
    if (key) {
      setEnvVars(prev => ({
        ...prev,
        [key]: ''
      }))
    }
  }

  return (
    <div className="app-config">
      <div className="config-section">
        <div className="config-section-header">
          <Database size={18} />
          <h4>Database Connection</h4>
        </div>
        <div className="config-content">
          <label className="config-label">Select Database</label>
          <select
            className="config-select"
            value={selectedDatabase}
            onChange={(e) => setSelectedDatabase(e.target.value)}
          >
            <option value="">None</option>
            {databases.map(db => (
              <option key={db.id} value={db.id}>
                {db.name} ({db.status})
              </option>
            ))}
          </select>
          <button className="config-link-btn">
            <Database size={14} />
            Create New Database
          </button>
        </div>
      </div>

      <div className="config-section">
        <div className="config-section-header">
          <Key size={18} />
          <h4>Environment Variables</h4>
        </div>
        <div className="config-content">
          {Object.entries(envVars).map(([key, value]) => (
            <div key={key} className="env-var-row">
              <input
                type="text"
                className="env-var-key"
                value={key}
                readOnly
                placeholder="KEY"
              />
              <input
                type={value.includes('•••') ? 'password' : 'text'}
                className="env-var-value"
                value={value}
                onChange={(e) => handleEnvVarChange(key, e.target.value)}
                placeholder="value"
              />
            </div>
          ))}
          <button className="config-add-btn" onClick={handleAddEnvVar}>
            + Add Variable
          </button>
        </div>
      </div>

      <div className="config-section">
        <div className="config-section-header">
          <Globe size={18} />
          <h4>App Settings</h4>
        </div>
        <div className="config-content">
          <div className="config-row">
            <label className="config-label">App URL</label>
            <div className="config-value">{app.url}</div>
          </div>
          <div className="config-row">
            <label className="config-label">Framework</label>
            <div className="config-value">{app.framework}</div>
          </div>
          <div className="config-row">
            <label className="config-label">Mode</label>
            <div className="config-value">{app.mode === 'single' ? 'Single File' : 'Multi-file'}</div>
          </div>
        </div>
      </div>

      <div className="config-footer">
        <button className="config-save-btn">
          <Save size={16} />
          Save Configuration
        </button>
      </div>
    </div>
  )
}

export default AppConfig
