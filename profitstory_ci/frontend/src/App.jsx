import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import PageLogin from './pages/PageLogin';
import PageSignup from './pages/PageSignup';
import PageProducts from './pages/PageProducts';
import PageProductDetail from './pages/PageProductDetail';
import PageIntelligence from './pages/PageIntelligence';
import PageSettings from './pages/PageSettings';
import PageAudit from './pages/PageAudit';
import PageForgotPassword from './pages/PageForgotPassword';
import PageResetPassword from './pages/PageResetPassword';
import './index.css';

function ProtectedRoute() {
  const { seller, loading } = useAuth();
  if (loading) return <div className="app-container"><div className="main-content"><div className="empty-state">Loading…</div></div></div>;
  if (!seller) return <Navigate to="/login" replace />;
  return (
    <div className="app-container">
      <Sidebar />
      <Outlet />
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<PageLogin />} />
      <Route path="/signup" element={<PageSignup />} />
      <Route path="/forgot-password" element={<PageForgotPassword />} />
      <Route path="/reset-password" element={<PageResetPassword />} />
      <Route path="/" element={<ProtectedRoute />}>
        <Route index element={<Navigate to="/products" replace />} />
        <Route path="products" element={<PageProducts />} />
        <Route path="products/:id" element={<PageProductDetail />} />
        <Route path="products/:id/intelligence" element={<PageIntelligence />} />
        <Route path="settings" element={<PageSettings />} />
        <Route path="audit" element={<PageAudit />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster position="top-right" toastOptions={{ style: { background: 'var(--bg-card)', color: 'var(--text-primary)', border: '1px solid var(--border-light)' } }} />
      </AuthProvider>
    </BrowserRouter>
  );
}
