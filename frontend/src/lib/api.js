import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API_BASE = `${BACKEND_URL}/api`;

// Create axios instance
const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // send the httpOnly auth cookie
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user');
      // Don't bounce when already on the login page (avoids a reload loop
      // now that session restore hits /auth/me on every app mount).
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Extract a human-readable message from an API error.
// FastAPI 422 responses carry `detail` as an ARRAY of objects — rendering it
// directly crashes React, so always collapse it to a string.
export const getErrorMessage = (error, fallback = 'Something went wrong') => {
  const detail = error?.response?.data?.detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map((d) => d?.msg).filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }
  if (typeof detail === 'string' && detail) return detail;
  return error?.message || fallback;
};

// Auth APIs
export const authAPI = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout'),
  register: (userData) => api.post('/auth/register', userData),
  getMe: () => api.get('/auth/me'),
};

// Patient APIs
export const patientAPI = {
  getAll: (search) => api.get('/patients', { params: { search } }),
  getById: (id) => api.get(`/patients/${id}`),
  create: (data) => api.post('/patients', data),
  update: (id, data) => api.put(`/patients/${id}`, data),
};

// Test Catalog APIs
export const testAPI = {
  getAll: (params) => api.get('/tests', { params }),
  getById: (id) => api.get(`/tests/${id}`),
  create: (data) => api.post('/tests', data),
  update: (id, data) => api.put(`/tests/${id}`, data),
  getCategories: () => api.get('/test-categories'),
};

// Order APIs
export const orderAPI = {
  getAll: (params) => api.get('/orders', { params }),
  getById: (id) => api.get(`/orders/${id}`),
  create: (data) => api.post('/orders', data),
  updateStatus: (id, status) => api.put(`/orders/${id}/status`, null, { params: { status } }),
};

// Sample APIs
export const sampleAPI = {
  getAll: (params) => api.get('/samples', { params }),
  create: (data) => api.post('/samples', data),
  updateStatus: (id, status) => api.put(`/samples/${id}/status`, null, { params: { status } }),
};

// Result APIs
export const resultAPI = {
  enter: (data) => api.post('/results', data),
  getTechnicianQueue: () => api.get('/technician/queue'),
};

// Pathologist APIs
export const pathologistAPI = {
  getQueue: () => api.get('/pathologist/queue'),
  approve: (data) => api.post('/approve', data),
};

// Report APIs
export const reportAPI = {
  get: (orderId) => api.get(`/reports/${orderId}`),
  release: (orderId) => api.post(`/reports/${orderId}/release`),
  generatePdf: (orderId) => api.post(`/reports/${orderId}/generate-pdf`),
  getPdfUrl: (orderId, filename) => `${BACKEND_URL}/api/reports/${orderId}/download/${filename}`,
  streamPdf: (orderId) => `${BACKEND_URL}/api/reports/${orderId}/pdf-stream`,
};

// Invoice APIs
export const invoiceAPI = {
  getAll: (params) => api.get('/invoices', { params }),
  getById: (id) => api.get(`/invoices/${id}`),
  recordPayment: (data) => api.post('/payments', data),
};

// Analytics APIs
export const analyticsAPI = {
  getDashboard: () => api.get('/analytics/dashboard'),
};

// User APIs
export const userAPI = {
  getAll: () => api.get('/users'),
  update: (id, data) => api.put(`/users/${id}`, data),
};

// Seed API
export const seedAPI = {
  seed: () => api.post('/seed'),
};

// Doctor APIs (referring doctors list)
export const doctorAPI = {
  getAll: () => api.get('/doctors'),
};

export default api;
