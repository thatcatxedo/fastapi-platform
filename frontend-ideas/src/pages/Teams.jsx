import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import RoleBadge from '../components/RoleBadge'
import { mockTeamMembers } from '../utils/mockData'
import './Teams.css'

const Teams = () => {
  const [teams] = useState([
    {
      id: 'team-1',
      name: 'Engineering',
      members: 12,
      apps: 8,
      createdAt: '2024-01-15'
    },
    {
      id: 'team-2',
      name: 'Product',
      members: 5,
      apps: 3,
      createdAt: '2024-01-20'
    },
    {
      id: 'team-3',
      name: 'Marketing',
      members: 3,
      apps: 2,
      createdAt: '2024-02-01'
    }
  ])

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Teams</h1>
        <button className="btn btn-primary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
          + Create Team
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        {teams.map(team => (
          <div key={team.id} className="card" style={{ padding: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: '500', margin: 0 }}>{team.name}</h2>
              <Link to={`/teams/${team.id}/members`} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Manage
              </Link>
            </div>
            <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
              <div>
                <span style={{ fontWeight: '500', color: 'var(--text)' }}>{team.members}</span> members
              </div>
              <div>
                <span style={{ fontWeight: '500', color: 'var(--text)' }}>{team.apps}</span> apps
              </div>
            </div>
            <div style={{ marginTop: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Created {team.createdAt}
            </div>
          </div>
        ))}
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: '500' }}>My Teams</h2>
          <Link to="/members" className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            View All Members
          </Link>
        </div>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Team</th>
                <th>Your Role</th>
                <th>Members</th>
                <th>Apps</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {teams.map(team => (
                <tr key={team.id}>
                  <td style={{ fontWeight: '500' }}>{team.name}</td>
                  <td><RoleBadge role="admin" /></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{team.members}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{team.apps}</td>
                  <td>
                    <Link to={`/teams/${team.id}`} className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Teams
