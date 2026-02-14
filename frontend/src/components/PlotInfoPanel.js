"use client";

import {
  X,
  MapPin,
  Building2,
  Grid3X3,
  Hash,
  Factory,
  Shield,
  Eye,
  FileText,
  ChevronRight,
  AlertTriangle,
  User,
  Calendar,
  Clock,
  Ruler,
  TrendingUp,
  History,
} from "lucide-react";
import { useState } from "react";
import PlotHistoryViewer from "./PlotHistoryViewer";

const STATUS_STYLES = {
  Allotted: {
    bg: "bg-red-500/15",
    text: "text-red-400",
    border: "border-red-500/30",
    dot: "bg-red-400",
    label: "Allotted",
  },
  Available: {
    bg: "bg-emerald-500/15",
    text: "text-emerald-400",
    border: "border-emerald-500/30",
    dot: "bg-emerald-400",
    label: "Available",
  },
  "Under Construction": {
    bg: "bg-amber-500/15",
    text: "text-amber-400",
    border: "border-amber-500/30",
    dot: "bg-amber-400",
    label: "Under Construction",
  },
  Encroached: {
    bg: "bg-purple-500/15",
    text: "text-purple-400",
    border: "border-purple-500/30",
    dot: "bg-purple-400",
    label: "Encroached",
  },
  Disputed: {
    bg: "bg-rose-500/15",
    text: "text-rose-400",
    border: "border-rose-500/30",
    dot: "bg-rose-400",
    label: "Disputed",
  },
};

function InfoRow({ icon: Icon, label, value, valueClass = "" }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-white/[0.04] last:border-b-0">
      <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-slate-400" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] text-slate-500 uppercase tracking-wider font-medium">
          {label}
        </p>
        <p className={`text-sm text-slate-200 font-medium mt-0.5 ${valueClass}`}>
          {value}
        </p>
      </div>
    </div>
  );
}

export default function PlotInfoPanel({ plot, onClose }) {
  const [showHistory, setShowHistory] = useState(false);
  
  if (!plot) return null;

  const status = STATUS_STYLES[plot.status] || STATUS_STYLES["Available"];
  const riskPct = Math.round((plot.risk_score || 0) * 100);
  const riskColor =
    riskPct > 70
      ? "text-red-400"
      : riskPct > 40
        ? "text-amber-400"
        : "text-emerald-400";
  const riskBarColor =
    riskPct > 70
      ? "bg-red-500"
      : riskPct > 40
        ? "bg-amber-500"
        : "bg-emerald-500";

  return (
    <div className="plot-info-panel slide-in-right flex flex-col h-full">
      {/* ─── Header ─── */}
      <div className="shrink-0 px-5 pt-5 pb-4 border-b border-white/[0.06]">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-indigo-400 dot-pulse" />
              <span className="text-[10px] text-slate-500 uppercase tracking-widest font-semibold">
                Plot Details
              </span>
            </div>
            <h2 className="text-lg font-bold text-white truncate">
              {plot.plot_id}
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">{plot.region_name}</p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4 text-slate-400" />
          </button>
        </div>

        {/* Status Badge */}
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border ${status.bg} ${status.text} ${status.border}`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${status.dot}`} />
            {status.label}
          </span>
          {(plot.status === "Encroached" || plot.status === "Disputed") && (
            <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-yellow-500/10 text-yellow-400 text-[10px] font-semibold border border-yellow-500/20">
              <AlertTriangle className="w-3 h-3" />
              VIOLATION
            </span>
          )}
        </div>
      </div>

      {/* ─── Content ─── */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-5 py-3">
        {/* Primary Details */}
        <div className="space-y-0.5">
          <InfoRow
            icon={Building2}
            label="District"
            value={plot.district}
          />
          <InfoRow
            icon={Factory}
            label="Industrial Area"
            value={plot.region_name}
          />
          <InfoRow
            icon={Grid3X3}
            label="Sector / Block"
            value={`Sector ${plot.sector}`}
          />
          <InfoRow
            icon={Hash}
            label="Plot Number"
            value={`Plot #${plot.plot_number}`}
          />
          <InfoRow
            icon={Factory}
            label="Plot Type"
            value={plot.plot_type}
          />
          <InfoRow
            icon={Ruler}
            label="Area"
            value={`${plot.area_sqm?.toLocaleString()} m² (${(plot.area_sqm / 10000).toFixed(2)} ha)`}
          />
          <InfoRow
            icon={MapPin}
            label="Coordinates (WGS84)"
            value={`${plot.latitude?.toFixed(6)}°N, ${plot.longitude?.toFixed(6)}°E`}
            valueClass="font-mono text-xs"
          />
        </div>

        {/* Risk Score */}
        <div className="mt-4 p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-slate-400" />
              <span className="text-xs font-semibold text-slate-300">
                Risk Score
              </span>
            </div>
            <span className={`text-lg font-bold ${riskColor}`}>{riskPct}%</span>
          </div>
          <div className="w-full h-2 rounded-full bg-white/[0.06] overflow-hidden">
            <div
              className={`h-full rounded-full ${riskBarColor} transition-all duration-500`}
              style={{ width: `${riskPct}%` }}
            />
          </div>
          <p className="text-[10px] text-slate-500 mt-1.5">
            {riskPct > 70
              ? "High risk — immediate attention required"
              : riskPct > 40
                ? "Moderate risk — monitoring recommended"
                : "Low risk — compliant"}
          </p>
        </div>

        {/* Allottee Info */}
        {plot.allottee && (
          <div className="mt-4 p-3.5 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <div className="flex items-center gap-2 mb-3">
              <User className="w-4 h-4 text-indigo-400" />
              <span className="text-xs font-semibold text-slate-300">
                Allottee Information
              </span>
            </div>
            <div className="space-y-2">
              <div>
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">
                  Company Name
                </p>
                <p className="text-sm text-slate-200 font-medium mt-0.5">
                  {plot.allottee.name}
                </p>
              </div>
              <div className="flex gap-4">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">
                    Lease Start
                  </p>
                  <p className="text-xs text-slate-300 mt-0.5 flex items-center gap-1">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    {plot.allottee.lease_start}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-wider">
                    Lease Period
                  </p>
                  <p className="text-xs text-slate-300 mt-0.5 flex items-center gap-1">
                    <Clock className="w-3 h-3 text-slate-500" />
                    {plot.allottee.lease_years} years
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ─── F
          onClick={() => setShowHistory(true)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-blue-500 text-white text-sm font-semibold shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 transition-all"
        >
          <History className="w-4 h-4" />
          View Historical Timeline
          <ChevronRight className="w-4 h-4 ml-auto" />
        </button>
        <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 transition-all">
          <Eye className="w-4 h-4" />
          View Satellite Imagery
          <ChevronRight className="w-4 h-4 ml-auto" />
        </button>
        <button
          onClick={async () => {
            try {
              const { generateReport } = await import("@/lib/api");
              await generateReport({
                region_name: plot.region_name || plot.region_id || "",
                include_encroachment: true,
                include_change_detection: false,
              });
            } catch (e) {
              console.error("Report generation failed:", e);
            }
          }}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-slate-300 text-sm font-medium border border-white/[0.06] transition-all"
        >
          <FileText className="w-4 h-4" />
          Download Report (PDF)
          <ChevronRight className="w-4 h-4 ml-auto" />
        </button>
      </div>

      {/* Plot History Viewer Modal */}
      {showHistory && (
        <PlotHistoryViewer
          plot={plot}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
}
