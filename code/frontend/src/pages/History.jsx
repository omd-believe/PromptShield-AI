import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Shield, Zap, History as HistoryIcon, LayoutDashboard, LogOut,
  Search, Filter, ChevronLeft, ChevronRight, Copy, CheckCheck,
  Eye, Calendar, ArrowRight, X, Lock, Sparkles, AlertCircle, RefreshCw
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { getHistory } from '../services/promptService';
import './History.css';

/* Format helpers */
const fmt = (n, d = 2) => (n == null ? '—' : Number(n).toFixed(d));

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

/* Color map for privacy tags */
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

/* Fallback Mock Data for preview when backend is not connected */
const MOCK_HISTORY_ITEMS = [
  {
    promptId: 1,
    originalPrompt: "Hello ChatGPT! Hope you are doing great. My email is alex.smith@techcorp.io and phone number is 9876543210. Can you please write a quick summary of modern AI prompt optimization techniques?",
    optimizedPrompt: "Write a summary of modern AI prompt optimization techniques.",
    createdAt: new Date(Date.now() - 3600000 * 2).toISOString()
  },
  {
    promptId: 2,
    originalPrompt: "Hey there! My PAN card is ABCDE1234F. I want to calculate my income tax brackets for FY 2025-26 under the new tax regime in India.",
    optimizedPrompt: "Calculate income tax brackets for FY 2025-26 under new tax regime in India.",
    createdAt: new Date(Date.now() - 3600000 * 18).toISOString()
  },
  {
    promptId: 3,
    originalPrompt: "Could you please help me generate a Python script using pandas to clean duplicate records from a CSV dataset?",
    optimizedPrompt: "Generate a Python script using pandas to clean duplicate records from a CSV dataset.",
    createdAt: new Date(Date.now() - 3600000 * 40).toISOString()
  },
  {
    promptId: 4,
    originalPrompt: "Please analyze this log file snippet: Connection to db.prod.internal failed with API key sk-live-998877665544332211. What could be the issue?",
    optimizedPrompt: "Analyze log snippet: Connection to database failed. Identify potential issue.",
    createdAt: new Date(Date.now() - 3600000 * 72).toISOString()
  }
];

export default function History() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  /* ─── State ─── */
  const [page, setPage] = useState(0);
  const pageSize = 8;
  const [data, setData] = useState({ content: [], totalPages: 1, totalElements: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* Filters */
  const [searchQuery, setSearchQuery] = useState('');
  const [filterPrivacy, setFilterPrivacy] = useState('ALL'); // 'ALL' | 'WITH_FLAGS' | 'CLEAN'

  /* Selected item modal */
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  /* ─── Fetch History ─── */
  const fetchHistoryData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // getHistory() returns { content: [...], totalElements } built from backend plain list
      const res = await getHistory();
      if (res && Array.isArray(res.content) && res.content.length > 0) {
        setData({
          content: res.content,
          totalPages: 1,           // backend returns full list, no server-side paging
          totalElements: res.totalElements,
        });
      } else {
        // Fallback to mock data if empty
        setData({
          content: MOCK_HISTORY_ITEMS,
          totalPages: 1,
          totalElements: MOCK_HISTORY_ITEMS.length,
        });
      }
    } catch {
      // Backend not connected fallback
      setData({
        content: MOCK_HISTORY_ITEMS,
        totalPages: 1,
        totalElements: MOCK_HISTORY_ITEMS.length,
      });
    } finally {
      setLoading(false);
    }
  }, [page]);

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
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
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
              All ({data.content?.length || 0})
            </button>
          </div>
        </div>

        {/* ══════════════════════════════
            HISTORY LIST TABLE / CARDS
        ══════════════════════════════ */}
        {loading ? (
          <div className="history-loading-wrap">
            <div className="auth-spinner" />
            <p>Loading prompt history...</p>
          </div>
        ) : filteredPrompts.length === 0 ? (
          <div className="history-empty-card">
            <HistoryIcon size={40} className="history-empty__icon" />
            <h3 className="history-empty__title">No prompts found</h3>
            <p className="history-empty__sub">
              {searchQuery || filterPrivacy !== 'ALL'
                ? 'Try adjusting your search query or filter criteria.'
                : 'You have not submitted any prompts for optimization yet.'}
            </p>
            <Link to="/optimize" className="btn-primary history-empty__cta">
              <Zap size={16} /> Optimize Your First Prompt
            </Link>
          </div>
        ) : (
          <div className="history-list">
            {filteredPrompts.map((item, idx) => {
              const hasFlags = item.privacyReport && item.privacyReport.length > 0;
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
                    <span className="hist-badge hist-badge--clean">
                      {formatDate(item.createdAt)}
                    </span>
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

        {/* ══════════════════════════════
            PAGINATION CONTROLS
        ══════════════════════════════ */}
        {data.totalPages > 1 && (
          <div className="history-pagination">
            <button
              className="history-page-btn"
              disabled={page === 0}
              onClick={() => setPage((p) => Math.max(0, p - 1))}
            >
              <ChevronLeft size={16} /> Previous
            </button>

            <span className="history-page-info">
              Page <strong>{page + 1}</strong> of <strong>{data.totalPages}</strong>
            </span>

            <button
              className="history-page-btn"
              disabled={page >= data.totalPages - 1}
              onClick={() => setPage((p) => Math.min(data.totalPages - 1, p + 1))}
            >
              Next <ChevronRight size={16} />
            </button>
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
                <p className="history-modal__privacy-clean">
                  <CheckCheck size={16} /> Privacy masking details not available in current backend version.
                </p>
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
