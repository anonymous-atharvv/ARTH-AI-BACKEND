import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// API methods
export const apiClient = {
  // Dashboard
  getSummary: (userId: string) => api.get(`/api/analytics/summary/${userId}`),
  getPnl: (userId: string, period = '90d') => api.get(`/api/analytics/pnl/${userId}`, { params: { period } }),
  getCashFlow: (userId: string) => api.get(`/api/analytics/cash-flow/${userId}`),

  // Transactions
  getTransactions: (userId: string, page = 1, limit = 50) =>
    api.get(`/api/transactions/${userId}`, { params: { page, limit } }),

  // Score
  getArthScore: (userId: string) => api.get(`/api/score/${userId}`),

  // Reports
  generatePassport: (userId: string) => api.post(`/api/reports/passport/${userId}`),

  // Marketplace
  getLoanOffers: (userId: string) => api.get(`/api/marketplace/offers/${userId}`),

  // Demo
  seedDemo: () => api.post('/api/demo/seed'),
};

export default apiClient;
