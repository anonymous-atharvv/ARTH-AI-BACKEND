import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${API_BASE}/api/v1`,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor: Inject JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('arthai_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Response interceptor: Clear token on 401, and perform retry with exponential backoff on 5xx/network errors
const MAX_RETRIES = 3;
const INITIAL_DELAY = 1000;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error;
    if (!config) {
      return Promise.reject(error);
    }

    const cfg = config as any;
    cfg.__retryCount = cfg.__retryCount || 0;

    // Handle 401 unauthorized
    if (response?.status === 401 && !cfg._retry) {
      cfg._retry = true;
      localStorage.removeItem('arthai_token');
      localStorage.removeItem('arthai_user_id');
      if (!window.location.pathname.includes('/demo')) {
         window.location.href = '/demo';
      }
      return Promise.reject(error);
    }

    // Determine if we should retry (network error or 5xx server error)
    const shouldRetry = !response || (response.status >= 500 && response.status <= 599);

    if (shouldRetry && cfg.__retryCount < MAX_RETRIES) {
      cfg.__retryCount += 1;
      const delay = INITIAL_DELAY * Math.pow(2, cfg.__retryCount - 1);
      console.warn(`Request failed. Retrying (${cfg.__retryCount}/${MAX_RETRIES}) in ${delay}ms...`, cfg.url);
      await new Promise((resolve) => setTimeout(resolve, delay));
      return api(cfg);
    }

    return Promise.reject(error);
  }
);

// API methods
export const apiClient = {
  // Auth
  sendOtp: (phone: string) => api.post('/auth/send-otp', { phone }),
  verifyOtp: (phone: string, otp: string) => api.post('/auth/verify-otp', { phone, otp }),
  getDemoToken: () => api.post('/auth/demo-token'),

  // Dashboard
  getSummary: (userId: string) => api.get(`/analytics/summary/${userId}`),
  getPnl: (userId: string, period = '90d') => api.get(`/analytics/pnl/${userId}`, { params: { period } }),
  getCashFlow: (userId: string) => api.get(`/analytics/cash-flow/${userId}`),

  // Transactions
  getTransactions: (userId: string, page = 1, limit = 50) =>
    api.get(`/transactions/${userId}`, { params: { page, limit } }),
  createTransaction: (userId: string, txData: any) =>
    api.post(`/transactions/${userId}`, txData),

  // Score
  getArthScore: (userId: string) => api.get(`/score/${userId}`),
  getArthScoreHistory: (userId: string) => api.get(`/score/${userId}/history`),

  // Reports
  generatePassport: (userId: string) => api.post(`/reports/passport/${userId}`),
  generateGstInvoice: (userId: string, transactionId: string) => api.post(`/reports/gst-invoice/${userId}/${transactionId}`),
  getGSTR1Data: (userId: string, year: number, month: number) =>
    api.get(`/reports/gst-report/${userId}`, { params: { year, month } }),

  // Marketplace
  getLoanOffers: (userId: string) => api.get(`/marketplace/offers/${userId}`),

  // Demo
  seedDemo: () => api.post('/demo/seed'),

  // Account Aggregator
  initiateAAConsent: (userId: string) => api.post(`/aa/consent/initiate/${userId}`),

  // Benchmarking
  getPeerBenchmarks: (userId: string, periodDays: number = 30) =>
    api.get(`/analytics/benchmarks/${userId}`, { params: { period_days: periodDays } }),

  // Cash flow forecast
  getCashFlowForecast: (userId: string, forecastDays: number = 30) =>
    api.get(`/analytics/cash-flow/forecast/${userId}`, { params: { forecast_days: forecastDays } }),
};

export default apiClient;
