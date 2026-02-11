import React, { useState } from 'react'
import { Bell, Rocket, AlertTriangle, CheckCircle, X } from 'lucide-react'

const mockNotifications = [
  { id: 1, type: 'success', title: 'Deployment Complete', message: 'todo-api deployed successfully', time: '2 min ago', unread: true },
  { id: 2, type: 'warning', title: 'High Memory Usage', message: 'weather-dashboard is using 85% memory', time: '15 min ago', unread: true },
  { id: 3, type: 'success', title: 'Database Created', message: 'New database "analytics-db" created', time: '1 hour ago', unread: false },
  { id: 4, type: 'error', title: 'Deployment Failed', message: 'kanban-board build error on line 42', time: '2 hours ago', unread: false },
]

const NotificationCenter = () => {
  const [isOpen, setIsOpen] = useState(false)
  const [notifications, setNotifications] = useState(mockNotifications)

  const unreadCount = notifications.filter(n => n.unread).length

  const markAllRead = () => {
    setNotifications(notifications.map(n => ({ ...n, unread: false })))
  }

  const getIcon = (type) => {
    switch (type) {
      case 'success': return <CheckCircle size={16} />
      case 'warning': return <AlertTriangle size={16} />
      case 'error': return <X size={16} />
      default: return <Rocket size={16} />
    }
  }

  return (
    <div className="notification-center">
      <button
        className="btn btn-ghost btn-icon notification-trigger"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
      </button>

      {isOpen && (
        <>
          <div className="notification-dropdown">
            <div className="notification-header">
              <span className="notification-header-title">Notifications</span>
              {unreadCount > 0 && (
                <button className="btn btn-ghost btn-sm" onClick={markAllRead}>
                  Mark all read
                </button>
              )}
            </div>
            <div className="notification-list">
              {notifications.length === 0 ? (
                <div className="notification-empty">No notifications</div>
              ) : (
                notifications.map(notification => (
                  <div
                    key={notification.id}
                    className={`notification-item ${notification.unread ? 'unread' : ''}`}
                  >
                    <div className={`notification-icon ${notification.type}`}>
                      {getIcon(notification.type)}
                    </div>
                    <div className="notification-content">
                      <div className="notification-title">{notification.title}</div>
                      <div className="notification-message">{notification.message}</div>
                      <div className="notification-time">{notification.time}</div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          <div
            style={{ position: 'fixed', inset: 0, zIndex: 99 }}
            onClick={() => setIsOpen(false)}
          />
        </>
      )}
    </div>
  )
}

export default NotificationCenter
