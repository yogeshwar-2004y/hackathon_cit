import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import client from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [seller, setSeller] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('ps_token'));
  const [loading, setLoading] = useState(true);

  const restoreSession = useCallback(async () => {
    const t = localStorage.getItem('ps_token');
    if (!t) {
      setLoading(false);
      return;
    }
    try {
      const { data } = await client.get('/auth/me');
      setSeller(data);
      setToken(t);
    } catch {
      localStorage.removeItem('ps_token');
      setSeller(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (email, password) => {
    const form = new URLSearchParams();
    form.append('username', email);
    form.append('password', password);
    const { data } = await client.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('ps_token', data.access_token);
    setToken(data.access_token);
    setSeller(data.seller);
    return data;
  }, []);

  const signup = useCallback(async (data) => {
    const res = await client.post('/auth/signup', {
      email: data.email,
      password: data.password,
      business_name: data.business_name,
      phone: data.phone || null,
      platform: data.platform || 'amazon',
    });
    const { access_token, seller: s } = res.data;
    localStorage.setItem('ps_token', access_token);
    setToken(access_token);
    setSeller(s);
    return res.data;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('ps_token');
    setToken(null);
    setSeller(null);
    window.location.href = '/login';
  }, []);

  const value = { seller, token, login, signup, logout, loading };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
