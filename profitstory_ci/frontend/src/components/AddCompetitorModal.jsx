import React, { useState } from 'react';
import client from '../api/client';

const PLATFORMS = [
  { value: 'amazon', label: 'Amazon India', idLabel: 'Amazon ASIN' },
  { value: 'flipkart', label: 'Flipkart', idLabel: 'Flipkart Product ID / FSN' },
  { value: 'snapdeal', label: 'Snapdeal', idLabel: 'Snapdeal Product ID' },
];

const MODE_BESTSELLERS = 'bestsellers';
const MODE_MANUAL = 'manual';

export default function AddCompetitorModal({ productPlatform, productId, onClose, onSaved }) {
  const [mode, setMode] = useState(productPlatform === 'amazon' ? MODE_BESTSELLERS : MODE_MANUAL);
  const [competitorName, setCompetitorName] = useState('');
  const [platform, setPlatform] = useState(productPlatform || 'amazon');
  const [platformId, setPlatformId] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Bestsellers state
  const [bestsellersLoading, setBestsellersLoading] = useState(false);
  const [rankInfo, setRankInfo] = useState(null);
  const [top20, setTop20] = useState([]);
  const [selectedAsins, setSelectedAsins] = useState(new Set());
  const [bestsellersError, setBestsellersError] = useState('');
  const [addingBatch, setAddingBatch] = useState(false);

  const loadBestsellers = async () => {
    setBestsellersError('');
    setBestsellersLoading(true);
    try {
      const { data } = await client.get(`/products/${productId}/bestsellers`, { params: { top_n: 20 } });
      if (data.error) {
        setBestsellersError(data.error);
        setTop20([]);
        setRankInfo(null);
      } else {
        setRankInfo(data.rank_info || null);
        setTop20(data.top_20 || []);
        setSelectedAsins(new Set());
      }
    } catch (err) {
      setBestsellersError(err.response?.data?.detail || 'Failed to load bestsellers');
      setTop20([]);
    } finally {
      setBestsellersLoading(false);
    }
  };

  const toggleBestseller = (asin) => {
    setSelectedAsins((prev) => {
      const next = new Set(prev);
      if (next.has(asin)) next.delete(asin);
      else next.add(asin);
      return next;
    });
  };

  const addSelectedBestsellers = async () => {
    if (selectedAsins.size === 0) {
      setError('Select at least one competitor.');
      return;
    }
    setError('');
    setAddingBatch(true);
    try {
      const competitors = top20
        .filter((x) => selectedAsins.has(x.asin))
        .map((x) => ({ platform_id: x.asin, competitor_name: x.name, notes: null }));
      await client.post(`/products/${productId}/competitors/batch`, { competitors });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add competitors');
    } finally {
      setAddingBatch(false);
    }
  };

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
  const isAmazon = productPlatform === 'amazon';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content add-competitor-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Competitor</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>

        {isAmazon && (
          <div className="add-competitor-tabs">
            <button
              type="button"
              className={mode === MODE_BESTSELLERS ? 'active' : ''}
              onClick={() => { setMode(MODE_BESTSELLERS); setError(''); setBestsellersError(''); }}
            >
              From Bestsellers
            </button>
            <button
              type="button"
              className={mode === MODE_MANUAL ? 'active' : ''}
              onClick={() => { setMode(MODE_MANUAL); setError(''); }}
            >
              Add manually
            </button>
          </div>
        )}

        {mode === MODE_BESTSELLERS && isAmazon && (
          <div className="add-competitor-bestsellers">
            <p className="add-competitor-hint">
              Load the top 20 bestsellers in your product’s category (from Best Sellers Rank on Amazon), then select which to add as competitors.
            </p>
            <button
              type="button"
              className="btn-scan"
              onClick={loadBestsellers}
              disabled={bestsellersLoading}
              style={{ marginBottom: 16 }}
            >
              {bestsellersLoading ? 'Loading…' : 'Load Top 20 from category'}
            </button>
            {bestsellersError && <div className="auth-error" style={{ marginBottom: 12 }}>{bestsellersError}</div>}
            {rankInfo && (
              <div className="bestsellers-rank-info" style={{ marginBottom: 12, fontSize: 12, color: 'var(--text-muted)' }}>
                {rankInfo.category_name && <span>{rankInfo.category_name}</span>}
                {rankInfo.text && rankInfo.text !== rankInfo.category_name && <span> · {rankInfo.text}</span>}
                {rankInfo.bestsellers_url && (
                  <a href={rankInfo.bestsellers_url} target="_blank" rel="noopener noreferrer" style={{ marginLeft: 8, color: 'var(--brand)' }}>
                    View on Amazon
                  </a>
                )}
              </div>
            )}
            {top20.length > 0 && (
              <>
                <div className="bestsellers-list">
                  {top20.map((item) => (
                    <label key={item.asin} className="bestsellers-item">
                      <input
                        type="checkbox"
                        checked={selectedAsins.has(item.asin)}
                        onChange={() => toggleBestseller(item.asin)}
                      />
                      <span className="bestsellers-rank">#{item.rank}</span>
                      <span className="bestsellers-name" title={item.name}>{item.name.slice(0, 60)}{item.name.length > 60 ? '…' : ''}</span>
                      <span className="bestsellers-asin">{item.asin}</span>
                    </label>
                  ))}
                </div>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                  {selectedAsins.size} selected
                </p>
                {error && <div className="auth-error" style={{ marginBottom: 12 }}>{error}</div>}
                <div className="modal-actions">
                  <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
                  <button
                    type="button"
                    className="btn-scan"
                    onClick={addSelectedBestsellers}
                    disabled={addingBatch || selectedAsins.size === 0}
                  >
                    {addingBatch ? 'Adding…' : `Add ${selectedAsins.size} selected`}
                  </button>
                </div>
              </>
            )}
            {!bestsellersLoading && top20.length === 0 && !bestsellersError && (
              <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Click “Load Top 20 from category” to fetch bestsellers for this product’s category.</p>
            )}
          </div>
        )}

        {mode === MODE_MANUAL && (
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
        )}
      </div>
    </div>
  );
}
