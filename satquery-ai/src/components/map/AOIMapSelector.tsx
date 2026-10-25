// AOIMapSelector.tsx — Leaflet map with AOI drawing + Real Sentinel-2 imagery fetcher

import { useEffect, useRef, useState } from 'react';
import { MapPin } from 'lucide-react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Map as LeafletMap, Rectangle as LeafletRectangle } from 'leaflet';
import { fetchRealImagery } from '../../api/client';

interface AOI {
  name: string;
  bounds: [[number, number], [number, number]]; // [[south, west], [north, east]]
  center: [number, number];
  zoom: number;
}

const PRESET_AOIS: AOI[] = [
  {
    name: 'Guwahati, Assam',
    bounds: [[26.05, 91.55], [26.25, 91.85]],
    center: [26.15, 91.70],
    zoom: 12,
  },
  {
    name: 'Mumbai Metropolitan',
    bounds: [[18.85, 72.75], [19.30, 73.05]],
    center: [19.07, 72.88],
    zoom: 11,
  },
  {
    name: 'Chilika Lake, Odisha',
    bounds: [[19.50, 85.10], [19.90, 85.55]],
    center: [19.70, 85.32],
    zoom: 11,
  },
  {
    name: 'Delhi NCR Region',
    bounds: [[28.40, 76.80], [28.90, 77.40]],
    center: [28.65, 77.10],
    zoom: 11,
  },
];

