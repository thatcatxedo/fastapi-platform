import React from 'react'
import './MetricsChart.css'

const MetricsChart = ({ data, title, color = 'var(--primary)', height = 150 }) => {
  if (!data || data.length === 0) {
    return (
      <div className="metrics-chart" style={{ height }}>
        <div className="chart-empty">No data available</div>
      </div>
    )
  }

  const maxValue = Math.max(...data.map(d => d.value))
  const minValue = Math.min(...data.map(d => d.value))
  const range = maxValue - minValue || 1

  const points = data.map((point, index) => {
    const x = (index / (data.length - 1)) * 100
    const y = 100 - ((point.value - minValue) / range) * 100
    return `${x},${y}`
  }).join(' ')

  const areaPoints = `0,100 ${points} 100,100`

  return (
    <div className="metrics-chart" style={{ height }}>
      <div className="chart-header">
        <span className="chart-title">{title}</span>
        <span className="chart-value" style={{ color }}>
          {data[data.length - 1]?.value.toLocaleString()}
        </span>
      </div>
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="chart-svg">
        <defs>
          <linearGradient id={`gradient-${title}`} x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.05" />
          </linearGradient>
        </defs>
        <polyline
          points={points}
          fill="none"
          stroke={color}
          strokeWidth="0.5"
          className="chart-line"
        />
        <polygon
          points={areaPoints}
          fill={`url(#gradient-${title})`}
          className="chart-area"
        />
      </svg>
      <div className="chart-footer">
        <span className="chart-min">{minValue.toLocaleString()}</span>
        <span className="chart-max">{maxValue.toLocaleString()}</span>
      </div>
    </div>
  )
}

export default MetricsChart
