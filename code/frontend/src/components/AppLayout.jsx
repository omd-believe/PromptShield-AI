import { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Shield, LayoutDashboard, Zap, History, LogOut,
  Sun, Moon, Download, Menu, X, WifiOff, RefreshCw
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { usePwa } from '../contexts/PwaContext';
import './AppLayout.css';

export default function AppLayout({ children, activeRoute }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const { isOnline, isInstallable, installApp, updateAvailable, applyUpdate } = usePwa();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  // Close mobile drawer on route transition
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const currentRoute = activeRoute || (
    location.pathname.includes('optimize') ? 'optimize' :
    location.pathname.includes('history') ? 'history' : 'dashboard'
  );

  return (
    <div className="app-layout">
      {/* ── Offline Banner ── */}
      {!isOnline && (
        <div className="global-offline-banner" role="status">
          <WifiOff size={15} />
          <span>You are currently offline. Prompt optimization requires connectivity to contact the AI engine.</span>
        </div>
      )}

      {/* ── PWA Update Available Toast ── */}
      {updateAvailable && (
        <div className="global-update-banner" role="alert">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <RefreshCw size={15} className="spin-icon" style={{ color: 'var(--accent)' }} />
            <span>A new version of PromptShield is ready.</span>
          </div>
          <button className="btn-primary" style={{ padding: '5px 12px', fontSize: '0.8rem' }} onClick={applyUpdate}>
            Update Now
          </button>
        </div>
      )}

      {/* ══════════════════════════════
          DESKTOP SIDEBAR
      ══════════════════════════════ */}
      <aside className="app-sidebar" aria-label="Sidebar Navigation">
        <div className="app-sidebar__top">
          {/* Logo & Brand */}
          <Link to="/" className="app-sidebar__brand">
            <div className="app-sidebar__brand-icon">
              <Shield size={18} />
            </div>
            <span>
              Prompt<span className="gradient-text">Shield</span>
            </span>
          </Link>

          {/* Navigation Links */}
          <nav className="app-nav">
            <Link
              to="/dashboard"
              className={`app-nav__link ${currentRoute === 'dashboard' ? 'app-nav__link--active' : ''}`}
            >
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </Link>

            <Link
              to="/optimize"
              className={`app-nav__link ${currentRoute === 'optimize' ? 'app-nav__link--active' : ''}`}
            >
              <Zap size={18} />
              <span>Optimizer</span>
              <span className="app-nav__badge">AI Core</span>
            </Link>

            <Link
              to="/history"
              className={`app-nav__link ${currentRoute === 'history' ? 'app-nav__link--active' : ''}`}
            >
              <History size={18} />
              <span>History</span>
            </Link>
          </nav>
        </div>

        {/* Bottom Actions: Install PWA, Theme Switch, Profile, Logout */}
        <div className="app-sidebar__bottom">
          {/* PWA Install Button */}
          {isInstallable && (
            <button
              className="app-sidebar__tool-btn app-sidebar__pwa-btn"
              onClick={installApp}
              title="Install Desktop App"
            >
              <Download size={15} />
              <span>Install App</span>
            </button>
          )}

          {/* Theme Toggle Button */}
          <button
            className="app-sidebar__tool-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
            <span>{theme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
          </button>

          {/* User Profile Card */}
          <div className="app-user-card">
            <div className="app-user-card__avatar">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="app-user-card__details">
              <div className="app-user-card__name">{user?.name || 'User'}</div>
              <div className="app-user-card__email">{user?.email || ''}</div>
            </div>
          </div>

          {/* Logout */}
          <button className="app-logout-btn" onClick={handleLogout}>
            <LogOut size={15} />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      {/* ══════════════════════════════
          MOBILE HEADER (< 768px)
      ══════════════════════════════ */}
      <header className="app-mobile-header">
        <div className="app-mobile-header__left">
          <button
            className="app-mobile-header__btn"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open Navigation Drawer"
          >
            <Menu size={20} />
          </button>
          <Link to="/dashboard" className="app-mobile-header__brand">
            <Shield size={18} style={{ color: 'var(--accent)' }} />
            <span>Prompt<span className="gradient-text">Shield</span></span>
          </Link>
        </div>

        <div className="app-mobile-header__right">
          {isInstallable && (
            <button
              className="app-mobile-header__btn"
              onClick={installApp}
              aria-label="Install App"
              title="Install App"
            >
              <Download size={17} style={{ color: 'var(--accent)' }} />
            </button>
          )}

          <button
            className="app-mobile-header__btn"
            onClick={toggleTheme}
            aria-label="Toggle Theme"
          >
            {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
          </button>

          <div className="app-mobile-header__avatar" onClick={() => setDrawerOpen(true)}>
            {user?.name?.[0]?.toUpperCase() || 'U'}
          </div>
        </div>
      </header>

      {/* ══════════════════════════════
          MOBILE DRAWER SHEET
      ══════════════════════════════ */}
      {drawerOpen && (
        <div className="app-drawer-backdrop" onClick={() => setDrawerOpen(false)}>
          <div className="app-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="app-drawer__top">
              <div className="app-drawer__header">
                <div className="app-sidebar__brand" style={{ padding: 0, border: 'none', margin: 0 }}>
                  <div className="app-sidebar__brand-icon">
                    <Shield size={16} />
                  </div>
                  <span>Prompt<span className="gradient-text">Shield</span></span>
                </div>
                <button
                  className="app-drawer__close"
                  onClick={() => setDrawerOpen(false)}
                  aria-label="Close menu"
                >
                  <X size={20} />
                </button>
              </div>

              <div className="app-user-card" style={{ marginTop: 8 }}>
                <div className="app-user-card__avatar">
                  {user?.name?.[0]?.toUpperCase() || 'U'}
                </div>
                <div className="app-user-card__details">
                  <div className="app-user-card__name">{user?.name || 'User'}</div>
                  <div className="app-user-card__email">{user?.email || ''}</div>
                </div>
              </div>

              <nav className="app-drawer__nav">
                <Link
                  to="/dashboard"
                  className={`app-nav__link ${currentRoute === 'dashboard' ? 'app-nav__link--active' : ''}`}
                >
                  <LayoutDashboard size={18} />
                  <span>Dashboard</span>
                </Link>

                <Link
                  to="/optimize"
                  className={`app-nav__link ${currentRoute === 'optimize' ? 'app-nav__link--active' : ''}`}
                >
                  <Zap size={18} />
                  <span>Prompt Optimizer</span>
                </Link>

                <Link
                  to="/history"
                  className={`app-nav__link ${currentRoute === 'history' ? 'app-nav__link--active' : ''}`}
                >
                  <History size={18} />
                  <span>History</span>
                </Link>
              </nav>
            </div>

            <div className="app-sidebar__bottom">
              {isInstallable && (
                <button className="app-sidebar__tool-btn app-sidebar__pwa-btn" onClick={installApp}>
                  <Download size={15} />
                  <span>Install Web App</span>
                </button>
              )}

              <button className="app-sidebar__tool-btn" onClick={toggleTheme}>
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
              </button>

              <button className="app-logout-btn" onClick={handleLogout}>
                <LogOut size={15} />
                <span>Log Out</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ══════════════════════════════
          MOBILE BOTTOM NAV BAR (< 768px)
      ══════════════════════════════ */}
      <nav className="app-mobile-bottom-nav" aria-label="Mobile Bottom Navigation">
        <div className="app-mobile-bottom-nav__inner">
          <Link
            to="/dashboard"
            className={`app-mobile-bottom-nav__item ${currentRoute === 'dashboard' ? 'app-mobile-bottom-nav__item--active' : ''}`}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </Link>

          <Link
            to="/optimize"
            className={`app-mobile-bottom-nav__item ${currentRoute === 'optimize' ? 'app-mobile-bottom-nav__item--active' : ''}`}
          >
            <Zap size={20} />
            <span>Optimizer</span>
          </Link>

          <Link
            to="/history"
            className={`app-mobile-bottom-nav__item ${currentRoute === 'history' ? 'app-mobile-bottom-nav__item--active' : ''}`}
          >
            <History size={20} />
            <span>History</span>
          </Link>
        </div>
      </nav>

      {/* ══════════════════════════════
          MAIN CONTENT AREA
      ══════════════════════════════ */}
      <div className="app-content">
        <main className="app-content__inner">
          {children}
        </main>
      </div>
    </div>
  );
}

