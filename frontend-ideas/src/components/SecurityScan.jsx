import React from 'react'
import { mockSecurityScan } from '../utils/mockData'
import './SecurityScan.css'

const SecurityScan = () => {
  const scan = mockSecurityScan
  const formatDate = (timestamp) => {
    const date = new Date(timestamp)
    const hours = Math.floor((Date.now() - timestamp) / (1000 * 60 * 60))
    if (hours === 0) return 'Just now'
    if (hours === 1) return '1 hour ago'
    return `${hours} hours ago`
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'var(--error)'
      case 'high': return 'var(--warning)'
      case 'medium': return 'var(--text-muted)'
      default: return 'var(--text-muted)'
    }
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '0.25rem' }}>Security Scan</h3>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            Last scanned: {formatDate(scan.lastScanned)}
          </div>
        </div>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          Run Scan
        </button>
      </div>

      {/* Vulnerability Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Critical
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--error)' }}>
            {scan.vulnerabilities.critical}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            High
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--warning)' }}>
            {scan.vulnerabilities.high}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Medium
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {scan.vulnerabilities.medium}
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Dependencies
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {scan.dependencies.vulnerable}/{scan.dependencies.total}
          </div>
        </div>
      </div>

      {/* Vulnerabilities List */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h3 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Vulnerabilities</h3>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Package</th>
                <th>CVE</th>
                <th>Description</th>
                <th>Fixed In</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {scan.issues.map(issue => (
                <tr key={issue.id}>
                  <td>
                    <span className="status-badge" style={{ backgroundColor: getSeverityColor(issue.severity) }}>
                      {issue.severity}
                    </span>
                  </td>
                  <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {issue.package}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {issue.cve}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {issue.description}
                  </td>
                  <td style={{ color: 'var(--success)', fontSize: '0.875rem', fontFamily: 'monospace' }}>
                    {issue.fixedIn}
                  </td>
                  <td>
                    <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                      Update
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default SecurityScan
