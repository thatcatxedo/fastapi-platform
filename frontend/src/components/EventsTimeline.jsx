import { useState, useEffect } from 'react'
import { API_URL } from '../config'

const PHASE_LABELS = {
  pending: 'Waiting to be scheduled',
  scheduled: 'Pod scheduled',
  pulling: 'Pulling container image',
  pulled: 'Image pulled',
  creating: 'Creating container',
  starting: 'Starting application',
  ready: 'Application ready',
  error: 'Deployment error',
  unknown: 'Checking status...'
}

const PHASES_ORDER = ['pending', 'scheduled', 'pulling', 'pulled', 'creating', 'starting', 'ready']

function EventsTimeline({ appId, isDeploying }) {
  const [events, setEvents] = useState([])
  const [phase, setPhase] = useState('pending')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (appId && isDeploying) {
      fetchEvents()
      const interval = setInterval(fetchEvents, 2000)
      return () => clearInterval(interval)
    }
  }, [appId, isDeploying])

  const fetchEvents = async () => {
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(
        `${API_URL}/api/apps/${appId}/events`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      )
      if (response.ok) {
        const data = await response.json()
        setEvents(data.events || [])
        setPhase(data.deployment_phase || 'pending')
      }
    } catch (err) {
      console.error('Failed to fetch events:', err)
    } finally {
      setLoading(false)
    }
  }

  const getProgressWidth = () => {
    if (phase === 'error') return '100%'
    if (phase === 'ready') return '100%'
    const idx = PHASES_ORDER.indexOf(phase)
    if (idx === -1) return '5%'
    return `${((idx + 1) / PHASES_ORDER.length) * 100}%`
  }

  const getProgressColor = () => {
    if (phase === 'error') return 'var(--error)'
    if (phase === 'ready') return 'var(--success)'
    return 'var(--warning)'
  }

  if (!appId) return null

  return (
    <div className="events-timeline">
      <div className="events-timeline-header">
        <h3 style={{ margin: 0, fontSize: '0.9rem' }}>Deployment Progress</h3>
        <span className={`events-phase events-phase-${phase}`}>
          {PHASE_LABELS[phase] || phase}
        </span>
      </div>

      {/* Progress bar */}
      <div className="events-progress-bar">
        <div
          className="events-progress-fill"
          style={{
            width: getProgressWidth(),
            background: getProgressColor()
          }}
        />
      </div>

      {/* Recent events */}
      {loading ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '0.5rem 0' }}>
          Loading events...
        </div>
      ) : events.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '0.5rem 0' }}>
          Waiting for events...
        </div>
      ) : (
        <div className="events-list">
          {events.slice(0, 5).map((event, idx) => (
            <div key={idx} className="event-item">
              <span className={`event-icon ${event.type === 'Warning' ? 'event-warning' : 'event-normal'}`}>
                {event.type === 'Warning' ? '!' : '✓'}
              </span>
              <span className="event-time">
                {event.timestamp ? new Date(event.timestamp).toLocaleTimeString() : ''}
              </span>
              <span className="event-message">
                <strong>{event.reason}</strong>: {event.message}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default EventsTimeline
