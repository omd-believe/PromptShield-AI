import api from './api';

/**
 * Decode the payload from a JWT token (base64url → JSON).
 * Used to extract email/subject since backend AuthResponse only returns { message, token }.
 */
const decodeJwtPayload = (token) => {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return {};
  }
};

/**
 * Build a minimal user object from the JWT payload.
 * Backend sets the JWT subject to the user's email (see JwtService.generateToken).
 */
const userFromToken = (token, name = '') => {
  const payload = decodeJwtPayload(token);
  return {
    email: payload.sub || '',
    name: name || payload.sub?.split('@')[0] || 'User',
  };
};

/**
 * POST /api/v1/register
 * Body:     { name, email, password }
 * Response: { message, token }
 */
export const register = async (name, email, password) => {
  const response = await api.post('/register', { name, email, password });
  const { token } = response.data;
  return { token, user: userFromToken(token, name) };
};

/**
 * POST /api/v1/login
 * Body:     { email, password }
 * Response: { message, token }
 */
export const login = async (email, password) => {
  const response = await api.post('/login', { email, password });
  const { token } = response.data;
  return { token, user: userFromToken(token) };
};

export const logout = () => {
  localStorage.removeItem('ps_token');
  localStorage.removeItem('ps_user');
};

export const getCurrentUser = () => {
  const user = localStorage.getItem('ps_user');
  return user ? JSON.parse(user) : null;
};

export const getToken = () => localStorage.getItem('ps_token');
