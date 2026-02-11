import React, { useState } from 'react'
import UsageChart from '../components/UsageChart'
import { generateAnalytics } from '../utils/mockData'
import './Analytics.css'

const Analytics = () => {
  const [analytics] = useState(generateAnalytics())
  const [timeRange, setTimeRange] = useState('30d')

  const getCurrentValue = (key) => {
    const rangeMap = {
      '24h': 'last24h',
      '7d': 'last7d',
      '30d': 'last30d'
    }
    return analytics[key][rangeMap[timeRange]]
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Analytics</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['24h', '7d', '30d'].map(range => (
            <button
              key={range}
              className={`btn ${timeRange === range ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTimeRange(range)}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
            >
              {range}
            </button>
          ))}
        </div>
      </div>

      {/* Usage Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <UsageChart title="Requests" value={getCurrentValue('requests')} hours={timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720} />
        <UsageChart title="Errors" value={getCurrentValue('errors')} hours={timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720} />
        <UsageChart title="Compute Time" value={getCurrentValue('computeTime')} unit="hours" hours={timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720} />
      </div>

      {/* Top Endpoints */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Top Endpoints</h2>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th>Requests</th>
                <th>Errors</th>
                <th>Avg Response Time</th>
                <th>Error Rate</th>
              </tr>
            </thead>
            <tbody>
              {analytics.topEndpoints.map((endpoint, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: '500', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                    {endpoint.path}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {endpoint.requests.toLocaleString()}
                  </td>
                  <td style={{ color: endpoint.errors > 0 ? 'var(--error)' : 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {endpoint.errors}
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {endpoint.avgTime}ms
                  </td>
                  <td>
                    <span style={{ 
                      color: (endpoint.errors / endpoint.requests * 100) > 1 ? 'var(--error)' : 'var(--success)',
                      fontSize: '0.875rem'
                    }}>
                      {((endpoint.errors / endpoint.requests) * 100).toFixed(2)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Cost Summary */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Cost Summary ({timeRange})</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Compute
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              ${(getCurrentValue('computeTime') * 0.05).toFixed(2)}
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Storage
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              $12.50
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Bandwidth
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              $8.30
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Total
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--primary)' }}>
              ${(getCurrentValue('computeTime') * 0.05 + 12.50 + 8.30).toFixed(2)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Analytics
