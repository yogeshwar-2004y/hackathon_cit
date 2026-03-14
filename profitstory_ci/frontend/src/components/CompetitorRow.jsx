import React, { useState } from 'react';
import { Pencil, Trash2 } from 'lucide-react';
import client from '../api/client';

export default function CompetitorRow({ productId, competitor, onUpdated, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(competitor.competitor_name);
  const [platformId, setPlatformId] = useState(competitor.platform_id);
  const [notes, setNotes] = useState(competitor.notes || '');
  const [loading, setLoading] = useState(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await client.patch(`/products/${productId}/competitors/${competitor.id}`, {
        competitor_name: name,
        platform_id: platformId,
        notes: notes || null,
      });
      onUpdated?.();
      setEditing(false);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Remove this competitor?')) return;
    try {
      await client.delete(`/products/${productId}/competitors/${competitor.id}`);
      onDeleted?.();
    } catch (e) {
      console.error(e);
    }
  };

  const platformLabel = competitor.platform === 'amazon' ? 'Amazon' : competitor.platform === 'flipkart' ? 'Flipkart' : 'Snapdeal';

  if (editing) {
    return (
      <tr>
        <td><input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-visible" style={{ width: '100%', padding: 6 }} /></td>
        <td>{platformLabel}</td>
        <td><input type="text" value={platformId} onChange={(e) => setPlatformId(e.target.value)} className="input-visible" style={{ width: '100%', padding: 6 }} /></td>
        <td><input type="text" value={notes} onChange={(e) => setNotes(e.target.value)} className="input-visible" style={{ width: '100%', padding: 6 }} placeholder="Notes" /></td>
        <td>
          <button type="button" className="btn-scan" style={{ padding: '4px 10px', marginRight: 8 }} onClick={handleSave} disabled={loading}>Save</button>
          <button type="button" className="btn-secondary" style={{ padding: '4px 10px' }} onClick={() => setEditing(false)}>Cancel</button>
        </td>
      </tr>
    );
  }

  return (
    <tr>
      <td>{competitor.competitor_name}</td>
      <td>{platformLabel}</td>
      <td><code style={{ fontSize: 12 }}>{competitor.platform_id}</code></td>
      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{competitor.notes || '—'}</td>
      <td>
        <button type="button" className="icon-btn" onClick={() => setEditing(true)} aria-label="Edit"><Pencil size={14} /></button>
        <button type="button" className="icon-btn" onClick={handleDelete} aria-label="Delete" style={{ color: 'var(--red)' }}><Trash2 size={14} /></button>
      </td>
    </tr>
  );
}
