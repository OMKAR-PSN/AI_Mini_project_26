import type { EvidenceStatus, EvidenceBreakdown, ThresholdPolicy } from '../../types';

interface Props {
  evidenceStatus: EvidenceStatus;
  evidencePoints: string[];
  confidence: number;
  conflicts?: unknown[];
  evidenceBreakdown?: EvidenceBreakdown;
  evidenceFormula?: string;
  evidenceInterpretation?: string;
  hasRealImages?: boolean;
  thresholdPolicy?: ThresholdPolicy;
}

const STATUS_TONE: Record<EvidenceStatus, string> = {
  consistent:   'success',
  conflicting:  'error',
  insufficient: 'warning',
  pending:      '',
};

export default function EvidencePanel({
  evidenceStatus, evidencePoints, confidence, evidenceBreakdown,
  evidenceFormula, evidenceInterpretation, thresholdPolicy,
}: Props) {
  const pct = Math.round(confidence * 100);
  const barColor = 'var(--accent)'; // Magnitude only; semantic status comes from the backend.

  return (
    <div className="space-y-4">
      {/* Score header */}
      <div className="flex justify-between items-center gap-3">
        <h2 className="panel-title">Heuristic evidence</h2>
        <span
          className="status"
          data-tone={STATUS_TONE[evidenceStatus] || undefined}
          style={{ textTransform: 'capitalize' }}
        >
          {evidenceStatus}
        </span>
      </div>

      {/* Visual confidence bar */}
      <div>
        <div className="flex justify-between mb-1.5" style={{ fontSize: 11 }}>
          <span className="subtle">Evidence strength</span>
          <span className="font-bold technical" style={{ color: barColor }}>{pct}%</span>
        </div>
        <div className="confidence-bar">
          <div
            className="confidence-bar-fill"
            style={{ width: `${pct}%`, background: barColor }}
          />
        </div>
      </div>

      <p className="subtle">
        Independent evidence: {evidenceStatus}. High scores do not establish scientific verification.
      </p>

      {/* Factor breakdown */}
      {evidenceBreakdown
        ? Object.entries(evidenceBreakdown).map(([key, factor]) => factor && (
          <details key={key} style={{ borderTop: '1px solid var(--border)', paddingTop: 8 }}>
            <summary className="flex justify-between gap-2">
              <span style={{ fontSize: 12 }}>{key.replaceAll('_', ' ')}</span>
              <span
                className="technical font-semibold"
                style={{
                  color: factor.score === null ? 'var(--text-muted)' :
                    'var(--accent)',
                  fontSize: 11,
                }}
              >
                {factor.score === null ? 'N/A' : `${Math.round(factor.score * 100)}%`}
              </span>
            </summary>
            <div className="mt-2 space-y-1.5 pl-2">
              {factor.score !== null && (
                <div className="confidence-bar" style={{ height: 4 }}>
                  <div
                    className="confidence-bar-fill"
                    style={{
                      width: `${Math.round(factor.score * 100)}%`,
                      background: 'var(--accent)',
                    }}
                  />
                </div>
              )}
              <p className="subtle">{factor.reason}</p>
              <p className="technical" style={{ color: 'var(--text-muted)' }}>
                Weight: {factor.weight.toFixed(4)}
              </p>
            </div>
          </details>
        ))
        : <p className="subtle">No factor breakdown was returned.</p>
      }

      {/* Threshold policy */}
      {thresholdPolicy && (
        <dl className="detail-list" style={{ borderTop: '1px solid var(--border)', paddingTop: 8 }}>
          <dt>Runtime low evidence</dt><dd>{thresholdPolicy.low_evidence}</dd>
          <dt>Research threshold</dt>  <dd>{thresholdPolicy.research} · separate policy</dd>
        </dl>
      )}

      {/* Sources */}
      <details>
        <summary>Sources &amp; scoring formula</summary>
        <div className="mt-2 space-y-2">
          {evidencePoints.length
            ? evidencePoints.map(point => (
                <p key={point} className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>{point}</p>
              ))
            : <p className="subtle">No eligible supporting sources.</p>
          }
          <p className="technical mt-1" style={{ background: 'var(--surface-subtle)', padding: '6px 8px', borderRadius: 4, fontSize: 10 }}>
            {evidenceFormula ?? 'Formula not returned.'}
          </p>
          {evidenceInterpretation && (
            <p className="subtle">{evidenceInterpretation}</p>
          )}
        </div>
      </details>
    </div>
  );
}
