import { streamEvents } from './stream';
import type { AnalysisOutcome, ThresholdPolicy, ImageMetadata, EvidenceBreakdown } from "../types";
// SatQuery AI — API Client
// Handles all communication with the FastAPI backend, including SSE streaming.

import type {
  DemoScenario, SSEEvent, CompletedEvent, LiveTraceItem,
  VisualOutput, ConfidenceLevel, EvidenceStatus,
} from '../types';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

// ─── Demo Scenarios ───────────────────────────────────────────────────────────

export async function fetchDemoScenarios(signal?: AbortSignal): Promise<DemoScenario[]> {
  const res = await fetch(`${BASE_URL}/api/demo/scenarios`, { signal });
  if (!res.ok) throw new Error('Failed to fetch demo scenarios');
  const data = await res.json();
  return data.scenarios;
}

// ─── Real Imagery by Coordinates ───────────────────────────────────────────

export interface RealImageryParams {
  bbox: [number, number, number, number]; // [west, south, east, north]
  dateBefore: string;  // "YYYY-MM-DD"
  dateAfter: string;   // "YYYY-MM-DD"
  maxCloudPct?: number;
}

export interface RealImageryScene {
  image_b64: string;
  date: string;
  cloud_pct: number;
  scene_id: string;
}

export interface RealImageryResult {
  before: RealImageryScene;
  after: RealImageryScene;
  warnings: string[];
}

