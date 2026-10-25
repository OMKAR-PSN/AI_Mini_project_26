import { useEffect, useRef, useState } from 'react';
import { Satellite, RotateCcw, FileDown } from 'lucide-react';
import type { DemoScenario, ImageMetadata, LiveTraceItem, VisualOutput } from '../types';
import { fetchDemoScenarios, runAnalysis, runDemoScenario, type AnalysisCallbacks, type AnalysisResult } from '../api/client';
import QueryBox from '../components/query/QueryBox';
import SceneSelector, { ImageMetaPanel } from '../components/query/SceneSelector';
import AOIMapSelector, { type AOISelection, type FetchedRealImages } from '../components/map/AOIMapSelector';
import VisualOutputsGrid from '../components/visualization/VisualOutputs';
import FinalAnswerCard from '../components/analysis/FinalAnswerCard';
import EvidencePanel from '../components/evidence/EvidencePanel';
import TracePanel from '../components/trace/TracePanel';
import QueryHistoryPanel from '../components/history/QueryHistoryPanel';
import { useQueryHistory, type HistoryEntry } from '../hooks/useQueryHistory';
import { generateAnalysisReport } from '../utils/reportGenerator';

type Phase = 'setup' | 'running' | 'done' | 'error';
export default function AnalysisPage({ initialScenario = null }: { initialScenario?: string | null }) {
  const [scenarios, setScenarios] = useState<DemoScenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<string | null>(initialScenario);
  const [query, setQuery] = useState('');
  const [phase, setPhase] = useState<Phase>('setup');
  const [sourceTab, setSourceTab] = useState('scene');
  const [mobileSection, setMobileSection] = useState('setup');
  const [loading, setLoading] = useState(true);
  const [sceneError, setSceneError] = useState('');
  const [error, setError] = useState('');
  const [realImages, setRealImages] = useState<FetchedRealImages | null>(null);
  const [aoi, setAOI] = useState<AOISelection | null>(null);
  const [inputMetadata, setInputMetadata] = useState<ImageMetadata[]>([]);
  const [thumbnails, setThumbnails] = useState<string[]>([]);
  const [isDemo, setIsDemo] = useState(false);
  const [traceItems, setTraceItems] = useState<LiveTraceItem[]>([]);
  const [strategy, setStrategy] = useState('');
  const [insertion, setInsertion] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [runQuery, setRunQuery] = useState('');
  const [runAOI, setRunAOI] = useState<string>();
  const [exporting, setExporting] = useState(false);
  const requestRef = useRef<AbortController | null>(null);
  const { history, addEntry, clearHistory, storageError } = useQueryHistory();
  useEffect(() => () => { requestRef.current?.abort(); requestRef.current = null; }, []);
  useEffect(() => {
    const abort = new AbortController();
    fetchDemoScenarios(abort.signal).then(items => { if (abort.signal.aborted) return; setScenarios(items); const selected = items.find(s => s.scenario_id === initialScenario) ?? items[0]; setSelectedScenario(selected?.scenario_id ?? null); setQuery(q => q || selected?.default_query || ''); })
      .catch(e => { if (!abort.signal.aborted) setSceneError(e instanceof Error ? e.message : 'Scenes unavailable.'); })
      .finally(() => { if (!abort.signal.aborted) setLoading(false); });
    return () => abort.abort();
  }, [initialScenario]);
  const reset = () => { requestRef.current?.abort(); requestRef.current = null; setPhase('setup'); setResult(null); setTraceItems([]); setInputMetadata([]); setThumbnails([]); setStrategy(''); setInsertion(''); setError(''); };
  const running = phase === 'running';
  const selectScene = (id: string) => { if (requestRef.current) return; reset(); setRealImages(null); setSelectedScenario(id); setQuery(scenarios.find(s => s.scenario_id === id)?.default_query ?? ''); };
  const replay = (entry: HistoryEntry) => { if (requestRef.current) return; reset(); setRealImages(null); setSelectedScenario(entry.scenarioId); setQuery(entry.query); setSourceTab('scene'); setMobileSection('setup'); };
  const analyze = async (text: string) => {
    if (requestRef.current || !text.trim()) return;
    reset(); const abort = new AbortController(); requestRef.current = abort; setPhase('running'); setRunQuery(text); setRunAOI(realImages ? aoi?.name : undefined);
    const scenario = realImages ? null : selectedScenario;
    const callbacks: AnalysisCallbacks = {
      onInputsResolved: (images, demo) => { setInputMetadata(images); setIsDemo(demo); },
      onStrategySelected: (_detail, message) => setStrategy(message),
      onPlanUpdated: (message) => setInsertion(message),
      onThumbnails: setThumbnails,
      onToolStart: item => setTraceItems(prev => [...prev.filter(t => t.step_index !== item.step_index), { ...item, status: 'running' as const }].sort((a, b) => a.step_index - b.step_index)),
      onToolDone: item => setTraceItems(prev => [...prev.filter(t => t.step_index !== item.step_index), item].sort((a, b) => a.step_index - b.step_index)),
      onCompleted: completed => { setResult(completed); setInputMetadata(completed.inputMetadata ?? []); setPhase('done'); addEntry({ query: text, scenarioId: scenario, confidence: completed.confidence, confidenceLevel: completed.confidenceLevel, finalAnswer: completed.finalAnswer, outcome: completed.outcome, aoiName: realImages ? aoi?.name : undefined }); },
      onError: message => { setError(message); setPhase('error'); },
    };
    // Both transport cancellation and identity guarding protect against late callbacks.
    const safe = Object.fromEntries(Object.entries(callbacks).map(([name, fn]) => [name, (...args: unknown[]) => { if (requestRef.current === abort && !abort.signal.aborted) (fn as (...values: unknown[]) => void)(...args); }])) as AnalysisCallbacks;
    if (scenario) await runDemoScenario(scenario, text, safe, abort.signal);
    else await runAnalysis(text, null, safe, realImages ? [realImages.before_b64, realImages.after_b64] : [], realImages ? [
      { image_id: realImages.before_id, acquisition_date: realImages.before_date, sensor: 'Sentinel-2 (catalogue claim)', image_type: 'Optical', source: 'EarthSearch catalogue preview' },
      { image_id: realImages.after_id, acquisition_date: realImages.after_date, sensor: 'Sentinel-2 (catalogue claim)', image_type: 'Optical', source: 'EarthSearch catalogue preview' },
    ] : [], abort.signal);
    if (requestRef.current === abort) requestRef.current = null;
  };
  const exportReport = async () => { if (!result) return; setExporting(true); try { await generateAnalysisReport({ query: runQuery, analysisId: result.analysisId, aoiName: runAOI, images: inputMetadata, traceItems, finalAnswer: result.finalAnswer, confidence: result.confidence, confidenceLevel: result.confidenceLevel, evidenceStatus: result.evidenceStatus, evidencePoints: result.evidencePoints, visualOutputs: result.visualOutputs, outcome: result.outcome, limitations: result.limitations, verified: result.verified, scoreKind: result.scoreKind, auditHash: result.auditHash, thresholdPolicy: result.thresholdPolicy }); } catch (e) { setError(e instanceof Error ? e.message : 'Export failed.'); } finally { setExporting(false); } };
  const outputs: VisualOutput[] = result?.visualOutputs ?? thumbnails.map((b64, i) => ({ type: i === 0 ? 'before' : 'after', label: `${isDemo ? 'Demonstration input' : 'Original observation'} ${i + 1}`, b64 }));
  return <div>
    <div className="workspace-toolbar"><Satellite size={18} style={{ color: 'var(--accent)' }} /><h1>Analysis workspace</h1><span className="subtle" role="status">{running ? 'Processing imagery' : result?.outcome?.replaceAll('_', ' ') ?? 'Configure an analysis'}</span>
      <div className="ml-auto flex gap-2"><button className="btn-ghost text-xs" onClick={reset}><RotateCcw size={13} />{running ? 'Stop viewing run' : 'New analysis'}</button>{result && <button className="btn-primary text-xs" disabled={exporting} onClick={exportReport}><FileDown size={13} />{exporting ? 'Exporting…' : 'Export PDF'}</button>}</div></div>
    {error && <p role="alert" className="notice m-3">{error}</p>}
    <nav className="workspace-mobile-nav segmented" aria-label="Workspace sections">{['setup', 'imagery', 'results'].map(section => <button key={section} aria-pressed={mobileSection === section} onClick={() => setMobileSection(section)}>{section[0].toUpperCase() + section.slice(1)}</button>)}</nav>
    <div className="workspace-grid">
      <aside className="workspace-column" data-active={mobileSection === 'setup'} aria-label="Analysis setup">
        <section className="panel"><div className="panel-header"><h2 className="panel-title">01 / Input source</h2></div><div className="p-3 space-y-3">
          <div className="segmented" role="group" aria-label="Input source options">{['scene', 'map', 'history'].map(id => <button key={id} aria-pressed={sourceTab === id} onClick={() => setSourceTab(id)}>{id === 'scene' ? 'Scenes' : id === 'map' ? 'AOI' : 'History'}</button>)}</div>
          <div hidden={sourceTab !== 'scene'}>{loading ? <p role="status" className="subtle">Loading local scenarios…</p> : sceneError ? <p role="alert" className="notice">{sceneError} Check the backend and reload.</p> : <SceneSelector scenarios={scenarios} selectedId={realImages ? null : selectedScenario} onSelect={selectScene} disabled={running} />}</div>
          <div hidden={sourceTab !== 'map'}><AOIMapSelector selectedAOI={aoi} onAOISelected={setAOI} disabled={running} active={sourceTab === 'map'} onRealImagesFetched={images => { if (!requestRef.current) { setRealImages(images); if (images) { reset(); setSelectedScenario(null); } } }} /></div>
          <div hidden={sourceTab !== 'history'}><QueryHistoryPanel history={history} onReplay={replay} onClear={clearHistory} />{storageError && <p role="status" className="notice">{storageError}</p>}</div>
          {realImages && <p className="notice">Catalogue imagery attached. Returned acquisitions: {realImages.before_date} / {realImages.after_date}.</p>}
          {!realImages && selectedScenario && <p className="subtle">Demonstration source. Results are excluded from scientific evaluation.</p>}
        </div></section>
        <section className="panel"><div className="panel-header"><h2 className="panel-title">02 / Analysis request</h2></div><div className="p-3"><QueryBox query={query} onChange={setQuery} onSubmit={analyze} running={running} canAnalyze={Boolean(realImages || selectedScenario)} />{!realImages && !selectedScenario && <p className="notice mt-3">Select a scene or retrieve imagery before submitting.</p>}</div></section>
        {inputMetadata.length > 0 && <details className="panel p-3"><summary>Resolved input identities ({inputMetadata.length})</summary><ImageMetaPanel images={inputMetadata} thumbnails={[]} /></details>}
        <p className="subtle">Stopping the view disconnects this browser. Server computation may finish in memory.</p>
      </aside>
      <section className="workspace-column" data-active={mobileSection === 'imagery'} aria-label="Imagery workspace">
        <div className="panel"><div className="panel-header"><h2 className="panel-title">03 / Imagery workspace</h2><span className="subtle">Raster diagnostics</span></div><VisualOutputsGrid key={result?.analysisId ?? 'inputs'} outputs={outputs} isDemo={isDemo} /></div>
        <div className="notice">Pixel diagnostics do not establish land-cover classes or geographic area. Estimated pixels are not observations.</div>
        {running && <p role="status" className="subtle">{traceItems.filter(t => t.status !== 'running').length} tool executions returned. No completion percentage is inferred.</p>}
      </section>
      <aside className="workspace-column workspace-results" data-active={mobileSection === 'results'} aria-label="Results and evidence">
        {result ? <><FinalAnswerCard query={runQuery} answer={result.finalAnswer} confidence={result.confidence} confidenceLevel={result.confidenceLevel} evidenceStatus={result.evidenceStatus} evidencePoints={result.evidencePoints} analysisId={result.analysisId} traceItems={traceItems} images={inputMetadata} visualOutputs={result.visualOutputs} auditHash={result.auditHash} outcome={result.outcome} limitations={result.limitations} verified={result.verified} scoreKind={result.scoreKind} lowEvidence={result.lowEvidence} />
          <section className="panel p-3"><EvidencePanel evidenceStatus={result.evidenceStatus} evidencePoints={result.evidencePoints} confidence={result.confidence} evidenceBreakdown={result.evidenceBreakdown} evidenceFormula={result.evidenceFormula} evidenceInterpretation={result.evidenceInterpretation} hasRealImages={result.hasRealImages} thresholdPolicy={result.thresholdPolicy} /></section></> : <section className="panel p-4"><h2 className="panel-title">Results & evidence</h2><p className="subtle mt-3">{running ? 'Waiting for a grounded completion outcome.' : 'Run a diagnostic to inspect its summary, limitations and evidence factors.'}</p></section>}
        <section className="panel"><div className="panel-header"><h2 className="panel-title">Execution record</h2><span className="subtle">{traceItems.length} steps</span></div><div className="p-3"><TracePanel items={traceItems} strategyMessage={strategy} planUpdateMessage={insertion} /></div></section>
      </aside>
    </div>
  </div>;
}
