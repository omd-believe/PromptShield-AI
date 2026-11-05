import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Zap, Shield, Clock, TrendingUp,
  ChevronRight, Copy, CheckCheck, ArrowRight,
  AlertCircle, Activity, Loader2, Sparkles, RefreshCw
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { usePwa } from '../contexts/PwaContext';
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

const MOCK_STATS = {
  totalPrompts: 0,
  avgTokenReduction: 0,
  totalPrivacyFlags: 0,
  totalEntitiesDetected: 0,
  totalTokensSaved: 0,
  privacyCategories: {},
  riskLevels: {},
  semanticAcceptanceRate: null,
};
const MOCK_HISTORY = { content: [], totalElements: 0 };

export default function Dashboard() {
  const { user } = useAuth();
  const { isOnline } = usePwa();

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
      setStats(MOCK_STATS);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  /* ─── Load Recent History ─── */
  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    try {
      const data = await getHistory(5);
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
    if (!quickPrompt.trim() || !isOnline) return;
    setOptimizing(true);
    setQuickResult(null);
    setQuickError('');
    try {
      const result = await optimizePrompt(quickPrompt.trim());
      setQuickResult(result);
      loadStats();
      loadHistory();
    } catch (err) {
      setQuickError(
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not connect to the AI service. Ensure backend services are running.'
      );
    } finally {
      setOptimizing(false);
    }
  };

  /* ─── Copy optimized text ─── */
  const handleCopy = () => {
    if (!quickResult?.optimizedPrompt) return;
    navigator.clipboard.writeText(quickResult.optimizedPrompt).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setQuickError('Could not copy to clipboard. Please copy manually.')
    );
  };

  /* ─── Stat Cards config ─── */
  const statCards = [
    {
      id: 'total',
      icon: Activity,
      label: 'Prompts Analyzed',
      value: statsLoading ? null : (stats?.totalPrompts ?? 0),
      unit: '',
      color: 'var(--accent)',
      desc: 'All-time volume',
    },
    {
      id: 'reduction',
      icon: TrendingUp,
      label: 'Avg Token Reduction',
      value: statsLoading ? null : fmt(stats?.avgTokenReduction, 1),
      unit: '%',
      color: 'var(--accent-secondary)',
      desc: 'Per shielded prompt',
    },
    {
      id: 'flags',
      icon: Shield,
      label: 'Entities Masked',
      value: statsLoading ? null : (stats?.totalEntitiesDetected ?? 0),
      unit: '',
      color: 'var(--danger)',
      desc: 'PII threats neutralized',
    },
    {
      id: 'tokens-saved',
      icon: Zap,
      label: 'Tokens Saved',
      value: statsLoading ? null : (stats?.totalTokensSaved ?? 0),
      unit: '',
      color: 'var(--warning)',
      desc: 'Cumulative efficiency gain',
    },
  ];

  return (
    <div className="dash-container">
      {/* ── Header ── */}
      <header className="dash-header">
        <div className="dash-header__welcome">
          <div className="dash-header__badge">
            <Sparkles size={13} style={{ color: 'var(--accent)' }} />
            <span>Cybersecurity AI Dashboard</span>
          </div>
          <h1 className="dash-header__title">
            Good {getGreeting()},{' '}
            <span className="gradient-text">{user?.name?.split(' ')[0] || 'there'}</span> 👋
          </h1>
          <p className="dash-header__subtitle">
            System overview and real-time privacy &amp; prompt optimization metrics.
          </p>
        </div>

        <div className="dash-header__actions">
          <button
            className="btn-secondary"
            onClick={() => { loadStats(); loadHistory(); }}
            title="Refresh Dashboard Stats"
          >
            <RefreshCw size={14} className={statsLoading || historyLoading ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
          <Link to="/optimize" className="btn-primary dash-header__cta">
            <Zap size={16} />
            <span>New Optimization</span>
          </Link>
        </div>
      </header>

      {/* ══════════
          STAT CARDS
      ══════════ */}
      <section className="dash-stats" aria-label="Key Performance Indicators">
        {statCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.id} className="stat-card">
              <div
                className="stat-card__icon-wrap"
                style={{ background: `color-mix(in srgb, ${card.color} 15%, transparent)`, borderColor: `color-mix(in srgb, ${card.color} 25%, transparent)` }}
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
          ANALYTICS BREAKDOWN
      ══════════════════════════════ */}
      <section className="dash-analytics">
        {/* Privacy Analytics Panel */}
        <div className="dash-analytics__panel">
          <div className="dash-section__header">
            <h2 className="dash-section__title">
              <Shield size={18} className="dash-section__icon" style={{ color: 'var(--danger)' }} />
              Privacy Neutralization Breakdown
            </h2>
            <span className="badge badge--neutral">Sensitive PII</span>
          </div>

          {statsLoading ? (
            <div className="dash-analytics__loading" />
          ) : Object.keys(stats?.privacyCategories || {}).length === 0 ? (
            <div className="dash-empty-box">
              <Shield size={24} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
              <p>No sensitive entities masked yet. Try optimizing a prompt with personal data!</p>
            </div>
          ) : (
            <div className="dash-analytics__rows">
              {Object.entries(stats.privacyCategories)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 6)
                .map(([label, count]) => {
                  const maxCount = stats.totalEntitiesDetected || count || 1;
                  const pct = Math.min(100, Math.round((count / maxCount) * 100));
                  return (
                    <div className="dash-analytics__row" key={label}>
                      <span className="dash-analytics__label">{label}</span>
                      <div className="dash-analytics__bar" role="progressbar" aria-valuenow={pct} aria-valuemin="0" aria-valuemax="100">
                        <span style={{ width: `${Math.max(4, pct)}%` }} />
                      </div>
                      <strong className="dash-analytics__count">{count}</strong>
                    </div>
                  );
                })}
            </div>
          )}
        </div>

        {/* Quality & Risk Snapshot */}
        <div className="dash-analytics__panel">
          <div className="dash-section__header">
            <h2 className="dash-section__title">
              <TrendingUp size={18} className="dash-section__icon" style={{ color: 'var(--accent-secondary)' }} />
              Fidelity &amp; Risk Health
            </h2>
            <span className="badge badge--safe">Deterministic AI</span>
          </div>

          <div className="dash-quality__metric">
            <div>
              <div style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>Semantic Integrity</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Proportion passing fidelity threshold</div>
            </div>
            <strong>
              {statsLoading || stats?.semanticAcceptanceRate == null
                ? '—'
                : `${fmt(stats.semanticAcceptanceRate, 1)}%`}
            </strong>
          </div>

          <div className="dash-quality__risk-header">
            <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontWeight: 600 }}>Detected Risk Distribution:</span>
          </div>

          <div className="dash-quality__risk">
            {Object.entries(stats?.riskLevels || {}).map(([level, count]) => {
              const lvlLower = level.toLowerCase();
              const badgeClass =
                lvlLower === 'low' ? 'badge--safe' :
                lvlLower === 'medium' ? 'badge--warning' : 'badge--danger';
              return (
                <span key={level} className={`badge ${badgeClass}`}>
                  {level}: {count}
                </span>
              );
            })}
            {!statsLoading && Object.keys(stats?.riskLevels || {}).length === 0 && (
              <span className="dash-analytics__empty">No risk events evaluated yet.</span>
            )}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════
          QUICK OPTIMIZER
      ══════════════════════════════ */}
      <section className="dash-section">
        <div className="dash-section__header">
          <h2 className="dash-section__title">
            <Zap size={18} className="dash-section__icon" style={{ color: 'var(--accent)' }} />
            Quick Optimizer
          </h2>
          <Link to="/optimize" className="dash-section__link">
            <span>Advanced Controls</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="quick-optimizer">
          <form onSubmit={handleQuickOptimize} className="quick-optimizer__form">
            <textarea
              className="quick-optimizer__input"
              placeholder="Paste any prompt here to instantly sanitize sensitive PII, strip bloat, and compress tokens…"
              value={quickPrompt}
              onChange={(e) => {
                setQuickPrompt(e.target.value);
                if (quickError) setQuickError('');
                if (quickResult) setQuickResult(null);
              }}
              rows={4}
              disabled={optimizing || !isOnline}
            />

            <div className="quick-optimizer__footer">
              <div className="quick-optimizer__meta">
                <span className="quick-optimizer__char-count">
                  {quickPrompt.length} chars · ~{quickPrompt.trim().split(/\s+/).filter(Boolean).length} words
                </span>
                {!isOnline && (
                  <span className="badge badge--danger" style={{ fontSize: '0.72rem' }}>Offline</span>
                )}
              </div>

              <button
                type="submit"
                className="btn-primary quick-optimizer__submit"
                disabled={optimizing || !quickPrompt.trim() || !isOnline}
              >
                {optimizing ? (
                  <>
                    <Loader2 size={15} className="spin-icon" />
                    <span>Analyzing…</span>
                  </>
                ) : (
                  <>
                    <Shield size={15} />
                    <span>Shield &amp; Optimize</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Quick Error Banner */}
          {quickError && (
            <div className="quick-optimizer__error" role="alert">
              <AlertCircle size={16} />
              <span>{quickError}</span>
            </div>
          )}

          {/* Quick Result Output */}
          {quickResult && (
            <div className="quick-result">
              <div className="quick-result__metrics-grid">
                <div className="quick-result__mini-metric">
                  <span className="quick-result__metric-label">Tokens Saved</span>
                  <span className="quick-result__metric-val" style={{ color: 'var(--accent-secondary)' }}>
                    {Math.max(0, (quickResult.originalTokens || 0) - (quickResult.optimizedTokens || 0))}
                  </span>
                </div>
                <div className="quick-result__mini-metric">
                  <span className="quick-result__metric-label">Token Change</span>
                  <span className="quick-result__metric-val gradient-text">
                    {quickResult.reductionPercentage != null ? `${fmt(quickResult.reductionPercentage, 1)}%` : '0%'}
                  </span>
                </div>
                <div className="quick-result__mini-metric">
                  <span className="quick-result__metric-label">Privacy Risk</span>
                  <span
                    className="quick-result__metric-val"
                    style={{
                      color: (quickResult.riskScore || 0) > 60 ? 'var(--danger)' :
                             (quickResult.riskScore || 0) > 25 ? 'var(--warning)' : 'var(--accent-secondary)'
                    }}
                  >
                    {quickResult.riskScore ?? 0}/100 ({quickResult.riskLevel || 'LOW'})
                  </span>
                </div>
                <div className="quick-result__mini-metric">
                  <span className="quick-result__metric-label">Semantic Match</span>
                  <span className="quick-result__metric-val" style={{ color: 'var(--accent-secondary)' }}>
                    {quickResult.semanticSimilarityScore != null ? `${fmt(quickResult.semanticSimilarityScore, 1)}%` : '100%'}
                  </span>
                </div>
              </div>

              <div className="quick-result__text-wrap">
                <div className="quick-result__text-header">
                  <span className="quick-result__text-label">
                    <span className="dot dot--green" />
                    Optimized Output
                  </span>
                  <button
                    className="quick-result__copy-btn"
                    onClick={handleCopy}
                    title="Copy optimized prompt"
                  >
                    {copied ? <CheckCheck size={14} /> : <Copy size={14} />}
                    <span>{copied ? 'Copied!' : 'Copy'}</span>
                  </button>
                </div>
                <p className="quick-result__text">{quickResult.optimizedPrompt}</p>
              </div>

              <Link to="/optimize" className="quick-result__full-link">
                <span>Open in Full Pipeline Studio</span>
                <ArrowRight size={14} />
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
            <Clock size={18} className="dash-section__icon" style={{ color: 'var(--accent-secondary)' }} />
            Recent Prompt Stream
          </h2>
          <Link to="/history" className="dash-section__link">
            <span>View All</span>
            <ChevronRight size={14} />
          </Link>
        </div>

        <div className="activity-list">
          {historyLoading ? (
            Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="activity-skeleton" />
            ))
          ) : history.length === 0 ? (
            <div className="activity-empty">
              <Zap size={36} className="activity-empty__icon" />
              <p className="activity-empty__title">No activity recorded yet</p>
              <p className="activity-empty__sub">
                Shield and optimize your first prompt using the Quick Optimizer above or visit the{' '}
                <Link to="/optimize" className="gradient-text" style={{ fontWeight: 600 }}>full optimizer</Link>.
              </p>
            </div>
          ) : (
            history.map((item, i) => (
              <div key={item.promptId ?? i} className="activity-item">
                <div className="activity-item__left">
                  <div className="activity-item__index">{i + 1}</div>
                  <div className="activity-item__content">
                    <p className="activity-item__original">
                      <span className="activity-item__tag-prefix">Orig:</span>
                      {item.originalPrompt?.length > 90
                        ? item.originalPrompt.slice(0, 90) + '…'
                        : item.originalPrompt}
                    </p>
                    <p className="activity-item__optimized">
                      <span className="activity-item__tag-prefix activity-item__tag-prefix--opt">Opt:</span>
                      {item.optimizedPrompt?.length > 90
                        ? item.optimizedPrompt.slice(0, 90) + '…'
                        : item.optimizedPrompt}
                    </p>
                  </div>
                </div>

                <div className="activity-item__right">
                  {item.sensitiveDataDetected ? (
                    <span className="badge badge--danger" style={{ fontSize: '0.68rem' }}>
                      <Shield size={10} /> Masked
                    </span>
                  ) : (
                    <span className="badge badge--safe" style={{ fontSize: '0.68rem' }}>Clean</span>
                  )}
                  <span className="activity-time">{timeAgo(item.createdAt)}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </section>
    </div>
  );
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'morning';
  if (h < 17) return 'afternoon';
  return 'evening';
}
