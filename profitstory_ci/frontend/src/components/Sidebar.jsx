import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Target, Settings, LogOut, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import client from '../api/client';

export default function Sidebar() {
  const { seller, logout } = useAuth();
  const location = useLocation();
  const [recentProducts, setRecentProducts] = useState([]);

  useEffect(() => {
    client.get('/products').then(({ data }) => {
      setRecentProducts((data || []).slice(0, 5));
    }).catch(() => {});
  }, []);

  return (
    <div className="sidebar">
      <div className="brand-logo">Shadowspy.ai</div>
      <div className="sidebar-seller">
        <div className="sidebar-seller-name">{seller?.business_name}</div>
        <div className="sidebar-seller-email">{seller?.email}</div>
      </div>
      <nav className="nav-section">
        <Link to="/products" className={`nav-item ${location.pathname === '/products' ? 'active' : ''}`}>
          <Target size={14} /> My Products
        </Link>
        {recentProducts.length > 0 && (
          <div className="nav-section-title">Recent</div>
        )}
        {recentProducts.map((p) => (
          <Link key={p.id} to={`/products/${p.id}`} className={`nav-item ${location.pathname === `/products/${p.id}` && !location.pathname.includes('/intelligence') ? 'active' : ''}`}>
            {p.product_name?.slice(0, 20)}{(p.product_name?.length > 20) ? '…' : ''}
          </Link>
        ))}
      </nav>
      <div className="nav-section" style={{ marginTop: 'auto' }}>
        <div className="nav-section-title">Account</div>
        <Link to="/settings" className={`nav-item ${location.pathname === '/settings' ? 'active' : ''}`}>
          <Settings size={14} /> Settings
        </Link>
        <Link to="/audit" className={`nav-item ${location.pathname === '/audit' ? 'active' : ''}`}>
          <Shield size={14} /> Audit log
        </Link>
        <button type="button" className="nav-item nav-item-btn" onClick={logout}>
          <LogOut size={14} /> Logout
        </button>
        <div className="sidebar-version">v1.0</div>
      </div>
    </div>
  );
}
