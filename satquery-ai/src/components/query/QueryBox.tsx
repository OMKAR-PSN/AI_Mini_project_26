import { ArrowRight, Loader2 } from 'lucide-react';
interface QueryBoxProps { onSubmit: (query: string) => void; disabled?: boolean; running?: boolean; query: string; onChange: (query: string) => void; canAnalyze?: boolean; }
export default function QueryBox({ onSubmit, disabled, running, query, onChange, canAnalyze = true }: QueryBoxProps) {
  const submit = () => { if (query.trim() && !disabled && !running && canAnalyze) onSubmit(query.trim()); };
  return <form onSubmit={e => { e.preventDefault(); submit(); }} className="space-y-3">
    <label className="field-label" htmlFor="analysis-query">Analysis request</label>
    <textarea id="analysis-query" className="input-field" rows={4} value={query} onChange={e => onChange(e.target.value)} disabled={disabled || running} aria-describedby="query-help" placeholder="Detect cloud candidates in this image." onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); submit(); } }} />
    <p id="query-help" className="subtle">Describe a pixel diagnostic. Ctrl/⌘ + Enter to run. Semantic classification and SAR fusion are unavailable.</p>
    <div className="flex flex-wrap gap-2">{[{ label: 'Cloud candidates', query: 'Detect clouds and reconstruct cloud candidates if required.' }, { label: 'Intensity change · 2 images', query: 'Measure grayscale intensity change between these two images.' }].map(example => <button type="button" className="btn-ghost text-xs" key={example.label} disabled={disabled || running} onClick={() => onChange(example.query)}>{example.label}</button>)}</div>
    <button type="submit" className="btn-primary w-full" disabled={disabled || running || !query.trim() || !canAnalyze}>{running ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />} {running ? 'Processing imagery…' : 'Analyze imagery'}</button>
  </form>;
}