export async function fetchRealImagery(params: RealImageryParams, signal?: AbortSignal): Promise<RealImageryResult> {
  const res = await fetch(`${BASE_URL}/api/real-imagery`, {
    signal,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bbox: params.bbox,
      date_before: params.dateBefore,
      date_after: params.dateAfter,
      max_cloud_pct: params.maxCloudPct ?? 35,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
    const msg = typeof err.detail === 'object' ? err.detail.error : err.detail;
    throw new Error(msg || `Server error ${res.status}`);
  }
  return res.json();
}

// ─── Analysis result state ─────────────────────────────────────────────────

export interface AnalysisResult {
  analysisId: string;
  confidence: number;
  confidenceLevel: ConfidenceLevel;
  evidenceStatus: EvidenceStatus;
  finalAnswer: string;
  evidencePoints: string[];
  visualOutputs: VisualOutput[];
  conflicts: unknown[];
  // Evidence breakdown from evidence.py
  evidenceBreakdown?: EvidenceBreakdown;
  evidenceFormula?: string;
  evidenceInterpretation?: string;
  lowEvidence?: boolean;
  secondaryEvidenceStatus?: string;
  hasRealImages?: boolean;
  auditHash?: string;
  outcome?: AnalysisOutcome;
  limitations?: string[];
  verified?: boolean;
  scoreKind?: string;
  thresholdPolicy?: ThresholdPolicy;
  inputMetadata?: ImageMetadata[];
}

// ─── SSE Streaming Analysis ────────────────────────────────────────────────

export interface AnalysisCallbacks {
  onInputsResolved?: (inputs: ImageMetadata[], isDemo: boolean) => void;
  onSessionCreated?: (id: string) => void;
  onQueryUnderstood?: (detail: Record<string, unknown>, message: string) => void;
  onStrategySelected?: (detail: Record<string, unknown>, message: string) => void;
  onToolStart?: (item: Omit<LiveTraceItem, 'status'>) => void;
  onToolDone?: (item: LiveTraceItem) => void;
  onPlanUpdated?: (message: string, newPlan: string[]) => void;
  onThumbnails?: (thumbnails: string[]) => void;
  onLowEvidence?: (evidenceStrength: number, message: string, secondaryStatus: string, secondaryReason: string) => void;
  onCompleted?: (result: AnalysisResult) => void;
  onError?: (error: string) => void;
}

export async function runAnalysis(query: string, demoScenario: string | null, callbacks: AnalysisCallbacks,
  uploadedImages: string[] = [], imageMetadata: Partial<ImageMetadata>[] = [], signal?: AbortSignal): Promise<void> {
  await runStream('/api/analyze', { query, demo_scenario: demoScenario, image_ids: [], uploaded_images: uploadedImages, image_metadata: imageMetadata }, callbacks, signal);
}
async function runStream(path: string, payload: unknown, callbacks: AnalysisCallbacks, signal?: AbortSignal) {
  try { await streamEvents(`${BASE_URL}${path}`, payload, event => handleEvent(event as SSEEvent, callbacks), signal); }
  catch (error) { if (!signal?.aborted) callbacks.onError?.(error instanceof Error ? error.message : 'Analysis request failed.'); }
}

function handleEvent(event: SSEEvent, callbacks: AnalysisCallbacks) {
  switch (event.type) {
    case 'inputs_resolved':
      callbacks.onInputsResolved?.((event.inputs as { metadata: ImageMetadata }[]).map(i => i.metadata), Boolean(event.is_demo));
      break;
    case 'session_created':
      callbacks.onSessionCreated?.(event.analysis_id as string);
      break;

    case 'step': {
      const step = event.step as string;
      const status = event.status as string;
      const message = event.message as string;
      const detail = event.detail as Record<string, unknown> | undefined;
      if (step === 'query_understanding' && status === 'done') {
        callbacks.onQueryUnderstood?.(detail ?? {}, message);
      } else if (step === 'strategy_selection' && status === 'done') {
        callbacks.onStrategySelected?.(detail ?? {}, message);
      }
      break;
    }

    case 'tool_start': {
      callbacks.onToolStart?.({
        step_index: event.step_index as number,
        tool_name: event.tool_name as string,
        step_name: event.step_name as string,
        description: event.description as string,
        is_auto_inserted: event.is_auto_inserted as boolean,
      });
      break;
    }

    case 'tool_done': {
      callbacks.onToolDone?.({
        step_index: event.step_index as number,
        tool_name: event.tool_name as string,
        step_name: event.step_name as string,
        description: event.description as string,
        status: event.status as LiveTraceItem['status'],
        confidence: event.confidence as number,
        message: event.message as string,
        result: event.result as Record<string, unknown>,
        visual_output: event.visual_output as string | undefined,
        visual_type: event.visual_type as string | undefined,
        metadata: event.metadata as Record<string, unknown> | undefined,
        execution_time_ms: event.execution_time_ms as number,
        is_auto_inserted: event.is_auto_inserted as boolean,
        // Provenance fields
        execution_mode: event.execution_mode as LiveTraceItem['execution_mode'],
        input_provenance: event.input_provenance as LiveTraceItem['input_provenance'],
        algorithm: event.algorithm as string | undefined,
        registration_quality: event.registration_quality as LiveTraceItem['registration_quality'],
        evidence_excludable: event.evidence_excludable as boolean | undefined,
        warnings: event.warnings as string[] | undefined,
      });
      break;
    }

    case 'plan_updated':
      callbacks.onPlanUpdated?.(
        event.message as string,
        event.new_plan as string[],
      );
      break;

    case 'thumbnails':
      callbacks.onThumbnails?.(event.thumbnails as string[]);
      break;

    case 'low_evidence':
      callbacks.onLowEvidence?.(
        event.evidence_strength as number,
        event.message as string,
        event.secondary_evidence_status as string,
        event.secondary_evidence_reason as string,
      );
      break;

    case 'completed': {
      const c = event as unknown as CompletedEvent;
      callbacks.onCompleted?.({
        analysisId: c.analysis_id,
        confidence: c.confidence,
        confidenceLevel: c.confidence_level,
        evidenceStatus: c.evidence_status,
        finalAnswer: c.final_answer,
        evidencePoints: c.evidence_points,
        visualOutputs: c.visual_outputs,
        conflicts: c.conflicts,
        evidenceBreakdown: c.evidence_breakdown,
        evidenceFormula: c.evidence_formula,
        evidenceInterpretation: c.evidence_interpretation,
        lowEvidence: c.low_evidence,
        secondaryEvidenceStatus: c.secondary_evidence_status,
        hasRealImages: c.has_real_images,
        auditHash: c.audit_hash,
        outcome: c.outcome,
        limitations: c.limitations,
        verified: c.verified,
        scoreKind: c.score_kind,
        thresholdPolicy: c.threshold_policy,
        inputMetadata: c.inputs?.map(i => i.metadata),
      });
      break;
    }
  }
}

export async function runDemoScenario(scenarioId: string, query: string | null, callbacks: AnalysisCallbacks, signal?: AbortSignal): Promise<void> {
  await runStream('/api/demo/run', { scenario_id: scenarioId, query }, callbacks, signal);
}
