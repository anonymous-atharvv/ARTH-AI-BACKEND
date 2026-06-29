import { useState } from 'react';
import apiClient from '../api/client';

export function useAuth() {
  const [token, setToken] = useState<string | null>(localStorage.getItem('arthai_token'));
  const [userId, setUserId] = useState<string | null>(localStorage.getItem('arthai_user_id'));
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const isAuthenticated = !!token;

  const loginDemo = async () => {
    setLoading(true);
    setError(null);
    try {
      // First seed the demo
      const seedRes = await apiClient.seedDemo();
      const demoUserId = seedRes.data.demo_user_id;

      // Then fetch demo token
      const tokenRes = await apiClient.getDemoToken();
      const demoToken = tokenRes.data.access_token;

      // Store in localStorage
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

  const logout = () => {
    localStorage.removeItem('arthai_token');
    localStorage.removeItem('arthai_user_id');
    setToken(null);
    setUserId(null);
  };

  return {
    token,
    userId,
    isAuthenticated,
    loading,
    error,
    loginDemo,
    requestOtp,
    confirmOtp,
    logout
  };
}

export default useAuth;
