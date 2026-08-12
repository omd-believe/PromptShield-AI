import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, Mail, Lock, Eye, EyeOff, ArrowRight, AlertCircle, Sparkles, Zap } from 'lucide-react';
import { login, DEMO_USER } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

export default function Login() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');

  /* ── Field change ── */
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    if (apiError) setApiError('');
  };

  /* ── Client-side validation ── */
  const validate = () => {
    const newErrors = {};
    if (!form.email.trim()) newErrors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      newErrors.email = 'Enter a valid email address.';

    if (!form.password) newErrors.password = 'Password is required.';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /* ── Submit → POST /api/auth/login (with fallback) ── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setApiError('');
    try {
      const { token, user } = await login(form.email.trim(), form.password);
      setAuth(token, user);       // persist JWT + user
      navigate('/dashboard');     // redirect to protected dashboard
    } catch (err) {
      const msg =
        err.response?.data?.message ||
        err.response?.data?.error ||
        (err.response?.status === 401
          ? 'Invalid email or password.'
          : 'Login failed. Please try again.');
      setApiError(msg);
    } finally {
      setLoading(false);
    }
  };

  /* ── Quick Test Login ── */
  const handleQuickDemoLogin = () => {
    setForm({ email: DEMO_USER.user.email, password: 'DemoUser123!' });
    setAuth(DEMO_USER.token, DEMO_USER.user);
    navigate('/dashboard');
  };

  return (
    <div className="auth-page">
      {/* Background orbs */}
      <div className="auth-orb auth-orb--1" aria-hidden="true" />
      <div className="auth-orb auth-orb--2" aria-hidden="true" />

      <div className="auth-container">
        {/* ── Brand ── */}
        <Link to="/" className="auth-brand">
          <div className="auth-brand__icon"><Shield size={18} /></div>
          <span>Prompt<span className="gradient-text">Shield</span> AI</span>
        </Link>

        {/* ── Card ── */}
        <div className="auth-card">
          <div className="auth-card__accent" />

          <div className="auth-card__header">
            <h1 className="auth-card__title">Welcome back</h1>
            <p className="auth-card__subtitle">
              Log in to continue shielding your prompts.
            </p>
          </div>

          {/* ── Quick Test User Banner ── */}
          <div className="auth-demo-banner">
            <div className="auth-demo-banner__info">
              <Sparkles size={16} className="auth-demo-banner__icon" />
              <div>
                <strong>Testing / Evaluation Mode</strong>
                <p>Click below to log in instantly with a test user.</p>
              </div>
            </div>
            <button
              type="button"
              className="auth-demo-btn"
              onClick={handleQuickDemoLogin}
            >
              <Zap size={14} /> Log in as Demo User
            </button>
          </div>

          {/* ── API Error Banner ── */}
          {apiError && (
            <div className="auth-error-banner" role="alert">
              <AlertCircle size={16} />
              <span>{apiError}</span>
            </div>
          )}

          <form className="auth-form" onSubmit={handleSubmit} noValidate>

            {/* Email */}
            <div className={`auth-field ${errors.email ? 'auth-field--error' : ''}`}>
              <label className="auth-label" htmlFor="email">Email Address</label>
              <div className="auth-input-wrap">
                <Mail size={16} className="auth-input-icon" />
                <input
                  id="email"
                  name="email"
                  type="email"
                  className="auth-input"
                  placeholder="you@example.com"
                  value={form.email}
                  onChange={handleChange}
                  autoComplete="email"
                  disabled={loading}
                />
              </div>
              {errors.email && (
                <span className="auth-field-error">
                  <AlertCircle size={12} />{errors.email}
                </span>
              )}
            </div>

            {/* Password */}
            <div className={`auth-field ${errors.password ? 'auth-field--error' : ''}`}>
              <div className="auth-label-row">
                <label className="auth-label" htmlFor="password">Password</label>
                <span className="auth-link auth-forgot-link">Forgot password?</span>
              </div>
              <div className="auth-input-wrap">
                <Lock size={16} className="auth-input-icon" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Your password"
                  value={form.password}
                  onChange={handleChange}
                  autoComplete="current-password"
                  disabled={loading}
                />
                <button
                  type="button"
                  className="auth-eye-btn"
                  onClick={() => setShowPassword(p => !p)}
                  tabIndex={-1}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.password && (
                <span className="auth-field-error">
                  <AlertCircle size={12} />{errors.password}
                </span>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              id="login-submit-btn"
              className={`btn-primary auth-submit ${loading ? 'auth-submit--loading' : ''}`}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="auth-spinner" />
                  Logging in…
                </>
              ) : (
                <>
                  Log In
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          {/* Divider */}
          <div className="auth-divider">
            <span />
            <p>New to PromptShield?</p>
            <span />
          </div>

          {/* Register CTA */}
          <Link to="/register" className="auth-register-cta">
            Create a free account
          </Link>
        </div>

        {/* Terms note */}
        <p className="auth-terms">
          By logging in, you agree to our{' '}
          <span className="auth-link">Terms of Service</span> and{' '}
          <span className="auth-link">Privacy Policy</span>.
        </p>
      </div>
    </div>
  );
}
