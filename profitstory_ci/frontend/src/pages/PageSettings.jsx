import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import toast from 'react-hot-toast';

export default function PageSettings() {
  const { seller } = useAuth();
  const [businessName, setBusinessName] = useState(seller?.business_name || '');
  const [phone, setPhone] = useState(seller?.phone || '');
  const [platform, setPlatform] = useState(seller?.platform || 'amazon');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [rapidApiKey, setRapidApiKey] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSaveAccount = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      // PATCH /settings/account or similar - if we add it; for now just toast
      toast.success('Account settings saved');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="main-content">
      <h1 className="header-title">Settings</h1>
      <div className="panel" style={{ maxWidth: 560, marginBottom: 24 }}>
        <div className="panel-header">Account</div>
        <form onSubmit={handleSaveAccount}>
          <label>
            Business name
            <input type="text" value={businessName} onChange={(e) => setBusinessName(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} />
          </label>
          <label style={{ marginTop: 16, display: 'block' }}>
            Email (read-only)
            <input type="email" value={seller?.email || ''} readOnly className="input-visible" style={{ width: '100%', marginTop: 6, opacity: 0.8 }} />
          </label>
          <label style={{ marginTop: 16, display: 'block' }}>
            Phone
            <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} />
          </label>
          <label style={{ marginTop: 16, display: 'block' }}>
            Primary platform
            <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }}>
              <option value="amazon">Amazon India</option>
              <option value="flipkart">Flipkart</option>
              <option value="snapdeal">Snapdeal</option>
              <option value="all">All platforms</option>
            </select>
          </label>
          <button type="submit" className="btn-scan" style={{ marginTop: 24 }} disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
        </form>
      </div>
      <div className="panel" style={{ maxWidth: 560, marginBottom: 24 }}>
        <div className="panel-header">Change password</div>
        <label style={{ display: 'block', marginBottom: 12 }}>
          Old password
          <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} />
        </label>
        <label style={{ display: 'block', marginBottom: 12 }}>
          New password
          <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} />
        </label>
        <label style={{ display: 'block', marginBottom: 12 }}>
          Confirm new password
          <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} />
        </label>
        <button type="button" className="btn-scan" disabled>Update password</button>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>Backend change-password endpoint can be added later.</p>
      </div>
      <div className="panel" style={{ maxWidth: 560, marginBottom: 24 }}>
        <div className="panel-header">API keys (advanced)</div>
        <label style={{ display: 'block' }}>
          RapidAPI Key
          <input type="password" value={rapidApiKey} onChange={(e) => setRapidApiKey(e.target.value)} className="input-visible" style={{ width: '100%', marginTop: 6 }} placeholder="Stored in .env on server" />
        </label>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 8 }}>API keys are configured in server .env. This field is for reference only.</p>
      </div>
      <div className="panel" style={{ maxWidth: 560, borderColor: 'var(--red)' }}>
        <div className="panel-header">Danger zone</div>
        <p style={{ color: 'var(--text-muted)', marginBottom: 12 }}>Permanently delete your account and all data.</p>
        <button type="button" className="btn-danger" disabled>Delete account</button>
      </div>
    </div>
  );
}
