import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Shield, User, Mail, Lock, Eye, EyeOff, ArrowRight, CheckCircle, AlertCircle } from 'lucide-react';
import { register } from '../services/authService';
import { useAuth } from '../contexts/AuthContext';
import './Auth.css';

/* ── Password strength helper ── */
const getPasswordStrength = (password) => {
  if (!password) return { score: 0, label: '', color: '' };
  let score = 0;
  if (password.length >= 8) score++;
  if (/[A-Z]/.test(password)) score++;
  if (/[0-9]/.test(password)) score++;
  if (/[^A-Za-z0-9]/.test(password)) score++;

  const levels = [
    { score: 1, label: 'Weak', color: '#ff4d6d' },
    { score: 2, label: 'Fair', color: '#f59e0b' },
    { score: 3, label: 'Good', color: '#6c63ff' },
    { score: 4, label: 'Strong', color: '#00d4aa' },
  ];
  return levels[score - 1] || { score: 0, label: '', color: '' };
};

export default function Register() {
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState('');

  const strength = getPasswordStrength(form.password);

  /* ── Field change ── */
  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(prev => ({ ...prev, [name]: value }));
    // Clear field error on type
    if (errors[name]) setErrors(prev => ({ ...prev, [name]: '' }));
    if (apiError) setApiError('');
  };

  /* ── Client-side validation ── */
  const validate = () => {
    const newErrors = {};
    if (!form.name.trim()) newErrors.name = 'Full name is required.';
    else if (form.name.trim().length < 2) newErrors.name = 'Name must be at least 2 characters.';

    if (!form.email.trim()) newErrors.email = 'Email is required.';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) newErrors.email = 'Enter a valid email address.';

    if (!form.password) newErrors.password = 'Password is required.';
    else if (form.password.length < 8) newErrors.password = 'Password must be at least 8 characters.';
    else if (form.password.length > 72) newErrors.password = 'Password must be at most 72 characters.';

    if (!form.confirmPassword) newErrors.confirmPassword = 'Please confirm your password.';
    else if (form.password !== form.confirmPassword) newErrors.confirmPassword = 'Passwords do not match.';

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /* ── Submit → POST /api/v1/register ── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setLoading(true);
    setApiError('');
    try {
      const { token, user } = await register(form.name.trim(), form.email.trim(), form.password);
      setAuth(token, user);       // persist JWT + user in context & localStorage
      navigate('/dashboard');     // redirect to protected dashboard
    } catch (err) {
      // Backend ErrorResponse is { timestamp, status, error }
      const msg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Registration failed. Please try again.';
      setApiError(msg);
    } finally {
      setLoading(false);
    }
  };

  /* ── Password requirements list ── */
  const requirements = [
    { label: 'At least 8 characters', met: form.password.length >= 8 },
    { label: 'One uppercase letter', met: /[A-Z]/.test(form.password) },
    { label: 'One number', met: /[0-9]/.test(form.password) },
    { label: 'One special character', met: /[^A-Za-z0-9]/.test(form.password) },
  ];

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
          {/* Top accent line */}
          <div className="auth-card__accent" />

          <div className="auth-card__header">
            <h1 className="auth-card__title">Create your account</h1>
            <p className="auth-card__subtitle">
              Start shielding your prompts — free, forever.
            </p>
          </div>

          {/* ── API Error Banner ── */}
          {apiError && (
            <div className="auth-error-banner" role="alert">
              <AlertCircle size={16} />
              <span>{apiError}</span>
            </div>
          )}

          <form className="auth-form" onSubmit={handleSubmit} noValidate>

            {/* Full Name */}
            <div className={`auth-field ${errors.name ? 'auth-field--error' : ''}`}>
              <label className="auth-label" htmlFor="name">Full Name</label>
              <div className="auth-input-wrap">
                <User size={16} className="auth-input-icon" />
                <input
                  id="name"
                  name="name"
                  type="text"
                  className="auth-input"
                  placeholder="John Doe"
                  value={form.name}
                  onChange={handleChange}
                  autoComplete="name"
                  disabled={loading}
                />
              </div>
              {errors.name && <span className="auth-field-error"><AlertCircle size={12} />{errors.name}</span>}
            </div>

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
              {errors.email && <span className="auth-field-error"><AlertCircle size={12} />{errors.email}</span>}
            </div>

            {/* Password */}
            <div className={`auth-field ${errors.password ? 'auth-field--error' : ''}`}>
              <label className="auth-label" htmlFor="password">Password</label>
              <div className="auth-input-wrap">
                <Lock size={16} className="auth-input-icon" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Min. 8 characters"
                  value={form.password}
                  onChange={handleChange}
                  autoComplete="new-password"
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
              {errors.password && <span className="auth-field-error"><AlertCircle size={12} />{errors.password}</span>}

              {/* Strength bar */}
              {form.password && (
                <div className="auth-strength">
                  <div className="auth-strength__bars">
                    {[1, 2, 3, 4].map(i => (
                      <div
                        key={i}
                        className="auth-strength__bar"
                        style={{ background: i <= strength.score ? strength.color : 'var(--border-light)' }}
                      />
                    ))}
                  </div>
                  <span className="auth-strength__label" style={{ color: strength.color }}>
                    {strength.label}
                  </span>
                </div>
              )}

              {/* Requirements */}
              {form.password && (
                <ul className="auth-requirements">
                  {requirements.map(req => (
                    <li key={req.label} className={`auth-req-item ${req.met ? 'auth-req-item--met' : ''}`}>
                      <CheckCircle size={11} />
                      {req.label}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Confirm Password */}
            <div className={`auth-field ${errors.confirmPassword ? 'auth-field--error' : ''}`}>
              <label className="auth-label" htmlFor="confirmPassword">Confirm Password</label>
              <div className="auth-input-wrap">
                <Lock size={16} className="auth-input-icon" />
                <input
                  id="confirmPassword"
                  name="confirmPassword"
                  type={showConfirm ? 'text' : 'password'}
                  className="auth-input"
                  placeholder="Re-enter your password"
                  value={form.confirmPassword}
                  onChange={handleChange}
                  autoComplete="new-password"
                  disabled={loading}
                />
                <button
                  type="button"
                  className="auth-eye-btn"
                  onClick={() => setShowConfirm(p => !p)}
                  tabIndex={-1}
                  aria-label={showConfirm ? 'Hide password' : 'Show password'}
                >
                  {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {errors.confirmPassword && (
                <span className="auth-field-error"><AlertCircle size={12} />{errors.confirmPassword}</span>
              )}
              {/* Match indicator */}
              {form.confirmPassword && !errors.confirmPassword && form.password === form.confirmPassword && (
                <span className="auth-field-success"><CheckCircle size={12} />Passwords match</span>
              )}
            </div>

            {/* Submit */}
            <button
              type="submit"
              className={`btn-primary auth-submit ${loading ? 'auth-submit--loading' : ''}`}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="auth-spinner" />
                  Creating your account…
                </>
              ) : (
                <>
                  Create Account
                  <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          {/* Footer */}
          <p className="auth-footer-text">
            Already have an account?{' '}
            <Link to="/login" className="auth-link">Log in</Link>
          </p>
        </div>

        {/* Terms note */}
        <p className="auth-terms">
          By registering, you agree to our{' '}
          <span className="auth-link">Terms of Service</span> and{' '}
          <span className="auth-link">Privacy Policy</span>.
        </p>
      </div>
    </div>
  );
}
