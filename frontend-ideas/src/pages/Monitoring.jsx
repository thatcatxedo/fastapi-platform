import React, { useState } from 'react'
import MetricsChart from '../components/MetricsChart'
import { generateRequestMetrics, generateErrorMetrics, generateResponseTimeMetrics } from '../utils/mockData'
import './Monitoring.css'

const Monitoring = () => {
  const [timeRange, setTimeRange] = useState('24h')
  
  const hours = timeRange === '24h' ? 24 : timeRange === '7d' ? 168 : 720
  const requestData = generateRequestMetrics(hours)
  const errorData = generateErrorMetrics(hours)
  const responseTimeData = generateResponseTimeMetrics(hours)

  const currentRequests = requestData[requestData.length - 1]?.value || 0
  const currentErrors = errorData[errorData.length - 1]?.value || 0
  const currentResponseTime = responseTimeData[responseTimeData.length - 1]?.value || 0
  const errorRate = currentRequests > 0 ? ((currentErrors / currentRequests) * 100).toFixed(2) : 0

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Monitoring</h1>
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

      {/* Key Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Requests ({timeRange})
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {currentRequests.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.25rem' }}>
            ↑ 12.5% from previous period
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Error Rate
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: errorRate > 1 ? 'var(--error)' : 'var(--text)' }}>
            {errorRate}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.25rem' }}>
            ↓ 5.2% from previous period
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Avg Response Time
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)' }}>
            {currentResponseTime}ms
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)', marginTop: '0.25rem' }}>
            ↓ 8ms from previous period
          </div>
        </div>

        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Uptime (30d)
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--success)' }}>
            99.97%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
            SLA: 99.9%
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <MetricsChart
          data={requestData}
          title="Requests"
          color="var(--primary)"
          height={200}
        />
        <MetricsChart
          data={errorData}
          title="Errors"
          color="var(--error)"
          height={200}
        />
        <MetricsChart
          data={responseTimeData}
          title="Response Time (ms)"
          color="var(--warning)"
          height={200}
        />
      </div>

      {/* Alerts */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: '500' }}>Active Alerts</h2>
          <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Configure Alerts
          </button>
        </div>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Alert Rule</th>
                <th>Status</th>
                <th>Condition</th>
                <th>Last Triggered</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>High Error Rate</td>
                <td><span className="status-badge status-running">Active</span></td>
                <td>Error rate &gt; 5%</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Never</td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    Edit
                  </button>
                </td>
              </tr>
              <tr>
                <td>Slow Response Time</td>
                <td><span className="status-badge status-running">Active</span></td>
                <td>P95 response time &gt; 500ms</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>2 hours ago</td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    Edit
                  </button>
                </td>
              </tr>
              <tr>
                <td>Low Uptime</td>
                <td><span className="status-badge" style={{ color: 'var(--text-muted)' }}>Inactive</span></td>
                <td>Uptime &lt; 99%</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Never</td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    Edit
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Health Checks */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Health Checks</h2>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th>Status</th>
                <th>Last Check</th>
                <th>Response Time</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>/health</td>
                <td><span className="status-badge status-running">Healthy</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Just now</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>12ms</td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    View Logs
                  </button>
                </td>
              </tr>
              <tr>
                <td>/api/status</td>
                <td><span className="status-badge status-running">Healthy</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>1 minute ago</td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>8ms</td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    View Logs
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Monitoring
