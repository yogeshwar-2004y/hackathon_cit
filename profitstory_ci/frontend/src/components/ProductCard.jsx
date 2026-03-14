import React from 'react';
import { Link } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';

export default function ProductCard({ product, lastRunAt }) {
  const platformLabel = product.platform === 'amazon' ? 'Amazon' : product.platform === 'flipkart' ? 'Flipkart' : 'Snapdeal';
  const competitorCount = product.competitor_count ?? product.competitors?.length ?? 0;

  return (
    <div className="product-card">
      <div className="product-card-header">
        <h3>{product.product_name}</h3>
        <span className="badge blue">{product.category}</span>
      </div>
      <div className="product-card-meta">
        <span className="platform-badge">{platformLabel}</span>
        <code className="platform-id">{product.platform_id}</code>
      </div>
      <div className="product-card-price">
        {product.price != null ? `₹${Number(product.price).toLocaleString()}` : '—'}
        {product.cost != null && <span className="muted">Cost: ₹{Number(product.cost).toLocaleString()}</span>}
      </div>
      <div className="product-card-stats">
        {competitorCount} competitor{competitorCount !== 1 ? 's' : ''}
        {lastRunAt && <span className="muted"> · Last scan: {lastRunAt}</span>}
      </div>
      <div className="product-card-actions">
        <Link to={`/products/${product.id}`} className="btn-link">View Details</Link>
        <Link to={`/products/${product.id}/intelligence`} className="btn-scan" style={{ padding: '8px 14px', fontSize: 13 }}>
          Run Analysis
        </Link>
      </div>
    </div>
  );
}
