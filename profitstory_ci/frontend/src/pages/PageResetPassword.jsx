import React, { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { Eye, EyeOff } from 'lucide-react';
import axios from 'axios';
import { validatePassword, PASSWORD_REQUIREMENTS } from '../utils/passwordPolicy';

export default function PageResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token') || '';
  const navigate = useNavigate();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const v = validatePassword(newPassword);
    if (!v.ok) {
      setError(v.message);
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match');
      return;
    }
    if (!token.trim()) {
      setError('Missing reset token. Use the link from your email.');
      return;
    }
    setLoading(true);
    try {
      await axios.post('/api/auth/reset-password', { token: token.trim(), new_password: newPassword });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Reset failed');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
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
            <h2>Password updated</h2>
            <p style={{ color: 'var(--text-secondary)' }}>You can sign in with your new password. Redirecting…</p>
            <Link to="/login" style={{ color: 'var(--brand)', marginTop: 16, display: 'inline-block' }}>Sign in</Link>
          </div>
        </div>
      </div>
    );
  }

  if (!token) {
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
            <h2>Invalid link</h2>
            <p style={{ color: 'var(--text-secondary)' }}>This reset link is invalid or missing. Request a new one from the sign-in page.</p>
            <Link to="/forgot-password" style={{ color: 'var(--brand)', marginTop: 16, display: 'inline-block' }}>Request reset</Link>
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
          <h2>Set new password</h2>
          {error && <div className="auth-error">{error}</div>}
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
            {PASSWORD_REQUIREMENTS.join(' · ')}
          </p>
          <label>
            New password
            <div className="input-with-icon">
              <input
                type={showPassword ? 'text' : 'password'}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="new-password"
              />
              <button type="button" className="icon-btn" onClick={() => setShowPassword(!showPassword)} aria-label="Toggle password">
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </label>
          <label>
            Confirm new password
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="••••••••"
              required
              autoComplete="new-password"
            />
          </label>
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Updating…' : 'Update password'}
          </button>
          <p className="auth-switch">
            <Link to="/login">Back to sign in</Link>
          </p>
        </form>
      </div>
    </div>
  );
}
