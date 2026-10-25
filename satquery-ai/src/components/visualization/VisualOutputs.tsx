import { useState } from 'react';
import { Image as ImageIcon, ZoomIn, ZoomOut, Maximize } from 'lucide-react';
import type { VisualOutput } from '../../types';
function imageMeaning(output: VisualOutput, isDemo = false) {
  const meaning = output.type === 'reconstruction' ? 'Estimated pixels · CPU inpainting' :
    ['before', 'after', 'optical', 'sar'].includes(output.type) ? 'Original observation / supplied raster' : 'Computed diagnostic output';
  return isDemo || /DEMO|synthetic|demonstration/i.test(output.label) ? `Demonstration imagery · ${meaning}` : meaning;
}
export default function VisualOutputsGrid({ outputs, isDemo = false }: { outputs: VisualOutput[]; isDemo?: boolean }) {
  const unique = outputs.filter((item, index, all) => item.b64 && all.findIndex(other => other.b64 === item.b64 && other.type === item.type) === index);
  const [selected, setSelected] = useState('0'); const [zoom, setZoom] = useState(1); const [position, setPosition] = useState(50);
  const [loaded, setLoaded] = useState<Record<string, { width: number; height: number }>>({}); const [failed, setFailed] = useState<string[]>([]);
  const before = unique.find(o => o.type === 'before'); const after = unique.find(o => o.type === 'after');
  const compare = selected === 'compare' && before && after; const item = unique[Number(selected)] ?? unique[0];
  const first = compare ? before : item; const source = first ? `data:image/png;base64,${first.b64}` : '';
  const sizesMatch = before && after && loaded[before.b64] && loaded[after.b64] && loaded[before.b64].width === loaded[after.b64].width && loaded[before.b64].height === loaded[after.b64].height;
  const onLoaded = (image: HTMLImageElement, key: string) => setLoaded(prev => ({ ...prev, [key]: { width: image.naturalWidth, height: image.naturalHeight } }));
  if (!item) return <div className="empty-view"><ImageIcon size={36} style={{ color: 'var(--text-muted)' }} /><h3 className="font-semibold">Your imagery, in context</h3><p className="subtle max-w-xs">Choose an input and run a diagnostic. Original rasters, masks and estimated outputs will appear here.</p></div>;
  return <>
    <div className="viewer-toolbar"><label htmlFor="image-layer" className="sr-only">Image layer</label><select id="image-layer" className="input-field text-xs" value={compare ? 'compare' : String(unique.indexOf(item))} onChange={e => { setSelected(e.target.value); setZoom(1); setPosition(50); }}>{unique.map((o, i) => <option key={`${o.type}-${i}`} value={i}>{o.label}</option>)}{before && after && <option value="compare">Compare original inputs</option>}</select>
      <button className="btn-ghost" aria-label="Zoom out" disabled={zoom <= 1} onClick={() => setZoom(v => Math.max(1, v - .25))}><ZoomOut size={15} /></button><span className="technical">{Math.round(zoom * 100)}%</span><button className="btn-ghost" aria-label="Zoom in" disabled={zoom >= 3} onClick={() => setZoom(v => Math.min(3, v + .25))}><ZoomIn size={15} /></button><button className="btn-ghost" aria-label="Fit image and reset comparison" onClick={() => { setZoom(1); setPosition(50); }}><Maximize size={15} /></button>
    </div>
    <div className="viewer-stage" tabIndex={0} aria-label="Scrollable imagery viewport">
      <div className="viewer-canvas" style={{ width: `${zoom * 100}%`, maxWidth: zoom === 1 ? '100%' : undefined }}>
        <img src={source} alt={first.label} onLoad={e => onLoaded(e.currentTarget, first.b64)} onError={() => setFailed(prev => [...prev, first.b64])} />
        {compare && <img className="comparison-layer" style={{ clipPath: `inset(0 ${100 - position}% 0 0)` }} src={`data:image/png;base64,${after.b64}`} alt={after.label} onLoad={e => onLoaded(e.currentTarget, after.b64)} onError={() => setFailed(prev => [...prev, after.b64])} />}
        {compare && <span aria-hidden="true" style={{ position: 'absolute', top: 0, bottom: 0, left: `${position}%`, width: 2, background: '#fff', boxShadow: '0 0 2px #000' }} />}
      </div>
    </div>
    {failed.includes(first.b64) ? <p role="alert" className="notice">This image could not be decoded.</p> : !loaded[first.b64] && <p role="status" className="subtle p-3">Decoding image…</p>}
    {compare && <div className="p-3 space-y-2"><div className="flex justify-between gap-3 text-xs"><span>{after.label}</span><span>{before.label}</span></div><label htmlFor="comparison-divider" className="field-label">Comparison divider · {position}%</label><input id="comparison-divider" aria-label="Comparison divider" type="range" min="0" max="100" value={position} onChange={e => setPosition(Number(e.target.value))} className="w-full" style={{ accentColor: 'var(--accent)', touchAction: 'pan-y' }} /><p className="subtle">Drag or touch the slider; use arrow keys, Home or End. Original inputs are not geospatially aligned by this viewer.</p>{loaded[before.b64] && loaded[after.b64] && !sizesMatch && <p className="notice">Input dimensions differ. The overlay fits the display bounds; it is not a pixel-aligned scientific comparison.</p>}</div>}
    <div className="viewer-caption"><strong>{imageMeaning(first, isDemo)}</strong><p className="mt-1">{first.label}</p>{loaded[first.b64] && <p className="technical mt-1">{loaded[first.b64].width} × {loaded[first.b64].height} pixels · No coordinate overlay</p>}</div>
  </>;
}
