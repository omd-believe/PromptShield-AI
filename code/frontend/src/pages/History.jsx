import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Zap, History as HistoryIcon,
  Search, Copy, CheckCheck,
  Eye, Calendar, ArrowRight, X, Lock, AlertCircle, RefreshCw, Sparkles
} from 'lucide-react';
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
  /* ─── State ─── */
  const [data, setData] = useState({ content: [], totalElements: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  /* Filters */
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'flagged' | 'clean' | 'highRisk'

  /* Selected item modal */
  const [selectedPrompt, setSelectedPrompt] = useState(null);
  const [copiedId, setCopiedId] = useState(null);

  /* ─── Fetch History ─── */
  const fetchHistoryData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const res = await getHistory();
      setData({
        content: Array.isArray(res?.content) ? res.content : [],
        totalElements: res?.totalElements ?? (res?.content?.length || 0),
      });
    } catch (err) {
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

  /* Keyboard listener for closing modal */
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && selectedPrompt) {
        setSelectedPrompt(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [selectedPrompt]);

  /* ─── Client Filter & Search ─── */
  const filteredPrompts = useMemo(() => {
    const list = data.content || [];
    return list.filter((item) => {
      // 1. Text search
      const q = searchQuery.toLowerCase().trim();
      const matchQuery =
        !q ||
        item.originalPrompt?.toLowerCase().includes(q) ||
        item.optimizedPrompt?.toLowerCase().includes(q);

      if (!matchQuery) return false;

      // 2. Category filter
      if (activeFilter === 'flagged') {
        return Boolean(item.sensitiveDataDetected);
      }
      if (activeFilter === 'clean') {
        return !item.sensitiveDataDetected;
      }
      if (activeFilter === 'highRisk') {
        return (
          (item.riskScore != null && item.riskScore > 50) ||
          item.riskLevel === 'HIGH' ||
          item.riskLevel === 'CRITICAL'
        );
      }

      return true;
    });
  }, [data.content, searchQuery, activeFilter]);

  /* ─── Counts for Filter Tabs ─── */
  const counts = useMemo(() => {
    const list = data.content || [];
    return {
      all: list.length,
      flagged: list.filter((i) => i.sensitiveDataDetected).length,
      clean: list.filter((i) => !i.sensitiveDataDetected).length,
      highRisk: list.filter(
        (i) => (i.riskScore != null && i.riskScore > 50) || i.riskLevel === 'HIGH' || i.riskLevel === 'CRITICAL'
      ).length,
    };
  }, [data.content]);

  /* ─── Copy handler ─── */
  const handleCopy = (text, id, e) => {
    if (e) e.stopPropagation();
    if (!text) return;
    navigator.clipboard.writeText(text).then(
      () => {
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
      },
      () => setError('Could not copy to clipboard. Please copy manually.')
    );
  };

  return (
    <div className="history-container">
      {/* ── Page Header ── */}
      <header className="history-header">
        <div className="history-header__left">
          <div className="history-header__badge">
            <HistoryIcon size={13} style={{ color: 'var(--accent)' }} />
            <span>Audit &amp; Archival</span>
          </div>
          <h1 className="history-header__title">
            Prompt <span className="gradient-text">History</span>
          </h1>
          <p className="history-header__sub">
            Browse, search, and inspect all previously shielded prompts, privacy audits, and optimization metrics.
          </p>
        </div>

        <div className="history-header__actions">
          <button
            className="btn-secondary history-refresh-btn"
            onClick={fetchHistoryData}
            title="Refresh Prompt History"
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
          <Link to="/optimize" className="btn-primary history-new-btn">
            <Zap size={16} />
            <span>New Optimization</span>
          </Link>
        </div>
      </header>

      {/* ── Search & Filter Controls ── */}
      <div className="history-controls">
        <div className="history-search-wrap">
          <Search size={16} className="history-search-icon" aria-hidden="true" />
          <input
            type="search"
            className="history-search-input"
            placeholder="Search original or optimized prompts by keyword…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search prompt history"
          />
          {searchQuery && (
            <button
              className="history-search-clear"
              onClick={() => setSearchQuery('')}
              title="Clear search query"
              aria-label="Clear search"
            >
              <X size={14} />
            </button>
          )}
        </div>

        <div className="history-filter-tabs" role="tablist" aria-label="Filter prompts by security status">
          <button
            role="tab"
            aria-selected={activeFilter === 'all'}
            className={`history-filter-btn ${activeFilter === 'all' ? 'history-filter-btn--active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            <span>All</span>
            <span className="history-filter-count">{counts.all}</span>
          </button>
          <button
            role="tab"
            aria-selected={activeFilter === 'flagged'}
            className={`history-filter-btn ${activeFilter === 'flagged' ? 'history-filter-btn--active' : ''}`}
            onClick={() => setActiveFilter('flagged')}
          >
            <span>PII Flagged</span>
            <span className="history-filter-count">{counts.flagged}</span>
          </button>
          <button
            role="tab"
            aria-selected={activeFilter === 'clean'}
            className={`history-filter-btn ${activeFilter === 'clean' ? 'history-filter-btn--active' : ''}`}
            onClick={() => setActiveFilter('clean')}
          >
            <span>Clean</span>
            <span className="history-filter-count">{counts.clean}</span>
          </button>
          {counts.highRisk > 0 && (
            <button
              role="tab"
              aria-selected={activeFilter === 'highRisk'}
              className={`history-filter-btn ${activeFilter === 'highRisk' ? 'history-filter-btn--active' : ''}`}
              onClick={() => setActiveFilter('highRisk')}
            >
              <span>High Risk</span>
              <span className="history-filter-count history-filter-count--danger">{counts.highRisk}</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Error Banner ── */}
      {error && (
        <div className="history-error-banner" role="alert">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* ── Loading State ── */}
      {loading ? (
        <div className="history-loading-wrap" aria-live="polite">
          <div className="auth-spinner" />
          <p>Retrieving your encrypted prompt history…</p>
        </div>
      ) : error && filteredPrompts.length === 0 ? null : filteredPrompts.length === 0 ? (
        /* ── Empty State ── */
        <div className="history-empty-card">
          <div className="history-empty__icon-wrap">
            <HistoryIcon size={36} className="history-empty__icon" />
          </div>
          <h3 className="history-empty__title">
            {searchQuery || activeFilter !== 'all' ? 'No matching prompts found' : 'No prompt history yet'}
          </h3>
          <p className="history-empty__sub">
            {searchQuery || activeFilter !== 'all'
              ? 'Try adjusting your search keywords or switching filters.'
              : 'Submit your first prompt in Prompt Studio to see shielded versions and privacy audits here.'}
          </p>
          {searchQuery || activeFilter !== 'all' ? (
            <button
              className="btn-secondary history-empty__cta"
              onClick={() => { setSearchQuery(''); setActiveFilter('all'); }}
            >
              Reset Filters
            </button>
          ) : (
            <Link to="/optimize" className="btn-primary history-empty__cta">
              <Zap size={16} />
              <span>Optimize Your First Prompt</span>
            </Link>
          )}
        </div>
      ) : (
        /* ── Prompt Cards List ── */
        <div className="history-list">
          {filteredPrompts.map((item, idx) => {
            const cardKey = item.promptId || idx;
            const isCopied = copiedId === cardKey;

            return (
              <article
                key={cardKey}
                className="history-card"
                onClick={() => setSelectedPrompt(item)}
                tabIndex={0}
                role="button"
                aria-label={`View prompt details from ${formatDate(item.createdAt)}`}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedPrompt(item);
                  }
                }}
              >
                {/* Header row */}
                <div className="history-card__header">
                  <div className="history-card__date">
                    <Calendar size={13} aria-hidden="true" />
                    <span>{formatDate(item.createdAt)}</span>
                  </div>

                  <div className="history-card__badges">
                    {item.sensitiveDataDetected ? (
                      <span className="hist-badge hist-badge--shield">
                        <Shield size={11} aria-hidden="true" /> Sensitive Data Masked
                      </span>
                    ) : (
                      <span className="hist-badge hist-badge--clean">
                        No Sensitive Data
                      </span>
                    )}

                    {item.riskScore != null && (
                      <span
                        className="hist-badge hist-badge--risk"
                        style={{
                          color: item.riskScore > 60 ? 'var(--danger)' : item.riskScore > 25 ? 'var(--warning)' : 'var(--accent-secondary)',
                          background: item.riskScore > 60 ? 'rgba(239, 68, 68, 0.1)' : item.riskScore > 25 ? 'rgba(245, 158, 11, 0.1)' : 'rgba(0, 212, 170, 0.1)',
                          borderColor: item.riskScore > 60 ? 'rgba(239, 68, 68, 0.25)' : item.riskScore > 25 ? 'rgba(245, 158, 11, 0.25)' : 'rgba(0, 212, 170, 0.25)',
                        }}
                      >
                        Risk {item.riskScore}/100 ({item.riskLevel || 'LOW'})
                      </span>
                    )}

                    {item.semanticSimilarityScore != null && (
                      <span className="hist-badge hist-badge--clean">
                        Semantic {Number(item.semanticSimilarityScore).toFixed(0)}%
                      </span>
                    )}

                    {item.grammarCorrectionCount > 0 && (
                      <span className="hist-badge hist-badge--accent">
                        {item.grammarCorrectionCount} grammar fix{item.grammarCorrectionCount === 1 ? '' : 'es'}
                      </span>
                    )}
                  </div>
                </div>

                {/* Body: Side-by-side prompt previews */}
                <div className="history-card__body">
                  <div className="history-card__prompt-section">
                    <span className="history-card__label">Original Input</span>
                    <p className="history-card__text history-card__text--original">
                      {item.originalPrompt}
                    </p>
                  </div>

                  <div className="history-card__divider" aria-hidden="true">
                    <ArrowRight size={14} />
                  </div>

                  <div className="history-card__prompt-section">
                    <span className="history-card__label history-card__label--opt">Shielded Output</span>
                    <p className="history-card__text history-card__text--optimized">
                      {item.optimizedPrompt}
                    </p>
                  </div>
                </div>

                {/* Footer action bar */}
                <div className="history-card__footer">
                  <span className="history-card__hint">Click anywhere on card for full breakdown</span>
                  <div className="history-card__actions">
                    <button
                      type="button"
                      className="history-copy-btn"
                      onClick={(e) => handleCopy(item.optimizedPrompt, cardKey, e)}
                      title="Copy shielded prompt to clipboard"
                    >
                      {isCopied ? <CheckCheck size={14} style={{ color: 'var(--accent-secondary)' }} /> : <Copy size={14} />}
                      <span>{isCopied ? 'Copied' : 'Copy'}</span>
                    </button>
                    <button
                      type="button"
                      className="history-detail-btn"
                      onClick={(e) => { e.stopPropagation(); setSelectedPrompt(item); }}
                      title="Open full inspector modal"
                    >
                      <Eye size={14} />
                      <span>Inspect</span>
                    </button>
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* ── Detail Modal ── */}
      {selectedPrompt && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedPrompt(null)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
        >
          <div className="history-modal" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="history-modal__header">
              <div className="history-modal__title-row">
                <div className="history-modal__icon-wrap">
                  <Shield size={18} />
                </div>
                <div>
                  <h2 id="modal-title">Prompt Audit Inspector</h2>
                  <p className="history-modal__timestamp">
                    <Calendar size={12} /> {formatDate(selectedPrompt.createdAt)}
                  </p>
                </div>
              </div>
              <button
                className="history-modal__close"
                onClick={() => setSelectedPrompt(null)}
                aria-label="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Body */}
            <div className="history-modal__body">
              {/* Side-by-side prompt view */}
              <div className="history-modal__prompts">
                <div className="history-modal__pane history-modal__pane--orig">
                  <div className="history-modal__pane-head">
                    <span><span className="dot dot--red" /> Original Prompt</span>
                    <button
                      className="history-pane-copy"
                      onClick={() => handleCopy(selectedPrompt.originalPrompt, 'modal-orig')}
                      title="Copy original prompt"
                    >
                      {copiedId === 'modal-orig' ? <CheckCheck size={13} /> : <Copy size={13} />}
                      <span>{copiedId === 'modal-orig' ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="history-modal__pane-content">
                    {selectedPrompt.originalPrompt}
                  </div>
                </div>

                <div className="history-modal__pane history-modal__pane--opt">
                  <div className="history-modal__pane-head">
                    <span><span className="dot dot--green" /> Shielded &amp; Optimized Prompt</span>
                    <button
                      className="history-pane-copy"
                      onClick={() => handleCopy(selectedPrompt.optimizedPrompt, 'modal-opt')}
                      title="Copy shielded prompt"
                    >
                      {copiedId === 'modal-opt' ? <CheckCheck size={13} /> : <Copy size={13} />}
                      <span>{copiedId === 'modal-opt' ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                  <div className="history-modal__pane-content">
                    {selectedPrompt.optimizedPrompt}
                  </div>
                </div>
              </div>

              {/* Privacy Breakdown */}
              <section className="history-modal__section">
                <h3 className="history-modal__section-title">
                  <Lock size={15} /> Privacy Masking &amp; Entity Breakdown
                </h3>

                {selectedPrompt.privacyReport?.entityTypes?.length ? (
                  <div className="history-modal__privacy-grid">
                    <div className="history-modal__flag-card">
                      <span className="history-modal__flag-lbl">Total Masked Entities</span>
                      <strong className="history-modal__flag-val">
                        {selectedPrompt.privacyReport.totalEntities ?? selectedPrompt.privacyReport.entityTypes.length}
                      </strong>
                    </div>

                    <div className="history-modal__flag-card">
                      <span className="history-modal__flag-lbl">Risk Assessment</span>
                      <strong
                        className="history-modal__flag-val"
                        style={{
                          color: (selectedPrompt.riskScore || 0) > 60 ? 'var(--danger)' : (selectedPrompt.riskScore || 0) > 25 ? 'var(--warning)' : 'var(--accent-secondary)'
                        }}
                      >
                        {selectedPrompt.riskScore != null ? selectedPrompt.riskScore : 0}/100 ({selectedPrompt.riskLevel || 'LOW'})
                      </strong>
                    </div>

                    {selectedPrompt.privacyReport.entityTypes.map((entity, i) => (
                      <div className="history-modal__flag-card" key={`${entity.label}-${i}`}>
                        <div className="history-modal__flag-values">
                          <span className="history-modal__flag-type">{entity.label}</span>
                          <span className="history-modal__flag-count">{entity.count} match{entity.count === 1 ? '' : 'es'}</span>
                        </div>
                        <span className="history-modal__flag-masked">
                          {entity.maskedAs || `[${entity.label}]`}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="history-modal__clean-banner">
                    <CheckCheck size={16} />
                    <span>No sensitive data entities (PII/secrets) were detected in this prompt.</span>
                  </div>
                )}
              </section>

              {/* Quality & Validation Breakdown */}
              <section className="history-modal__section">
                <h3 className="history-modal__section-title">
                  <Sparkles size={15} /> Quality &amp; Semantic Validation
                </h3>
                <div className="history-modal__quality-grid">
                  <div className="history-modal__flag-card">
                    <span className="history-modal__flag-lbl">Semantic Similarity</span>
                    <strong className="history-modal__flag-val">
                      {selectedPrompt.semanticSimilarityScore != null
                        ? `${Number(selectedPrompt.semanticSimilarityScore).toFixed(1)}%`
                        : '—'}
                    </strong>
                  </div>
                  <div className="history-modal__flag-card">
                    <span className="history-modal__flag-lbl">Semantic Check Status</span>
                    <strong
                      className="history-modal__flag-val"
                      style={{
                        color: selectedPrompt.semanticValid === false ? 'var(--warning)' : 'var(--accent-secondary)'
                      }}
                    >
                      {selectedPrompt.semanticValid === false ? 'Needs Review' : 'Passed'}
                    </strong>
                  </div>
                  <div className="history-modal__flag-card">
                    <span className="history-modal__flag-lbl">Grammar Fixes</span>
                    <strong className="history-modal__flag-val">
                      {selectedPrompt.grammarCorrectionCount != null ? selectedPrompt.grammarCorrectionCount : 0}
                    </strong>
                  </div>
                </div>
              </section>
            </div>

            {/* Modal Footer */}
            <div className="history-modal__footer">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setSelectedPrompt(null)}
              >
                Close
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={() => handleCopy(selectedPrompt.optimizedPrompt, 'modal-btn')}
              >
                {copiedId === 'modal-btn' ? <CheckCheck size={15} /> : <Copy size={15} />}
                <span>{copiedId === 'modal-btn' ? 'Copied Prompt' : 'Copy Shielded Prompt'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
