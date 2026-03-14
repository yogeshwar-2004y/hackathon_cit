import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';

export default function PageForgotPassword() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [resetPath, setResetPath] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { data } = await axios.post('/api/auth/forgot-password', { email: email.trim().toLowerCase() });
      setSent(true);
      if (data.reset_path) setResetPath(data.reset_path);
    } catch (err) {
      setError(err.response?.data?.detail || 'Request failed');
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
    return (
      <div className="auth-page">
        <div className="auth-left">
          <div className="auth-brand">
            <h1>Shadowspy.ai</h1>
            <p>Net Profit over Gross Revenue</p>
          </div>
        </div>
        <div className="auth-right">
          <div className="auth-form">
            <h2>Check your email</h2>
            <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
              If an account exists with that email, we sent a password reset link.
            </p>
            {resetPath && (
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, wordBreak: 'break-all' }}>
                For development, use this link: <a href={resetPath} style={{ color: 'var(--brand)' }}>{window.location.origin}{resetPath}</a>
              </p>
            )}
            <Link to="/login" className="auth-submit" style={{ display: 'inline-block', textAlign: 'center', textDecoration: 'none' }}>
              Back to sign in
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-left">
        <div className="auth-brand">
          <h1>Shadowspy.ai</h1>
          <p>Net Profit over Gross Revenue</p>
        </div>
      </div>
      <div className="auth-right">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Forgot password</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: 24 }}>
            Enter your email and we’ll send a link to reset your password.
          </p>
          {error && <div className="auth-error">{error}</div>}
          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              required
              autoComplete="email"
            />
          </label>
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Sending…' : 'Send reset link'}
          </button>
          <p className="auth-switch">
            <Link to="/login">Back to sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