export interface AOISelection { name: string; bounds: [[number, number], [number, number]]; }
export interface FetchedRealImages { before_b64: string; after_b64: string; before_date: string; after_date: string; before_cloud_pct: number; after_cloud_pct: number; before_id?: string; after_id?: string; }
interface Props { selectedAOI: AOISelection | null; onAOISelected: (aoi: AOISelection | null) => void; onRealImagesFetched?: (images: FetchedRealImages | null) => void; disabled?: boolean; active?: boolean; }
export default function AOIMapSelector({ selectedAOI, onAOISelected, onRealImagesFetched, disabled = false, active = true }: Props) {
  const container = useRef<HTMLDivElement>(null); const map = useRef<LeafletMap | null>(null); const rectangle = useRef<LeafletRectangle | null>(null);
  const callbacks = useRef({ onAOISelected, onRealImagesFetched }); useEffect(() => { callbacks.current = { onAOISelected, onRealImagesFetched }; }, [onAOISelected, onRealImagesFetched]);
  const request = useRef<AbortController | null>(null); const drawing = useRef(false); const [drawMode, setDrawMode] = useState(false);
  const [dateBefore, setDateBefore] = useState('2022-04-21'); const [dateAfter, setDateAfter] = useState('2022-07-15'); const [cloud, setCloud] = useState(35);
  const [bounds, setBounds] = useState(['26.05', '91.55', '26.25', '91.85']); const [fetching, setFetching] = useState(false); const [error, setError] = useState(''); const [warnings, setWarnings] = useState<string[]>([]); const [loaded, setLoaded] = useState(false); const [tiles, setTiles] = useState(false);
  const invalidate = () => { request.current?.abort(); request.current = null; setFetching(false); setLoaded(false); setWarnings([]); callbacks.current.onRealImagesFetched?.(null); };
  useEffect(() => {
    if (!container.current) return;
    const instance = L.map(container.current, { center: [22.5, 82.5], zoom: 5, attributionControl: true }); map.current = instance;
    const resize = new ResizeObserver(() => instance.invalidateSize()); resize.observe(container.current);
    let start: L.LatLng | null = null;
    const finish = (e: L.LeafletMouseEvent) => {
if (!drawing.current || !start) return; const b = L.latLngBounds(start, e.latlng); start = null; drawing.current = false; setDrawMode(false); instance.dragging.enable(); if (b.getSouth() === b.getNorth() || b.getWest() === b.getEast()) return;
      request.current?.abort(); request.current = null; setFetching(false); setLoaded(false); setWarnings([]); callbacks.current.onRealImagesFetched?.(null);
      const next: AOISelection = { name: 'Custom requested AOI', bounds: [[b.getSouth(), b.getWest()], [b.getNorth(), b.getEast()]] }; setBounds(next.bounds.flat().map(v => v.toFixed(5))); callbacks.current.onAOISelected(next);
    };
    instance.on('mousedown', (e: L.LeafletMouseEvent) => { if (drawing.current) { start = e.latlng; instance.dragging.disable(); } });
    instance.on('mousemove', (e: L.LeafletMouseEvent) => { if (drawing.current && start) { const b = L.latLngBounds(start, e.latlng); if (rectangle.current) rectangle.current.setBounds(b); else rectangle.current = L.rectangle(b, { color: '#16877e', weight: 2 }).addTo(instance); } });
    instance.on('mouseup', finish);
    return () => { request.current?.abort(); request.current = null; resize.disconnect(); instance.remove(); map.current = null; rectangle.current = null; };
  }, []);
  useEffect(() => { const instance = map.current; if (!instance || !tiles) return; const layer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 18, attribution: 'Tiles © Esri, Maxar, Earthstar Geographics' }).addTo(instance); layer.on('tileerror', () => setError('Reference tiles could not load. Coordinate entry remains available.')); return () => { layer.remove(); }; }, [tiles]);
  useEffect(() => { const instance = map.current; if (!instance) return; rectangle.current?.remove(); rectangle.current = null; if (selectedAOI) { rectangle.current = L.rectangle(selectedAOI.bounds, { color: '#16877e', weight: 2, fillOpacity: .1 }).addTo(instance); instance.fitBounds(selectedAOI.bounds, { padding: [12, 12], animate: false }); } }, [selectedAOI]);
  useEffect(() => { if (active) map.current?.invalidateSize(); }, [active]);
  useEffect(() => { if (disabled) { drawing.current = false; map.current?.dragging.enable(); } }, [disabled]);
  const choose = (aoi: AOISelection) => { invalidate(); setError(''); drawing.current = false; setDrawMode(false); map.current?.dragging.enable(); setBounds(aoi.bounds.flat().map(String)); onAOISelected(aoi); };
  const apply = () => { const n = bounds.map(Number); if (bounds.some(v => !v.trim()) || n.some(v => !Number.isFinite(v)) || n[0] < -90 || n[2] > 90 || n[1] < -180 || n[3] > 180 || n[0] >= n[2] || n[1] >= n[3]) { setError('Use valid south < north and west < east coordinates within latitude/longitude limits.'); return; } choose({ name: 'Custom requested AOI', bounds: [[n[0], n[1]], [n[2], n[3]]] }); };
  const fetchImages = async () => {
if (!selectedAOI || disabled || fetching) return; if (!dateBefore || !dateAfter || dateBefore >= dateAfter) { setError('Choose an earlier first date and a later second date.'); return; } invalidate(); const abort = new AbortController(); request.current = abort; setFetching(true); setError(''); const [[south, west], [north, east]] = selectedAOI.bounds;
    try {
const response = await fetchRealImagery({ bbox: [west, south, east, north], dateBefore, dateAfter, maxCloudPct: cloud }, abort.signal); if (request.current !== abort || abort.signal.aborted) return;
      callbacks.current.onRealImagesFetched?.({ before_b64: response.before.image_b64, after_b64: response.after.image_b64, before_date: response.before.date, after_date: response.after.date, before_cloud_pct: response.before.cloud_pct, after_cloud_pct: response.after.cloud_pct, before_id: response.before.scene_id, after_id: response.after.scene_id }); setLoaded(true); setWarnings(response.warnings ?? []);
    } catch (e) { if (!abort.signal.aborted && request.current === abort) setError(e instanceof Error ? e.message : 'Imagery request failed.'); } finally { if (request.current === abort) { request.current = null; setFetching(false); } }
  };
  return <div className="space-y-3"><p className="subtle">Requested search bounds, not verified image coverage. Catalogue previews may cover a larger area.</p>
    <fieldset disabled={disabled} className="space-y-3" onKeyDown={e => { if (e.key === 'Escape') { drawing.current = false; setDrawMode(false); map.current?.dragging.enable(); } }}><legend className="field-label">Area of interest</legend><div className="grid grid-cols-2 gap-2">{PRESET_AOIS.map(p => <button key={p.name} type="button" className="btn-ghost text-xs" onClick={() => choose(p)}><MapPin size={12} />{p.name.split(',')[0]}</button>)}</div>
      <div ref={container} style={{ height: 220 }} aria-label="Reference map, coordinate alternative below" />
      <button type="button" className="btn-ghost text-xs w-full" onClick={() => setTiles(v => !v)}>{tiles ? 'Hide reference tiles' : 'Load Esri reference tiles (external)'}</button>
      <div className="flex gap-2"><button type="button" className="btn-ghost text-xs" aria-pressed={drawMode} onClick={() => { drawing.current = !drawing.current; setDrawMode(drawing.current); map.current?.dragging.enable(); }}> {drawMode ? 'Cancel drawing' : 'Draw rectangle'}</button><button type="button" className="btn-ghost text-xs" onClick={() => { invalidate(); drawing.current = false; setDrawMode(false); map.current?.dragging.enable(); onAOISelected(null); }}>Clear AOI</button></div>
      {drawMode && <p role="status" className="subtle">Drag on the map, or use coordinate fields below. Escape cancels drawing.</p>}
      <div className="grid grid-cols-2 gap-2" onKeyDown={e => { if (e.key === 'Escape') { drawing.current = false; setDrawMode(false); map.current?.dragging.enable(); } }}>{['South latitude', 'West longitude', 'North latitude', 'East longitude'].map((label, i) => <label key={label} className="field-label">{label}<input className="input-field mt-1" type="number" step="any" value={bounds[i]} onChange={e => { invalidate(); setBounds(prev => prev.map((v, n) => n === i ? e.target.value : v)); onAOISelected(null); }} /></label>)}</div>
      <button type="button" className="btn-ghost w-full text-xs" onClick={apply}>Apply coordinates</button>
      <div className="grid grid-cols-2 gap-2"><label className="field-label">First requested date<input className="input-field mt-1" type="date" value={dateBefore} onChange={e => { invalidate(); setDateBefore(e.target.value); }} /></label><label className="field-label">Second requested date<input className="input-field mt-1" type="date" value={dateAfter} onChange={e => { invalidate(); setDateAfter(e.target.value); }} /></label></div>
      <label className="field-label">Maximum catalogue cloud cover (%)<input className="input-field mt-1" type="number" min="0" max="100" value={cloud} onChange={e => { invalidate(); setCloud(Math.min(100, Math.max(0, Number(e.target.value)))); }} /></label>
      <button className="btn-primary w-full text-xs" type="button" disabled={!selectedAOI || fetching} onClick={fetchImages}>{fetching ? 'Retrieving catalogue imagery…' : 'Retrieve imagery pair'}</button></fieldset>
    {fetching && <button className="btn-ghost text-xs" onClick={invalidate}>Cancel retrieval</button>}{loaded && <p role="status" className="subtle">Imagery attached. Returned acquisition dates appear in the setup summary.</p>}{error && <p role="alert" className="notice">{error}</p>}{warnings.map(w => <p className="notice" key={w}>{w}</p>)}
  </div>;
}
