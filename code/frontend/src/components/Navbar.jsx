import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Menu, X, Sun, Moon, Download, ArrowRight } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { usePwa } from '../contexts/PwaContext';
import './Navbar.css';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();
  const { theme, toggleTheme } = useTheme();
  const { isInstallable, installApp } = usePwa();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 15);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => setMenuOpen(false), [pathname]);

  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  const navLinks = [
    { label: 'Capabilities', href: '/#features' },
    { label: 'Pipeline', href: '/#how-it-works' },
    { label: 'Security', href: '/#about' },
  ];

  return (
    <header className={`navbar ${scrolled ? 'navbar--scrolled' : ''}`}>
      <div className="container navbar__inner">
        {/* Logo */}
        <Link to="/" className="navbar__logo">
          <div className="navbar__logo-icon">
            <Shield size={20} />
          </div>
          <span className="navbar__logo-text">
            Prompt<span className="gradient-text">Shield</span> AI
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="navbar__links" aria-label="Main Navigation">
          {navLinks.map(link => (
            <a key={link.label} href={link.href} className="navbar__link">
              {link.label}
            </a>
          ))}
        </nav>

        {/* Right Actions */}
        <div className="navbar__actions">
          {/* PWA Install Button */}
          {isInstallable && (
            <button
              className="navbar__icon-btn"
              onClick={installApp}
              title="Install Web App"
              aria-label="Install PromptShield App"
            >
              <Download size={18} />
            </button>
          )}

          {/* Theme Switcher */}
          <button
            className="navbar__icon-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            aria-label="Toggle visual theme"
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <Link to="/login" className="btn-outline navbar__btn-small">Log In</Link>
          <Link to="/register" className="btn-primary navbar__btn-small">
            <span>Get Started</span>
            <ArrowRight size={14} />
          </Link>
        </div>

        {/* Hamburger */}
        <div className="navbar__mobile-triggers">
          <button
            className="navbar__icon-btn"
            onClick={toggleTheme}
            aria-label="Toggle visual theme"
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>

          <button
            className="navbar__hamburger"
            onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {menuOpen && (
        <div className="navbar__mobile">
          <div className="navbar__mobile-links">
            {navLinks.map(link => (
              <a key={link.label} href={link.href} className="navbar__mobile-link" onClick={() => setMenuOpen(false)}>
                {link.label}
              </a>
            ))}
          </div>

          <div className="navbar__mobile-actions">
            {isInstallable && (
              <button className="btn-secondary" style={{ width: '100%', justifyContent: 'center' }} onClick={installApp}>
                <Download size={16} />
                <span>Install PromptShield App</span>
              </button>
            )}
            <Link to="/login" className="btn-outline" onClick={() => setMenuOpen(false)}>Log In</Link>
            <Link to="/register" className="btn-primary" onClick={() => setMenuOpen(false)}>
              <span>Get Started Free</span>
              <ArrowRight size={15} />
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
