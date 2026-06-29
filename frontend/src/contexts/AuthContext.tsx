import React, { createContext, useContext, useState } from 'react';
import apiClient from '../api/client';

interface AuthContextType {
  token: string | null;
  userId: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (token: string, userId: string) => void;
  logout: () => Promise<void>;
  loginDemo: () => Promise<string>;
  requestOtp: (phone: string) => Promise<void>;
  confirmOtp: (phone: string, otp: string) => Promise<any>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem('arthai_token'));
  const [userId, setUserId] = useState<string | null>(localStorage.getItem('arthai_user_id'));
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const login = (newToken: string, newUserId: string) => {
    localStorage.setItem('arthai_token', newToken);
    localStorage.setItem('arthai_user_id', newUserId);
    setToken(newToken);
    setUserId(newUserId);
  };

  const logout = async () => {
    try {
      await apiClient.logout();
    } catch (err) {
      console.warn('Failed to call backend logout endpoint:', err);
    } finally {
      localStorage.removeItem('arthai_token');
      localStorage.removeItem('arthai_user_id');
      setToken(null);
      setUserId(null);
    }
  };

  const loginDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      const seedRes = await apiClient.seedDemo();
      const demoUserId = seedRes.data.demo_user_id;

      const tokenRes = await apiClient.getDemoToken();
      const demoToken = tokenRes.data.access_token;

      localStorage.setItem('arthai_token', demoToken);
      localStorage.setItem('arthai_user_id', demoUserId);

      setToken(demoToken);
      setUserId(demoUserId);
      return demoUserId;
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || 'Failed to authenticate demo';
      setError(errMsg);
      throw new Error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const requestOtp = async (phone: string) => {
    setLoading(true);
    setError(null);
    try {
      await apiClient.sendOtp(phone);
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || 'Failed to send OTP';
      setError(errMsg);
      throw new Error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const confirmOtp = async (phone: string, otp: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiClient.verifyOtp(phone, otp);
      const { access_token, user_id } = res.data;

      localStorage.setItem('arthai_token', access_token);
      localStorage.setItem('arthai_user_id', user_id);

      setToken(access_token);
      setUserId(user_id);
      return res.data;
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || 'Invalid OTP';
      setError(errMsg);
      throw new Error(errMsg);
    } finally {
      setLoading(false);
    }
  };

  const isAuthenticated = !!token;

  return (
    <AuthContext.Provider value={{
      token,
      userId,
      isAuthenticated,
      loading,
      error,
      login,
      logout,
      loginDemo,
      requestOtp,
      confirmOtp
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
