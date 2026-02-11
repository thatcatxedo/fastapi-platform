import React, { useState } from 'react'
import './Documentation.css'

const Documentation = () => {
  const [selectedEndpoint, setSelectedEndpoint] = useState(null)

  const endpoints = [
    {
      method: 'GET',
      path: '/api/items',
      summary: 'List all items',
      parameters: [],
      responses: {
        '200': { description: 'Successful response', schema: 'Item[]' }
      }
    },
    {
      method: 'POST',
      path: '/api/items',
      summary: 'Create a new item',
      parameters: [
        { name: 'name', type: 'string', required: true },
        { name: 'description', type: 'string', required: false }
      ],
      responses: {
        '201': { description: 'Item created', schema: 'Item' },
        '400': { description: 'Validation error' }
      }
    },
    {
      method: 'GET',
      path: '/api/items/{item_id}',
      summary: 'Get item by ID',
      parameters: [
        { name: 'item_id', type: 'integer', required: true, in: 'path' }
      ],
      responses: {
        '200': { description: 'Successful response', schema: 'Item' },
        '404': { description: 'Item not found' }
      }
    }
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>API Documentation</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Export OpenAPI
          </button>
          <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Refresh Docs
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', gap: '2rem' }}>
          <div style={{ flex: '0 0 300px', borderRight: '1px solid var(--border)', paddingRight: '1rem' }}>
            <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Endpoints</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {endpoints.map((endpoint, idx) => (
                <button
                  key={idx}
                  onClick={() => setSelectedEndpoint(idx)}
                  style={{
                    padding: '0.75rem',
                    background: selectedEndpoint === idx ? 'var(--bg-light)' : 'transparent',
                    border: '1px solid var(--border)',
                    borderRadius: '0',
                    textAlign: 'left',
                    cursor: 'pointer',
                    fontSize: '0.875rem'
                  }}
                >
                  <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>
                    <span style={{ 
                      color: endpoint.method === 'GET' ? 'var(--success)' : 
                             endpoint.method === 'POST' ? 'var(--primary)' : 
                             'var(--warning)',
                      marginRight: '0.5rem'
                    }}>
                      {endpoint.method}
                    </span>
                    {endpoint.path}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                    {endpoint.summary}
                  </div>
                </button>
              ))}
            </div>
          </div>
          <div style={{ flex: 1, paddingLeft: '1rem' }}>
            {selectedEndpoint !== null ? (
              <div>
                <div style={{ marginBottom: '1rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <span style={{ 
                      fontWeight: '500',
                      color: endpoints[selectedEndpoint].method === 'GET' ? 'var(--success)' : 
                             endpoints[selectedEndpoint].method === 'POST' ? 'var(--primary)' : 
                             'var(--warning)'
                    }}>
                      {endpoints[selectedEndpoint].method}
                    </span>
                    <code style={{ fontSize: '1rem', fontFamily: 'monospace' }}>
                      {endpoints[selectedEndpoint].path}
                    </code>
                  </div>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {endpoints[selectedEndpoint].summary}
                  </p>
                </div>

                {endpoints[selectedEndpoint].parameters.length > 0 && (
                  <div style={{ marginBottom: '1.5rem' }}>
                    <h3 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>Parameters</h3>
                    <div className="table-container">
                      <table className="apps-table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Type</th>
                            <th>Location</th>
                            <th>Required</th>
                          </tr>
                        </thead>
                        <tbody>
                          {endpoints[selectedEndpoint].parameters.map((param, idx) => (
                            <tr key={idx}>
                              <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                {param.name}
                              </td>
                              <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                                {param.type}
                              </td>
                              <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                                {param.in || 'query'}
                              </td>
                              <td>
                                {param.required ? (
                                  <span className="status-badge status-running">Yes</span>
                                ) : (
                                  <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>No</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                <div>
                  <h3 style={{ fontSize: '0.875rem', fontWeight: '500', marginBottom: '0.75rem' }}>Responses</h3>
                  <div className="table-container">
                    <table className="apps-table">
                      <thead>
                        <tr>
                          <th>Status Code</th>
                          <th>Description</th>
                          <th>Schema</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.entries(endpoints[selectedEndpoint].responses).map(([code, resp]) => (
                          <tr key={code}>
                            <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                              {code}
                            </td>
                            <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                              {resp.description}
                            </td>
                            <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem', fontFamily: 'monospace' }}>
                              {resp.schema || '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
                Select an endpoint to view details
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default Documentation
