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
    // Branch scoping: admin users may pin a branch via the header selector.
    const storedUser = localStorage.getItem('user');
    const branchId = localStorage.getItem('branch_id');
    if (branchId && storedUser) {
      try {
        if (JSON.parse(storedUser)?.role === 'admin') {
          config.headers['X-Branch-Id'] = branchId;
        }
      } catch {
        // ignore malformed stored user
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

const handleUnauthorized = () => {
  localStorage.removeItem('user');
  localStorage.removeItem('token');
  // Don't bounce when already on the login page (avoids a reload loop
  // now that session restore hits /auth/me on every app mount).
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
};

// Silent token rotation: on 401 (except for /auth/login and /auth/refresh
// themselves, and only one retry per request via _retry), hit
// POST /api/auth/refresh (which rotates the refresh cookie) and replay the
// original request. Concurrent 401s queue behind a single refresh call.
let isRefreshing = false;
let refreshQueue = [];

const processRefreshQueue = (error) => {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve();
  });
  refreshQueue = [];
};

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    const url = originalRequest.url || '';
    const status = error.response?.status;
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/refresh');

    if (status === 401 && !isAuthCall && !originalRequest._retry) {
      if (isRefreshing) {
        try {
          await new Promise((resolve, reject) => {
            refreshQueue.push({ resolve, reject });
          });
          originalRequest._retry = true;
          return api(originalRequest);
        } catch (queueError) {
          return Promise.reject(queueError);
        }
      }

      originalRequest._retry = true;
      isRefreshing = true;
      try {
        await api.post('/auth/refresh');
        processRefreshQueue(null);
        return api(originalRequest);
      } catch (refreshError) {
        processRefreshQueue(refreshError);
        // Refresh failed (cookie invalid/expired) → existing logout-redirect.
        handleUnauthorized();
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    if (status === 401) {
      handleUnauthorized();
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
  refresh: () => api.post('/auth/refresh'),
  register: (userData) => api.post('/auth/register', userData),
  getMe: () => api.get('/auth/me'),
};

// Inventory APIs
export const inventoryAPI = {
  getAll: (params) => api.get('/inventory', { params }),
  getById: (id) => api.get(`/inventory/${id}`),
  create: (data) => api.post('/inventory', data),
  update: (id, data) => api.put(`/inventory/${id}`, data),
  remove: (id) => api.delete(`/inventory/${id}`),
  getAlerts: () => api.get('/inventory/alerts'),
};

// QC APIs
export const qcAPI = {
  getControls: () => api.get('/qc/controls'),
  createControl: (data) => api.post('/qc/controls', data),
  updateControl: (id, data) => api.put(`/qc/controls/${id}`, data),
  deleteControl: (id) => api.delete(`/qc/controls/${id}`),
  logRun: (id, data) => api.post(`/qc/controls/${id}/runs`, data),
  getRuns: (id) => api.get(`/qc/controls/${id}/runs`),
  getChartData: (id) => api.get(`/qc/controls/${id}/chart-data`),
};

// Branch APIs
export const branchAPI = {
  getAll: () => api.get('/branches'),
  create: (data) => api.post('/branches', data),
  update: (id, data) => api.put(`/branches/${id}`, data),
  remove: (id) => api.delete(`/branches/${id}`),
};

// Patient APIs
export const patientAPI = {
  getAll: (params) => {
    // Back-compat: getAll("search text") still works
    const q = typeof params === 'string' ? { search: params } : params || {};
    return api.get('/patients', { params: q });
  },
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
  getCriticalAlerts: (status = 'pending') => api.get('/critical-alerts', { params: { status } }),
  acknowledgeAlert: (alertId) => api.post(`/critical-alerts/${alertId}/acknowledge`),
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
