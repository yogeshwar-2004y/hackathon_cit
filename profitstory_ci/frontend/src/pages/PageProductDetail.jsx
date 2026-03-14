import React, { useState, useEffect } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { Pencil, Trash2 } from 'lucide-react';
import client from '../api/client';
import AddCompetitorModal from '../components/AddCompetitorModal';
import CompetitorRow from '../components/CompetitorRow';

export default function PageProductDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddCompetitor, setShowAddCompetitor] = useState(false);
  const [editingField, setEditingField] = useState(null);
  const [editPrice, setEditPrice] = useState('');
  const [editCost, setEditCost] = useState('');
  const [editUnits, setEditUnits] = useState('');
  const [lastRun, setLastRun] = useState(null);

  const fetchProduct = async () => {
    try {
      const { data } = await client.get(`/products/${id}`);
      setProduct(data);
      setEditPrice(data.price != null ? String(data.price) : '');
      setEditCost(data.cost != null ? String(data.cost) : '');
      setEditUnits(String(data.monthly_units ?? 40));
    } catch (e) {
      setProduct(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProduct();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    client.get(`/scan/${id}/history?limit=1`).then(({ data }) => {
      if (data.runs?.[0]) setLastRun(data.runs[0]);
    }).catch(() => {});
  }, [id]);

  const handleRunAnalysis = async () => {
    try {
      const { data } = await client.post(`/scan/${id}`);
      navigate(`/products/${id}/intelligence?run_id=${data.run_id}`);
    } catch (e) {
      console.error(e);
    }
  };

  const saveField = async (field, value) => {
    try {
      const payload = {};
      if (field === 'price') payload.price = value ? parseFloat(value) : null;
      if (field === 'cost') payload.cost = value ? parseFloat(value) : null;
      if (field === 'monthly_units') payload.monthly_units = value ? parseInt(value, 10) : 40;
      await client.patch(`/products/${id}`, payload);
      setEditingField(null);
      fetchProduct();
    } catch (e) {
      console.error(e);
    }
  };

  const deleteProduct = async () => {
    if (!window.confirm('Delete this product? This cannot be undone.')) return;
    try {
      await client.delete(`/products/${id}`);
      navigate('/products');
    } catch (e) {
      console.error(e);
    }
  };

  const platformLabel = product?.platform === 'amazon' ? 'Amazon' : product?.platform === 'flipkart' ? 'Flipkart' : 'Snapdeal';

  if (loading || !product) {
    return (
      <div className="main-content">
        <div className="empty-state">Loading…</div>
      </div>
    );
  }

  return (
    <div className="main-content">
      <nav className="breadcrumb">
        <Link to="/products">Products</Link>
        <span>/</span>
        <span>{product.product_name}</span>
      </nav>

      <div className="panel product-detail-card">
        <div className="product-detail-header">
          <h1>{product.product_name}</h1>
          <span className="badge blue">{platformLabel}</span>
          <code className="platform-id" style={{ marginLeft: 8 }}>{product.platform_id}</code>
        </div>
        <div className="product-detail-fields">
          <div className="editable-field">
            <span className="label">Listed Price:</span>
            {editingField === 'price' ? (
              <span>
                ₹ <input type="number" step="0.01" value={editPrice} onChange={(e) => setEditPrice(e.target.value)} className="input-visible" style={{ width: 100 }} />
                <button type="button" className="btn-scan" style={{ marginLeft: 8, padding: '4px 10px' }} onClick={() => saveField('price', editPrice)}>Save</button>
                <button type="button" className="btn-secondary" style={{ marginLeft: 4, padding: '4px 10px' }} onClick={() => { setEditingField(null); setEditPrice(product.price != null ? String(product.price) : ''); }}>Cancel</button>
              </span>
            ) : (
              <span>₹{product.price != null ? Number(product.price).toLocaleString() : '—'} <button type="button" className="icon-btn" onClick={() => setEditingField('price')} aria-label="Edit"><Pencil size={14} /></button></span>
            )}
          </div>
          <div className="editable-field">
            <span className="label">Cost Price:</span>
            {editingField === 'cost' ? (
              <span>
                ₹ <input type="number" step="0.01" value={editCost} onChange={(e) => setEditCost(e.target.value)} className="input-visible" style={{ width: 100 }} />
                <button type="button" className="btn-scan" style={{ marginLeft: 8, padding: '4px 10px' }} onClick={() => saveField('cost', editCost)}>Save</button>
                <button type="button" className="btn-secondary" style={{ marginLeft: 4, padding: '4px 10px' }} onClick={() => { setEditingField(null); setEditCost(product.cost != null ? String(product.cost) : ''); }}>Cancel</button>
              </span>
            ) : (
              <span>₹{product.cost != null ? Number(product.cost).toLocaleString() : '—'} <button type="button" className="icon-btn" onClick={() => setEditingField('cost')} aria-label="Edit"><Pencil size={14} /></button></span>
            )}
          </div>
          <div className="editable-field">
            <span className="label">Monthly Units:</span>
            {editingField === 'monthly_units' ? (
              <span>
                <input type="number" min="0" value={editUnits} onChange={(e) => setEditUnits(e.target.value)} className="input-visible" style={{ width: 80 }} />
                <button type="button" className="btn-scan" style={{ marginLeft: 8, padding: '4px 10px' }} onClick={() => saveField('monthly_units', editUnits)}>Save</button>
                <button type="button" className="btn-secondary" style={{ marginLeft: 4, padding: '4px 10px' }} onClick={() => { setEditingField(null); setEditUnits(String(product.monthly_units ?? 40)); }}>Cancel</button>
              </span>
            ) : (
              <span>{product.monthly_units ?? 40} <button type="button" className="icon-btn" onClick={() => setEditingField('monthly_units')} aria-label="Edit"><Pencil size={14} /></button></span>
            )}
          </div>
        </div>
        <div style={{ marginTop: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <button className="btn-scan" onClick={handleRunAnalysis} style={{ padding: '12px 24px' }}>
            Run Competitive Analysis
          </button>
          {lastRun && <span className="muted">Last run: {new Date(lastRun.created_at).toLocaleString()}</span>}
          <button type="button" className="btn-danger" onClick={deleteProduct}>Delete product</button>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 24 }}>
        <div className="panel-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Competitors</span>
          <button className="btn-scan" style={{ padding: '8px 16px' }} onClick={() => setShowAddCompetitor(true)}>+ Add Competitor</button>
        </div>
        {product.competitors?.length > 0 ? (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                <th style={{ textAlign: 'left', padding: 12 }}>Name</th>
                <th style={{ textAlign: 'left', padding: 12 }}>Platform</th>
                <th style={{ textAlign: 'left', padding: 12 }}>Product ID</th>
                <th style={{ textAlign: 'left', padding: 12 }}>Notes</th>
                <th style={{ textAlign: 'right', padding: 12 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {product.competitors.map((c) => (
                <CompetitorRow key={c.id} productId={product.id} competitor={c} onUpdated={fetchProduct} onDeleted={fetchProduct} />
              ))}
            </tbody>
          </table>
        ) : (
          <div className="empty-state">No competitors yet. Add competitors to run analysis.</div>
        )}
      </div>

      {showAddCompetitor && (
        <AddCompetitorModal
          productPlatform={product.platform}
          productId={product.id}
          onClose={() => setShowAddCompetitor(false)}
          onSaved={() => { fetchProduct(); setShowAddCompetitor(false); }}
        />
      )}
    </div>
  );
}
