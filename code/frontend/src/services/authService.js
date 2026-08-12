import api from './api';

export const DEMO_USER = {
  token: 'demo-jwt-token-xyz-12345',
  user: {
    userId: 999,
    name: 'Testing Account (Demo)',
    email: 'demo@promptshield.ai',
  },
};

export const register = async (name, email, password) => {
  try {
    const response = await api.post('/auth/register', { name, email, password });
    return response.data;
  } catch (err) {
    if (!err.response) {
      console.warn('Backend offline — providing demo testing registration.');
      return {
        token: DEMO_USER.token,
        user: { userId: Date.now(), name, email },
      };
    }
    throw err;
  }
};

export const login = async (email, password) => {
  try {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  } catch (err) {
    if (!err.response || email === DEMO_USER.user.email) {
      console.warn('Backend offline or Demo login requested — returning demo user.');
      return DEMO_USER;
    }
    throw err;
  }
};

export const loginAsDemoUser = () => DEMO_USER;

export const logout = () => {
  localStorage.removeItem('ps_token');
  localStorage.removeItem('ps_user');
};

export const getCurrentUser = () => {
  const user = localStorage.getItem('ps_user');
  return user ? JSON.parse(user) : null;
};

export const getToken = () => localStorage.getItem('ps_token');
