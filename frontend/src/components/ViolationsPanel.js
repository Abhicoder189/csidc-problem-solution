"use client";

import { useState, useEffect } from "react";
import {
  AlertTriangle, Shield, ShieldAlert, ChevronRight, MapPin,
  Filter, CheckCircle2, Clock, XCircle, Scale, FileText,
  TrendingUp, ArrowUpRight, Eye, Loader2,
} from "lucide-react";
import { getViolations, updateViolation } from "@/lib/api";

const SEVERITY_STYLES = {
  critical: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/25", dot: "bg-red-500" },
  high: { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/25", dot: "bg-orange-500" },
  medium: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/25", dot: "bg-amber-500" },
  low: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/25", dot: "bg-emerald-500" },
};

const STATUS_STYLES = {
  open: { label: "Open", color: "text-red-400", bg: "bg-red-500/10" },
  acknowledged: { label: "Acknowledged", color: "text-amber-400", bg: "bg-amber-500/10" },
  under_review: { label: "Under Review", color: "text-blue-400", bg: "bg-blue-500/10" },
  resolved: { label: "Resolved", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  escalated: { label: "Escalated", color: "text-purple-400", bg: "bg-purple-500/10" },
  dismissed: { label: "Dismissed", color: "text-slate-400", bg: "bg-slate-500/10" },
};

const TYPE_ICONS = {
  encroachment: AlertTriangle,
  unauthorized_construction: ShieldAlert,
  vacant_unused: Eye,
  boundary_deviation: MapPin,
  land_use_violation: Scale,
  partial_construction: Clock,
};

export default function ViolationsPanel({ regionId, onSelectViolation }) {
  const [violations, setViolations] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ severity: null, status: "open" });
  const [selectedViolation, setSelectedViolation] = useState(null);
  const [updating, setUpdating] = useState(null);

  useEffect(() => {
    loadViolations();
  }, [regionId, filter]);

  async function loadViolations() {
    setLoading(true);
    try {
      const data = await getViolations({
        region: regionId || undefined,
        severity: filter.severity || undefined,
        status: filter.status || undefined,
        limit: 100,
      });
      setViolations(data);
    } catch (err) {
      console.error("Load violations failed:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleStatusUpdate(violationId, newStatus) {
    setUpdating(violationId);
    try {
      await updateViolation(violationId, newStatus, `Status changed to ${newStatus}`);
      await loadViolations();
    } catch (err) {
      console.error("Status update failed:", err);
    } finally {
      setUpdating(null);
    }
  }

  const sevFilters = [
    { key: null, label: "All" },
    { key: "critical", label: "Critical" },
    { key: "high", label: "High" },
    { key: "medium", label: "Medium" },
    { key: "low", label: "Low" },
  ];

  const statusFilters = [
    { key: null, label: "All" },
    { key: "open", label: "Open" },
    { key: "acknowledged", label: "Ack'd" },
    { key: "resolved", label: "Resolved" },
    { key: "escalated", label: "Escalated" },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="shrink-0 px-5 pt-5 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center">
            <ShieldAlert className="w-4 h-4 text-red-400" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white">Violation Monitor</h2>
            <p className="text-[10px] text-slate-500">
              {violations ? `${violations.total} violations found` : "Loading…"}
            </p>
          </div>
        </div>

        {/* Severity filter */}
        <div className="flex gap-1 mb-2">
          {sevFilters.map((f) => (
            <button
              key={f.key || "all"}
              onClick={() => setFilter((prev) => ({ ...prev, severity: f.key }))}
              className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-all ${
                filter.severity === f.key
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                  : "bg-white/[0.03] text-slate-500 border border-transparent hover:bg-white/[0.06]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <div className="flex gap-1">
          {statusFilters.map((f) => (
            <button
              key={f.key || "all-s"}
              onClick={() => setFilter((prev) => ({ ...prev, status: f.key }))}
              className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-all ${
                filter.status === f.key
                  ? "bg-white/[0.08] text-slate-200"
                  : "bg-white/[0.02] text-slate-600 hover:bg-white/[0.05]"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Severity summary badges */}
        {violations?.severity_summary && (
          <div className="flex gap-2 mt-2">
            {Object.entries(violations.severity_summary).map(([sev, count]) => {
              const style = SEVERITY_STYLES[sev] || SEVERITY_STYLES.low;
              return (
                <span key={sev} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold ${style.bg} ${style.text} border ${style.border}`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${style.dot}`} />
                  {count} {sev}
                </span>
              );
            })}
          </div>
        )}
      </div>

      {/* Violation List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-8">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
            <span className="text-sm text-slate-500">Loading violations…</span>
          </div>
        ) : !violations?.violations?.length ? (
          <div className="flex flex-col items-center gap-2 p-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            <p className="text-sm text-slate-400">No violations found</p>
            <p className="text-xs text-slate-600">All plots are compliant</p>
          </div>
        ) : (
          violations.violations.map((v) => {
            const sev = SEVERITY_STYLES[v.severity] || SEVERITY_STYLES.low;
            const st = STATUS_STYLES[v.status] || STATUS_STYLES.open;
            const TypeIcon = TYPE_ICONS[v.violation_type] || AlertTriangle;
            const isExpanded = selectedViolation === v.id;

            return (
              <div key={v.id} className="border-b border-white/[0.04]">
                <button
                  onClick={() => setSelectedViolation(isExpanded ? null : v.id)}
                  className="w-full text-left px-4 py-3 hover:bg-white/[0.02] transition-all"
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 w-8 h-8 rounded-lg ${sev.bg} flex items-center justify-center shrink-0`}>
                      <TypeIcon className={`w-4 h-4 ${sev.text}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-xs font-bold text-slate-200 truncate">{v.plot_id}</span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${sev.bg} ${sev.text}`}>
                          {v.severity}
                        </span>
                        <span className={`px-1.5 py-0.5 rounded text-[9px] font-medium ${st.bg} ${st.color}`}>
                          {st.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate">{v.violation_label}</p>
                      <div className="flex items-center gap-3 mt-1 text-[10px] text-slate-500">
                        <span>IoU: {v.iou_score?.toFixed(2)}</span>
                        <span>Dev: {v.area_deviation_pct?.toFixed(1)}%</span>
                        <span>Risk: {(v.risk_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                    <ChevronRight className={`w-4 h-4 text-slate-600 transition-transform ${isExpanded ? "rotate-90" : ""}`} />
                  </div>
                </button>

                {/* Expanded detail */}
                {isExpanded && (
                  <div className="px-4 pb-3 space-y-2 fade-in">
                    <div className="bg-white/[0.02] rounded-lg p-3 text-xs space-y-1.5">
                      <p className="text-slate-400">{v.description}</p>
                      <div className="grid grid-cols-2 gap-2 mt-2">
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase">Encroachment Area</span>
                          <p className="text-slate-200 font-semibold">{v.encroachment_area_sqm?.toLocaleString()} m²</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase">Confidence</span>
                          <p className="text-slate-200 font-semibold">{(v.confidence * 100).toFixed(0)}%</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase">Legal Section</span>
                          <p className="text-slate-200 text-[10px]">{v.legal_section}</p>
                        </div>
                        <div>
                          <span className="text-[10px] text-slate-500 uppercase">Penalty Range</span>
                          <p className="text-slate-200 text-[10px]">{v.penalty_range}</p>
                        </div>
                      </div>
                      {v.assigned_to && (
                        <div className="mt-2 pt-2 border-t border-white/[0.04]">
                          <span className="text-[10px] text-slate-500 uppercase">Assigned To</span>
                          <p className="text-slate-300 font-medium">{v.assigned_to}</p>
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    {v.status === "open" && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStatusUpdate(v.id, "acknowledged")}
                          disabled={updating === v.id}
                          className="flex-1 flex items-center justify-center gap-1 py-2 rounded-lg bg-amber-500/10 text-amber-400 text-[11px] font-semibold hover:bg-amber-500/20 transition-all border border-amber-500/20"
                        >
                          {updating === v.id ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
                          Acknowledge
                        </button>
                        <button
                          onClick={() => handleStatusUpdate(v.id, "escalated")}
                          disabled={updating === v.id}
                          className="flex-1 flex items-center justify-center gap-1 py-2 rounded-lg bg-red-500/10 text-red-400 text-[11px] font-semibold hover:bg-red-500/20 transition-all border border-red-500/20"
                        >
                          <ArrowUpRight className="w-3 h-3" />
                          Escalate
                        </button>
                      </div>
                    )}
                    {v.status === "acknowledged" && (
                      <div className="flex gap-2">
                        <button
                          onClick={() => handleStatusUpdate(v.id, "resolved")}
                          disabled={updating === v.id}
                          className="flex-1 flex items-center justify-center gap-1 py-2 rounded-lg bg-emerald-500/10 text-emerald-400 text-[11px] font-semibold hover:bg-emerald-500/20 transition-all border border-emerald-500/20"
                        >
                          <CheckCircle2 className="w-3 h-3" />
                          Mark Resolved
                        </button>
                        <button
                          onClick={() => handleStatusUpdate(v.id, "escalated")}
                          disabled={updating === v.id}
                          className="flex-1 flex items-center justify-center gap-1 py-2 rounded-lg bg-red-500/10 text-red-400 text-[11px] font-semibold hover:bg-red-500/20 transition-all border border-red-500/20"
                        >
                          <ArrowUpRight className="w-3 h-3" />
                          Escalate
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
