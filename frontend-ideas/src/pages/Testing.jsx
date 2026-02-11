import React, { useState } from 'react'
import { mockTestResults } from '../utils/mockData'
import './Testing.css'

const Testing = () => {
  const [testResults] = useState(mockTestResults)
  const [running, setRunning] = useState(false)

  const runTests = () => {
    setRunning(true)
    setTimeout(() => setRunning(false), 2000)
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return 'var(--success)'
      case 'failed': return 'var(--error)'
      case 'skipped': return 'var(--text-muted)'
      default: return 'var(--text-muted)'
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Testing</h1>
        <button 
          className="btn btn-primary" 
          onClick={runTests}
          disabled={running}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          {running ? 'Running...' : 'Run Tests'}
        </button>
      </div>

      {/* Test Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Total Tests
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {testResults.total}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Passed
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--success)' }}>
            {testResults.passed}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Failed
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--error)' }}>
            {testResults.failed}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Coverage
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {testResults.coverage}%
          </div>
        </div>
      </div>

      {/* Test Results */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: '500' }}>Test Results</h2>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Last run: {new Date(testResults.lastRun).toLocaleString()} • Duration: {testResults.duration}s
          </div>
        </div>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Test</th>
                <th>Status</th>
                <th>Duration</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {testResults.tests.map((test, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {test.name}
                  </td>
                  <td>
                    <span className="status-badge" style={{ backgroundColor: getStatusColor(test.status) }}>
                      {test.status}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {test.duration}s
                  </td>
                  <td style={{ color: 'var(--error)', fontSize: '0.875rem', fontFamily: 'monospace' }}>
                    {test.error || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Test Configuration */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Test Configuration</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Test Framework</label>
            <select style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}>
              <option>pytest</option>
              <option>unittest</option>
              <option>nose2</option>
            </select>
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Test Pattern</label>
            <input
              type="text"
              defaultValue="test_*.py"
              style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Coverage Threshold</label>
            <input
              type="number"
              defaultValue="80"
              style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0', fontSize: '0.875rem' }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Testing
