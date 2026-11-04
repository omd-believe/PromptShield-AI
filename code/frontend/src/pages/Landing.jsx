import { Link } from 'react-router-dom';
import {
  Shield, Zap, Eye, Brain, ArrowRight, CheckCircle,
  Lock, Cpu, Sparkles, ChevronRight, Star
} from 'lucide-react';
import './Landing.css';

/* ── Data ── */
const features = [
  {
    icon: Eye,
    color: '#ff4d6d',
    title: 'Privacy Detection',
    description:
      'Automatically detects and masks sensitive data — emails, phone numbers, PAN, Aadhaar, API keys — using Regex + Named Entity Recognition.',
  },
  {
    icon: Zap,
    color: '#6c63ff',
    title: 'Prompt Optimization',
    description:
      'Deterministic rule-based optimizer removes politeness filler, redundancies, and connective phrasing while preserving constraints and meaning.',
  },
  {
    icon: Sparkles,
    color: '#00d4aa',
    title: 'Grammar Correction',
    description:
      'Automatically polishes your prompt for grammatical accuracy so your AI gets the clearest possible instruction.',
  },
  {
    icon: Brain,
    color: '#f59e0b',
    title: 'Semantic Evaluation',
    description:
      'Calculates a similarity score between original and optimized prompts to guarantee semantic fidelity after all transformations.',
  },
];

const steps = [
  { number: '01', title: 'Paste Your Prompt', desc: 'Drop any prompt into the editor — no matter how long or messy.' },
  { number: '02', title: 'AI Pipeline Runs', desc: 'Privacy detection → prompt optimization → grammar cleanup → quality & semantic validation.' },
  { number: '03', title: 'Get Your Results', desc: 'Receive the optimized prompt, privacy report, similarity score, and token savings.' },
];

const stats = [
  { value: '40%', label: 'Avg Token Reduction' },
  { value: '99%', label: 'Semantic Accuracy' },
  { value: '6+', label: 'Sensitive Data Types Detected' },
  { value: '<2s', label: 'Processing Time' },
];

const privacyTags = [
  'Email Addresses', 'Phone Numbers', 'PAN Cards', 'Aadhaar Numbers',
  'API Keys', 'Person Names', 'Organization Names', 'Locations',
];

