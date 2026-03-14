import React, { useState, useEffect } from 'react';
import client from '../api/client';

const ACTION_LABELS = {
  login_ok: 'Login',
  login_fail: 'Login failed',
  signup: 'Sign up',
  password_change: 'Password changed',
  password_reset_request: 'Password reset requested',
  password_reset_used: 'Password reset completed',
};

export default function PageAudit() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    client.get('/auth/audit')
      .then(({ data }) => setEvents(data.events || []))
      .catch((e) => setError(e.response?.data?.detail || 'Failed to load audit log'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="main-content">
      <h1 className="header-title">Audit log</h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>
        Security and account activity for your account.
      </p>
      {loading && <div className="empty-state">Loading…</div>}
      {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}
      {!loading && !error && (
        <div className="panel" style={{ overflowX: 'auto' }}>
          {events.length === 0 ? (
            <div className="empty-state">No events yet.</div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Detail</th>
                  <th>IP</th>
                </tr>
              </thead>
              <tbody>
                {events.map((ev) => (
                  <tr key={ev.id}>
                    <td>{ev.created_at ? new Date(ev.created_at).toLocaleString() : '—'}</td>
                    <td>{ACTION_LABELS[ev.action] || ev.action}</td>
                    <td>{ev.resource || '—'}</td>
                    <td>{ev.detail || '—'}</td>
                    <td>{ev.ip_address || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
