import React, { useState } from 'react'
import RoleBadge from '../components/RoleBadge'
import { mockTeamMembers } from '../utils/mockData'
import './Members.css'

const Members = () => {
  const [members] = useState(mockTeamMembers)
  const [showInviteModal, setShowInviteModal] = useState(false)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Team Members</h1>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowInviteModal(true)}
          style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
        >
          + Invite Member
        </button>
      </div>

      <div className="card" style={{ padding: '1.25rem' }}>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Role</th>
                <th>Joined</th>
                <th>Last Active</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {members.map(member => (
                <tr key={member.id}>
                  <td>
                    <div>
                      <div style={{ fontWeight: '500' }}>{member.username}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{member.email}</div>
                    </div>
                  </td>
                  <td><RoleBadge role={member.role} /></td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{member.joinedAt}</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{member.lastActive}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                        Edit
                      </button>
                      {member.role !== 'owner' && (
                        <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem', color: 'var(--error)' }}>
                          Remove
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Role Permissions Info */}
      <div className="card" style={{ padding: '1.25rem', marginTop: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Role Permissions</h2>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Permission</th>
                <th>Owner</th>
                <th>Admin</th>
                <th>Developer</th>
                <th>Viewer</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>View Apps</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
              </tr>
              <tr>
                <td>Edit Code</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✗</td>
              </tr>
              <tr>
                <td>Deploy Apps</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✗</td>
              </tr>
              <tr>
                <td>Manage Members</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✗</td>
                <td style={{ textAlign: 'center' }}>✗</td>
              </tr>
              <tr>
                <td>Manage Billing</td>
                <td style={{ textAlign: 'center' }}>✓</td>
                <td style={{ textAlign: 'center' }}>✗</td>
                <td style={{ textAlign: 'center' }}>✗</td>
                <td style={{ textAlign: 'center' }}>✗</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {showInviteModal && (
        <div className="modal-overlay" onClick={() => setShowInviteModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: '1rem', fontWeight: '500' }}>Invite Team Member</h2>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Email</label>
              <input
                type="email"
                className="form-input"
                placeholder="user@example.com"
                style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0' }}
              />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem' }}>Role</label>
              <select
                className="form-input"
                style={{ width: '100%', padding: '0.5rem', border: '1px solid var(--border)', borderRadius: '0' }}
              >
                <option>Developer</option>
                <option>Viewer</option>
                <option>Admin</option>
              </select>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button className="btn btn-secondary" onClick={() => setShowInviteModal(false)}>
                Cancel
              </button>
              <button className="btn btn-primary" onClick={() => setShowInviteModal(false)}>
                Send Invitation
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Members
