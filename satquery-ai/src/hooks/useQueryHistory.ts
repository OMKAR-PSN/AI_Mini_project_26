import { useState, useCallback, useRef } from 'react';
import type { AnalysisOutcome } from '../types';
export interface HistoryEntry { id: string; query: string; scenarioId: string | null; confidence: number; confidenceLevel: string; finalAnswer: string; timestamp: number; aoiName?: string; outcome?: AnalysisOutcome; }
const KEY = 'satquery_history';
export function parseHistory(raw: string | null): HistoryEntry[] {
  try { const data: unknown = JSON.parse(raw ?? '[]'); if (!Array.isArray(data)) return []; return data.filter((x): x is HistoryEntry => Boolean(x) && typeof x === 'object' && typeof x.id === 'string' && typeof x.query === 'string' && (x.scenarioId === null || typeof x.scenarioId === 'string') && typeof x.finalAnswer === 'string' && typeof x.confidence === 'number' && Number.isFinite(x.confidence) && x.confidence >= 0 && x.confidence <= 1 && typeof x.confidenceLevel === 'string' && (x.aoiName === undefined || typeof x.aoiName === 'string') && (x.outcome === undefined || ['completed_supported', 'completed_partial', 'abstained', 'unsupported', 'failed'].includes(x.outcome)) && typeof x.timestamp === 'number' && Number.isFinite(x.timestamp)).slice(0, 10); } catch { return []; }
}
function load() { try { return parseHistory(localStorage.getItem(KEY)); } catch { return []; } }
export function useQueryHistory() {
  const [history, setHistory] = useState<HistoryEntry[]>(load); const current = useRef(history); const [storageError, setStorageError] = useState('');
  const persist = useCallback((entries: HistoryEntry[]) => { current.current = entries; setHistory(entries); try { localStorage.setItem(KEY, JSON.stringify(entries)); setStorageError(''); } catch { setStorageError('Browser storage is unavailable. History is kept only for this session.'); } }, []);
  const addEntry = useCallback((entry: Omit<HistoryEntry, 'id' | 'timestamp'>) => persist([{ ...entry, id: crypto.randomUUID(), timestamp: Date.now() }, ...current.current].slice(0, 10)), [persist]);
  const clearHistory = useCallback(() => persist([]), [persist]); return { history, addEntry, clearHistory, storageError };
}
