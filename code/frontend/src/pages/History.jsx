import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Shield, Zap, History as HistoryIcon, LayoutDashboard, LogOut,
  Search, Copy, CheckCheck,
  Eye, Calendar, ArrowRight, X, Lock, AlertCircle, RefreshCw, Sparkles
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getHistory } from '../services/promptService';
import './History.css';

/* Format helpers */
const formatDate = (isoString) => {
  if (!isoString) return '—';
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return isoString;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

export default function History() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  /* ─── State ─── */
  const [data, setData] = useState({ content: [], totalElements: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* Filters */
  const [searchQuery, setSearchQuery] = useState('');

  /* Selected item modal */
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  /* ─── Fetch History ─── */
  const fetchHistoryData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // getHistory() returns { content: [...], totalElements } built from the backend list
      const res = await getHistory();
      setData({ content: res.content, totalElements: res.totalElements });
    } catch (err) {
      // Show the real failure instead of silently displaying fake prompts.
      setData({ content: [], totalElements: 0 });
      setError(
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not load your prompt history. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHistoryData();
  }, [fetchHistoryData]);

  /* ─── Client Filter ─── */
  const filteredPrompts = useMemo(() => {
    const list = data.content || [];
    return list.filter((item) => {
      const q = searchQuery.toLowerCase().trim();
      // Backend fields: originalPrompt / optimizedPrompt
      const matchQuery =
        !q ||
        item.originalPrompt?.toLowerCase().includes(q) ||
        item.optimizedPrompt?.toLowerCase().includes(q);

      return matchQuery;
    });
  }, [data.content, searchQuery]);

  /* ─── Copy handler ─── */
  const handleCopy = (text, id, e) => {
    if (e) e.stopPropagation();
    navigator.clipboard.writeText(text).then(
      () => {
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      },
      () => setError('Could not copy to the clipboard. Please copy the text manually.')
    );
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="history-page">
      {/* ══════════════════════════════
          SIDEBAR
      ══════════════════════════════ */}
      <aside className="dash-sidebar">
        <div className="dash-sidebar__top">
          <Link to="/" className="dash-sidebar__brand">
            <div className="dash-sidebar__brand-icon">
              <Shield size={18} />
            </div>
            <span>Prompt<span className="gradient-text">Shield</span></span>
          </Link>

          <nav className="dash-nav">
            <Link to="/dashboard" className="dash-nav__item">
              <LayoutDashboard size={18} />
              <span>Dashboard</span>
            </Link>
            <Link to="/optimize" className="dash-nav__item">
              <Zap size={18} />
              <span>Optimizer</span>
            </Link>
            <Link to="/history" className="dash-nav__item dash-nav__item--active">
              <HistoryIcon size={18} />
              <span>History</span>
            </Link>
          </nav>
        </div>

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
      <main className="history-main">
        {/* Header */}
        <header className="history-header">
          <div>
            <h1 className="history-header__title">
              Prompt <span className="gradient-text">History</span>
            </h1>
            <p className="history-header__sub">
              Review and manage all your previously shielded and optimized prompts.
            </p>
          </div>

          <button className="history-refresh-btn" onClick={fetchHistoryData} title="Refresh History">
            <RefreshCw size={15} className={loading ? 'spin-icon' : ''} />
            Refresh
          </button>
        </header>

        {/* ══════════════════════════════
            SEARCH & FILTER BAR
        ══════════════════════════════ */}
        <div className="history-controls">
          {/* Search box */}
          <div className="history-search-wrap">
            <Search size={16} className="history-search-icon" />
            <input
              type="text"
              className="history-search-input"
              placeholder="Search prompts by keyword..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button className="history-search-clear" onClick={() => setSearchQuery('')}>
                <X size={14} />
              </button>
            )}
          </div>

          {/* Filter tab — All only (privacy filters need backend support) */}
          <div className="history-filter-tabs">
            <button
              className="history-filter-btn history-filter-btn--active"
            >
              All ({data.totalElements})
            </button>
          </div>
        </div>

        {/* ══════════════════════════════
            HISTORY LIST TABLE / CARDS
        ══════════════════════════════ */}
        {error && (
          <div className="auth-error-banner" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="history-loading-wrap">
            <div className="auth-spinner" />
            <p>Loading prompt history...</p>
          </div>
        ) : error ? null : filteredPrompts.length === 0 ? (
          <div className="history-empty-card">
            <HistoryIcon size={40} className="history-empty__icon" />
            <h3 className="history-empty__title">No prompts found</h3>
            <p className="history-empty__sub">
              {searchQuery
                ? 'Try adjusting your search query.'
                : 'You have not submitted any prompts for optimization yet.'}
            </p>
            <Link to="/optimize" className="btn-primary history-empty__cta">
              <Zap size={16} /> Optimize Your First Prompt
            </Link>
          </div>
        ) : (
          <div className="history-list">
            {filteredPrompts.map((item, idx) => {
              const isCopied = copiedId === (item.promptId || idx);

              return (
                <div
                  key={item.promptId || idx}
                  className="history-card"
                  onClick={() => setSelectedPrompt(item)}
                >
                  <div className="history-card__header">
                    <div className="history-card__date">
                      <Calendar size={13} />
                      {formatDate(item.createdAt)}
                    </div>

                    <div className="history-card__badges">
                      {item.sensitiveDataDetected ? (
                        <span className="hist-badge hist-badge--shield">
                          <Shield size={11} /> Sensitive data detected &amp; masked
                        </span>
                      ) : (
                        <span className="hist-badge hist-badge--clean">
                          No sensitive data
                        </span>
                      )}
                      {item.riskScore != null && (
                        <span className="hist-badge hist-badge--shield" style={{ color: item.riskScore > 60 ? '#ff4d6d' : item.riskScore > 25 ? '#f59e0b' : '#00d4aa' }}>
                          Risk {item.riskScore}/100 ({item.riskLevel || 'LOW'})
                        </span>
                      )}
                      {item.semanticSimilarityScore != null && (
                        <span className="hist-badge hist-badge--clean">
                          Semantic {Number(item.semanticSimilarityScore).toFixed(0)}%
                        </span>
                      )}
                      {item.grammarCorrectionCount > 0 && (
                        <span className="hist-badge hist-badge--shield">
                          {item.grammarCorrectionCount} grammar correction{item.grammarCorrectionCount === 1 ? '' : 's'}
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="history-card__body">
                    {/* Original Preview — backend field: originalPrompt */}
                    <div className="history-card__prompt-section">
                      <span className="history-card__label">Original</span>
                      <p className="history-card__text history-card__text--original">
                        {item.originalPrompt}
                      </p>
                    </div>

                    <div className="history-card__divider">
                      <ArrowRight size={14} />
                    </div>

                    {/* Optimized Preview — backend field: optimizedPrompt */}
                    <div className="history-card__prompt-section">
                      <span className="history-card__label history-card__label--opt">Optimized</span>
                      <p className="history-card__text history-card__text--optimized">
                        {item.optimizedPrompt}
                      </p>
                    </div>
                  </div>

                  <div className="history-card__footer">
                    <div className="history-card__actions">
                      <button
                        className="history-copy-btn"
                        onClick={(e) => handleCopy(item.optimizedPrompt, item.promptId || idx, e)}
                        title="Copy optimized prompt"
                      >
                        {isCopied ? <CheckCheck size={14} /> : <Copy size={14} />}
                        {isCopied ? 'Copied' : 'Copy'}
                      </button>
                      <button className="history-detail-btn" title="View Full Details">
                        <Eye size={14} /> Details
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </main>

      {/* ══════════════════════════════
          DETAIL MODAL
      ══════════════════════════════ */}
      {selectedPrompt && (
        <div className="modal-backdrop" onClick={() => setSelectedPrompt(null)}>
          <div className="history-modal" onClick={(e) => e.stopPropagation()}>
            <div className="history-modal__header">
              <div className="history-modal__title-row">
                <Shield size={20} className="history-modal__icon" />
                <h2>Prompt Details</h2>
              </div>
              <button
                className="history-modal__close"
                onClick={() => setSelectedPrompt(null)}
              >
                <X size={18} />
              </button>
            </div>

            <div className="history-modal__body">
              {/* Timestamp */}
              <div className="history-modal__meta">
                <span><Calendar size={13} /> {formatDate(selectedPrompt.createdAt)}</span>
              </div>

              {/* Side-by-side prompt view */}
              <div className="history-modal__prompts">
                <div className="history-modal__pane history-modal__pane--orig">
                  <div className="history-modal__pane-head">
                    <span><span className="dot dot--red" /> Original Prompt</span>
                  </div>
                  <div className="history-modal__pane-content">
                    {selectedPrompt.originalPrompt}
                  </div>
                </div>

                <div className="history-modal__pane history-modal__pane--opt">
                  <div className="history-modal__pane-head">
                    <span><span className="dot dot--green" /> Optimized Prompt</span>
                    <button
                      className="quick-result__copy-btn"
                      onClick={() => handleCopy(selectedPrompt.optimizedPrompt, 'modal')}
                    >
                      {copiedId === 'modal' ? <CheckCheck size={14} /> : <Copy size={14} />}
                      {copiedId === 'modal' ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <div className="history-modal__pane-content">
                    {selectedPrompt.optimizedPrompt}
                  </div>
                </div>
              </div>

              {/* Privacy Breakdown - shown only if data exists */}
              <div className="history-modal__privacy">
                <h4 className="history-modal__section-title">
                  <Lock size={14} /> Privacy Masking Breakdown
                </h4>

                {selectedPrompt.privacyReport?.entityTypes?.length ? (
                  <div className="history-modal__privacy-grid">
                    <div className="history-modal__flag-card">
                      <span>Total detected entities</span>
                      <strong>{selectedPrompt.privacyReport.totalEntities ?? 0}</strong>
                    </div>
                    <div className="history-modal__flag-card">
                      <span>Risk Assessment</span>
                      <strong style={{ color: (selectedPrompt.riskScore || 0) > 60 ? '#ff4d6d' : (selectedPrompt.riskScore || 0) > 25 ? '#f59e0b' : '#00d4aa' }}>
                        {selectedPrompt.riskScore != null ? selectedPrompt.riskScore : 0}/100 ({selectedPrompt.riskLevel || 'LOW'})
                      </strong>
                    </div>
                    {selectedPrompt.privacyReport.entityTypes.map((entity) => (
                      <div className="history-modal__flag-card" key={`${entity.label}-${entity.count}`}>
                        <div className="history-modal__flag-values">
                          <span className="history-modal__flag-type">{entity.label}</span>
                          <span className="history-modal__flag-orig">{entity.count}</span>
                        </div>
                        <span className="history-modal__flag-masked">→ {entity.maskedAs || `[${entity.label}]`}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="history-modal__privacy-clean">
                    <CheckCheck size={16} /> No sensitive entities detected for this prompt.
                  </p>
                )}
              </div>

              <div className="history-modal__privacy">
                <h4 className="history-modal__section-title">
                  <Sparkles size={14} /> Quality Validation
                </h4>
                <p className="history-modal__privacy-clean">
                  {selectedPrompt.semanticSimilarityScore != null
                    ? `Semantic similarity: ${Number(selectedPrompt.semanticSimilarityScore).toFixed(1)}% · ${selectedPrompt.semanticValid === false ? 'Needs review' : 'Accepted'}`
                    : 'Quality validation details are not available for this older prompt.'}
                </p>
                {selectedPrompt.grammarCorrectionCount > 0 && (
                  <p className="history-modal__privacy-clean">
                    {selectedPrompt.grammarCorrectionCount} grammar correction{selectedPrompt.grammarCorrectionCount === 1 ? '' : 's'} applied.
                  </p>
                )}
              </div>
            </div>

            <div className="history-modal__footer">
              <button
                className="btn-primary history-modal__done-btn"
                onClick={() => setSelectedPrompt(null)}
              >
                Close Details
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
