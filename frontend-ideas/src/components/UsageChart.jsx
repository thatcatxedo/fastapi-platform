import React from 'react'
import MetricsChart from './MetricsChart'
import { generateTimeSeries } from '../utils/mockData'

const UsageChart = ({ title, value, unit = '', hours = 24 }) => {
  const data = generateTimeSeries(hours, value * 0.7, value * 1.3)

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div style={{ marginBottom: '1rem' }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
          {title}
        </div>
        <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
          {value.toLocaleString()} {unit}
        </div>
      </div>
      <MetricsChart data={data} title={title} height={120} />
    </div>
  )
}

export default UsageChart
