import React, { useState } from 'react'
import { generateActivityLog } from '../utils/mockData'
import './Activity.css'

const Activity = () => {
  const [activities] = useState(generateActivityLog(50))
  const [filter, setFilter] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')

  const filteredActivities = activities.filter(activity => {
    if (filter !== 'all' && activity.action !== filter) return false
    if (searchTerm && !activity.user.toLowerCase().includes(searchTerm.toLowerCase()) && 
        !activity.resource.toLowerCase().includes(searchTerm.toLowerCase())) {
      return false
    }
    return true
  })

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp)
    const now = Date.now()
    const diff = now - timestamp
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const days = Math.floor(hours / 24)
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''} ago`
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''} ago`
    return 'Just now'
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Activity Log</h1>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <input
            type="text"
            placeholder="Search..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid var(--border)',
              borderRadius: '0',
              fontSize: '0.875rem',
              width: '200px'
            }}
          />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            style={{
              padding: '0.5rem',
              border: '1px solid var(--border)',
              borderRadius: '0',
              fontSize: '0.875rem'
            }}
          >
            <option value="all">All Actions</option>
            <option value="deployed">Deployed</option>
            <option value="updated">Updated</option>
            <option value="created">Created</option>
            <option value="deleted">Deleted</option>
          </select>
        </div>
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {filteredActivities.map(activity => (
                <tr key={activity.id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
                    {formatTimestamp(activity.timestamp)}
                  </td>
                  <td style={{ fontWeight: '500' }}>{activity.user}</td>
                  <td>
                    <span className="status-badge" style={{ 
                      backgroundColor: activity.action === 'deployed' ? 'var(--success)' : 
                                      activity.action === 'deleted' ? 'var(--error)' : 
                                      'var(--primary)'
                    }}>
                      {activity.action}
                    </span>
                  </td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{activity.resource}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{activity.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Activity
