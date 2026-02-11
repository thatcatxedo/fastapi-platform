const PHASE_LABELS = {
  validating: 'Validating...',
  creating_resources: 'Creating resources...',
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

const PHASES_ORDER = ['validating', 'creating_resources', 'pending', 'scheduled', 'pulling', 'pulled', 'creating', 'starting', 'ready']

function EventsTimeline({ events = [], phase = 'pending' }) {

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
      {events.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', padding: '0.5rem 0' }}>
          {phase === 'validating' ? 'Validating code...' : phase === 'creating_resources' ? 'Creating Kubernetes resources...' : 'Waiting for events...'}
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
