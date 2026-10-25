import jsPDF from 'jspdf';
import type { ImageMetadata, LiveTraceItem, VisualOutput } from '../types';

interface ReportData {
  outcome?: string;
  limitations?: string[];
  verified?: boolean;
  scoreKind?: string;
  auditHash?: string;
  thresholdPolicy?: { low_evidence: number; high_evidence: number; research: number };
  query: string;
  analysisId: string;
  aoiName?: string;
  images: ImageMetadata[];
  traceItems: LiveTraceItem[];
  finalAnswer: string;
  confidence: number;
  confidenceLevel: string;
  evidenceStatus: string;
  evidencePoints: string[];
  visualOutputs: VisualOutput[];
}


// Standard PDF fonts are limited to Latin text. Keep punctuation deterministic.
const printable = (value: unknown) => String(value ?? 'Not reported').replace(/[\u2013\u2014]/g, '-').replace(/[\u2018\u2019]/g, "'").replace(/[\u201c\u201d]/g, '"').replace(/[^\x20-\x7e\n\r\u00a0-\u00ff]/g, '?');

export function buildAnalysisReport(data: ReportData): jsPDF {
  const doc = new jsPDF({ unit: 'mm', format: 'a4' });
  let y = 22;
  const ensure = (height = 6) => { if (y + height > 277) { doc.addPage(); y = 22; } };
  const text = (value: unknown, bold = false) => {
    doc.setFont('helvetica', bold ? 'bold' : 'normal');
    doc.setFontSize(9); doc.setTextColor(30, 48, 64);
    const lines: string[] = doc.splitTextToSize(printable(value), 178);
    for (const line of lines) { ensure(); doc.text(line, 16, y); y += 4.8; }
    y += 2;
  };
  const section = (title: string) => {
    ensure(18); y += 4; doc.setDrawColor(190, 205, 214); doc.line(16, y, 194, y); y += 7;
    text(title.toUpperCase(), true);
  };
  doc.setFont('helvetica', 'bold'); doc.setFontSize(20); doc.setTextColor(15, 64, 69);
  doc.text('SatQuery AI', 16, y); y += 9;
  text('Earth-observation analysis record');
  text(`Analysis: ${data.analysisId}`);
  text(`Exported: ${new Date().toISOString()}`);
  section('Request and outcome');
  text(`Query: ${data.query}`);
  if (data.aoiName) text(`Requested area: ${data.aoiName} (request context, not verified image extent)`);
  text(`Outcome: ${data.outcome ?? 'Not reported'}`, true);
  text(`Verification: ${data.verified === true ? 'Backend reports verified' : data.verified === false ? 'Not independently verified' : 'Not reported'}`);
  text(data.finalAnswer);
  section('Limitations');
  if (!data.limitations?.length) text('No separate limitations were returned. This does not establish validity.');
  data.limitations?.forEach(item => text(`- ${item}`));
  section('Evidence');
  text(`Evidence score: ${Number.isFinite(data.confidence) ? data.confidence.toFixed(3) : 'Not reported'} / 1; band: ${data.confidenceLevel}`);
  text(`Score kind: ${data.scoreKind ?? 'Not reported'}. Heuristic evidence is not a calibrated probability or independent verification.`);
  text(`Evidence status: ${data.evidenceStatus}`);
  if (data.thresholdPolicy) text(`Backend thresholds: low ${data.thresholdPolicy.low_evidence}; high ${data.thresholdPolicy.high_evidence}; separate research threshold ${data.thresholdPolicy.research}.`);
  data.evidencePoints.forEach(point => text(`- ${point}`));
  section('Resolved input identities');
  if (!data.images.length) text('No input metadata returned.');
  data.images.forEach((image, index) => {
    text(`Input ${index + 1}: ${image.image_id || 'Identity not reported'}`, true);
    text(`File: ${image.filename}; type: ${image.image_type}; sensor: ${image.sensor}`);
    text(`Acquisition: ${image.acquisition_date}; resolution: ${image.resolution_m == null ? 'Unknown' : image.resolution_m + ' m'}; dimensions: ${image.width_px} x ${image.height_px} pixels`);
    text(`Source: ${image.source ?? 'Not reported'}; provenance: ${image.provenance ?? 'Not reported'}`);
    text(`Cloud coverage: ${image.cloud_coverage_pct == null ? 'Not measured' : image.cloud_coverage_pct + '%'}; status: ${image.cloud_status}`);
    text(`Pixel SHA-256: ${image.pixel_sha256 ?? 'Not reported'}`);
  });
  section('Actual execution record');
  if (!data.traceItems.length) text('No tool events returned.');
  data.traceItems.forEach(item => {
    text(`Step ${item.step_index}: ${item.tool_name} / ${item.status}${item.is_auto_inserted ? ' / automatically inserted' : ''}`, true);
    text(`Duration: ${item.execution_time_ms == null ? 'Not reported' : item.execution_time_ms + ' ms'}; warnings: ${item.warnings?.length ?? 0}`);
    text(`Execution: ${item.execution_mode ?? 'Not reported'}; provenance: ${item.input_provenance ?? 'Not reported'}; algorithm: ${item.algorithm ?? 'Not reported'}`);
    if (item.message) text(item.message);
    if (item.metadata) Object.entries(item.metadata).filter(([key]) => !key.includes('b64')).forEach(([key, value]) => text(`${key}: ${typeof value === 'object' ? JSON.stringify(value) : value}`));
    item.warnings?.forEach(warning => text(`Warning: ${warning}`));
  });
  section('Raster outputs');
  const seen = new Set<string>();
  data.visualOutputs.forEach(output => {
    if (!output.b64 || seen.has(output.type + output.b64)) return;
    seen.add(output.type + output.b64);
    const meaning = output.type === 'reconstruction' ? 'Estimated pixels - CPU inpainting, not an observation' : ['before', 'after', 'optical', 'sar'].includes(output.type) ? 'Supplied raster / original observation; see input provenance' : 'Computed diagnostic output';
    try {
      const uri = `data:image/png;base64,${output.b64}`;
      const properties = doc.getImageProperties(uri);
      const scale = Math.min(178 / properties.width, 110 / properties.height);
      const width = properties.width * scale, height = properties.height * scale;
      ensure(height + 36); section(output.label); text(meaning);
      ensure(height + 5); doc.addImage(uri, 'PNG', 16, y, width, height); y += height + 6;
    } catch { text('Image could not be included; inspect the workspace output.'); }
  });
  section('Audit provenance');
  text(`Audit SHA-256: ${data.auditHash ?? 'Not reported'}`);
  text('A SHA-256 digest is tamper-evident when compared with a trusted digest. It is not a digital signature, proof of authenticity or scientific validation.');
  const count = doc.getNumberOfPages();
  for (let page = 1; page <= count; page++) {
    doc.setPage(page); doc.setDrawColor(190, 205, 214); doc.line(16, 283, 194, 283);
    doc.setFont('helvetica', 'normal'); doc.setFontSize(8); doc.setTextColor(75, 94, 105);
    doc.text('SatQuery AI / Evidence and provenance record', 16, 289);
    doc.text(`${page} / ${count}`, 194, 289, { align: 'right' });
  }
  return doc;
}

export async function generateAnalysisReport(data: ReportData): Promise<void> {
  const doc = buildAnalysisReport(data);
  doc.save(`SatQuery_Analysis_${data.analysisId.slice(0, 8)}_${Date.now()}.pdf`);
}
