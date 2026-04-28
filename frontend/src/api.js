import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Use environment variable or fallback to empty string (user will input via UI)
let currentMerchantId = process.env.REACT_APP_MERCHANT_ID || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to ensure merchant ID is sent
api.interceptors.request.use((config) => {
  if (currentMerchantId) {
    config.headers['X-Merchant-ID'] = currentMerchantId;
  }
  console.log('API Request:', config.method?.toUpperCase(), config.url, 'Merchant:', currentMerchantId);
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const setMerchantId = (id) => {
  if (id) {
    currentMerchantId = id;
    api.defaults.headers['X-Merchant-ID'] = id;
    console.log('Merchant ID updated:', id);
  }
};

// Initialize with default
api.defaults.headers['X-Merchant-ID'] = currentMerchantId;

export const getMerchant = () => api.get('/merchants/me/');
export const getTransactions = () => api.get('/transactions/');
export const getPayouts = () => api.get('/payouts/');
export const createPayout = (data, idempotencyKey) =>
  api.post('/payouts/', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  });

export default api;
