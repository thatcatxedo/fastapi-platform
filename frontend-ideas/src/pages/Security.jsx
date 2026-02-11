import React, { useState } from 'react'
import SecretsManager from '../components/SecretsManager'
import ApiKeys from '../components/ApiKeys'
import SecurityScan from '../components/SecurityScan'
import './Security.css'

const Security = () => {
  const [activeTab, setActiveTab] = useState('secrets')

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Security</h1>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '0', marginBottom: '1.5rem', borderBottom: '1px solid var(--border)' }}>
        {[
          { id: 'secrets', label: 'Secrets' },
          { id: 'apikeys', label: 'API Keys' },
          { id: 'scan', label: 'Security Scan' }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'transparent',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid var(--primary)' : '2px solid transparent',
              color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-muted)',
              fontWeight: activeTab === tab.id ? '500' : '400',
              fontSize: '0.875rem',
              cursor: 'pointer',
              borderRadius: '0'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'secrets' && <SecretsManager />}
        {activeTab === 'apikeys' && <ApiKeys />}
        {activeTab === 'scan' && <SecurityScan />}
      </div>
    </div>
  )
}

export default Security
