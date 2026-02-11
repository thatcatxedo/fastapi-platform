import React from 'react'
import './Billing.css'

const Billing = () => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h1 style={{ fontWeight: '400' }}>Billing</h1>
      </div>

      {/* Current Plan */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Current Plan</h2>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', marginBottom: '0.25rem' }}>Pro Plan</div>
            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>$99/month</div>
          </div>
          <button className="btn btn-secondary" style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}>
            Change Plan
          </button>
        </div>
        <div style={{ paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            Next billing date: March 1, 2024
          </div>
        </div>
      </div>

      {/* Usage */}
      <div className="card" style={{ padding: '1.25rem', marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Current Usage</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Apps
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              3 / 10
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Requests
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              1.2M / 5M
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Storage
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              2.4 GB / 10 GB
            </div>
          </div>
          <div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem', fontWeight: '400' }}>
              Team Members
            </div>
            <div style={{ fontSize: '1.5rem', fontWeight: '500', color: 'var(--text)' }}>
              4 / 10
            </div>
          </div>
        </div>
      </div>

      {/* Billing History */}
      <div className="card" style={{ padding: '1.25rem' }}>
        <h2 style={{ fontSize: '1rem', fontWeight: '500', marginBottom: '1rem' }}>Billing History</h2>
        <div className="table-container">
          <table className="apps-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Description</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Feb 1, 2024</td>
                <td>Pro Plan - Monthly</td>
                <td style={{ fontWeight: '500' }}>$99.00</td>
                <td><span className="status-badge status-running">Paid</span></td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    Invoice
                  </button>
                </td>
              </tr>
              <tr>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Jan 1, 2024</td>
                <td>Pro Plan - Monthly</td>
                <td style={{ fontWeight: '500' }}>$99.00</td>
                <td><span className="status-badge status-running">Paid</span></td>
                <td>
                  <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                    Invoice
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default Billing
