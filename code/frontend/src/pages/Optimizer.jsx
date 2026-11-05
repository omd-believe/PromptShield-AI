import { useState, useRef, useEffect } from 'react';
import {
  Shield, Zap, Brain, Sparkles, Eye, Copy, CheckCheck,
  ArrowRight, AlertCircle, ChevronDown, ChevronUp, RotateCcw,
  FileText, TrendingDown, Lock, Sliders, Info, WifiOff
} from 'lucide-react';
import { usePwa } from '../contexts/PwaContext';
import { analyzePrompt, optimizePrompt, recordPrivacyAudit } from '../services/promptService';
import './Optimizer.css';

/* ─── Pipeline stages ─── */
const PIPELINE_STAGES = [
  { id: 'preprocess',   label: 'Preprocessing',          icon: FileText,     desc: 'Normalizing text, validating constraints…' },
  { id: 'privacy',      label: 'Privacy Detection',       icon: Eye,          desc: 'Regex + NER scanning, risk scoring, masking…' },
  { id: 'optimizer',    label: 'Prompt Optimization',     icon: TrendingDown, desc: 'Removing filler and redundant phrases…' },
  { id: 'grammar',      label: 'Grammar Polish',          icon: Sparkles,     desc: 'Applying conservative corrections…' },
  { id: 'quality',      label: 'Quality & Constraints',   icon: Shield,       desc: 'Checking placeholders, negations, constraints…' },
  { id: 'semantic',     label: 'Semantic Validation',     icon: Brain,        desc: 'Measuring lexical similarity score…' },
];

const RESULT_TABS = ['Optimized Prompt', 'Privacy Report', 'System Diagnostics'];

const fmt = (n, d = 2) => (n == null ? '—' : Number(n).toFixed(d));

const TYPE_COLOR = {
  EMAIL:        '#6366f1',
  PHONE:        '#10b981',
  PAN:          '#f59e0b',
  AADHAAR:      '#f43f5e',
  API_KEY:      '#ec4899',
  PERSON:       '#3b82f6',
  ORGANIZATION: '#8b5cf6',
  LOCATION:     '#06b6d4',
};

const typeColor = (t) => TYPE_COLOR[t?.toUpperCase()] ?? '#6366f1';

