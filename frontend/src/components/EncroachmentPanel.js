"use client";

import {
  AlertTriangle,
  ShieldCheck,
  Target,
  Ruler,
  Activity,
  TrendingUp,
} from "lucide-react";

const SEVERITY_COLORS = {
  critical: { bg: "rgba(239,68,68,0.12)", border: "rgba(239,68,68,0.25)", text: "#f87171", dot: "#ef4444" },
  high: { bg: "rgba(249,115,22,0.12)", border: "rgba(249,115,22,0.25)", text: "#fb923c", dot: "#f97316" },
  medium: { bg: "rgba(234,179,8,0.12)", border: "rgba(234,179,8,0.25)", text: "#facc15", dot: "#eab308" },
  low: { bg: "rgba(34,197,94,0.12)", border: "rgba(34,197,94,0.25)", text: "#4ade80", dot: "#22c55e" },
};

const TYPE_LABELS = {
  outside_boundary: "Outside Boundary",
  vacant_plot: "Vacant Plot",
  partial_construction: "Partial Construction",
};

const ACTIVITY_COLORS = {
  RUNNING: "#10b981",
  CLOSED: "#ef4444",
  UNDER_CONSTRUCTION: "#f59e0b",
  IDLE: "#64748b",
};

export default function EncroachmentPanel({ data }) {
  if (!data || !data.encroachments) return null;

  const {
    encroachments,
    total_plots,
    compliance_score,
    avg_iou,
    total_affected_area_sqm,
  } = data;
  const criticalOrHigh = encroachments.filter(
    (e) => e.severity === "critical" || e.severity === "high"
  );

  const scoreColor =
    compliance_score > 70
      ? "#10b981"
      : compliance_score > 40
      ? "#f59e0b"
      : "#ef4444";

  return (
    <div className="rounded-2xl bg-[#0a0f1e]/90 backdrop-blur-2xl border border-white/[0.08] shadow-2xl shadow-black/40 overflow-hidden fade-in">
      {/* Header */}
      <div className="px-4 py-3 border-b border-white/[0.06] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-amber-500/10 flex items-center justify-center">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-white">
              Encroachment Alerts
            </h3>
            <span className="text-[10px] text-slate-500">
              {encroachments.length} detected
            </span>
          </div>
        </div>
        {compliance_score != null && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold"
            style={{
              background: `${scoreColor}15`,
              color: scoreColor,
              border: `1px solid ${scoreColor}30`,
            }}
          >
            <ShieldCheck className="w-3 h-3" />
            {compliance_score}
          </div>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-px bg-white/[0.04]">
        {[
          {
            icon: Target,
            label: "Plots",
            value: total_plots,
            color: "text-indigo-400",
          },
          {
            icon: Ruler,
            label: "Affected",
            value: `${(total_affected_area_sqm || 0).toLocaleString()} m²`,
            color: "text-amber-400",
          },
          {
            icon: TrendingUp,
            label: "Avg IoU",
            value:
              avg_iou != null ? `${(avg_iou * 100).toFixed(1)}%` : "—",
            color: "text-indigo-400",
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="bg-[#0a0f1e] px-3 py-2.5 text-center"
          >
            <stat.icon
              className={`w-3 h-3 mx-auto mb-1 ${stat.color}`}
            />
            <div className="text-xs font-bold text-slate-200">
              {stat.value}
            </div>
            <div className="text-[9px] text-slate-600 uppercase tracking-wider">
              {stat.label}
            </div>
          </div>
        ))}
      </div>

      {/* Alert list */}
      <div className="max-h-52 overflow-y-auto scrollbar-thin">
        {criticalOrHigh.length === 0 ? (
          <div className="flex items-center justify-center gap-2 py-5 text-xs text-emerald-400">
            <ShieldCheck className="w-4 h-4" />
            No critical alerts detected
          </div>
        ) : (
          <div className="p-2 space-y-1.5">
            {criticalOrHigh.map((e, i) => {
              const sev = SEVERITY_COLORS[e.severity] || SEVERITY_COLORS.medium;
              return (
                <div
                  key={i}
                  className="rounded-lg px-3 py-2.5 transition-all duration-150 hover:scale-[1.01] cursor-default"
                  style={{
                    background: sev.bg,
                    borderLeft: `3px solid ${sev.dot}`,
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-200">
                      {e.plot_id}
                    </span>
                    <span
                      className="text-[10px] font-bold px-2 py-0.5 rounded-md"
                      style={{
                        background: `${sev.dot}20`,
                        color: sev.text,
                      }}
                    >
                      {e.severity?.toUpperCase()}
                    </span>
                  </div>
                  {e.plot_name && (
                    <div className="text-[11px] text-slate-400 mb-1.5">
                      {e.plot_name}
                    </div>
                  )}
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[10px] text-slate-500">
                    <span className="flex items-center gap-1">
                      <Ruler className="w-2.5 h-2.5" />
                      {TYPE_LABELS[e.encroachment_type] || e.encroachment_type}
                    </span>
                    <span>
                      {e.affected_area_sqm?.toLocaleString()} m²
                    </span>
                    {e.risk_score != null && (
                      <span
                        style={{
                          color:
                            e.risk_score > 0.6 ? "#ef4444" : "#f59e0b",
                        }}
                      >
                        Risk: {(e.risk_score * 100).toFixed(0)}%
                      </span>
                    )}
                    {e.iou_score != null && (
                      <span>IoU: {(e.iou_score * 100).toFixed(1)}%</span>
                    )}
                    {e.activity_status && (
                      <span
                        className="flex items-center gap-0.5"
                        style={{
                          color:
                            ACTIVITY_COLORS[e.activity_status] || "#94a3b8",
                        }}
                      >
                        <Activity className="w-2.5 h-2.5" />
                        {e.activity_status}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
