import React, { useState } from 'react'
import { Plus, Database } from 'lucide-react'
import './Databases.css'

const Databases = () => {
  const [databases] = useState([
    {
      id: 'db-1',
      name: 'my-app-db',
      is_default: true,
      description: 'Production database for live apps',
      total_collections: 5,
      total_documents: 1234,
      total_size_mb: 2.4,
      mongo_database: 'my-app-db'
    },
    {
      id: 'db-2',
      name: 'analytics-db',
      is_default: false,
      description: 'Analytics and metrics storage',
      total_collections: 12,
      total_documents: 5678,
      total_size_mb: 15.8,
      mongo_database: 'analytics-db'
    }
  ])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Databases</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Refresh
          </button>
          <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            <Plus size={16} />
            New Database
          </button>
        </div>
      </div>

      <div style={{ marginBottom: '1rem', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        {databases.length} database{databases.length !== 1 ? 's' : ''} · {databases.reduce((sum, db) => sum + db.total_size_mb, 0)} MB total
      </div>

      {databases.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
          <h2 style={{ marginBottom: '0.5rem', fontWeight: '500' }}>No Databases</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Create your first database to get started.
          </p>
          <button className="btn btn-primary">
            + New Database
          </button>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {databases.map((db) => (
            <div key={db.id} className="card" style={{ padding: '1rem 1.25rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '1rem' }}>
                <div style={{ flex: 1, minWidth: '200px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    {db.is_default && <span style={{ color: 'var(--warning)' }}>★</span>}
                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: '500' }}>{db.name}</h3>
                    {db.is_default && (
                      <span style={{ fontSize: '0.75rem', padding: '0.125rem 0.5rem', background: 'var(--bg-light)', borderRadius: '0', border: '1px solid var(--border)', color: 'var(--text-muted)' }}>
                        Default
                      </span>
                    )}
                  </div>
                  {db.description && (
                    <p style={{ margin: '0.25rem 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                      {db.description}
                    </p>
                  )}
                  <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    {db.total_collections} collection{db.total_collections !== 1 ? 's' : ''} · {db.total_documents.toLocaleString()} documents · {db.total_size_mb} MB
                  </div>
                  <div style={{ marginTop: '0.25rem', fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                    {db.mongo_database}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  <button className="btn btn-primary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
                    View
                  </button>
                  {!db.is_default && (
                    <button className="btn btn-secondary" style={{ padding: '0.4rem 0.75rem', fontSize: '0.8rem' }}>
                      Set Default
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Databases
