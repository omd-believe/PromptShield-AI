import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Shield, Menu, X } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const { pathname } = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => setMenuOpen(false), [pathname]);

  const navLinks = [
    { label: 'Features', href: '#features' },
    { label: 'How It Works', href: '#how-it-works' },
    { label: 'About', href: '#about' },
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
            Prompt<span className="gradient-text">Shield</span>
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="navbar__links">
          {navLinks.map(link => (
            <a key={link.label} href={link.href} className="navbar__link">
              {link.label}
            </a>
          ))}
        </nav>

        {/* CTA Buttons */}
        <div className="navbar__actions">
          <Link to="/login" className="btn-outline navbar__btn-small">Log In</Link>
          <Link to="/register" className="btn-primary navbar__btn-small">Get Started</Link>
        </div>

        {/* Hamburger */}
        <button
          className="navbar__hamburger"
          onClick={() => setMenuOpen(o => !o)}
          aria-label="Toggle menu"
        >
          {menuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="navbar__mobile">
          {navLinks.map(link => (
            <a key={link.label} href={link.href} className="navbar__mobile-link">
              {link.label}
            </a>
          ))}
          <div className="navbar__mobile-actions">
            <Link to="/login" className="btn-outline">Log In</Link>
            <Link to="/register" className="btn-primary">Get Started</Link>
          </div>
        </div>
      )}
    </header>
  );
}
