import { createContext, useContext, useState, useEffect } from 'react';
import { getCurrentUser, getToken, logout as authLogout } from '../services/authService';

const AuthContext = createContext(null);

/**
 * AuthProvider — wraps the app and provides global auth state.
 *
 * Exposed values:
 *   user     → { userId, name, email } | null
 *   token    → JWT string | null
 *   isAuthenticated → boolean
 *   setAuth(token, user) → called after login/register
 *   logout() → clears state + localStorage
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate from localStorage on app start
  useEffect(() => {
    const storedToken = getToken();
    const storedUser = getCurrentUser();
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(storedUser);
    }
    setLoading(false);
  }, []);

  /**
   * Called after a successful register or login response.
   * Persists token + user to localStorage and updates context.
   */
  const setAuth = (newToken, newUser) => {
    localStorage.setItem('ps_token', newToken);
    localStorage.setItem('ps_user', JSON.stringify(newUser));
    setToken(newToken);
    setUser(newUser);
  };

  /**
   * Clears auth state from context and localStorage.
   */
  const logout = () => {
    authLogout();
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token,
    loading,
    setAuth,
    logout,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
}

/** Custom hook — use anywhere in the app */
export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
};
