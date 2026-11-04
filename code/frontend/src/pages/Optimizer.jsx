import { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Shield, Zap, Brain, Sparkles, Eye, Copy, CheckCheck,
  ArrowRight, LayoutDashboard, History, LogOut,
  AlertCircle, ChevronDown, ChevronUp, RotateCcw,
  FileText, TrendingDown, Lock
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { analyzePrompt, optimizePrompt, recordPrivacyAudit } from '../services/promptService';
import { useNavigate } from 'react-router-dom';
import './Optimizer.css';

/* ─── Pipeline stages (from Activity Diagram) ─── */
const PIPELINE_STAGES = [
  { id: 'preprocess',   label: 'Preprocessing',          icon: FileText,     desc: 'Normalizing text, validating constraints…' },
  { id: 'privacy',      label: 'Privacy Detection',       icon: Eye,          desc: 'Regex + NER scanning, risk scoring, masking…' },
  { id: 'optimizer',    label: 'Prompt Optimization',     icon: TrendingDown, desc: 'Removing filler and redundant phrases…' },
  { id: 'grammar',      label: 'Grammar Polish',          icon: Sparkles,     desc: 'Applying conservative corrections…' },
  { id: 'quality',      label: 'Quality & Constraints',   icon: Shield,       desc: 'Checking placeholders, negations, constraints…' },
  { id: 'semantic',     label: 'Semantic Validation',     icon: Brain,        desc: 'Measuring lexical similarity score…' },
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
  const [targetMaxTokens, setTargetMaxTokens] = useState('');
  const [minimumSemanticScore, setMinimumSemanticScore] = useState('');
  const [privacyPolicyText, setPrivacyPolicyText] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);   // pipeline step index
  const [completedStages, setCompletedStages] = useState([]);
  const [result, setResult] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [reviewPending, setReviewPending] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [copied, setCopied] = useState(false);
  const [expandedFlag, setExpandedFlag] = useState(null);
  const resultRef = useRef(null);
  const animRef = useRef(null);

  const readPrivacyPolicy = () => {
    if (!privacyPolicyText.trim()) return undefined;
    try {
      return JSON.parse(privacyPolicyText);
    } catch {
      throw new Error('Privacy policy must be valid JSON.');
    }
  };

  /* Stop the progress animation if the page is left while a request is running */
  useEffect(() => () => clearInterval(animRef.current), []);

  /* ─── Simulate pipeline progression while waiting for API ─── */
  const runPipelineAnimation = () => {
    const totalStages = PIPELINE_STAGES.length;
    let current = 0;
    clearInterval(animRef.current);
    // Spread stage animations over ~3s (will be cut short when API responds)
    const interval = setInterval(() => {
      if (current < totalStages) {
        // Capture the index NOW: React may run the state updater after `current++`,
        // which used to mark the wrong stage as completed.
        const stageIndex = current;
        setActiveStage(stageIndex);
        if (stageIndex > 0) {
          setCompletedStages(prev => (prev.includes(stageIndex - 1) ? prev : [...prev, stageIndex - 1]));
        }
        current++;
      } else {
        clearInterval(interval);
      }
    }, 520);
    animRef.current = interval;
    return interval;
  };

  /* ─── Submit handler → POST /api/v1/prompts ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!promptText.trim()) return;

    setLoading(true);
    setResult(null);
    setAnalysisResult(null);
    setReviewPending(false);
    setError('');
    setActiveStage(0);
    setCompletedStages([]);

    const animInterval = runPipelineAnimation();

    try {
      const privacyPolicy = readPrivacyPolicy();
      const privacy = await analyzePrompt(promptText.trim(), privacyPolicy);
      if (privacy.blocked || privacy.confirmationRequired) {
        clearInterval(animInterval);
        setActiveStage(-1);
        setCompletedStages([]);
        setAnalysisResult(privacy);
        setReviewPending(true);
        recordPrivacyAudit({
          eventType: privacy.blocked ? 'BLOCKED_REVIEW' : 'CONFIRMATION_REQUIRED',
          riskLevel: privacy.riskLevel,
          riskScore: privacy.riskScore,
          categories: Object.keys(privacy.policyActions || {}),
        }).catch(() => setError('Privacy review was shown, but the audit event could not be recorded.'));
        setLoading(false);
        setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
        return;
      }
      const data = await optimizePrompt(promptText.trim(), {
        targetMaxTokens,
        minimumSemanticScore,
        privacyPolicy,
      });
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
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not connect to the AI service. Make sure the Spring Boot + FastAPI backends are running.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzePrivacy = async () => {
    if (!promptText.trim()) return;

    setAnalyzing(true);
    setResult(null);
    setAnalysisResult(null);
    setReviewPending(false);
    setError('');
    try {
      const data = await analyzePrompt(promptText.trim(), readPrivacyPolicy());
      setAnalysisResult(data);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      setError(
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not analyze the prompt. Make sure the Spring Boot + FastAPI backends are running.'
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const continueWithSafePrompt = async () => {
    if (!analysisResult) return;
    const originalText = promptText.trim();
    const approvedPolicy = { ...(readPrivacyPolicy() || {}) };
    if (analysisResult.policyActions) {
      Object.keys(analysisResult.policyActions).forEach(cat => {
        if (analysisResult.policyActions[cat] === 'REQUIRE_CONFIRMATION' || analysisResult.policyActions[cat] === 'BLOCK') {
          approvedPolicy[cat] = 'MASK';
        }
      });
    }
    recordPrivacyAudit({
      eventType: 'SAFE_PROMPT_APPROVED',
      riskLevel: analysisResult.riskLevel,
      riskScore: analysisResult.riskScore,
      categories: Object.keys(analysisResult.policyActions || {}),
    }).catch(() => setError('Safe prompt approved, but the audit event could not be recorded.'));
    setReviewPending(false);
    setError('');
    setLoading(true);
    setResult(null);
    setActiveStage(0);
    setCompletedStages([]);
    const animInterval = runPipelineAnimation();
    try {
      const data = await optimizePrompt(originalText, {
        targetMaxTokens,
        minimumSemanticScore,
        privacyPolicy: Object.keys(approvedPolicy).length > 0 ? approvedPolicy : undefined,
      });
      clearInterval(animInterval);
      setCompletedStages(PIPELINE_STAGES.map((_, i) => i));
      setActiveStage(-1);
      const finalResult = {
        ...data,
        entities: data.entities && data.entities.length > 0 ? data.entities : (analysisResult.entities || []),
        privacyReport: data.privacyReport || analysisResult.privacyReport,
        riskScore: data.riskScore != null ? data.riskScore : analysisResult.riskScore,
        riskLevel: data.riskLevel || analysisResult.riskLevel,
      };
      setResult(finalResult);
      setAnalysisResult(null);
      setActiveTab(0);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      clearInterval(animInterval);
      setActiveStage(-1);
      setCompletedStages([]);
      setError(
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not continue with the safe prompt.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setPromptText('');
    setResult(null);
    setAnalysisResult(null);
    setReviewPending(false);
    setError('');
    setActiveStage(-1);
    setCompletedStages([]);
  };

  const handleCopy = () => {
    // Backend field: optimizedPrompt
    if (!result?.optimizedPrompt) return;
    navigator.clipboard.writeText(result.optimizedPrompt).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setError('Could not copy to the clipboard. Please copy the text manually.')
    );
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

              <div className="opt-targets">
                <label>
                  Max tokens
                  <input
                    type="number"
                    min="1"
                    max="100000"
                    placeholder="Optional"
                    value={targetMaxTokens}
                    onChange={(e) => setTargetMaxTokens(e.target.value)}
                    disabled={loading}
                  />
                </label>
                <label>
                  Minimum semantic score
                  <input
                    type="number"
                    min="0"
                    max="100"
                    step="1"
                    placeholder="Optional"
                    value={minimumSemanticScore}
                    onChange={(e) => setMinimumSemanticScore(e.target.value)}
                    disabled={loading}
                  />
                </label>
                <span className="opt-targets__hint">
                  Required content is never truncated to force a target.
                </span>
              </div>

              <label className="opt-policy">
                Privacy policy overrides (JSON, optional)
                <textarea
                  rows={2}
                  placeholder='{"EMAIL":"MASK","ORG":"REPORT","API_KEY":"BLOCK"}'
                  value={privacyPolicyText}
                  onChange={(e) => setPrivacyPolicyText(e.target.value)}
                  disabled={loading || analyzing}
                />
                <span className="opt-targets__hint">
                  Actions: MASK, REPORT, ALLOW, BLOCK, REQUIRE_CONFIRMATION.
                </span>
              </label>

              <div className="opt-input-footer">
                <div className="opt-hints">
                  <span className="opt-hint"><Eye size={11} /> Detects: Email, Phone, PAN, Aadhaar, API Keys, Names</span>
                  <span className="opt-hint"><Zap size={11} /> Pipeline: Deterministic Baseline V1</span>
                </div>
                <div className="opt-actions">
                  <button
                    type="button"
                    className="btn-secondary opt-submit-btn"
                    onClick={handleAnalyzePrivacy}
                    disabled={loading || analyzing || !promptText.trim()}
                  >
                    {analyzing ? (
                      <><span className="auth-spinner" /> Analyzing…</>
                    ) : (
                      <><Eye size={16} /> Analyze Privacy</>
                    )}
                  </button>
                  <button
                    type="submit"
                    className={`btn-primary opt-submit-btn ${loading ? 'opt-submit-btn--loading' : ''}`}
                    disabled={loading || analyzing || !promptText.trim()}
                  >
                    {loading ? (
                      <><span className="auth-spinner" /> Processing…</>
                    ) : (
                      <><Shield size={16} /> Analyze &amp; Optimize</>
                    )}
                  </button>
                </div>
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

        {analysisResult && (
          <div className="privacy-analysis-card" ref={resultRef}>
            <div className="privacy-analysis-card__header">
              <div>
                <h2>Privacy Analysis</h2>
                <p>Detected sensitive information is shown below. No optimization was performed.</p>
              </div>
              <div className={`privacy-analysis-risk privacy-analysis-risk--${analysisResult.riskLevel?.toLowerCase()}`}>
                {analysisResult.riskLevel} · {analysisResult.riskScore}/100
              </div>
            </div>

            {(analysisResult.blocked || analysisResult.confirmationRequired || reviewPending) && (
              <div className={`privacy-review-banner ${analysisResult.blocked ? 'privacy-review-banner--blocked' : ''}`}>
                <strong>
                  {analysisResult.blocked
                    ? 'Optimization blocked by your privacy policy.'
                    : 'Confirmation required before optimization.'}
                </strong>
                <p>
                  {analysisResult.blocked
                    ? `Blocked categories: ${(analysisResult.blockedLabels || []).join(', ') || 'sensitive data'}.`
                    : 'Review the detected values and continue only with the anonymized prompt.'}
                </p>
                <div className="privacy-review-actions">
                  <button type="button" className="btn-primary" onClick={continueWithSafePrompt} disabled={loading}>
                    <Shield size={15} /> Continue with safe prompt
                  </button>
                  <button
                    type="button"
                    className="btn-secondary privacy-review-edit"
                    onClick={() => {
                      setPromptText(analysisResult.anonymizedPrompt || promptText);
                      setReviewPending(false);
                      setError('');
                    }}
                    disabled={loading}
                  >
                    Edit safe prompt
                  </button>
                </div>
              </div>
            )}

            <div className="privacy-analysis-card__preview">
              <span>Anonymized preview</span>
              <p>{analysisResult.anonymizedPrompt}</p>
            </div>

            <div className="privacy-analysis-summary">
              {(analysisResult.privacyReport?.entityTypes || []).map((item) => (
                <div className="privacy-analysis-summary__item" key={item.label}>
                  <span style={{ color: typeColor(item.label) }}>{item.label}</span>
                  <strong>{item.count}</strong>
                  <small>{item.maskedAs}</small>
                </div>
              ))}
              {(analysisResult.privacyReport?.totalEntities ?? 0) === 0 && (
                <p className="privacy-analysis-empty">No sensitive information detected.</p>
              )}
            </div>

            {analysisResult.entities?.length > 0 && (
              <div className="privacy-analysis-entities">
                <h3>Detected values</h3>
                {analysisResult.entities.map((entity, index) => (
                  <div className="privacy-analysis-entity" key={`${entity.label}-${entity.text}-${index}`}>
                    <span style={{ color: typeColor(entity.label) }}>{entity.label}</span>
                    <code>{entity.text}</code>
                    <span>→ {entity.policyAction || 'REPORT'}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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
              const origTok   = result.originalTokens != null ? result.originalTokens : Math.ceil(origWords * 1.33);
              const optTok    = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil(optWords * 1.33);
              const diffTok   = origTok - optTok;
              const rawPct    = origTok > 0 ? (diffTok / origTok * 100) : 0;
              const pct       = result.reductionPercentage != null && result.reductionPercentage > 0 ? result.reductionPercentage : rawPct;
              const isIncrease = diffTok < 0;
              
              const rawEntities = Array.isArray(result.entities) ? result.entities : [];
              const rawReportTypes = Array.isArray(result.privacyReport?.entityTypes) ? result.privacyReport.entityTypes : [];
              const entities = rawEntities.length > 0 
                ? rawEntities.map(e => ({
                    type: e.label || e.type || 'SENSITIVE',
                    masked: `[${e.label || e.type || 'REDACTED'}]`,
                    value: e.text || e.value || '',
                    policyAction: e.policyAction || e.policy_action || (result.policyActions && result.policyActions[e.label]) || 'MASK'
                  }))
                : rawReportTypes.flatMap(et =>
                    Array.from({ length: et.count || 1 }, () => ({
                      type: et.label || 'SENSITIVE',
                      masked: et.maskedAs || `[${et.label || 'REDACTED'}]`,
                      value: et.maskedAs || `[${et.label || 'REDACTED'}]`,
                      policyAction: 'MASK'
                    }))
                  );

              const entitiesDetected = result.privacyReport?.totalEntities ?? entities.length;
              const riskScore = result.riskScore != null ? result.riskScore : 0;
              const riskLevel = result.riskLevel || 'LOW';
              const semanticScore = result.semanticSimilarityScore != null ? result.semanticSimilarityScore : 0;
              const semanticValid = result.semanticValid ?? true;

              return (
                <>
                  <div className="opt-metrics">
                    <div className="opt-metric">
                      <span className="opt-metric__val" style={{ color: isIncrease ? '#f59e0b' : '#00d4aa' }}>
                        {pct > 0 ? fmt(pct, 1) + '%' : isIncrease ? '+' + fmt(Math.abs(rawPct), 1) + '%' : '0%'}
                      </span>
                      <span className="opt-metric__label">{isIncrease ? 'Token Increase' : 'End-to-End Change'}</span>
                    </div>
                    <div className="opt-metric-divider" />
                    <div className="opt-metric">
                      <span className="opt-metric__val" style={{ color: '#6c63ff' }}>
                        {result.compressionPercentage != null && result.compressionPercentage > 0
                          ? fmt(result.compressionPercentage, 1) + '%'
                          : '0%'}
                      </span>
                      <span className="opt-metric__label">Compression Savings</span>
                    </div>
                    <div className="opt-metric-divider" />
                    <div className="opt-metric">
                      <span className="opt-metric__val" style={{ color: '#00d4aa' }}>
                        {Math.max(0, diffTok)}
                      </span>
                      <span className="opt-metric__label">Tokens Saved</span>
                    </div>
                    <div className="opt-metric-divider" />
                    <div className="opt-metric">
                      <span className="opt-metric__val" style={{ color: riskScore > 60 ? '#ff4d6d' : riskScore > 25 ? '#f59e0b' : '#00d4aa' }}>
                        {riskScore}/100 ({riskLevel})
                      </span>
                      <span className="opt-metric__label">Privacy Risk</span>
                    </div>
                    <div className="opt-metric-divider" />
                    <div className="opt-metric">
                      <span className="opt-metric__val" style={{ color: semanticValid ? '#00d4aa' : '#ff4d6d' }}>
                        {fmt(semanticScore, 1)}%
                      </span>
                      <span className="opt-metric__label">Semantic Match</span>
                    </div>
                  </div>

                  {result.optimizationWarnings && result.optimizationWarnings.length > 0 && (
                    <div style={{ margin: '14px 0', padding: '12px 16px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#f59e0b', fontWeight: 600, marginBottom: '6px', fontSize: '13px' }}>
                        <AlertCircle size={15} />
                        <span>Optimization Safeguards &amp; Notices</span>
                      </div>
                      <ul style={{ margin: 0, paddingLeft: '20px', color: '#e2e8f0', fontSize: '13px', lineHeight: 1.5 }}>
                        {result.optimizationWarnings.map((warn, idx) => (
                          <li key={idx}>{warn}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              );
            })()}

            {/* ── Tabs ── */}
            {(() => {
              const count = result.privacyReport?.totalEntities ?? (Array.isArray(result.entities) ? result.entities.length : 0);
              return (
                <div className="opt-tabs">
                  {RESULT_TABS.map((tab, i) => (
                    <button
                      key={tab}
                      className={`opt-tab ${activeTab === i ? 'opt-tab--active' : ''}`}
                      onClick={() => setActiveTab(i)}
                    >
                      {tab}
                      {i === 1 && count > 0 && (
                        <span className="opt-tab__badge">{count}</span>
                      )}
                    </button>
                  ))}
                </div>
              );
            })()}

            {/* ── Tab: Optimized Prompt ── */}
            {activeTab === 0 && (
              <div className="opt-tab-content">
                {/* Side by side comparison — backend fields: originalPrompt / optimizedPrompt */}
                {(() => {
                  const origTok = result.originalTokens != null ? result.originalTokens : Math.ceil((result.originalPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
                  const optTok  = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil((result.optimizedPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
                  const pct     = result.reductionPercentage != null ? Math.round(result.reductionPercentage) : (origTok > 0 ? Math.round((origTok - optTok) / origTok * 100) : 0);
                  return (
                    <div className="opt-compare">
                      <div className="opt-compare__pane opt-compare__pane--original">
                        <div className="opt-compare__pane-header">
                          <span><span className="dot dot--red" /> Original</span>
                          <span className="opt-compare__token-count">{origTok} tokens</span>
                        </div>
                        <p className="opt-compare__text">{result.originalPrompt}</p>
                      </div>

                      <div className="opt-compare__arrow">
                        <ArrowRight size={20} className="opt-compare__arrow-icon" />
                        {origTok > optTok && (
                          <span className="opt-compare__reduction">
                            {fmt(((origTok - optTok) / origTok) * 100, 1)}% fewer tokens
                          </span>
                        )}
                        {optTok > origTok && (
                          <span className="opt-compare__reduction" style={{ color: '#f59e0b', background: 'rgba(245, 158, 11, 0.15)' }}>
                            +{fmt(((optTok - origTok) / origTok) * 100, 1)}% more tokens
                          </span>
                        )}
                        {origTok === optTok && (
                          <span className="opt-compare__reduction" style={{ color: '#94a3b8' }}>
                            0% change
                          </span>
                        )}
                      </div>

                      <div className="opt-compare__pane opt-compare__pane--optimized">
                        <div className="opt-compare__pane-header">
                          <span><span className="dot dot--green" /> Optimized</span>
                          <span className="opt-compare__token-count">{optTok} tokens</span>
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
            {activeTab === 1 && (() => {
              const rawEntities = Array.isArray(result.entities) ? result.entities : [];
              const rawReportTypes = Array.isArray(result.privacyReport?.entityTypes) ? result.privacyReport.entityTypes : [];
              const entities = rawEntities.length > 0
                ? rawEntities.map(e => ({
                    type: e.label || e.type || 'SENSITIVE',
                    masked: `[${e.label || e.type || 'REDACTED'}]`,
                    value: e.text || e.value || '',
                    confidence: e.confidence,
                    policyAction: e.policyAction || e.policy_action || (result.policyActions && result.policyActions[e.label]) || 'MASK'
                  }))
                : rawReportTypes.flatMap(et =>
                    Array.from({ length: et.count || 1 }, () => ({
                      type: et.label || 'SENSITIVE',
                      masked: et.maskedAs || `[${et.label || 'REDACTED'}]`,
                      value: et.maskedAs || `[${et.label || 'REDACTED'}]`,
                      confidence: 1.0,
                      policyAction: 'MASK'
                    }))
                  );

              const entitiesDetected = result.privacyReport?.totalEntities ?? entities.length;
              const entitiesMasked = entities.filter(e => (e.policyAction || 'MASK').toUpperCase() === 'MASK').length;
              const residualLeakage = result.leakageDetected ? 'Detected' : 'None (0)';
              const privacyValid = result.privacyValid !== false;
              const riskScore = result.riskScore != null ? result.riskScore : 0;
              const riskLevel = result.riskLevel || 'LOW';

              return (
                <div className="opt-tab-content">
                  {/* Explicit Privacy Audit Breakdown Cards */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', marginBottom: '18px' }}>
                    <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '10px 14px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Detections</span>
                      <p style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: entitiesDetected > 0 ? '#ff4d6d' : '#00d4aa' }}>{entitiesDetected}</p>
                    </div>
                    <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '10px 14px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Masked</span>
                      <p style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: '#00d4aa' }}>{entitiesMasked}</p>
                    </div>
                    <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '10px 14px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Residual Leakage</span>
                      <p style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: result.leakageDetected ? '#ff4d6d' : '#00d4aa' }}>{residualLeakage}</p>
                    </div>
                    <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '10px 14px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Privacy Valid</span>
                      <p style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: privacyValid ? '#00d4aa' : '#ff4d6d' }}>{privacyValid ? 'Passed' : 'Failed'}</p>
                    </div>
                    <div style={{ background: 'rgba(255, 255, 255, 0.04)', border: '1px solid rgba(255, 255, 255, 0.08)', borderRadius: '8px', padding: '10px 14px' }}>
                      <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Risk Assessment</span>
                      <p style={{ margin: '4px 0 0', fontSize: '18px', fontWeight: 700, color: riskScore > 60 ? '#ff4d6d' : riskScore > 25 ? '#f59e0b' : '#00d4aa' }}>{riskScore}/100 ({riskLevel})</p>
                    </div>
                  </div>

                  {entities.length === 0 ? (
                    <div className="opt-privacy-empty">
                      <Shield size={36} className="opt-privacy-empty__icon" />
                      <p>No sensitive data detected in this prompt.</p>
                    </div>
                  ) : (
                    <div className="opt-privacy-list">
                      <p className="opt-privacy-intro">
                        <Lock size={13} />
                        The following sensitive items were evaluated against the privacy policy.
                      </p>
                      {entities.map((item, i) => {
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
                                <span
                                  className="privacy-row__policy"
                                  style={{
                                    fontSize: 10,
                                    fontWeight: 600,
                                    padding: '2px 6px',
                                    borderRadius: 4,
                                    background: item.policyAction === 'ALLOW' ? 'rgba(0, 212, 170, 0.15)' : item.policyAction === 'BLOCK' ? 'rgba(255, 77, 109, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                                    color: item.policyAction === 'ALLOW' ? '#00d4aa' : item.policyAction === 'BLOCK' ? '#ff4d6d' : '#94a3b8',
                                    border: '1px solid rgba(255, 255, 255, 0.1)'
                                  }}
                                >
                                  {item.policyAction}
                                </span>
                                {item.confidence != null && (
                                  <span className="privacy-row__confidence">
                                    {Math.round(item.confidence * 100)}% confidence
                                  </span>
                                )}
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
              );
            })()}

            {/* ── Tab: Statistics — computed from available backend fields ── */}
            {activeTab === 2 && (() => {
              const origWords = result.originalPrompt?.trim().split(/\s+/).length ?? 0;
              const optWords  = result.optimizedPrompt?.trim().split(/\s+/).length ?? 0;
              const origTok   = result.originalTokens != null ? result.originalTokens : Math.ceil(origWords * 1.33);
              const optTok    = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil(optWords * 1.33);
              const saved     = origTok - optTok;
              const pct       = result.reductionPercentage != null ? result.reductionPercentage : (origTok > 0 ? (saved / origTok * 100) : 0);
              const entities  = (result.entities || result.privacyReport || []);
              const riskScore = result.riskScore != null ? result.riskScore : 0;
              const riskLevel = result.riskLevel || 'LOW';

              return (
                <div className="opt-tab-content">
                  <div className="opt-stats-grid">
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Original Token Count</div>
                      <div className="opt-stat-card__val">{origTok}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Anonymized Baseline Count</div>
                      <div className="opt-stat-card__val" style={{ color: '#94a3b8' }}>
                        {result.anonymizedTokens != null ? result.anonymizedTokens : origTok}
                      </div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Optimized Token Count</div>
                      <div className="opt-stat-card__val" style={{ color: '#00d4aa' }}>{optTok}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Tokens Saved</div>
                      <div className="opt-stat-card__val" style={{ color: '#6c63ff' }}>{Math.max(0, saved)}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">End-to-End Token Change</div>
                      <div className="opt-stat-card__val gradient-text">{pct > 0 ? fmt(pct, 1) + '%' : '0%'}</div>
                    </div>
                    <div className="opt-stat-card">
                      <div className="opt-stat-card__label">Compression Savings</div>
                      <div className="opt-stat-card__val" style={{ color: '#00d4aa' }}>
                        {result.compressionPercentage != null && result.compressionPercentage > 0
                          ? fmt(result.compressionPercentage, 1) + '%'
                          : '0%'}
                      </div>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Shield size={13} /> Privacy Risk Level &amp; Score
                      </div>
                      <div className="opt-stat-card__val" style={{ color: riskScore > 60 ? '#ff4d6d' : riskScore > 25 ? '#f59e0b' : '#00d4aa' }}>
                        {riskScore} / 100
                        <span className="opt-stat-card__sub"> — Level: {riskLevel}</span>
                      </div>
                      <p className="opt-stat-card__desc">
                        Deterministic privacy risk calculation based on detected entity types, sensitivities, and densities.
                      </p>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Brain size={13} /> Semantic Validation
                      </div>
                      <div className="opt-stat-card__val" style={{ color: (result.semanticValid ?? true) ? '#00d4aa' : '#ff4d6d' }}>
                        {fmt(result.semanticSimilarityScore ?? 0, 1)}% similarity
                        <span className="opt-stat-card__sub"> — {result.semanticValid === false ? 'Needs review' : 'Accepted'}</span>
                      </div>
                      <p className="opt-stat-card__desc">
                        Deterministic semantic preservation check comparing the original prompt to the optimized prompt after masking.
                      </p>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Sparkles size={13} /> Grammar Correction
                      </div>
                      <div className="opt-stat-card__val" style={{ color: result.grammarCorrected ? '#00d4aa' : '#94a3b8' }}>
                        {result.grammarCorrected ? `${result.grammarCorrections?.length ?? 0} correction(s)` : 'No changes'}
                      </div>
                      <p className="opt-stat-card__desc">
                        {result.grammarCorrections?.length
                          ? result.grammarCorrections.join(' · ')
                          : 'No high-confidence spelling or grammar corrections were needed.'}
                      </p>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Lock size={13} /> Privacy Detection Summary
                      </div>
                      <div className="opt-stat-card__val" style={{ color: entities.length > 0 ? '#ff4d6d' : '#00d4aa' }}>
                        {entities.length} sensitive flag(s) detected
                      </div>
                      <p className="opt-stat-card__desc">
                        Sensitive PII entities identified by regex patterns and spaCy NER, normalized and masked before prompt optimization.
                      </p>
                    </div>

                    <div className="opt-stat-card opt-stat-card--wide">
                      <div className="opt-stat-card__label">
                        <Shield size={13} /> Post-Optimization Privacy Check
                      </div>
                      <div
                        className="opt-stat-card__val"
                        style={{ color: result.privacyValid === false ? '#ff4d6d' : '#00d4aa' }}
                      >
                        {result.privacyValid === false ? 'Review required' : 'Privacy valid'}
                      </div>
                      <p className="opt-stat-card__desc">
                        {result.leakageDetected
                          ? 'Protected data was detected after optimization and the safe anonymized prompt was returned.'
                          : 'No protected entity values were found in the optimized prompt.'}
                      </p>
                    </div>

                    {(result.targetMaxTokens != null || result.minimumSemanticScore != null) && (
                      <div className="opt-stat-card opt-stat-card--wide">
                        <div className="opt-stat-card__label">
                          <TrendingDown size={13} /> Optimization Targets
                        </div>
                        <div className="opt-stat-card__val" style={{ color: result.tokenBudgetMet === false ? '#f59e0b' : '#00d4aa' }}>
                          {result.tokenBudgetMet == null
                            ? 'Not configured'
                            : result.tokenBudgetMet ? 'Token budget met' : 'Token budget not met'}
                        </div>
                        <p className="opt-stat-card__desc">
                          {result.targetMaxTokens != null && `Max tokens: ${result.targetMaxTokens}. `}
                          {result.minimumSemanticScore != null && `Minimum semantic score: ${result.minimumSemanticScore}%. `}
                          {result.optimizationWarnings?.join(' ')}
                        </p>
                      </div>
                    )}
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