export default function Landing() {
  return (
    <main className="landing">
      {/* ── Floating Orbs ── */}
      <div className="landing__orb landing__orb--1" aria-hidden="true" />
      <div className="landing__orb landing__orb--2" aria-hidden="true" />
      <div className="landing__orb landing__orb--3" aria-hidden="true" />

      {/* ══════════════════════════════
          HERO
      ══════════════════════════════ */}
      <section className="hero" id="hero">
        <div className="container hero__inner">
          {/* Badge */}
          <div className="hero__badge fade-up">
            <Shield size={14} />
            <span>AI-Powered Prompt Security &amp; Optimization</span>
          </div>

          {/* Headline */}
          <h1 className="hero__title fade-up">
            Protect Your Prompts.
            <br />
            <span className="gradient-text">Optimize Every Word.</span>
          </h1>

          <p className="hero__subtitle fade-up">
            PromptShield AI automatically detects sensitive data, compresses your prompts,
            corrects grammar, and evaluates semantic accuracy — giving you a clean,
            private, and token-efficient prompt in seconds.
          </p>

          {/* CTAs */}
          <div className="hero__ctas fade-up">
            <Link to="/register" className="btn-primary hero__cta-main">
              Start Shielding Free
              <ArrowRight size={18} />
            </Link>
            <a href="#how-it-works" className="btn-outline">
              See How It Works
            </a>
          </div>

          {/* Trust Row */}
          <div className="hero__trust fade-up">
            {['No credit card required', 'Processing 100% private', 'Open-source AI models'].map(t => (
              <span key={t} className="hero__trust-item">
                <CheckCircle size={14} className="hero__trust-icon" />
                {t}
              </span>
            ))}
          </div>

          {/* ── Demo Card ── */}
          <div className="demo-card fade-up">
            <div className="demo-card__header">
              <div className="demo-card__dots">
                <span /><span /><span />
              </div>
              <span className="demo-card__title">Live Preview</span>
            </div>

            <div className="demo-card__body">
              {/* Original */}
              <div className="demo-card__prompt demo-card__prompt--original">
                <div className="demo-card__prompt-label">
                  <span className="demo-card__label-dot demo-card__label-dot--red" />
                  Original Prompt
                </div>
                <p className="demo-card__prompt-text">
                  Hey ChatGPT, hope you&apos;re doing great! I wanted to ask, my email is{' '}
                  <mark className="demo-highlight--danger">john.doe@gmail.com</mark> and my Aadhaar is{' '}
                  <mark className="demo-highlight--danger">1234 5678 9012</mark>. Can you please help me
                  write a professional letter to my boss for requesting leave?
                </p>
                <div className="demo-card__meta">
                  <span className="demo-tag demo-tag--red">
                    <Lock size={11} /> 2 sensitive items detected
                  </span>
                  <span className="demo-tag demo-tag--muted">87 tokens</span>
                </div>
              </div>

              {/* Arrow */}
              <div className="demo-card__arrow">
                <div className="demo-card__pipeline">
                  <span>Privacy Detection</span>
                  <ChevronRight size={12} />
                  <span>Compression</span>
                  <ChevronRight size={12} />
                  <span>Grammar Fix</span>
                </div>
                <div className="demo-card__arrow-line">
                  <div className="demo-card__arrow-dot" />
                </div>
              </div>

              {/* Optimized */}
              <div className="demo-card__prompt demo-card__prompt--optimized">
                <div className="demo-card__prompt-label">
                  <span className="demo-card__label-dot demo-card__label-dot--green" />
                  Optimized Prompt
                </div>
                <p className="demo-card__prompt-text">
                  Write a professional leave request letter to my manager.
                </p>
                <div className="demo-card__meta">
                  <span className="demo-tag demo-tag--green">
                    <Shield size={11} /> Privacy Protected
                  </span>
                  <span className="demo-tag demo-tag--accent">↓ 69% tokens saved</span>
                </div>
              </div>
            </div>

            {/* Stats row */}
            <div className="demo-card__footer">
              <div className="demo-footer-stat">
                <span className="demo-footer-stat__val gradient-text">0.94</span>
                <span className="demo-footer-stat__label">Similarity Score</span>
              </div>
              <div className="demo-footer-stat">
                <span className="demo-footer-stat__val" style={{ color: '#ff4d6d' }}>2</span>
                <span className="demo-footer-stat__label">Sensitive Items Masked</span>
              </div>
              <div className="demo-footer-stat">
                <span className="demo-footer-stat__val" style={{ color: '#00d4aa' }}>60</span>
                <span className="demo-footer-stat__label">Tokens Saved</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════
          STATS BAND
      ══════════════════════════════ */}
      <section className="stats-band">
        <div className="container stats-band__inner">
          {stats.map(s => (
            <div key={s.label} className="stats-band__item">
              <span className="stats-band__value gradient-text">{s.value}</span>
              <span className="stats-band__label">{s.label}</span>
            </div>
          ))}
        </div>
      </section>

      {/* ══════════════════════════════
          FEATURES
      ══════════════════════════════ */}
      <section className="features" id="features">
        <div className="container">
          <div className="section-header">
            <div className="section-badge">
              <Cpu size={13} />
              Core Capabilities
            </div>
            <h2 className="section-title">
              Everything Your Prompts Need to Stay <span className="gradient-text">Safe &amp; Sharp</span>
            </h2>
            <p className="section-subtitle">
              A full AI pipeline working in concert — each stage building on the last to produce
              a perfect prompt.
            </p>
          </div>

          <div className="features__grid">
            {features.map((f, i) => {
              const Icon = f.icon;
              return (
                <div key={i} className="feature-card card">
                  <div
                    className="feature-card__icon"
                    style={{ background: `${f.color}18`, border: `1px solid ${f.color}30` }}
                  >
                    <Icon size={24} style={{ color: f.color }} />
                  </div>
                  <h3 className="feature-card__title">{f.title}</h3>
                  <p className="feature-card__desc">{f.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════
          PRIVACY TAGS
      ══════════════════════════════ */}
      <section className="privacy-section">
        <div className="container privacy-section__inner">
          <div className="privacy-section__left">
            <div className="section-badge">
              <Lock size={13} />
              Privacy Shield
            </div>
            <h2 className="section-title" style={{ textAlign: 'left' }}>
              Detects <span className="gradient-text">8+ Types</span> of Sensitive Data
            </h2>
            <p className="section-subtitle" style={{ textAlign: 'left' }}>
              Using a combination of Regex patterns and Named Entity Recognition (NER),
              PromptShield catches sensitive information before it ever leaves your device.
            </p>
            <Link to="/register" className="btn-primary privacy-section__cta">
              Try It Free <ArrowRight size={16} />
            </Link>
          </div>

          <div className="privacy-section__tags">
            {privacyTags.map(tag => (
              <div key={tag} className="privacy-tag">
                <Shield size={14} className="privacy-tag__icon" />
                {tag}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════
          HOW IT WORKS
      ══════════════════════════════ */}
      <section className="how-it-works" id="how-it-works">
        <div className="container">
          <div className="section-header">
            <div className="section-badge">
              <Zap size={13} />
              Simple Process
            </div>
            <h2 className="section-title">
              From Raw Prompt to <span className="gradient-text">Perfect Output</span> in 3 Steps
            </h2>
          </div>

          <div className="steps">
            {steps.map((step, i) => (
              <div key={i} className="step">
                <div className="step__number">{step.number}</div>
                <div className="step__connector" aria-hidden="true" />
                <div className="step__content card">
                  <h3 className="step__title">{step.title}</h3>
                  <p className="step__desc">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════
          CTA BANNER
      ══════════════════════════════ */}
      <section className="cta-banner" id="about">
        <div className="container cta-banner__inner">
          <div className="cta-banner__glow" aria-hidden="true" />
          <div className="section-badge" style={{ margin: '0 auto 20px' }}>
            <Star size={13} />
            Start Today
          </div>
          <h2 className="cta-banner__title">
            Ready to Shield Your Prompts?
          </h2>
          <p className="cta-banner__subtitle">
            Join developers and researchers who use PromptShield AI to keep their prompts
            private, concise, and powerful.
          </p>
          <div className="cta-banner__actions">
            <Link to="/register" className="btn-primary">
              Create Free Account <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn-outline">
              Log In
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="footer">
        <div className="container footer__inner">
          <div className="footer__brand">
            <div className="navbar__logo-icon" style={{ width: 30, height: 30 }}>
              <Shield size={16} />
            </div>
            <span className="footer__brand-name">
              Prompt<span className="gradient-text">Shield</span> AI
            </span>
          </div>
          <p className="footer__copy">
            © 2026 PromptShield AI. Built as a mini-project by Team PromptShield.
          </p>
        </div>
      </footer>
    </main>
  );
}
