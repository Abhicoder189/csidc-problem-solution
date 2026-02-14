import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const api = axios.create({ baseURL: API_URL, timeout: 60000 });

/* ── Region Search ─────────────────────────────────────────────── */
export async function searchRegions(query) {
  const { data } = await api.get("/search-regions", { params: { q: query } });
  return data;
}

/* ── Fetch Imagery ─────────────────────────────────────────────── */
export async function fetchImagery(params) {
  const { data } = await api.post("/fetch-imagery", params);
  return data;
}

/* ── Enhance Image ─────────────────────────────────────────────── */
export async function enhanceImage(imageUrl, scaleFactor = 4) {
  const { data } = await api.post("/enhance-image", {
    image_url: imageUrl,
    scale_factor: scaleFactor,
  });
  return data;
}

/* ── Change Detection ──────────────────────────────────────────── */
export async function detectChange(params) {
  const { data } = await api.post("/detect-change", params);
  return data;
}

/* ── Plot Timeline Analysis ────────────────────────────────────── */
export async function analyzePlotTimeline(params) {
  const { data } = await api.post("/plot/timeline-analysis", params);
  return data;
}

/* ── Encroachment Detection ────────────────────────────────────── */
export async function detectEncroachment(params) {
  const { data } = await api.post("/detect-encroachment", params);
  return data;
}

/* ── Generate Report ───────────────────────────────────────────── */
export async function generateReport(params) {
  const { data, headers } = await api.post("/generate-report", params, {
    responseType: "blob",
  });

  // Trigger download directly from blob
  const url = window.URL.createObjectURL(new Blob([data], { type: "application/pdf" }));
  const link = document.createElement("a");
  link.href = url;

  // Try to get filename from headers
  let fileName = `ILMCS_Report_${Date.now()}.pdf`;
  const disposition = headers["content-disposition"];
  if (disposition && disposition.indexOf("filename=") !== -1) {
    const matches = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/.exec(disposition);
    if (matches != null && matches[1]) {
      fileName = matches[1].replace(/['"]/g, "");
    }
  }

  link.setAttribute("download", fileName);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);

  return { success: true };
}

/* ── Dashboard ─────────────────────────────────────────────────── */
export async function getDashboard() {
  const { data } = await api.get("/dashboard/"); // Ensure trailing slash for root router path
  return data;
}

/* ── Compliance Heatmap ────────────────────────────────────────── */
export async function getComplianceHeatmap() {
  const { data } = await api.get("/dashboard/heatmap");
  return data;
}

/* ── Trend Analytics ───────────────────────────────────────────── */
export async function getTrendAnalytics(regionId = null) {
  const { data } = await api.get("/dashboard/trend-analytics", {
    params: regionId ? { region_id: regionId } : {},
  });
  return data;
}

/* ── Compliance Score ──────────────────────────────────────────── */
export async function getComplianceScore(regionId) {
  const { data } = await api.get(`/compliance-score/${regionId}`);
  return data;
}

/* ── Violations ────────────────────────────────────────────────── */
export async function getViolations(params = {}) {
  const { data } = await api.get("/violations", { params });
  return data;
}

/* ── Update Violation Status ───────────────────────────────────── */
export async function updateViolation(violationId, newStatus, note = "") {
  const { data } = await api.patch(`/violations/${violationId}`, null, {
    params: { new_status: newStatus, note },
  });
  return data;
}

/* ── Alerts ────────────────────────────────────────────────────── */
export async function getAlerts(unreadOnly = false) {
  const { data } = await api.get("/alerts", { params: { unread_only: unreadOnly } });
  return data;
}

/* ── GIS Spatial Analysis ──────────────────────────────────────── */
export async function getGISAnalysis(regionId) {
  const { data } = await api.get(`/gis-analysis/${regionId}`);
  return data;
}

/* ── Region Summary ────────────────────────────────────────────── */
export async function getRegionSummary(regionId) {
  const { data } = await api.get(`/region-summary/${regionId}`);
  return data;
}

/* ── Violation Types ───────────────────────────────────────────── */
export async function getViolationTypes() {
  const { data } = await api.get("/violation-types");
  return data;
}

/* ── Audit Log ─────────────────────────────────────────────────── */
export async function getAuditLog(params = {}) {
  const { data } = await api.get("/audit-log", { params });
  return data;
}
