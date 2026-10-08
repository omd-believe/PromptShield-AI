import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, Zap, Shield, Clock, TrendingUp,
  ChevronRight, Copy, CheckCheck, ArrowRight, LogOut,
  History, AlertCircle, Activity, Target, Loader2
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getDashboardStats, getHistory, optimizePrompt } from '../services/promptService';
import './Dashboard.css';

/* ─── Helpers ─── */
const fmt = (n, decimals = 1) =>
  n == null ? '—' : Number(n).toFixed(decimals);

const timeAgo = (isoString) => {
  if (!isoString) return '';
  const diff = (Date.now() - new Date(isoString)) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

/* Mock data shown while backend is not connected */
const MOCK_STATS = {
  totalPrompts: 0,
  avgTokenReduction: 0,
  totalPrivacyFlags: 0,
  avgSimilarityScore: 0,
};
const MOCK_HISTORY = { content: [], totalElements: 0 };

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  /* ─── State ─── */
  const [stats, setStats] = useState(null);
  const [history, setHistory] = useState([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [quickPrompt, setQuickPrompt] = useState('');
  const [optimizing, setOptimizing] = useState(false);
  const [quickResult, setQuickResult] = useState(null);
  const [quickError, setQuickError] = useState('');
  const [copied, setCopied] = useState(false);

  /* ─── Load Stats ─── */
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await getDashboardStats();
      setStats(data);
    } catch {
      setStats(MOCK_STATS); // fallback when backend not connected
    } finally {
      setStatsLoading(false);
    }
  }, []);

  /* ─── Load Recent History ─── */
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await getHistory(0, 5);
      setHistory(data.content || []);
    } catch {
      setHistory(MOCK_HISTORY.content);
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
    loadHistory();
  }, [loadStats, loadHistory]);

  /* ─── Quick Optimize ─── */
  const handleQuickOptimize = async (e) => {
    e.preventDefault();
    if (!quickPrompt.trim()) return;
    setOptimizing(true);
    setQuickResult(null);
    setQuickError('');
    try {
      const result = await optimizePrompt(quickPrompt.trim());
      setQuickResult(result);
      // Refresh stats + history after successful optimization
      loadStats();
      loadHistory();
    } catch (err) {
      setQuickError(
        err.response?.data?.message ||
        'Could not connect to the AI service. Make sure the backend is running.'
      );
    } finally {
      setOptimizing(false);
    }
  };

  /* ─── Copy optimized text ─── */
  const handleCopy = () => {
    // Backend field: optimizedPrompt
    if (!quickResult?.optimizedPrompt) return;
    navigator.clipboard.writeText(quickResult.optimizedPrompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  /* ─── Logout ─── */
  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  /* ─── Stat Cards config ─── */
  const statCards = [
    {
      id: 'total',
      icon: Activity,
      label: 'Total Prompts Analyzed',
      value: statsLoading ? null : (stats?.totalPrompts ?? 0),
      unit: '',
      color: '#6c63ff',
      desc: 'Since you joined',
    },
    {
      id: 'reduction',
      icon: TrendingUp,
      label: 'Avg Token Reduction',
      value: statsLoading ? null : fmt(stats?.avgTokenReduction, 1),
      unit: '%',
      color: '#00d4aa',
      desc: 'Tokens saved per prompt',
    },
    {
      id: 'flags',
      icon: Shield,
      label: 'Privacy Flags Detected',
      value: statsLoading ? null : (stats?.totalPrivacyFlags ?? 0),
      unit: '',
      color: '#ff4d6d',
      desc: 'Sensitive items masked',
    },
    {
      id: 'similarity',
      icon: Target,
      label: 'Avg Similarity Score',
      value: statsLoading ? null : fmt(stats?.avgSimilarityScore, 2),
      unit: '',
      color: '#f59e0b',
      desc: 'Semantic fidelity (0–1)',
    },
  ];

  return (
    <div className="dashboard">
      {/* ══════════════════════════════
          SIDEBAR
      ══════════════════════════════ */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar__top">
          {/* Logo */}
          <Link to="/" className="dash-sidebar__brand">
            <div className="dash-sidebar__brand-icon">
              <Shield size={18} />
            </div>
            <span>Prompt<span className="gradient-text">Shield</span></span>
          </Link>

          {/* Nav */}
          <nav className="dash-nav">
            <Link to="/dashboard" className="dash-nav__item dash-nav__item--active">
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </Link>
            <Link to="/optimize" className="dash-nav__item">
              <Zap size={18} />
              <span>Optimizer</span>
            </Link>
            <Link to="/history" className="dash-nav__item">
              <History size={18} />
              <span>History</span>
            </Link>
          </nav>
        </div>

        {/* User + Logout */}
        <div className="dash-sidebar__bottom">
          <div className="dash-user">
            <div className="dash-user__avatar">
              {user?.name?.[0]?.toUpperCase() || 'U'}
            </div>
            <div className="dash-user__info">
              <p className="dash-user__name">{user?.name || 'User'}</p>
              <p className="dash-user__email">{user?.email || ''}</p>
            </div>
          </div>
          <button className="dash-logout-btn" onClick={handleLogout}>
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* ══════════════════════════════
          MAIN CONTENT
      ══════════════════════════════ */}
      <main className="dash-main">
        {/* ── Header ── */}
        <header className="dash-header">
          <div>
            <h1 className="dash-header__title">
              Good {getGreeting()},{' '}
              <span className="gradient-text">{user?.name?.split(' ')[0] || 'there'}</span> 👋
            </h1>
            <p className="dash-header__subtitle">
              Here's an overview of your prompt activity.
            </p>
          </div>
          <Link to="/optimize" className="btn-primary dash-header__cta">
            <Zap size={16} />
            New Optimization
          </Link>
        </header>

        {/* ══════════
            STAT CARDS
        ══════════ */}
        <section className="dash-stats">
          {statCards.map((card) => {
            const Icon = card.icon;
            return (
              <div key={card.id} className="stat-card">
                <div
                  className="stat-card__icon-wrap"
                  style={{ background: `${card.color}15`, border: `1px solid ${card.color}25` }}
                >
                  <Icon size={20} style={{ color: card.color }} />
                </div>
                <div className="stat-card__body">
                  <p className="stat-card__label">{card.label}</p>
                  <div className="stat-card__value-row">
                    {statsLoading ? (
                      <div className="stat-card__skeleton" />
                    ) : (
                      <span className="stat-card__value" style={{ color: card.color }}>
                        {card.value}{card.unit}
                      </span>
                    )}
                  </div>
                  <p className="stat-card__desc">{card.desc}</p>
                </div>
              </div>
            );
          })}
        </section>

        {/* ══════════════════════════════
            QUICK OPTIMIZER
        ══════════════════════════════ */}
        <section className="dash-section">
          <div className="dash-section__header">
            <h2 className="dash-section__title">
              <Zap size={18} className="dash-section__icon" style={{ color: '#6c63ff' }} />
              Quick Optimizer
            </h2>
            <Link to="/optimize" className="dash-section__link">
              Full Optimizer <ChevronRight size={14} />
            </Link>
          </div>

          <div className="quick-optimizer">
            <form onSubmit={handleQuickOptimize} className="quick-optimizer__form">
              <textarea
                className="quick-optimizer__input"
                placeholder="Paste your prompt here and hit Analyze — the AI pipeline will detect sensitive data, compress, correct grammar, and return an optimized version…"
                value={quickPrompt}
                onChange={(e) => {
                  setQuickPrompt(e.target.value);
                  if (quickError) setQuickError('');
                  if (quickResult) setQuickResult(null);
                }}
                rows={4}
                disabled={optimizing}
              />
              <div className="quick-optimizer__footer">
                <span className="quick-optimizer__char-count">
                  {quickPrompt.length} chars
                </span>
                <button
                  type="submit"
                  className="btn-primary quick-optimizer__submit"
                  disabled={optimizing || !quickPrompt.trim()}
                >
                  {optimizing ? (
                    <>
                      <Loader2 size={15} className="spin-icon" />
                      Analyzing…
                    </>
                  ) : (
                    <>
                      <Zap size={15} />
                      Analyze
                    </>
                  )}
                </button>
              </div>
            </form>

            {/* ── Quick Error ── */}
            {quickError && (
              <div className="quick-optimizer__error">
                <AlertCircle size={15} />
                {quickError}
              </div>
            )}

            {/* ── Quick Result ── */}
            {quickResult && (
              <div className="quick-result">
                {/* Optimized text — backend field: optimizedPrompt */}
                <div className="quick-result__text-wrap">
                  <div className="quick-result__text-header">
                    <span className="quick-result__text-label">
                      <span className="dot dot--green" />
                      Optimized Prompt
                    </span>
                    <button
                      className="quick-result__copy-btn"
                      onClick={handleCopy}
                      title="Copy optimized prompt"
                    >
                      {copied ? <CheckCheck size={15} /> : <Copy size={15} />}
                      {copied ? 'Copied!' : 'Copy'}
                    </button>
                  </div>
                  <p className="quick-result__text">{quickResult.optimizedPrompt}</p>
                </div>

                <Link to="/optimize" className="quick-result__full-link">
                  View full analysis <ArrowRight size={13} />
                </Link>
              </div>
            )}
          </div>
        </section>

        {/* ══════════════════════════════
            RECENT ACTIVITY
        ══════════════════════════════ */}
        <section className="dash-section">
          <div className="dash-section__header">
            <h2 className="dash-section__title">
              <Clock size={18} className="dash-section__icon" style={{ color: '#00d4aa' }} />
              Recent Activity
            </h2>
            <Link to="/history" className="dash-section__link">
              View All <ChevronRight size={14} />
            </Link>
          </div>

          <div className="activity-list">
            {historyLoading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="activity-skeleton" />
              ))
            ) : history.length === 0 ? (
              <div className="activity-empty">
                <Zap size={32} className="activity-empty__icon" />
                <p className="activity-empty__title">No prompts yet</p>
                <p className="activity-empty__sub">
                  Use the Quick Optimizer above or the{' '}
                  <Link to="/optimize" className="auth-link">full optimizer</Link> to get started.
                </p>
              </div>
            ) : (
              history.map((item, i) => (
                <div key={item.promptId ?? i} className="activity-item">
                  <div className="activity-item__left">
                    <div className="activity-item__index">{i + 1}</div>
                    <div className="activity-item__content">
                      {/* Backend fields: originalPrompt / optimizedPrompt */}
                      <p className="activity-item__original">
                        {item.originalPrompt?.length > 80
                          ? item.originalPrompt.slice(0, 80) + '…'
                          : item.originalPrompt}
                      </p>
                      <p className="activity-item__optimized">
                        {item.optimizedPrompt?.length > 80
                          ? item.optimizedPrompt.slice(0, 80) + '…'
                          : item.optimizedPrompt}
                      </p>
                    </div>
                  </div>
                  <div className="activity-item__right">
                    <span className="activity-time">{timeAgo(item.createdAt)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </div>
  );
}

/* ─── Greeting helper ─── */
function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}
