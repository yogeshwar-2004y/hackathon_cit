import React, { useState } from 'react';
import client from '../api/client';

const PLATFORMS = [
  { value: 'amazon', label: 'Amazon India', idLabel: 'Amazon ASIN' },
  { value: 'flipkart', label: 'Flipkart', idLabel: 'Flipkart Product ID / FSN' },
  { value: 'snapdeal', label: 'Snapdeal', idLabel: 'Snapdeal Product ID' },
];

export default function AddCompetitorModal({ productPlatform, productId, onClose, onSaved }) {
  const [competitorName, setCompetitorName] = useState('');
  const [platform, setPlatform] = useState(productPlatform || 'amazon');
  const [platformId, setPlatformId] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!competitorName.trim() || !platformId.trim()) {
      setError('Competitor name and Product ID are required.');
      return;
    }
    setLoading(true);
    try {
      await client.post(`/products/${productId}/competitors`, {
        competitor_name: competitorName.trim(),
        platform,
        platform_id: platformId.trim(),
        notes: notes.trim() || null,
      });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add competitor');
    } finally {
      setLoading(false);
    }
  };

  const idLabel = PLATFORMS.find((p) => p.value === platform)?.idLabel || 'Product ID';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Competitor</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}
          <label>
            Competitor Name
            <input type="text" value={competitorName} onChange={(e) => setCompetitorName(e.target.value)} placeholder="e.g. JBL C100SI" required />
          </label>
          <label>
            Platform
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </label>
          <label>
            {idLabel}
            <input type="text" value={platformId} onChange={(e) => setPlatformId(e.target.value)} placeholder="e.g. B01DEWVZ2C" required />
          </label>
          <label>
            Notes
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional seller note" rows={3} style={{ resize: 'vertical', minHeight: 60 }} />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-scan" disabled={loading}>{loading ? 'Adding…' : 'Add Competitor'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
