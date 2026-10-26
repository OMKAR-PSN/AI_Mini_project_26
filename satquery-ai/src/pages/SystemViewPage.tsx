import { CheckCircle2, Circle } from 'lucide-react';

const stages = [
  { num: '01', title: 'React workspace',         desc: 'Typed requests, image inspection, results and local browser history.', color: 'var(--accent)' },
  { num: '02', title: 'FastAPI service',          desc: 'Resolves supplied pixels and metadata; streams actual execution events. Sessions remain in server memory.', color: '#4ecdc4' },
  { num: '03', title: 'Deterministic controller', desc: 'Chooses a strategy from the registry. Per-image cloud checks can insert CPU repair steps into the executing queue.', color: '#5b7ed7' },
  { num: '04', title: 'Registered tools',         desc: 'Classical screening, registration and raster diagnostics. The current repair provider runs locally on CPU.', color: '#E07B39' },
  { num: '05', title: 'Evidence aggregation',     desc: 'Applies provenance and eligibility rules. Missing independent evidence is not counted as agreement.', color: '#236746' },
  { num: '06', title: 'Grounded answer & audit',  desc: 'Assembles actual findings, limitations and outcome; records input identities and a SHA-256 digest.', color: '#86429a' },
];

const tools: { name: string; status: string; available: boolean }[] = [
  { name: 'image_validation',         status: 'Input bookkeeping',                available: true  },
  { name: 'cloud_detection',          status: 'Classical RGB screening',           available: true  },
  { name: 'cloud_reconstruction',     status: 'CPU inpainting estimates',          available: true  },
  { name: 'bi_temporal_change_detection', status: 'Registration + intensity diff', available: true  },
  { name: 'evidence_comparison',      status: 'Evidence aggregation',             available: true  },
  { name: 'confidence_check',         status: 'Heuristic eligibility check',      available: true  },
  { name: 'answer_synthesis',         status: 'Deterministic grounded summary',   available: true  },
  { name: 'scene_understanding',      status: 'Learned capability unavailable',   available: false },
  { name: 'object_region_detection',  status: 'Learned capability unavailable',   available: false },
  { name: 'land_cover_classification',status: 'Learned capability unavailable',   available: false },
  { name: 'sar_optical_fusion',       status: 'Trained fusion unavailable',        available: false },
  { name: 'spatial_reasoning',        status: 'Geospatial inference unavailable', available: false },
];

export default function SystemViewPage() {
  return (
    <div className="page-shell space-y-8 animate-fade-in">
      {/* Header */}
      <header className="animate-slide-up">
        <p className="field-label" style={{ color: 'var(--accent)', letterSpacing: '.12em' }}>
          Implementation reference
        </p>
        <h1 className="page-heading mt-2">System view</h1>
        <p className="page-intro mt-3">
          The current classical processing pipeline, its registered interfaces and its operational
          boundaries. This architecture reference is not a live service-health monitor.
        </p>
      </header>

      {/* Pipeline stages */}
      <section aria-labelledby="pipeline">
        <h2 id="pipeline" className="text-lg font-bold mb-1" style={{ letterSpacing: '-.02em' }}>
          Request to evidence
        </h2>
        <p className="subtle mb-4">Data flows through 6 deterministic stages in sequence.</p>
        <ol className="architecture-grid" style={{ gap: '1rem', position: 'relative' }}>
          {stages.map(({ num, title, desc, color }) => (
            <li
              key={title}
              className="panel p-5 pipeline-stage animate-slide-up"
              style={{ animationDelay: `${parseInt(num) * 0.07}s` }}
            >
              <div
                className="w-9 h-9 rounded-xl flex items-center justify-center mb-4 font-bold text-xs"
                style={{ background: `color-mix(in srgb, ${color} 15%, transparent)`, color, fontFamily: 'JetBrains Mono, monospace' }}
              >
                {num}
              </div>
              <h3 className="font-bold text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
                {title}
              </h3>
              <p className="subtle">{desc}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Tool registry */}
      <section className="panel p-5">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-lg font-bold" style={{ letterSpacing: '-.02em' }}>Tool registry</h2>
          <div className="flex gap-3">
            <span className="badge badge-teal">
              <CheckCircle2 size={10} />
              {tools.filter(t => t.available).length} operational
            </span>
            <span className="badge badge-gray">
              <Circle size={10} />
              {tools.filter(t => !t.available).length} unavailable
            </span>
          </div>
        </div>
        <p className="subtle mb-5">
          Registration is not a claim that a learned model is available. The execution record shows
          which tools actually ran for each input.
        </p>
        <div className="registry-grid">
          {tools.map(({ name, status, available }) => (
            <div className="registry-row" key={name}>
              <div className="flex items-center gap-2">
                {available
                  ? <CheckCircle2 size={12} style={{ color: 'var(--success)', flexShrink: 0 }} />
                  : <Circle      size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                }
                <code className="technical font-medium" style={{ color: available ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                  {name}
                </code>
              </div>
              <span className="subtle" style={{ paddingLeft: 20 }}>{status}</span>
            </div>
          ))}
        </div>
      </section>

      {/* External connectors + policy */}
      <div className="feature-grid">
        <section className="panel p-5">
          <h2 className="font-bold text-sm mb-4">External connectors</h2>
          <dl className="space-y-4 text-sm">
            {[
              {
                name: 'EarthSearch / Sentinel catalogue',
                desc: 'On-demand search and preview retrieval. Network availability is established only by a request; previews have geospatial and acquisition limitations.',
                available: true,
              },
              {
                name: 'Bhoonidhi',
                desc: 'Connector exists; access requires server-side configuration and successful authentication. Connectivity has not been checked on this screen.',
                available: null,
              },
              {
                name: 'Remote GPU / precomputed providers',
                desc: 'Provider interfaces exist. The current repair pipeline explicitly uses CPU inpainting, not remote diffusion inference.',
                available: false,
              },
            ].map(({ name, desc, available }) => (
              <div key={name}>
                <dt className="font-semibold flex items-center gap-2" style={{ fontSize: 13 }}>
                  {available === true && <CheckCircle2 size={13} style={{ color: 'var(--success)' }} />}
                  {available === false && <Circle size={13} style={{ color: 'var(--text-muted)' }} />}
                  {available === null && <Circle size={13} style={{ color: 'var(--warning)' }} />}
                  {name}
                </dt>
                <dd className="subtle mt-1" style={{ paddingLeft: 21 }}>{desc}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="panel p-5">
          <h2 className="font-bold text-sm mb-4">Policy &amp; provenance</h2>
          <div className="space-y-3">
            <div
              className="p-3 rounded-lg"
              style={{ background: 'var(--accent-soft)', border: '1px solid color-mix(in srgb, var(--accent) 20%, transparent)' }}
            >
              <p className="font-semibold text-xs mb-1" style={{ color: 'var(--accent)' }}>Evidence thresholds</p>
              <p className="subtle">Runtime low-evidence threshold: <strong>0.55</strong>. Research threshold: <strong>0.60</strong> (separate policy). Run-specific values are displayed from the backend response.</p>
            </div>
            <p className="subtle">
              A SHA-256 digest makes recorded content tamper-evident when compared with a trusted
              digest. It is not a digital signature or proof of scientific validity.
            </p>
            <p className="subtle">
              No learned VQA model, trained SAR fusion, diffusion reconstruction or independent
              expert verification is operational in this pipeline.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
