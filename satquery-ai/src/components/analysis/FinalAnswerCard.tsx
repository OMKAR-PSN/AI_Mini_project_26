import { useState } from 'react';
import type { AnalysisOutcome, ConfidenceLevel, EvidenceStatus, ImageMetadata, LiveTraceItem, VisualOutput } from '../../types';
import EvidenceTrailModal from '../evidence/EvidenceTrailModal';

const OUTCOMES: Record<AnalysisOutcome, { label: string; tone: string }> = {
  completed_supported: { label: 'Supported computation', tone: 'success' },
  completed_partial:   { label: 'Partial result',         tone: 'warning' },
  abstained:           { label: 'Abstained · insufficient evidence', tone: 'warning' },
  unsupported:         { label: 'Unsupported request',    tone: 'warning' },
  failed:              { label: 'Analysis failed',        tone: 'error' },
};

interface Props {
  query: string;
  answer: string;
  confidence: number;
  confidenceLevel: ConfidenceLevel;
  evidenceStatus: EvidenceStatus;
  evidencePoints: string[];
  analysisId?: string;
  traceItems?: LiveTraceItem[];
  images?: ImageMetadata[];
  visualOutputs?: VisualOutput[];
  auditHash?: string;
  outcome?: AnalysisOutcome;
  lowEvidence?: boolean;
  limitations?: string[];
  verified?: boolean;
  scoreKind?: string;
}

function confidenceColor(level: ConfidenceLevel): string {
  return level === 'high' ? 'var(--success)' : level === 'medium' ? 'var(--warning)' : 'var(--danger)';
}

export default function FinalAnswerCard({
  query, answer, confidence, confidenceLevel, evidenceStatus, evidencePoints,
  analysisId = '', traceItems = [], images = [], visualOutputs = [],
  auditHash, outcome, lowEvidence, limitations = [], verified, scoreKind,
}: Props) {
  const [open, setOpen] = useState(false);
  const state = outcome ? OUTCOMES[outcome] : { label: 'Outcome not reported', tone: 'warning' };
  const pct = Math.round(confidence * 100);
  const summary = limitations.reduce((text, item) => text.replace(item, ''), answer).trim();

  return (
    <section className="panel">
      {/* Header */}
      <div className="panel-header">
        <h2 className="panel-title">Analysis outcome</h2>
        <span className="status" data-tone={state.tone}>{state.label}</span>
      </div>

      <div className="p-4 space-y-4">
        {/* Confidence meter */}
        <div>
          <div className="flex justify-between items-center mb-1.5">
            <span className="field-label" style={{ marginBottom: 0 }}>Evidence strength</span>
            <span
              className="font-bold text-sm"
              style={{ color: confidenceColor(confidenceLevel), fontFamily: 'JetBrains Mono, monospace' }}
            >
              {pct}%
              <span className="subtle ml-1" style={{ fontSize: 10, fontFamily: 'inherit' }}>
                ({confidenceLevel})
              </span>
            </span>
          </div>
          <div className="confidence-bar">
            <div
              className="confidence-bar-fill"
              style={{
                width: `${pct}%`,
                background: confidenceColor(confidenceLevel),
              }}
            />
          </div>
          <p className="subtle mt-1" style={{ fontSize: 10 }}>
            {scoreKind === 'heuristic_evidence'
              ? 'Heuristic score — not a calibrated probability.'
              : `Score method: ${scoreKind ?? 'not reported'}.`}
          </p>
        </div>

        {/* Main answer */}
        <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
          {summary || 'No supported findings were returned for this request.'}
        </p>

        {/* Verification notice */}
        <p className="subtle">
          {verified === true
            ? '✓ Backend reports verified status.'
            : verified === false
            ? '✗ Not independently verified.'
            : 'Verification status not reported.'}
        </p>

        {/* Limitations */}
        {limitations.length > 0 && (
          <div>
            <h3 className="field-label">Limitations &amp; missing capabilities</h3>
            <ul
              className="list-disc pl-4 space-y-1.5 mt-1"
              style={{ fontSize: 12, color: 'var(--text-secondary)' }}
            >
              {limitations.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
        )}

        {/* Low evidence alert */}
        {lowEvidence && (
          <p className="notice">
            Backend flags low evidence. No analyst review or secondary verification is implied.
          </p>
        )}

        {/* Audit digest (collapsible) */}
        <details>
          <summary>Request &amp; audit digest</summary>
          <div className="mt-2 space-y-2">
            <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{query}</p>
            <p className="technical">Run: {analysisId}</p>
            {auditHash ? (
              <>
                <p className="subtle" style={{ fontSize: 11 }}>
                  SHA-256 tamper-evident digest. Not a digital signature or proof of authenticity.
                </p>
                <p
                  className="technical p-2 rounded"
                  style={{ background: 'var(--surface-subtle)', fontSize: 10, wordBreak: 'break-all' }}
                >
                  {auditHash}
                </p>
              </>
            ) : (
              <p className="subtle">No audit digest returned.</p>
            )}
          </div>
        </details>

        {/* CTA */}
        <button
          className="btn-ghost w-full text-xs"
          onClick={() => setOpen(true)}
        >
          Inspect full evidence record
        </button>
      </div>

      <EvidenceTrailModal
        open={open}
        onClose={() => setOpen(false)}
        query={query}
        analysisId={analysisId}
        images={images}
        traceItems={traceItems}
        finalAnswer={answer}
        confidence={confidence}
        confidenceLevel={confidenceLevel}
        evidenceStatus={evidenceStatus}
        evidencePoints={evidencePoints}
        visualOutputs={visualOutputs}
        verified={verified}
        outcome={outcome}
        limitations={limitations}
      />
    </section>
  );
}
