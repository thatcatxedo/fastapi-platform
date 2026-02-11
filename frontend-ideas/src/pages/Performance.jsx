import React from 'react'
import { mockPerformanceInsights } from '../utils/mockData'
import './Performance.css'

const Performance = () => {
  const insights = mockPerformanceInsights

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Performance Insights</h1>
      </div>

      {/* Trends */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Response Time
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)', marginBottom: '0.25rem' }}>
            {insights.trends.responseTime.current}ms
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
            ↓ {Math.abs(insights.trends.responseTime.change)}% ({insights.trends.responseTime.previous}ms)
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Error Rate
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)', marginBottom: '0.25rem' }}>
            {insights.trends.errorRate.current}%
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
            ↓ {Math.abs(insights.trends.errorRate.change)}% ({insights.trends.errorRate.previous}%)
          </div>
        </div>
        <div className="card" style={{ padding: '1.25rem' }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
            Throughput
          </div>
          <div style={{ fontSize: '2rem', fontWeight: '500', color: 'var(--text)', marginBottom: '0.25rem' }}>
            {insights.trends.throughput.current}/s
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
            ↑ {insights.trends.throughput.change}% ({insights.trends.throughput.previous}/s)
          </div>
        </div>
      </div>

      {/* Recommendations */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Recommendations</h2>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {insights.recommendations.map((rec, idx) => (
            <div key={idx} style={{ 
              padding: '1rem', 
              border: '1px solid var(--border)', 
              borderRadius: '0',
              borderLeft: `4px solid ${rec.severity === 'high' ? 'var(--error)' : 'var(--warning)'}`
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                <div>
                  <div style={{ fontWeight: '500', marginBottom: '0.25rem' }}>{rec.title}</div>
                  <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                    {rec.description}
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--success)' }}>
                    {rec.impact}
                  </div>
                </div>
                <span className="status-badge" style={{ 
                  backgroundColor: rec.severity === 'high' ? 'var(--error)' : 'var(--warning)'
                }}>
                  {rec.severity}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Performance
