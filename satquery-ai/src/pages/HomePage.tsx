import { useEffect, useState } from 'react';
import { ArrowRight, Cloud, Layers, ScanLine, Shield, Cpu, GitBranch, Sparkles, SlidersHorizontal, Play, Pause } from 'lucide-react';
import { fetchDemoScenarios } from '../api/client';
import type { DemoScenario } from '../types';
import DriftWall from '../components/driftwall/DriftWall';
import { SATELLITE_WALL_ITEMS, type DriftWallItem } from '../components/driftwall/satelliteItems';

interface Props { onNavigate: (page: string) => void; onStartDemo: (id: string) => void; }

export default function HomePage({ onNavigate, onStartDemo }: Props) {
  const [scenes, setScenes] = useState<DemoScenario[]>([]);
  const [status, setStatus] = useState('Loading demonstration workflows…');
  const [activeFilter, setActiveFilter] = useState<'all' | 'bundled' | 'stock' | 'diagnostics'>('all');
  const [pauseOnHover, setPauseOnHover] = useState(false);
  const [speed, setSpeed] = useState(38);
  const [selectedTile, setSelectedTile] = useState<DriftWallItem | null>(null);

  useEffect(() => {
    const abort = new AbortController();
    fetchDemoScenarios(abort.signal)
      .then(items => {
        if (!abort.signal.aborted) {
          setScenes(items);
          setStatus(items.length ? '' : 'No demonstration workflows available.');
        }
      })
      .catch(() => {
        if (!abort.signal.aborted)
          setStatus('Demonstrations unavailable. Start the backend to load local scenes.');
      });
    return () => abort.abort();
  }, []);

  const filteredItems = SATELLITE_WALL_ITEMS.filter(item => activeFilter === 'all' || item.category === activeFilter);

  const CAPABILITIES = [
    {
      Icon: Cloud,
      title: 'Cloud Screening',
      text: 'RGB brightness and whiteness screening with morphological processing. Bright terrain can produce false positives.',
      accent: 'var(--accent)',
      bg: 'var(--accent-soft)',
    },
    {
      Icon: Cpu,
      title: 'Pixel Reconstruction',
      text: 'Local OpenCV inpainting estimates masked pixels. Reconstructed content is explicitly labelled and is not an observation.',
      accent: '#E07B39',
      bg: '#fde8d6',
    },
    {
      Icon: ScanLine,
      title: 'Two-date Comparison',
      text: 'Registration screening and grayscale difference diagnostics. These do not establish land-cover classes or geographic area.',
      accent: '#236746',
      bg: '#d1f0e0',
    },
  ];

  const TRUST_ITEMS = [
    {
      Icon: Shield,
      title: 'Evidence, with boundaries',
      text: 'Scores are heuristic evidence strengths, not calibrated probabilities. Each run exposes limitations, tool events and a tamper-evident SHA-256 digest.',
    },
    {
      Icon: GitBranch,
      title: 'Deterministic pipeline',
      text: 'The controller uses deterministic rules. Learned VQA, SAR fusion and diffusion reconstruction are not connected to this pipeline.',
      action: { label: 'Inspect system architecture', page: 'system' },
    },
    {
      Icon: Layers,
      title: 'Full provenance trace',
      text: 'Every tool execution records its input identity, algorithm, execution mode and evidence eligibility. Nothing is inferred silently.',
      action: { label: 'Open analysis workspace', page: 'analysis' },
    },
  ];

  return (
    <div className="page-shell space-y-12">

      {/* ── Hero ───────────────────────────────────────────────────────── */}
      <section className="home-intro hero-section rounded-2xl p-6 -mx-2 animate-fade-in">
        <div className="animate-slide-up" style={{ animationDelay: '0.05s' }}>
          <p className="field-label flex items-center gap-2" style={{ color: 'var(--accent)', letterSpacing: '.12em' }}>
            <span className="w-2 h-2 rounded-full animate-ping" style={{ background: 'var(--accent)' }} />
            ISRO SIH26167 &nbsp;·&nbsp; Earth Observation Workspace
          </p>
          <h1 className="page-heading gradient-heading mt-4">
            Inspect imagery.<br />Understand the evidence.
          </h1>
          <p className="page-intro">
            SatQuery AI is a satellite-analysis workspace for cloud screening, CPU pixel reconstruction
            and two-date raster diagnostics. Follow each computation from its input identity to its
            recorded outcome.
          </p>
          <div className="flex flex-wrap gap-3 mt-6">
            <button
              className="btn-primary"
              onClick={() => onNavigate('analysis')}
            >
              Open analysis workspace <ArrowRight size={16} />
            </button>
            <button
              className="btn-ghost"
              onClick={() => onNavigate('system')}
            >
              View system architecture
            </button>
          </div>
        </div>

        <figure
          className="panel overflow-hidden animate-fade-in"
          style={{ animationDelay: '0.2s', background: 'var(--viewer)' }}
        >
          <img
            src="/images/sat_urban_river.jpg"
            alt="Illustrative raster of a river and surrounding urban terrain"
            className="w-full object-cover feature-card"
            style={{ maxHeight: 270, display: 'block' }}
          />
          <figcaption className="p-3 subtle text-xs" style={{ borderTop: '1px solid var(--border)' }}>
            Static bundled illustration · Acquisition, sensor and geographic provenance are not
            established; this is not a live satellite feed.
          </figcaption>
        </figure>
      </section>

      {/* ── Multi-Sensor Satellite Drift Wall Showcase ─────────────────────── */}
      <section aria-labelledby="observation-wall" className="space-y-4 animate-slide-up" style={{ animationDelay: '0.12s' }}>
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-mono font-bold tracking-wider uppercase" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                <Sparkles size={12} /> Illustration gallery
              </span>
              <span className="subtle text-xs font-mono">Interactive imagery display</span>
            </div>
            <h2 id="observation-wall" className="text-xl md:text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
              Earth Observation Drift Wall
            </h2>
            <p className="subtle text-sm max-w-2xl mt-1">
              Explore decorative bundled illustrations and stock photography. These tiles are not live satellite observations or analysis inputs. Select a tile to inspect its source description.
            </p>
          </div>

          {/* Quick HUD controls */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            {/* Filter Pills */}
            <div className="inline-flex rounded-lg p-0.5 border" style={{ background: 'var(--panel)', borderColor: 'var(--border)' }}>
              <button
                type="button"
                onClick={() => setActiveFilter('all')}
                className={`px-2.5 py-1 rounded-md transition-colors ${activeFilter === 'all' ? 'font-bold' : 'subtle'}`}
                style={activeFilter === 'all' ? { background: 'var(--accent)', color: '#fff' } : {}}
              >
                All ({SATELLITE_WALL_ITEMS.length})
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter('bundled')}
                className={`px-2.5 py-1 rounded-md transition-colors ${activeFilter === 'bundled' ? 'font-bold' : 'subtle'}`}
                style={activeFilter === 'bundled' ? { background: 'var(--accent)', color: '#fff' } : {}}
              >
                Bundled
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter('stock')}
                className={`px-2.5 py-1 rounded-md transition-colors ${activeFilter === 'stock' ? 'font-bold' : 'subtle'}`}
                style={activeFilter === 'stock' ? { background: 'var(--accent)', color: '#fff' } : {}}
              >
                Stock photos
              </button>
              <button
                type="button"
                onClick={() => setActiveFilter('diagnostics')}
                className={`px-2.5 py-1 rounded-md transition-colors ${activeFilter === 'diagnostics' ? 'font-bold' : 'subtle'}`}
                style={activeFilter === 'diagnostics' ? { background: 'var(--accent)', color: '#fff' } : {}}
              >
                Diagnostic
              </button>
            </div>

            {/* Pause button */}
            <button
              type="button"
              onClick={() => setPauseOnHover(p => !p)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors"
              style={{
                borderColor: 'var(--border)',
                background: pauseOnHover ? 'var(--accent-soft)' : 'var(--panel)',
                color: pauseOnHover ? 'var(--accent)' : 'var(--text-secondary)'
              }}
              title="Toggle pause on hover"
            >
              {pauseOnHover ? <Pause size={12} /> : <Play size={12} />}
              <span>{pauseOnHover ? 'Hover: Pause' : 'Hover: Drift'}</span>
            </button>

            {/* Speed toggle */}
            <button
              type="button"
              onClick={() => setSpeed(s => (s === 38 ? 60 : s === 60 ? 20 : 38))}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border transition-colors subtle hover:text-primary"
              style={{ borderColor: 'var(--border)', background: 'var(--panel)' }}
              title="Cycle drift speed"
            >
              <SlidersHorizontal size={12} />
              <span>{speed === 20 ? 'Slow' : speed === 60 ? 'Fast' : 'Normal'}</span>
            </button>
          </div>
        </div>

        {/* DriftWall Viewport Container */}
        <div
          className="relative rounded-2xl overflow-hidden border shadow-2xl transition-all"
          style={{
            height: 520,
            background: 'radial-gradient(130% 110% at 50% 10%, #0c1b2c 0%, #030810 100%)',
            borderColor: 'var(--border)',
          }}
        >
          <DriftWall
            items={filteredItems}
            columns={5}
            tileWidth={205}
            tileHeight={135}
            gap={18}
            tilt={16}
            turn={-14}
            perspective={1200}
            depth={110}
            speed={speed}
            direction="up"
            variance={0.42}
            parallax={0.65}
            pauseOnHover={pauseOnHover}
            lift={65}
            fade={0.62}
            dim={0.58}
            overlayColor="#040914"
            onTileClick={item => setSelectedTile(item)}
          />

          {/* Persistent status watermark in bottom-left */}
          <div
            className="absolute bottom-4 left-4 z-20 pointer-events-none flex items-center gap-3 px-3 py-1.5 rounded-lg text-xs font-mono"
            style={{
              background: 'rgba(5, 12, 22, 0.8)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: '#94a3b8',
            }}
          >
            <span className="flex items-center gap-1.5 text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              {filteredItems.length} Illustrations shown
            </span>
            <span>·</span>
            <span className="hidden sm:inline">Move pointer for 3D tilt</span>
            <span>·</span>
            <span>Click tile to inspect</span>
          </div>

          {/* Selected Tile Inspector Modal Overlay if clicked */}
          {selectedTile && (
            <div
              className="absolute inset-0 z-30 flex items-center justify-center p-4"
              style={{ background: 'rgba(3, 8, 16, 0.75)', backdropFilter: 'blur(8px)' }}
              onClick={() => setSelectedTile(null)}
            >
              <div
                className="panel p-6 max-w-md w-full rounded-2xl shadow-2xl space-y-4 animate-scale-in"
                style={{ background: 'var(--panel)', borderColor: 'var(--border)' }}
                onClick={e => e.stopPropagation()}
              >
                <div className="flex items-center justify-between">
                  <span className="field-label uppercase font-mono text-xs" style={{ color: 'var(--accent)' }}>
                    Illustration details
                  </span>
                  <button
                    onClick={() => setSelectedTile(null)}
                    className="subtle text-sm px-2 py-1 rounded hover:bg-[var(--surface-subtle)]"
                  >
                    ✕
                  </button>
                </div>

                <div className="rounded-xl overflow-hidden border" style={{ borderColor: 'var(--border)' }}>
                  <img
                    src={selectedTile.image}
                    alt={selectedTile.title}
                    className="w-full h-44 object-cover"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-bold text-base" style={{ color: 'var(--text-primary)' }}>
                      {selectedTile.title}
                    </h3>
                    {selectedTile.badge && (
                      <span className="text-xs px-2 py-0.5 rounded-full font-mono font-bold" style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                        {selectedTile.badge}
                      </span>
                    )}
                  </div>
                  <p className="subtle text-xs">{selectedTile.subtitle || 'Decorative illustration; source metadata unavailable'}</p>
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    className="btn-primary flex-1 text-xs"
                    onClick={() => onNavigate('analysis')}
                  >
                    Go to Analysis Workspace <ArrowRight size={14} />
                  </button>
                  <button
                    className="btn-ghost text-xs"
                    onClick={() => setSelectedTile(null)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Capabilities ───────────────────────────────────────────────── */}
      <section aria-labelledby="available">
        <h2
          id="available"
          className="text-lg font-bold mb-1"
          style={{ letterSpacing: '-.02em' }}
        >
          Available diagnostics
        </h2>
        <p className="subtle mb-4">What this pipeline can compute — and what it explicitly cannot.</p>
        <div className="feature-grid">
          {CAPABILITIES.map(({ Icon, title, text, accent, bg }, i) => (
            <article
              key={title}
              className="panel p-5 feature-card animate-slide-up"
              style={{ animationDelay: `${0.08 * i}s` }}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-4"
                style={{ background: bg, color: accent }}
              >
                <Icon size={20} />
              </div>
              <h3 className="font-bold text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
                {title}
              </h3>
              <p className="subtle">{text}</p>
            </article>
          ))}
        </div>
      </section>

      {/* ── Demo scenarios ─────────────────────────────────────────────── */}
      <section aria-labelledby="workflows">
        <h2
          id="workflows"
          className="text-lg font-bold mb-1"
          style={{ letterSpacing: '-.02em' }}
        >
          Start with a demonstration
        </h2>
        <p className="subtle mb-4">
          Local scenes exercise the pipeline. Demonstration evidence is excluded from scientific
          evaluation; unsupported requests return structured limitations.
        </p>

        {status && <p role="status" className="notice mb-4">{status}</p>}

        <div className="feature-grid">
          {scenes.map((scene, i) => (
            <button
              key={scene.scenario_id}
              className="scene-card text-left animate-slide-up"
              style={{ animationDelay: `${0.1 * i}s` }}
              onClick={() => onStartDemo(scene.scenario_id)}
            >
              <span className="field-label">Demonstration &nbsp;·&nbsp; {scene.images.length} input(s)</span>
              <span className="block font-bold text-sm my-2" style={{ color: 'var(--text-primary)' }}>
                {scene.title}
              </span>
              <span className="subtle">
                {scene.task_type === 'cloud_analysis'
                  ? 'Inspect cloud screening and estimated pixel repair.'
                  : scene.task_type === 'bi_temporal_change'
                  ? 'Inspect two-date processing and eligibility limits.'
                  : 'Inspect capability limits and structured unsupported outcomes.'}
              </span>
              <span
                className="block text-xs mt-3 font-semibold"
                style={{ color: 'var(--accent)' }}
              >
                Configure workflow →
              </span>
            </button>
          ))}

          {/* Loading skeletons */}
          {!status.includes('unavailable') && scenes.length === 0 && status && (
            [1, 2, 3].map(n => (
              <div key={n} className="panel p-5 space-y-3">
                <div className="shimmer h-3 rounded w-1/3" />
                <div className="shimmer h-4 rounded w-3/4" />
                <div className="shimmer h-3 rounded w-full" />
                <div className="shimmer h-2/3" />
              </div>
            ))
          )}
        </div>
      </section>

      {/* ── Trust & boundaries ─────────────────────────────────────────── */}
      <section className="feature-grid">
        {TRUST_ITEMS.map(({ Icon, title, text, action }) => (
          <article key={title} className="panel p-5 feature-card">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center mb-3"
              style={{ background: 'var(--accent-soft)', color: 'var(--accent)' }}
            >
              <Icon size={18} />
            </div>
            <h2 className="font-bold text-sm mb-2">{title}</h2>
            <p className="subtle">{text}</p>
            {action && (
              <button
                className="btn-ghost mt-4 text-xs"
                onClick={() => onNavigate(action.page)}
              >
                {action.label} <ArrowRight size={13} />
              </button>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