export default function Optimizer() {
  const { isOnline } = usePwa();

  /* ─── State ─── */
  const [promptText, setPromptText] = useState('');
  const [targetMaxTokens, setTargetMaxTokens] = useState('');
  const [minimumSemanticScore, setMinimumSemanticScore] = useState('');
  const [privacyPolicyText, setPrivacyPolicyText] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
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

  useEffect(() => () => clearInterval(animRef.current), []);

  /* ─── Simulate pipeline progression while waiting for API ─── */
  const runPipelineAnimation = () => {
    const totalStages = PIPELINE_STAGES.length;
    let current = 0;
    clearInterval(animRef.current);
    const interval = setInterval(() => {
      if (current < totalStages) {
        const stageIndex = current;
        setActiveStage(stageIndex);
        if (stageIndex > 0) {
          setCompletedStages(prev => (prev.includes(stageIndex - 1) ? prev : [...prev, stageIndex - 1]));
        }
        current++;
      } else {
        clearInterval(interval);
      }
    }, 500);
    animRef.current = interval;
    return interval;
  };

  /* ─── Submit handler → POST /api/v1/prompts ─── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!promptText.trim() || !isOnline) return;

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
        }).catch(() => setError('Privacy review was triggered, but the audit event could not be logged.'));
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
      setCompletedStages(PIPELINE_STAGES.map((_, i) => i));
      setActiveStage(-1);
      setResult(data);
      setActiveTab(0);
      setTimeout(() => resultRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    } catch (err) {
      clearInterval(animInterval);
      setActiveStage(-1);
      setCompletedStages([]);
      setError(
        err.response?.data?.error ||
        err.response?.data?.message ||
        'Could not connect to the AI service. Verify that the Spring Boot and FastAPI backends are running.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzePrivacy = async () => {
    if (!promptText.trim() || !isOnline) return;

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
        'Could not analyze prompt privacy. Verify that backend services are active.'
      );
    } finally {
      setAnalyzing(false);
    }
  };

  const continueWithSafePrompt = async () => {
    if (!analysisResult || !isOnline) return;
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
    }).catch(() => setError('Safe prompt approved, but audit logging failed.'));
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
    if (!result?.optimizedPrompt) return;
    navigator.clipboard.writeText(result.optimizedPrompt).then(
      () => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      },
      () => setError('Could not copy to clipboard. Please copy manually.')
    );
  };

  return (
    <div className="optimizer-page-container">
      {/* ── Header ── */}
      <header className="opt-page-header">
        <div className="opt-page-header__badge">
          <Shield size={13} style={{ color: 'var(--accent)' }} />
          <span>Multi-Stage AI Pipeline</span>
        </div>
        <h1 className="opt-page-header__title">
          Prompt <span className="gradient-text">Studio</span> &amp; Shield
        </h1>
        <p className="opt-page-header__sub">
          Paste any prompt. PromptShield strips sensitive PII, removes conversational bloat, fixes grammar, and verifies semantic fidelity.
        </p>
      </header>

      {/* ══════════════════════════════
          INPUT PANEL
      ══════════════════════════════ */}
      <div className="opt-input-panel">
        <form onSubmit={handleSubmit} className="opt-form">
          <div className="opt-input-wrap">
            <div className="opt-input-header">
              <span className="opt-input-label">
                <span className="dot dot--red" />
                Raw Input Prompt
              </span>
              <div className="opt-input-meta">
                <span className="opt-char-count">
                  {promptText.length} chars · ~{promptText.trim().split(/\s+/).filter(Boolean).length} words
                </span>
                {promptText && (
                  <button
                    type="button"
                    className="opt-clear-btn"
                    onClick={handleReset}
                    title="Clear prompt"
                  >
                    <RotateCcw size={12} />
                    <span>Clear</span>
                  </button>
                )}
              </div>
            </div>

            <textarea
              className="opt-textarea"
              placeholder={`Paste your prompt here to protect and optimize it…\n\nExample:\n"Hey ChatGPT, hope you're doing well! My email is john.doe@acme.corp and my phone is +1-555-0199. Can you please kindly help me write a concise summary of the attached Q3 performance report for our executive meeting?"`}
              value={promptText}
              onChange={(e) => {
                setPromptText(e.target.value);
                if (error) setError('');
              }}
              rows={8}
              disabled={loading || !isOnline}
            />

            {/* Advanced Controls Toggle */}
            <div className="opt-advanced-bar">
              <button
                type="button"
                className="opt-advanced-toggle"
                onClick={() => setShowAdvanced(prev => !prev)}
                aria-expanded={showAdvanced}
              >
                <Sliders size={14} />
                <span>Advanced Target &amp; Policy Controls</span>
                {showAdvanced ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
              </button>
            </div>

            {/* Collapsible Advanced Controls */}
            {showAdvanced && (
              <div className="opt-advanced-content">
                <div className="opt-targets-grid">
                  <label className="opt-field">
                    <span className="opt-field__label">Target Max Tokens</span>
                    <input
                      type="number"
                      min="1"
                      max="100000"
                      className="opt-field__input"
                      placeholder="e.g. 50 (optional)"
                      value={targetMaxTokens}
                      onChange={(e) => setTargetMaxTokens(e.target.value)}
                      disabled={loading || !isOnline}
                    />
                    <span className="opt-field__hint">Tokens are never forced if core intent would be lost.</span>
                  </label>

                  <label className="opt-field">
                    <span className="opt-field__label">Minimum Semantic Score (%)</span>
                    <input
                      type="number"
                      min="0"
                      max="100"
                      step="1"
                      className="opt-field__input"
                      placeholder="e.g. 80 (optional)"
                      value={minimumSemanticScore}
                      onChange={(e) => setMinimumSemanticScore(e.target.value)}
                      disabled={loading || !isOnline}
                    />
                    <span className="opt-field__hint">Reject output if semantic similarity drops below threshold.</span>
                  </label>
                </div>

                <label className="opt-field" style={{ marginTop: 12 }}>
                  <span className="opt-field__label">Privacy Policy JSON Overrides</span>
                  <textarea
                    rows={2}
                    className="opt-field__textarea"
                    placeholder='{"EMAIL":"MASK", "PHONE":"MASK", "API_KEY":"BLOCK", "PERSON":"ALLOW"}'
                    value={privacyPolicyText}
                    onChange={(e) => setPrivacyPolicyText(e.target.value)}
                    disabled={loading || analyzing || !isOnline}
                  />
                  <span className="opt-field__hint">
                    Valid actions: MASK, REPORT, ALLOW, BLOCK, REQUIRE_CONFIRMATION.
                  </span>
                </label>
              </div>
            )}

            {/* Input Footer & Actions */}
            <div className="opt-input-footer">
              <div className="opt-hints">
                <span className="opt-hint">
                  <Eye size={12} style={{ color: 'var(--accent)' }} />
                  Detects: Email, Phone, PAN, Aadhaar, API Keys, Person Names
                </span>
                <span className="opt-hint">
                  <Shield size={12} style={{ color: 'var(--accent-secondary)' }} />
                  Deterministic Engine + NER Protection
                </span>
              </div>

              <div className="opt-actions">
                {!isOnline && (
                  <span className="badge badge--danger">
                    <WifiOff size={12} />
                    Offline Mode
                  </span>
                )}

                <button
                  type="button"
                  className="btn-secondary opt-action-btn"
                  onClick={handleAnalyzePrivacy}
                  disabled={loading || analyzing || !promptText.trim() || !isOnline}
                  title="Inspect sensitive items without modifying the prompt text"
                >
                  {analyzing ? (
                    <>
                      <span className="spin-icon"><Eye size={15} /></span>
                      <span>Scanning…</span>
                    </>
                  ) : (
                    <>
                      <Eye size={15} />
                      <span>Inspect Privacy</span>
                    </>
                  )}
                </button>

                <button
                  type="submit"
                  className={`btn-primary opt-action-btn ${loading ? 'opt-submit-btn--loading' : ''}`}
                  disabled={loading || analyzing || !promptText.trim() || !isOnline}
                >
                  {loading ? (
                    <>
                      <span className="spin-icon"><Zap size={15} /></span>
                      <span>Shielding &amp; Optimizing…</span>
                    </>
                  ) : (
                    <>
                      <Shield size={15} />
                      <span>Shield &amp; Optimize</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </form>

        {/* Global Error Alert */}
        {error && (
          <div className="opt-error-banner" role="alert">
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* ══════════════════════════════
          PRIVACY ANALYSIS CARD (INSPECT ONLY)
      ══════════════════════════════ */}
      {analysisResult && (
        <div className="privacy-analysis-card" ref={resultRef}>
          <div className="privacy-analysis-card__header">
            <div>
              <div className="badge badge--neutral" style={{ marginBottom: 6 }}>Pre-flight Scan</div>
              <h2 className="privacy-analysis-card__title">Privacy Scan Results</h2>
              <p className="privacy-analysis-card__subtitle">
                Detected sensitive data is displayed below. No compression or grammar transformation has been performed.
              </p>
            </div>
            <div
              className="privacy-risk-badge"
              style={{
                borderColor: (analysisResult.riskScore || 0) > 60 ? 'var(--danger)' :
                             (analysisResult.riskScore || 0) > 25 ? 'var(--warning)' : 'var(--accent-secondary)'
              }}
            >
              <Shield size={16} />
              <span>{analysisResult.riskLevel} · {analysisResult.riskScore}/100 Risk</span>
            </div>
          </div>

          {(analysisResult.blocked || analysisResult.confirmationRequired || reviewPending) && (
            <div className={`privacy-review-banner ${analysisResult.blocked ? 'privacy-review-banner--blocked' : ''}`}>
              <strong>
                {analysisResult.blocked
                  ? 'Prompt Optimization Blocked by Policy'
                  : 'Confirmation Required Prior to Processing'}
              </strong>
              <p>
                {analysisResult.blocked
                  ? `Blocked categories found: ${(analysisResult.blockedLabels || []).join(', ') || 'Restricted entity types'}.`
                  : 'Review the masked values below. You can continue safely with sensitive data scrubbed.'}
              </p>
              <div className="privacy-review-actions">
                <button type="button" className="btn-primary" onClick={continueWithSafePrompt} disabled={loading}>
                  <Shield size={14} /> Continue with Safe Masked Prompt
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => {
                    setPromptText(analysisResult.anonymizedPrompt || promptText);
                    setReviewPending(false);
                    setError('');
                  }}
                  disabled={loading}
                >
                  Apply Masking to Editor
                </button>
              </div>
            </div>
          )}

          <div className="privacy-preview-box">
            <div className="privacy-preview-box__head">
              <span className="dot dot--green" />
              <span>Anonymized Preview</span>
            </div>
            <p className="privacy-preview-box__text">{analysisResult.anonymizedPrompt}</p>
          </div>

          <div className="privacy-entities-grid">
            {(analysisResult.privacyReport?.entityTypes || []).map((item) => (
              <div className="privacy-entity-card" key={item.label}>
                <span className="privacy-entity-card__type" style={{ color: typeColor(item.label) }}>
                  {item.label}
                </span>
                <strong className="privacy-entity-card__count">{item.count} detected</strong>
                <small className="privacy-entity-card__mask">Replaced with {item.maskedAs}</small>
              </div>
            ))}
            {(analysisResult.privacyReport?.totalEntities ?? 0) === 0 && (
              <p className="privacy-analysis-empty">Zero sensitive PII detected. Prompt is clean.</p>
            )}
          </div>
        </div>
      )}

      {/* ══════════════════════════════
          PIPELINE PROGRESS TRACKER
      ══════════════════════════════ */}
      {(loading || completedStages.length > 0) && (
        <div className="pipeline-tracker" aria-live="polite">
          <div className="pipeline-tracker__header">
            <span className="pipeline-tracker__title">
              {loading ? 'Pipeline Execution in Progress…' : '✅ Optimization Pipeline Complete'}
            </span>
            <span className="badge badge--safe">{completedStages.length} of {PIPELINE_STAGES.length} Stages</span>
          </div>

          <div className="pipeline-steps">
            {PIPELINE_STAGES.map((stage, i) => {
              const Icon = stage.icon;
              const isDone = completedStages.includes(i);
              const isActive = activeStage === i;
              return (
                <div
                  key={stage.id}
                  className={`pipeline-step ${isDone ? 'pipeline-step--done' : ''} ${isActive ? 'pipeline-step--active' : ''}`}
                >
                  <div className="pipeline-step__icon">
                    <Icon size={14} />
                  </div>
                  <div className="pipeline-step__info">
                    <span className="pipeline-step__label">{stage.label}</span>
                  </div>
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
          RESULTS STUDIO
      ══════════════════════════════ */}
      {result && (
        <div className="opt-results" ref={resultRef}>
          {/* Quick Metrics Bar */}
          {(() => {
            const origWords = result.originalPrompt?.trim().split(/\s+/).length ?? 0;
            const optWords  = result.optimizedPrompt?.trim().split(/\s+/).length ?? 0;
            const origTok   = result.originalTokens != null ? result.originalTokens : Math.ceil(origWords * 1.33);
            const optTok    = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil(optWords * 1.33);
            const diffTok   = origTok - optTok;
            const rawPct    = origTok > 0 ? (diffTok / origTok * 100) : 0;
            const pct       = result.reductionPercentage != null && result.reductionPercentage > 0 ? result.reductionPercentage : rawPct;
            const isIncrease = diffTok < 0;
            const riskScore = result.riskScore != null ? result.riskScore : 0;
            const riskLevel = result.riskLevel || 'LOW';
            const semanticScore = result.semanticSimilarityScore != null ? result.semanticSimilarityScore : 0;
            const semanticValid = result.semanticValid ?? true;

            return (
              <>
                <div className="opt-metrics-banner">
                  <div className="opt-metric-block">
                    <span className="opt-metric-block__label">End-to-End Change</span>
                    <span className="opt-metric-block__val" style={{ color: isIncrease ? 'var(--warning)' : 'var(--accent-secondary)' }}>
                      {pct > 0 ? `${fmt(pct, 1)}%` : isIncrease ? `+${fmt(Math.abs(rawPct), 1)}%` : '0%'}
                    </span>
                  </div>

                  <div className="opt-metric-block">
                    <span className="opt-metric-block__label">Compression Savings</span>
                    <span className="opt-metric-block__val" style={{ color: 'var(--accent)' }}>
                      {result.compressionPercentage != null && result.compressionPercentage > 0
                        ? `${fmt(result.compressionPercentage, 1)}%`
                        : '0%'}
                    </span>
                  </div>

                  <div className="opt-metric-block">
                    <span className="opt-metric-block__label">Tokens Saved</span>
                    <span className="opt-metric-block__val" style={{ color: 'var(--accent-secondary)' }}>
                      {Math.max(0, diffTok)}
                    </span>
                  </div>

                  <div className="opt-metric-block">
                    <span className="opt-metric-block__label">Privacy Risk</span>
                    <span
                      className="opt-metric-block__val"
                      style={{ color: riskScore > 60 ? 'var(--danger)' : riskScore > 25 ? 'var(--warning)' : 'var(--accent-secondary)' }}
                    >
                      {riskScore}/100 ({riskLevel})
                    </span>
                  </div>

                  <div className="opt-metric-block">
                    <span className="opt-metric-block__label">Semantic Fidelity</span>
                    <span className="opt-metric-block__val" style={{ color: semanticValid ? 'var(--accent-secondary)' : 'var(--danger)' }}>
                      {fmt(semanticScore, 1)}%
                    </span>
                  </div>
                </div>

                {result.optimizationWarnings && result.optimizationWarnings.length > 0 && (
                  <div className="opt-warning-callout">
                    <div className="opt-warning-callout__title">
                      <AlertCircle size={15} />
                      <span>Pipeline Safeguards &amp; Notices</span>
                    </div>
                    <ul className="opt-warning-callout__list">
                      {result.optimizationWarnings.map((warn, idx) => (
                        <li key={idx}>{warn}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            );
          })()}

          {/* Studio Tab Navigation */}
          {(() => {
            const count = result.privacyReport?.totalEntities ?? (Array.isArray(result.entities) ? result.entities.length : 0);
            return (
              <div className="opt-tab-bar" role="tablist">
                {RESULT_TABS.map((tab, i) => (
                  <button
                    key={tab}
                    role="tab"
                    aria-selected={activeTab === i}
                    className={`opt-tab-btn ${activeTab === i ? 'opt-tab-btn--active' : ''}`}
                    onClick={() => setActiveTab(i)}
                  >
                    <span>{tab}</span>
                    {i === 1 && count > 0 && (
                      <span className="opt-tab-badge">{count}</span>
                    )}
                  </button>
                ))}
              </div>
            );
          })()}

          {/* ── Tab 0: Before/After Comparison ── */}
          {activeTab === 0 && (() => {
            const origTok = result.originalTokens != null ? result.originalTokens : Math.ceil((result.originalPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);
            const optTok  = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil((result.optimizedPrompt?.trim().split(/\s+/).length ?? 0) * 1.33);

            return (
              <div className="opt-tab-content">
                <div className="opt-comparison-container">
                  {/* Left: Original */}
                  <div className="opt-compare-pane opt-compare-pane--orig">
                    <div className="opt-compare-pane__head">
                      <div className="opt-compare-pane__title">
                        <span className="dot dot--red" />
                        <span>Original Prompt</span>
                      </div>
                      <span className="badge badge--neutral">{origTok} tokens</span>
                    </div>
                    <div className="opt-compare-pane__body">
                      {result.originalPrompt}
                    </div>
                  </div>

                  {/* Center arrow indicator */}
                  <div className="opt-compare-divider">
                    <ArrowRight size={18} className="opt-compare-divider__icon" />
                    <span className="badge badge--safe">
                      {origTok > optTok ? `↓ ${origTok - optTok} tokens` : 'Shielded'}
                    </span>
                  </div>

                  {/* Right: Optimized */}
                  <div className="opt-compare-pane opt-compare-pane--opt">
                    <div className="opt-compare-pane__head">
                      <div className="opt-compare-pane__title">
                        <span className="dot dot--green" />
                        <span>Shielded &amp; Optimized</span>
                      </div>
                      <span className="badge badge--safe">{optTok} tokens</span>
                    </div>
                    <div className="opt-compare-pane__body">
                      {result.optimizedPrompt}
                    </div>
                  </div>
                </div>

                <div className="opt-copy-row">
                  <button className="btn-primary opt-copy-btn" onClick={handleCopy}>
                    {copied ? (
                      <>
                        <CheckCheck size={16} />
                        <span>Copied to Clipboard!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={16} />
                        <span>Copy Shielded Prompt</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })()}

          {/* ── Tab 1: Privacy Report ── */}
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
                <div className="privacy-metrics-grid">
                  <div className="privacy-stat-box">
                    <span className="privacy-stat-box__label">Entities Detected</span>
                    <strong className="privacy-stat-box__val" style={{ color: entitiesDetected > 0 ? 'var(--danger)' : 'var(--accent-secondary)' }}>
                      {entitiesDetected}
                    </strong>
                  </div>
                  <div className="privacy-stat-box">
                    <span className="privacy-stat-box__label">Masked Placeholders</span>
                    <strong className="privacy-stat-box__val" style={{ color: 'var(--accent-secondary)' }}>
                      {entitiesMasked}
                    </strong>
                  </div>
                  <div className="privacy-stat-box">
                    <span className="privacy-stat-box__label">Residual Leakage</span>
                    <strong className="privacy-stat-box__val" style={{ color: result.leakageDetected ? 'var(--danger)' : 'var(--accent-secondary)' }}>
                      {residualLeakage}
                    </strong>
                  </div>
                  <div className="privacy-stat-box">
                    <span className="privacy-stat-box__label">Validation Status</span>
                    <strong className="privacy-stat-box__val" style={{ color: privacyValid ? 'var(--accent-secondary)' : 'var(--danger)' }}>
                      {privacyValid ? 'Passed' : 'Failed'}
                    </strong>
                  </div>
                  <div className="privacy-stat-box">
                    <span className="privacy-stat-box__label">Risk Index</span>
                    <strong className="privacy-stat-box__val" style={{ color: riskScore > 60 ? 'var(--danger)' : riskScore > 25 ? 'var(--warning)' : 'var(--accent-secondary)' }}>
                      {riskScore}/100 ({riskLevel})
                    </strong>
                  </div>
                </div>

                {entities.length === 0 ? (
                  <div className="privacy-clean-box">
                    <Shield size={36} style={{ color: 'var(--accent-secondary)' }} />
                    <h4>100% Clean Prompt</h4>
                    <p>No sensitive PII (emails, phone numbers, identifiers, or secrets) were found.</p>
                  </div>
                ) : (
                  <div className="privacy-rows-list">
                    <div className="privacy-rows-list__head">
                      <Lock size={14} />
                      <span>Evaluated Sensitive Items &amp; Assigned Policy Actions</span>
                    </div>

                    {entities.map((item, i) => {
                      const color = typeColor(item.type);
                      const isOpen = expandedFlag === i;
                      return (
                        <div key={i} className="privacy-entity-row">
                          <div
                            className="privacy-entity-row__summary"
                            onClick={() => setExpandedFlag(isOpen ? null : i)}
                          >
                            <div className="privacy-entity-row__chips">
                              <span
                                className="privacy-type-tag"
                                style={{ background: `${color}18`, color, borderColor: `${color}35` }}
                              >
                                {item.type}
                              </span>
                              <span className="privacy-masked-tag">{item.masked}</span>
                              <span
                                className="badge"
                                style={{
                                  background: item.policyAction === 'ALLOW' ? 'rgba(16, 185, 129, 0.15)' :
                                              item.policyAction === 'BLOCK' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(255, 255, 255, 0.08)',
                                  color: item.policyAction === 'ALLOW' ? 'var(--accent-secondary)' :
                                         item.policyAction === 'BLOCK' ? 'var(--danger)' : 'var(--text-secondary)'
                                }}
                              >
                                {item.policyAction}
                              </span>
                              {item.confidence != null && (
                                <span className="privacy-confidence">
                                  {Math.round(item.confidence * 100)}% match
                                </span>
                              )}
                            </div>
                            <button className="privacy-expand-btn" aria-label="Expand entity details">
                              {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </button>
                          </div>

                          {isOpen && (
                            <div className="privacy-entity-row__detail">
                              <div className="privacy-detail-col">
                                <span className="privacy-detail-label">Original Extracted Text:</span>
                                <code className="privacy-detail-val privacy-detail-val--danger">{item.value}</code>
                              </div>
                              <div className="privacy-detail-col">
                                <span className="privacy-detail-label">Neutralized Replacement:</span>
                                <code className="privacy-detail-val privacy-detail-val--safe">{item.masked}</code>
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

          {/* ── Tab 2: System Diagnostics & Stats ── */}
          {activeTab === 2 && (() => {
            const origWords = result.originalPrompt?.trim().split(/\s+/).length ?? 0;
            const optWords  = result.optimizedPrompt?.trim().split(/\s+/).length ?? 0;
            const origTok   = result.originalTokens != null ? result.originalTokens : Math.ceil(origWords * 1.33);
            const optTok    = result.optimizedTokens != null ? result.optimizedTokens : Math.ceil(optWords * 1.33);
            const saved     = origTok - optTok;
            const pct       = result.reductionPercentage != null ? result.reductionPercentage : (origTok > 0 ? (saved / origTok * 100) : 0);
            const riskScore = result.riskScore != null ? result.riskScore : 0;
            const riskLevel = result.riskLevel || 'LOW';

            return (
              <div className="opt-tab-content">
                <div className="diagnostics-grid">
                  <div className="diag-card">
                    <span className="diag-card__label">Input Token Count</span>
                    <strong className="diag-card__val">{origTok}</strong>
                  </div>
                  <div className="diag-card">
                    <span className="diag-card__label">Anonymized Baseline</span>
                    <strong className="diag-card__val" style={{ color: 'var(--text-muted)' }}>
                      {result.anonymizedTokens != null ? result.anonymizedTokens : origTok}
                    </strong>
                  </div>
                  <div className="diag-card">
                    <span className="diag-card__label">Optimized Token Count</span>
                    <strong className="diag-card__val" style={{ color: 'var(--accent-secondary)' }}>
                      {optTok}
                    </strong>
                  </div>
                  <div className="diag-card">
                    <span className="diag-card__label">Tokens Saved</span>
                    <strong className="diag-card__val" style={{ color: 'var(--accent)' }}>
                      {Math.max(0, saved)}
                    </strong>
                  </div>
                  <div className="diag-card">
                    <span className="diag-card__label">End-to-End Change</span>
                    <strong className="diag-card__val gradient-text">
                      {pct > 0 ? `${fmt(pct, 1)}%` : '0%'}
                    </strong>
                  </div>
                  <div className="diag-card">
                    <span className="diag-card__label">Compression Savings</span>
                    <strong className="diag-card__val" style={{ color: 'var(--accent-secondary)' }}>
                      {result.compressionPercentage != null && result.compressionPercentage > 0
                        ? `${fmt(result.compressionPercentage, 1)}%`
                        : '0%'}
                    </strong>
                  </div>

                  <div className="diag-card diag-card--wide">
                    <div className="diag-card__header">
                      <Shield size={15} style={{ color: 'var(--accent)' }} />
                      <span>Privacy Risk Scoring</span>
                    </div>
                    <div
                      className="diag-card__val-row"
                      style={{ color: riskScore > 60 ? 'var(--danger)' : riskScore > 25 ? 'var(--warning)' : 'var(--accent-secondary)' }}
                    >
                      {riskScore} / 100 — Severity: {riskLevel}
                    </div>
                    <p className="diag-card__desc">
                      Computed deterministically based on sensitive entity occurrences, type weightings, and token density.
                    </p>
                  </div>

                  <div className="diag-card diag-card--wide">
                    <div className="diag-card__header">
                      <Brain size={15} style={{ color: 'var(--accent-secondary)' }} />
                      <span>Semantic Fidelity Assessment</span>
                    </div>
                    <div
                      className="diag-card__val-row"
                      style={{ color: (result.semanticValid ?? true) ? 'var(--accent-secondary)' : 'var(--danger)' }}
                    >
                      {fmt(result.semanticSimilarityScore ?? 0, 1)}% Similarity — Status: {result.semanticValid === false ? 'Review Needed' : 'Passed'}
                    </div>
                    <p className="diag-card__desc">
                      Measures semantic preservation between original prompt context and sanitized output after masking.
                    </p>
                  </div>

                  <div className="diag-card diag-card--wide">
                    <div className="diag-card__header">
                      <Sparkles size={15} style={{ color: 'var(--info)' }} />
                      <span>Grammar &amp; Phrasing Polish</span>
                    </div>
                    <div className="diag-card__val-row">
                      {result.grammarCorrected ? `${result.grammarCorrections?.length ?? 0} correction(s) applied` : 'No grammar modifications needed'}
                    </div>
                    <p className="diag-card__desc">
                      {result.grammarCorrections?.length
                        ? result.grammarCorrections.join(' · ')
                        : 'High-confidence spelling and structural checks completed without edits.'}
                    </p>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
