import axios from 'axios';

/**
 * Axios instance pre-configured for the Spring Boot backend.
 * Base URL: adjust in .env as VITE_API_BASE_URL
 * Default: http://localhost:8080/api
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
});

// ── Request Interceptor: attach JWT token to every request ──
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('ps_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor: handle 401 globally ──
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      // Do NOT redirect on auth routes — let Login.jsx / Register.jsx handle the error
      const isAuthRoute = url.includes('/login') || url.includes('/register');
      if (!isAuthRoute) {
        // Token expired on a protected route — clear and redirect
        localStorage.removeItem('ps_token');
        localStorage.removeItem('ps_user');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
