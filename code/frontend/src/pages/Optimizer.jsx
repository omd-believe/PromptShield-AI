import { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Zap, Brain, Sparkles, Eye, Copy, CheckCheck,
  ArrowRight, LayoutDashboard, History, LogOut,
  AlertCircle, ChevronDown, ChevronUp, RotateCcw,
  FileText, Target, TrendingDown, Lock
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { optimizePrompt } from '../services/promptService';
import { useNavigate } from 'react-router-dom';
import './Optimizer.css';

/* ─── Pipeline stages (from Activity Diagram) ─── */
const PIPELINE_STAGES = [
  { id: 'preprocess',   label: 'Preprocessing',          icon: FileText,   desc: 'Normalizing text, tokenizing…' },
  { id: 'privacy',      label: 'Privacy Detection',       icon: Eye,        desc: 'Regex + NER scanning for sensitive data…' },
  { id: 'precompress',  label: 'Rule-Based Compression',  icon: TrendingDown, desc: 'Removing greetings and redundancies…' },
  { id: 'mlcompress',   label: 'ML Compression',          icon: Zap,        desc: 'Fine-tuned T5/FLAN-T5 compressing…' },
  { id: 'grammar',      label: 'Grammar Correction',      icon: Sparkles,   desc: 'Polishing for grammatical accuracy…' },
  { id: 'semantic',     label: 'Semantic Evaluation',     icon: Brain,      desc: 'Calculating similarity score…' },
];

const RESULT_TABS = ['Optimized Prompt', 'Privacy Report', 'Statistics'];

const fmt = (n, d = 2) => (n == null ? '—' : Number(n).toFixed(d));

/* ─── Sensitive data type → color map ─── */
const TYPE_COLOR = {
  EMAIL:        '#6c63ff',
  PHONE:        '#00d4aa',
  PAN:          '#f59e0b',
  AADHAAR:      '#ff4d6d',
  API_KEY:      '#ec4899',
  PERSON:       '#3b82f6',
  ORGANIZATION: '#8b5cf6',
  LOCATION:     '#10b981',
};
const typeColor = (t) => TYPE_COLOR[t?.toUpperCase()] ?? '#6c63ff';

export default function Optimizer() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  /* ─── State ─── */
  const [promptText, setPromptText] = useState('');
  const [loading, setLoading] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);   // pipeline step index
  const [completedStages, setCompletedStages] = useState([]);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [expandedFlag, setExpandedFlag] = useState(null);
  const resultRef = useRef(null);

  /* ─── Simulate pipeline progression while waiting for API ─── */
  const runPipelineAnimation = () => {
    const totalStages = PIPELINE_STAGES.length;
    let current = 0;
    // Spread stage animations over ~3s (will be cut short when API responds)
    const interval = setInterval(() => {
      if (current < totalStages) {
        setActiveStage(current);
        setCompletedStages(prev => [...prev, current - 1].filter(i => i >= 0));
        current++;
      } else {
        clearInterval(interval);
      }
    }, 520);
    return interval;
  };

  /* ─── Submit handler → POST /api/prompt/optimize ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!promptText.trim()) return;

    setLoading(true);
    setResult(null);
    setError('');
    setActiveStage(0);
    setCompletedStages([]);

    const animInterval = runPipelineAnimation();

    try {
      const data = await optimizePrompt(promptText.trim());
      clearInterval(animInterval);
      // Mark all stages complete
      setCompletedStages(PIPELINE_STAGES.map((_, i) => i));
      setActiveStage(-1);
      setResult(data);
      setActiveTab(0);
      // Scroll to results
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      clearInterval(animInterval);
      setActiveStage(-1);
      setCompletedStages([]);
      setError(
        err.response?.data?.message ||
        'Could not connect to the AI service. Make sure the Spring Boot + FastAPI backends are running.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPromptText('');
    setResult(null);
    setError('');
    setActiveStage(-1);
    setCompletedStages([]);
  };

  const handleCopy = () => {
    // Backend field: optimizedPrompt
    if (!result?.optimizedPrompt) return;
    navigator.clipboard.writeText(result.optimizedPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="optimizer-page">

      {/* ══════════════════════════════
          SIDEBAR (shared layout)
      ══════════════════════════════ */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar__top">
          <Link to="/" className="dash-sidebar__brand">
            <div className="dash-sidebar__brand-icon"><Shield size={18} /></div>
            <span>Prompt<span className="gradient-text">Shield</span></span>
          </Link>
          <nav className="dash-nav">
            <Link to="/dashboard" className="dash-nav__item">
              <LayoutDashboard size={18} /><span>Dashboard</span>
            </Link>
            <Link to="/optimize" className="dash-nav__item dash-nav__item--active">
              <Zap size={18} /><span>Optimizer</span>
            </Link>
            <Link to="/history" className="dash-nav__item">
              <History size={18} /><span>History</span>
            </Link>
          </nav>
        </div>
        <div className="dash-sidebar__bottom">
          <div className="dash-user">
            <div className="dash-user__avatar">{user?.name?.[0]?.toUpperCase() || 'U'}</div>
            <div className="dash-user__info">
              <p className="dash-user__name">{user?.name || 'User'}</p>
              <p className="dash-user__email">{user?.email || ''}</p>
            </div>
          </div>
          <button className="dash-logout-btn" onClick={handleLogout}>
            <LogOut size={16} /><span>Logout</span>
          </button>
        </div>
      </aside>

      {/* ══════════════════════════════
          MAIN
      ══════════════════════════════ */}
      <main className="optimizer-main">
        {/* Header */}
        <header className="optimizer-header">
          <div>
            <h1 className="optimizer-header__title">
              Prompt <span className="gradient-text">Optimizer</span>
            </h1>
            <p className="optimizer-header__sub">
              Paste any prompt — the AI pipeline will shield, compress, and perfect it.
            </p>
          </div>
        </header>

        {/* ══════════════════════════════
            INPUT PANEL
        ══════════════════════════════ */}
        <div className="opt-input-panel">
          <form onSubmit={handleSubmit}>
            <div className="opt-input-wrap">
              <div className="opt-input-header">
                <span className="opt-input-label">
                  <span className="dot dot--red" /> Original Prompt
                </span>
                {promptText && (
                  <div className="opt-input-meta">
                    <span className="opt-char-count">
                      ~{promptText.trim().split(/\s+/).filter(Boolean).length} words
                      &nbsp;·&nbsp; {promptText.length} chars
                    </span>
                    <button
                      type="button"
                      className="opt-clear-btn"
                      onClick={handleReset}
                      title="Clear"
                    >
                      <RotateCcw size={13} /> Clear
                    </button>
                  </div>
                )}
              </div>

              <textarea
                className="opt-textarea"
                placeholder={`Paste your prompt here…\n\nExample:\n"Hey ChatGPT, hope you're doing well! My email is john@gmail.com and my Aadhaar is 1234 5678 9012. Can you please help me write a professional leave request letter to my manager?"`}
                value={promptText}
                onChange={(e) => {
                  setPromptText(e.target.value);
                  if (error) setError('');
                }}
                rows={9}
                disabled={loading}
              />

              <div className="opt-input-footer">
                <div className="opt-hints">
                  <span className="opt-hint"><Eye size={11} /> Detects: Email, Phone, PAN, Aadhaar, API Keys, Names</span>
                  <span className="opt-hint"><Zap size={11} /> Model: T5 / FLAN-T5</span>
                </div>
                <button
                  type="submit"
                  className={`btn-primary opt-submit-btn ${loading ? 'opt-submit-btn--loading' : ''}`}
                  disabled={loading || !promptText.trim()}
                >
                  {loading ? (
                    <><span className="auth-spinner" /> Processing…</>
                  ) : (
                    <><Shield size={16} /> Analyze &amp; Optimize</>
                  )}
                </button>
              </div>
            </div>
          </form>

          {/* Error */}
          {error && (
            <div className="opt-error">
              <AlertCircle size={15} />
              {error}
            </div>
          )}
        </div>

        {/* ══════════════════════════════
            PIPELINE PROGRESS
        ══════════════════════════════ */}
        {(loading || completedStages.length > 0) && (
          <div className="pipeline-tracker">
            <p className="pipeline-tracker__title">
              {loading ? 'Running AI Pipeline…' : '✅ Pipeline Complete'}
            </p>
            <div className="pipeline-steps">
              {PIPELINE_STAGES.map((stage, i) => {
                const Icon = stage.icon;
                const isDone = completedStages.includes(i);
                const isActive = activeStage === i;
                return (
                  <div
                    key={stage.id}
                    className={`pipeline-step
                      ${isDone ? 'pipeline-step--done' : ''}
                      ${isActive ? 'pipeline-step--active' : ''}
                    `}
                  >
                    <div className="pipeline-step__icon">
                      <Icon size={14} />
                    </div>
                    <span className="pipeline-step__label">{stage.label}</span>
                    {i < PIPELINE_STAGES.length - 1 && (
                      <div className={`pipeline-step__line ${isDone ? 'pipeline-step__line--done' : ''}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* ══════════════════════════════
            RESULTS PANEL
        ══════════════════════════════ */}
        {result && (
          <div className="opt-results" ref={resultRef}>

            {/* ── Quick Metrics Bar — computed from backend fields ── */}
            {(() => {
              const origWords = result.originalPrompt?.trim().split(/\s+/).length ?? 0;
              const optWords  = result.optimizedPrompt?.trim().split(/\s+/).length ?? 0;
              const origTok   = Math.ceil(origWords * 1.33);
              const optTok    = Math.ceil(optWords  * 1.33);
              const pct       = origTok > 0 ? ((origTok - optTok) / origTok * 100) : 0;
              return (
                <div className="opt-metrics">
                  <div className="opt-metric">
                    <span className="opt-metric__val gradient-text">
                      {pct > 0 ? fmt(pct, 1) + '%' : '—'}
                    </span>
                    <span className="opt-metric__label">Tokens Saved</span>
                  </div>
                  <div className="opt-metric-divider" />
                  <div className="opt-metric">
                    <span className="opt-metric__val" style={{ color: '#00d4aa' }}>N/A</span>
                    <span className="opt-metric__label">Similarity Score</span>
                  </div>
                  <div className="opt-metric-divider" />
                  <div className="opt-metric">
                    <span className="opt-metric__val" style={{ color: '#ff4d6d' }}>N/A</span>
                    <span className="opt-metric__label">Privacy Flags</span>
                  </div>
                  <div className="opt-metric-divider" />
                  <div className="opt-metric">
                    <span className="opt-metric__val" style={{ color: '#f59e0b' }}>
                      {origTok} → {optTok}
                    </span>
                    <span className="opt-metric__label">Token Count (est.)</span>
                  </div>
                </div>
              );
            })()}

            {/* ── Tabs ── */}
            <div className="opt-tabs">
              {RESULT_TABS.map((tab, i) => (
                <button
                  key={tab}
                  className={`opt-tab ${activeTab === i ? 'opt-tab--active' : ''}`}
                  onClick={() => setActiveTab(i)}
                >
                  {tab}
                  {i === 1 && result.privacyReport?.length > 0 && (
                    <span className="opt-tab__badge">{result.privacyReport.length}</span>
                  )}
                </button>
              ))}
            </div>

            {/* ── Tab: Optimized Prompt ── */}
            {activeTab === 0 && (
              <div className="opt-tab-content">
                {/* Side by side comparison — backend fields: originalPrompt / optimizedPrompt */}
                {(() => {
                  const origTok = Math.ceil((result.originalPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
                  const optTok  = Math.ceil((result.optimizedPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
                  const pct     = origTok > 0 ? Math.round((origTok - optTok) / origTok * 100) : 0;
                  return (
                    <div className="opt-compare">
                      <div className="opt-compare__pane opt-compare__pane--original">
                        <div className="opt-compare__pane-header">
                          <span><span className="dot dot--red" /> Original</span>
                          <span className="opt-compare__token-count">~{origTok} tokens</span>
                        </div>
                        <p className="opt-compare__text">{result.originalPrompt}</p>
                      </div>

                      <div className="opt-compare__arrow">
                        <ArrowRight size={20} className="opt-compare__arrow-icon" />
                        {pct > 0 && <span className="opt-compare__reduction">-{pct}%</span>}
                      </div>

                      <div className="opt-compare__pane opt-compare__pane--optimized">
                        <div className="opt-compare__pane-header">
                          <span><span className="dot dot--green" /> Optimized</span>
                          <span className="opt-compare__token-count">~{optTok} tokens</span>
                        </div>
                        <p className="opt-compare__text">{result.optimizedPrompt}</p>
                      </div>
                    </div>
                  );
                })()}

                <button className="opt-copy-btn" onClick={handleCopy}>
                  {copied ? <><CheckCheck size={16} /> Copied!</> : <><Copy size={16} /> Copy Optimized Prompt</>}
                </button>
              </div>
            )}

            {/* ── Tab: Privacy Report ── */}
            {activeTab === 1 && (
              <div className="opt-tab-content">
                {!result.privacyReport || result.privacyReport.length === 0 ? (
                  <div className="opt-privacy-empty">
                    <Shield size={36} className="opt-privacy-empty__icon" />
                    <p>No sensitive data detected in this prompt.</p>
                  </div>
                ) : (
                  <div className="opt-privacy-list">
                    <p className="opt-privacy-intro">
                      <Lock size={13} />
                      The following sensitive items were detected and masked before compression.
                    </p>
                    {result.privacyReport.map((item, i) => {
                      const color = typeColor(item.type);
                      const isOpen = expandedFlag === i;
                      return (
                        <div key={i} className="privacy-row">
                          <div
                            className="privacy-row__header"
                            onClick={() => setExpandedFlag(isOpen ? null : i)}
                          >
                            <div className="privacy-row__left">
                              <span
                                className="privacy-row__type"
                                style={{ background: `${color}18`, color, border: `1px solid ${color}30` }}
                              >
                                {item.type}
                              </span>
                              <span className="privacy-row__masked">{item.masked}</span>
                            </div>
                            <button className="privacy-row__expand">
                              {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                            </button>
                          </div>
                          {isOpen && (
                            <div className="privacy-row__detail">
                              <div className="privacy-row__detail-row">
                                <span className="privacy-row__detail-label">Original Value</span>
                                <span className="privacy-row__detail-val privacy-row__detail-val--danger">
                                  {item.value}
                                </span>
                              </div>
                              <div className="privacy-row__detail-row">
                                <span className="privacy-row__detail-label">Replaced With</span>
                                <span className="privacy-row__detail-val">{item.masked}</span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* ── Tab: Statistics — computed from available backend fields ── */}
            {activeTab === 2 && (() => {
              const origTok = Math.ceil((result.originalPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
              const optTok  = Math.ceil((result.optimizedPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
              const saved   = origTok - optTok;
              const pct     = origTok > 0 ? (saved / origTok * 100) : 0;
              return (
                <div className="opt-tab-content">
                  <div className="opt-stats-grid">
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Original Token Count (est.)</div>
                      <div className="opt-stat-card__val">{origTok}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Optimized Token Count (est.)</div>
                      <div className="opt-stat-card__val" style={{ color: '#00d4aa' }}>{optTok}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Tokens Saved (est.)</div>
                      <div className="opt-stat-card__val" style={{ color: '#6c63ff' }}>{Math.max(0, saved)}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Token Reduction % (est.)</div>
                      <div className="opt-stat-card__val gradient-text">{pct > 0 ? fmt(pct, 1) + '%' : '—'}</div>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Target size={13} /> Semantic Similarity Score
                      </div>
                      <div className="opt-stat-card__val" style={{ color: '#00d4aa' }}>
                        N/A
                        <span className="opt-stat-card__sub"> — requires AI service</span>
                      </div>
                      <p className="opt-stat-card__desc">
                        Semantic similarity scoring will be available once the AI pipeline service is connected.
                      </p>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Shield size={13} /> Privacy Report Summary
                      </div>
                      <div className="opt-stat-card__val" style={{ color: '#ff4d6d' }}>
                        N/A
                        <span className="opt-stat-card__sub"> — requires AI service</span>
                      </div>
                      <p className="opt-stat-card__desc">
                        Privacy detection (PII masking) will be available once the AI pipeline service is connected.
                      </p>
                    </div>
                  </div>
                </div>
              );
            })()}

          </div>
        )}
      </main>
    </div>
  );
}
