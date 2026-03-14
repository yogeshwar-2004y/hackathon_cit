import React, { useState } from 'react';
import client from '../api/client';

const CATEGORIES = ['Earphones', 'Smartphones', 'Laptops', 'Clothing', 'Footwear', 'Home & Kitchen', 'Books', 'Toys', 'Sports', 'Other'];
const PLATFORMS = [
  { value: 'amazon', label: 'Amazon India', idLabel: 'Amazon ASIN (e.g. B0863TXGM3)' },
  { value: 'flipkart', label: 'Flipkart', idLabel: 'Flipkart Product ID / FSN' },
  { value: 'snapdeal', label: 'Snapdeal', idLabel: 'Snapdeal Product ID' },
];

export default function AddProductModal({ onClose, onSaved }) {
  const [productName, setProductName] = useState('');
  const [category, setCategory] = useState('Earphones');
  const [platform, setPlatform] = useState('amazon');
  const [platformId, setPlatformId] = useState('');
  const [price, setPrice] = useState('');
  const [cost, setCost] = useState('');
  const [monthlyUnits, setMonthlyUnits] = useState(40);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    if (!productName.trim() || !platformId.trim()) {
      setError('Product name and Product ID are required.');
      return;
    }
    setLoading(true);
    try {
      await client.post('/products', {
        product_name: productName.trim(),
        category,
        platform,
        platform_id: platformId.trim(),
        price: price ? parseFloat(price) : null,
        cost: cost ? parseFloat(cost) : null,
        monthly_units: monthlyUnits,
      });
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to save product');
    } finally {
      setLoading(false);
    }
  };

  const idLabel = PLATFORMS.find((p) => p.value === platform)?.idLabel || 'Product ID';

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Product</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">&times;</button>
        </div>
        <form onSubmit={handleSubmit}>
          {error && <div className="auth-error" style={{ marginBottom: 16 }}>{error}</div>}
          <label>
            Product Name
            <input type="text" value={productName} onChange={(e) => setProductName(e.target.value)} placeholder="e.g. boAt BassHeads 242" required />
          </label>
          <label>
            Category
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label>
            Platform
            <select value={platform} onChange={(e) => setPlatform(e.target.value)}>
              {PLATFORMS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </label>
          <label>
            {idLabel}
            <input type="text" value={platformId} onChange={(e) => setPlatformId(e.target.value)} placeholder={platform === 'amazon' ? 'B0863TXGM3' : 'ID'} required />
          </label>
          <label>
            Your listed price (₹)
            <input type="number" step="0.01" min="0" value={price} onChange={(e) => setPrice(e.target.value)} placeholder="Optional" />
          </label>
          <label>
            Your cost price (₹)
            <input type="number" step="0.01" min="0" value={cost} onChange={(e) => setCost(e.target.value)} placeholder="Used in profit sim" />
          </label>
          <label>
            Monthly unit sales
            <input type="number" min="0" value={monthlyUnits} onChange={(e) => setMonthlyUnits(Number(e.target.value) || 40)} />
          </label>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-scan" disabled={loading}>{loading ? 'Saving…' : 'Save Product'}</button>
          </div>
        </form>
      </div>
    </div>
  );
}
