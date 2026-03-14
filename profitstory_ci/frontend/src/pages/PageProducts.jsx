import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';
import ProductCard from '../components/ProductCard';
import AddProductModal from '../components/AddProductModal';

export default function PageProducts() {
  const { seller } = useAuth();
  const [products, setProducts] = useState([]);
  const [historyByProduct, setHistoryByProduct] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const fetchProducts = async () => {
    try {
      const { data } = await client.get('/products');
      setProducts(data);
    } catch (e) {
      setProducts([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  useEffect(() => {
    if (products.length === 0) return;
    const run = async () => {
      const out = {};
      for (const p of products) {
        try {
          const { data } = await client.get(`/scan/${p.id}/history?limit=1`);
          if (data.runs?.[0]?.created_at) out[p.id] = new Date(data.runs[0].created_at).toLocaleString();
        } catch {}
      }
      setHistoryByProduct(out);
    };
    run();
  }, [products]);

  return (
    <div className="main-content">
        <div className="header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <h1 className="header-title">My Products</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span className="seller-name">{seller?.business_name}</span>
            <button className="btn-scan" onClick={() => setShowAddModal(true)}>+ Add Product</button>
          </div>
        </div>
        {loading ? (
          <div className="empty-state">Loading…</div>
        ) : products.length === 0 ? (
          <div className="panel" style={{ maxWidth: 520, margin: '48px auto', textAlign: 'center' }}>
            <div className="empty-state">
              <h3 style={{ marginBottom: 8 }}>No products yet</h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: 24 }}>Add your first product to start competitive intelligence.</p>
              <button className="btn-scan" onClick={() => setShowAddModal(true)}>+ Add Product</button>
            </div>
          </div>
        ) : (
          <div className="product-grid">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} lastRunAt={historyByProduct[p.id] || null} />
            ))}
          </div>
        )}
      {showAddModal && <AddProductModal onClose={() => setShowAddModal(false)} onSaved={fetchProducts} />}
    </div>
  );
}

