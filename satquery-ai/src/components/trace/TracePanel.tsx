import type { LiveTraceItem } from '../../types';

interface Props {
  items: LiveTraceItem[];
  queryUnderstanding?: { taskType: string; target: string; reasoning: string };
  strategyMessage?: string;
  planUpdateMessage?: string;
  lowEvidenceAlert?: unknown;
}

const STATUS_LABEL: Record<string, string> = {
  success: 'Done',
  error:   'Error',
  warning: 'Warning',
  running: 'Running',
  pending: 'Pending',
  skipped: 'Skipped',
};

export default function TracePanel({ items, strategyMessage, planUpdateMessage }: Props) {
  return (
    <div className="space-y-3">
      {/* Strategy / plan messages */}
      {strategyMessage && (
        <p className="notice-info text-xs">{strategyMessage}</p>
      )}
      {planUpdateMessage && (
        <p className="notice text-xs">{planUpdateMessage}</p>
      )}

      {/* Empty state */}
      {items.length === 0 && (
        <div className="empty-trace">
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center"
              style={{ background: 'var(--surface-subtle)' }}
            >
              <span style={{ fontSize: 16 }}>⏱</span>
            </div>
            <p className="subtle">No tools executed yet.</p>
            <p className="subtle" style={{ fontSize: 11 }}>Steps appear as the backend reports them.</p>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="trace-timeline space-y-2">
        {items.map(item => (
          <details
            key={item.step_index}
            className="trace-step"
            data-status={item.status}
          >
            <summary style={{ listStyle: 'none', cursor: 'pointer' }}>
              <div className="flex items-start gap-2">
                {/* Step number badge */}
                <span className="trace-step-num flex-shrink-0 mt-0.5">
                  {item.status === 'running'
                    ? <span className="running-dot" />
                    : String(item.step_index + 1).padStart(2, '0')}
                </span>

                {/* Name + status */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="font-semibold text-xs truncate"
                      style={{ color: 'var(--text-primary)' }}
                    >
                      {item.step_name || item.tool_name}
                    </span>
                    <span className="status" data-tone={
                      item.status === 'error'   ? 'error'   :
                      item.status === 'warning' ? 'warning' :
                      item.status === 'success' ? 'success' : undefined
                    }>
                      {STATUS_LABEL[item.status] ?? item.status}
                    </span>
                    {item.is_auto_inserted && (
                      <span className="badge badge-orange" style={{ fontSize: 9 }}>Auto-inserted</span>
                    )}
                  </div>
                  <p className="subtle mt-0.5" style={{ fontSize: 11 }}>
                    {item.execution_time_ms !== undefined
                      ? `${item.execution_time_ms} ms`
                      : 'Duration pending'}
                    {(item.warnings?.length ?? 0) > 0 && ` · ${item.warnings!.length} warning(s)`}
                  </p>
                </div>
              </div>
            </summary>

            {/* Expanded detail */}
            <div className="mt-3 space-y-2 pl-7" style={{ borderTop: '1px solid var(--border)', paddingTop: 10 }}>
              {item.message && (
                <p className="text-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                  {item.message}
                </p>
              )}
              <dl className="detail-list">
                <dt>Tool</dt>       <dd className="technical">{item.tool_name}</dd>
                <dt>Mode</dt>       <dd>{item.execution_mode ?? 'Not reported'}</dd>
                <dt>Provenance</dt> <dd>{item.input_provenance ?? 'Not reported'}</dd>
                <dt>Algorithm</dt>  <dd>{item.algorithm ?? 'Not reported'}</dd>
                <dt>Evidence</dt>   <dd>{item.evidence_excludable ? 'Excluded from scoring' : 'Eligible for scoring'}</dd>
                {typeof item.metadata?.input_index === 'number' && (
                  <><dt>Image index</dt><dd>{(item.metadata.input_index as number) + 1}</dd></>
                )}
              </dl>

              {typeof item.metadata?.injection_reason === 'string' && (
                <p className="notice" style={{ fontSize: 11 }}>{item.metadata.injection_reason}</p>
              )}
              {item.warnings?.map((w, i) => (
                <p key={i} className="notice" style={{ fontSize: 11 }}>{w}</p>
              ))}

              <details>
                <summary>Computed values &amp; input hashes</summary>
                <pre className="technical whitespace-pre-wrap mt-2 p-2 rounded" style={{ background: 'var(--surface-subtle)', fontSize: 10 }}>
                  {JSON.stringify({
                    result: item.result,
                    metadata: Object.fromEntries(
                      Object.entries(item.metadata ?? {}).filter(([k]) => !k.includes('b64'))
                    ),
                  }, null, 2)}
                </pre>
              </details>
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
