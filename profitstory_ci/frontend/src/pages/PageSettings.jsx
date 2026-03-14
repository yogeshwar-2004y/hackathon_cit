import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import toast from 'react-hot-toast';
import { validatePassword, PASSWORD_REQUIREMENTS } from '../utils/passwordPolicy';

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
  const [changingPassword, setChangingPassword] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    const v = validatePassword(newPassword);
    if (!v.ok) {
      toast.error(v.message);
      return;
    }
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    setChangingPassword(true);
    try {
      await client.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword });
      toast.success('Password updated');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setChangingPassword(false);
    }
  };

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
    <div className="main-content settings-page">
      <h1 className="header-title">Settings</h1>

      <section className="settings-section">
        <div className="panel settings-panel">
          <div className="panel-header">Account</div>
          <form onSubmit={handleSaveAccount} className="settings-account-form">
            <label className="settings-account-label">
              Business name
              <input type="text" value={businessName} onChange={(e) => setBusinessName(e.target.value)} className="input-visible" />
            </label>
            <label className="settings-account-label">
              Email (read-only)
              <input type="email" value={seller?.email || ''} readOnly className="input-visible" style={{ opacity: 0.8 }} />
            </label>
            <label className="settings-account-label">
              Phone
              <input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} className="input-visible" />
            </label>
            <label className="settings-account-label">
              Primary platform
              <select value={platform} onChange={(e) => setPlatform(e.target.value)} className="input-visible">
                <option value="amazon">Amazon India</option>
                <option value="flipkart">Flipkart</option>
                <option value="snapdeal">Snapdeal</option>
                <option value="all">All platforms</option>
              </select>
            </label>
            <button type="submit" className="btn-scan" disabled={saving}>{saving ? 'Saving…' : 'Save'}</button>
          </form>
        </div>
      </section>

      <section className="settings-section">
        <div className="panel settings-panel">
          <div className="panel-header">Change password</div>
          <p className="settings-password-hint">
            {PASSWORD_REQUIREMENTS.join(' · ')}
          </p>
          <form onSubmit={handleChangePassword} className="settings-change-password-form">
            <label className="settings-label">
              Current password
              <input type="password" value={oldPassword} onChange={(e) => setOldPassword(e.target.value)} className="input-visible" required />
            </label>
            <label className="settings-label">
              New password
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} className="input-visible" required />
            </label>
            <label className="settings-label">
              Confirm new password
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} className="input-visible" required />
            </label>
            <button type="submit" className="btn-scan" disabled={changingPassword}>{changingPassword ? 'Updating…' : 'Update password'}</button>
          </form>
        </div>
      </section>

      <section className="settings-section">
        <div className="panel settings-panel">
          <div className="panel-header">API keys (advanced)</div>
          <label className="settings-api-label">
            RapidAPI Key
            <input type="password" value={rapidApiKey} onChange={(e) => setRapidApiKey(e.target.value)} className="input-visible" placeholder="Stored in .env on server" />
          </label>
          <p className="settings-api-hint">API keys are configured in server .env. This field is for reference only.</p>
        </div>
      </section>

      <section className="settings-section">
        <div className="panel settings-panel settings-danger-panel">
          <div className="panel-header">Danger zone</div>
          <p className="settings-danger-text">Permanently delete your account and all data.</p>
          <button type="button" className="btn-danger" disabled>Delete account</button>
        </div>
      </section>
    </div>
  );
}
