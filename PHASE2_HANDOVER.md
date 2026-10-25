# SatQuery AI - Phase 2 handover

## Scope and preservation

Updated the existing React/TypeScript/Tailwind frontend in place. Read PHASE1_HANDOVER.md, the existing pages, imports, API contracts and backend tool registry before editing. Backend source, scientific algorithms and thresholds were not changed in Phase 2. Existing Phase 1 and unrelated work remains in the working tree. No commit, push or deployment was performed.

## Implemented changes

- Restrained workstation design with neutral surfaces, teal accents, compact borders, consistent system sans-serif typography and visible focus indicators.
- Home, Analysis and System View remain the three pages. Mobile navigation remains visible. Home now explains implemented diagnostics and labels its static illustration. System View documents the deterministic controller, 12 registered tools, CPU repair, evidence/audit flow and unverified external connector availability.
- Analysis uses setup / imagery / results regions. Removed repeated optical/SAR display cards. One raster viewer exposes actual output layers, fit/reset, zoom and original-input comparison.
- Controlled, labelled query input; initial scenario synchronization; duplicate-run guard; running state; relevant examples; explicit unavailable capabilities.
- AbortController plus run-identity guards on stream callbacks; abort on reset/unmount; chunked SSE parsing with CRLF, multiline data, terminal-event and premature-EOF handling. Stopping viewing does not claim to stop server computation.
- Leaflet lifecycle cleanup, ResizeObserver and hidden-panel resize handling; abort/invalidate stale imagery requests; retained date/bounds controls; coordinate-entry alternative to dragging; coordinate/date validation; explicit external reference-tile loading.
- All five completion outcomes, backend limitations, verified state, heuristic score/factors and separate runtime/research policy values are shown. Missing metadata is labelled. No unconditional verification or scientific validity claims.
- Trace keyed by step_index, including repeated tools on separate inputs, duration, warnings, insertion reason, eligibility and provenance. Native details expose technical records. Native dialog presents evidence and input identities.
- Browser-local history validates stored values, handles malformed JSON/storage failures and stores up to ten summaries. Replay restores query/scenario selection; real imagery must be retrieved again. No durable server storage is claimed.
- PDF export includes query, outcome, limitations, verification state, thresholds, actual input IDs/source/digests, executed trace, warnings, raster outputs and audit digest. Text wraps and paginates; images retain aspect ratio and stay with their labels. Unsupported standard-font characters are replaced rather than silently rendered as broken glyphs.

## Modified files

- `satquery-ai/src/App.tsx`
- `satquery-ai/src/index.css`
- `satquery-ai/src/api/client.ts`
- `satquery-ai/src/hooks/useQueryHistory.ts`
- `satquery-ai/src/pages/AnalysisPage.tsx`
- `satquery-ai/src/pages/HomePage.tsx`
- `satquery-ai/src/pages/SystemViewPage.tsx`
- `satquery-ai/src/types/index.ts`
- `satquery-ai/src/utils/reportGenerator.ts`
- `satquery-ai/src/components/analysis/FinalAnswerCard.tsx`
- `satquery-ai/src/components/evidence/EvidencePanel.tsx`
- `satquery-ai/src/components/evidence/EvidenceTrailModal.tsx`
- `satquery-ai/src/components/history/QueryHistoryPanel.tsx`
- `satquery-ai/src/components/layout/NavBar.tsx`
- `satquery-ai/src/components/map/AOIMapSelector.tsx`
- `satquery-ai/src/components/query/QueryBox.tsx`
- `satquery-ai/src/components/query/SceneSelector.tsx`
- `satquery-ai/src/components/trace/TracePanel.tsx`
- `satquery-ai/src/components/visualization/VisualOutputs.tsx`
- `satquery-ai/index.html`
- `satquery-ai/tailwind.config.js`
- `satquery-ai/src/api/stream.ts`
- `satquery-ai/tests/frontend.test.cjs`

New documentation: `PHASE2_HANDOVER.md`. Validation artifacts are in `output/phase2/`; temporary baseline hashes and report-reproduction data/scripts are in `tmp/phase2/`. The tracked backend/tsconfig changes visible in git status predate this phase; they were not reverted. Existing tracked Python cache changes were also retained.

## UI architecture and tokens

Existing components remain behind AnalysisPage, which owns query, resolved inputs, execution trace, completion result and request identity. API event adaptation remains in api/client.ts; api/stream.ts owns transport parsing and cleanup. No frontend framework or dependency was added.

Tokens in index.css: --bg, --panel, --surface-subtle, --border, --text-primary, --text-secondary, --text-muted, --accent, --accent-soft, --focus, --danger, --warning, --success, --viewer. Tailwind rs colors map to tokens. Light uses off-white/white/navy; dark uses charcoal/navy surfaces and readable teal. Buttons, fields, dialogs, Leaflet controls and semantic states share these tokens. Existing unused component CSS/assets were retained to avoid unrelated deletion.

## Theme behavior

The head script resolves satquery_theme before React renders, otherwise using prefers-color-scheme. NavBar follows OS changes until a manual light/dark preference is saved. Storage failures fall back to session state. A browser reload confirmed the selected light theme persisted. No external font request is required. Reduced-motion preference disables animation and transitions.

## Responsive behavior

- >=1200px: setup, imagery and results columns; wider screens increase side-panel widths.
- 700-1199px: setup and imagery columns; results span the next row.
- <700px: deliberate Setup / Imagery / Results section controls, wrapping toolbar and visible primary navigation.
- Viewer retains image aspect ratio and supports scrollable zoom. Comparison clips a full-size overlay with inset(0, 100-position%, 0, 0), avoiding the former width distortion. Native range input supports pointer/touch and keyboard; no fabricated geographic overlay.

