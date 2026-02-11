import React from 'react'
import './RoleBadge.css'

const RoleBadge = ({ role }) => {
  const roleConfig = {
    owner: { label: 'Owner', color: 'var(--primary)' },
    admin: { label: 'Admin', color: 'var(--warning)' },
    developer: { label: 'Developer', color: 'var(--success)' },
    viewer: { label: 'Viewer', color: 'var(--text-muted)' }
  }

  const config = roleConfig[role] || roleConfig.viewer

  return (
    <span className="role-badge" style={{ backgroundColor: config.color }}>
      {config.label}
    </span>
  )
}

export default RoleBadge