## Outcome presentation

| Backend outcome | UI label |
| --- | --- |
| completed_supported | Supported computation |
| completed_partial | Partial result |
| abstained | Abstained / insufficient evidence |
| unsupported | Unsupported request |
| failed | Analysis failed |

Unknown/missing outcome is labelled unreported. High heuristic evidence is not verification. Backend runtime low threshold 0.55 and research threshold 0.60 remain distinct; values in run results come from the response. SHA-256 is described as a tamper-evident digest, not a digital signature.

## Validation results

- `python -B -m pytest tests/ -q -p no:cacheprovider`: **80 passed**. Local API tests required running outside the socket-restricted sandbox; the sandbox attempt stalled and was not counted as a pass.
- `node --test tests/frontend.test.cjs` (frontend directory): **9 passed**. Covers split/multiline/CRLF SSE, missing completion, malformed records, suppression after abort, invalid local history and all five rendered outcomes with limitations/unverified wording.
- `node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit --incremental false`: passed.
- `npm run build`: passed (TypeScript and Vite). Existing large-bundle warning remains (main chunk approximately 805 kB minified).
- `npm run lint`: final source/test scan has **0 warnings**, compared with 13 reported at the end of Phase 1. The temporary unused test import was removed.
- `git diff --check`: passed; existing line-ending notices only.

## Browser and PDF evidence

Browser inspected at 1440x1000, 1024x900 and 390x844. Captured files:

- `output/phase2/desktop-light.png`
- `output/phase2/desktop-dark.png`
- `output/phase2/tablet-dark.png`
- `output/phase2/mobile-imagery-dark.png`
- `output/phase2/mobile-aoi-light.png`
- `output/phase2/mobile-system-light.png`
- `output/phase2/home-light.png`

Checked real local demo execution: actual completed_partial result, separate cloud checks for image 1 and image 2, inserted CPU repair for image 2, withheld change percentage, actual factor scores and warnings. Comparison keyboard End/Home/ArrowRight yielded 100/0/1; fit/reset returned 50. Mobile imagery/results navigation and opening the evidence dialog worked; native dialog moved focus to Close. Coordinate entry rejected latitude 95 and enabled retrieval after valid bounds. Mobile System navigation and theme persistence after reload worked. DOM width checks found no horizontal overflow at the inspected tablet/mobile views.

`output/phase2/analysis-report.pdf` is an eight-page report generated from the actual inspected session and its completion response. The original browser download was inspected, then an orphaned-image-caption defect was corrected and the same record regenerated through buildAnalysisReport. Pages were rendered with bundled Poppler; all-page contact sheets and full-size first/last pages were inspected. Corrected renders: `final-report-1.png` through `final-report-8.png`. Poppler reported missing optional Symbol/ArialUnicode display fonts, but the standard-font report rendered legibly. Estimated imagery is labelled explicitly.

## Known limitations and remaining validation

- Physical touch hardware, mouse dragging across the comparison range, full screen-reader testing, automated contrast auditing and every cross-browser combination were not exercised. Native range/dialog semantics are implemented, but these checks remain before accessibility sign-off.
- External Esri tiles, EarthSearch retrieval, Bhoonidhi authentication and stale external-request races were not exercised against live services. Cancellation/identity guards were reviewed and stream cancellation was unit-tested. No external service availability is claimed.
- Browser automation intermittently lost its local connection and one download wait was unusually slow. Screenshots and the completed local run provide evidence for the inspected states, not exhaustive certification. Dialog Escape/focus restoration was not completed after a connection interruption.
- All five outcomes were component-render tested; only completed_partial was exercised end-to-end in the browser during this phase.
- History parsing was tested; full browser replay and quota-failure simulation remain untested. History is local and lossy; it does not persist image pixels or complete traces.
- Navigating away from Analysis unmounts it and disconnects the stream; in-progress workspace state is not retained across page changes. Completed summaries remain in browser history.
- Comparison currently pairs original before/after inputs. Reconstruction is an independently labelled layer; automatic original-to-reconstruction pairing is not inferred when the output contract lacks explicit image identity.
- PDF uses standard Latin fonts and is not a tagged accessible PDF; non-Latin query text needs an embedded Unicode font in future work. The inspected report was a real eight-page run, not an exhaustive arbitrary-length fuzz test.
- Original catalogue previews and lack of verified georeferencing remain Phase 1 limitations. No map coordinates, land-cover labels, SAR fusion, diffusion or learned VQA results are fabricated.
- The existing bundle-size warning remains; report code splitting is a reasonable later performance task.

These limits mean the work is not described as production-ready, independently verified or scientifically validated.

## Suggested Phase 3 research integration

Add explicit capability discovery before exposing any model options. Integrate evaluated learned models behind typed provider contracts with model/version/input provenance, failure outcomes and evidence eligibility. Establish georeferenced/nodata/cloud-valid overlap and registration accuracy before quantitative geographic claims. Keep observation, estimate and diagnostic outputs separately identified per input. Calibrate evidence against independent held-out validation; keep research and runtime policies separate. Add external-connector cancellation fixtures, full keyboard/touch/accessibility regression coverage, Unicode/tagged PDF support and lazy report loading.

## Run commands

From repository root, with the existing Python environment:

```powershell
python -B -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd satquery-ai
npm run dev -- --host 127.0.0.1
```

Default frontend API base is http://localhost:8000; VITE_API_URL can point to another backend. Vite normally starts at port 5173 and selects another port if occupied. The final inspected preview used port 5175. Run checks from the frontend directory with `npm run build`, `npm run lint`, and `node --test tests/frontend.test.cjs`.
