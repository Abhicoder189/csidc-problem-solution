"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Bell, BellRing, AlertTriangle, ShieldAlert, Clock, ChevronRight,
  Loader2, X, CheckCircle2, Volume2, VolumeX,
} from "lucide-react";
import { getAlerts } from "@/lib/api";

const SEV_STYLE = {
  critical: { bg: "bg-red-500/15", text: "text-red-400", accent: "border-l-red-500" },
  high: { bg: "bg-orange-500/15", text: "text-orange-400", accent: "border-l-orange-500" },
  medium: { bg: "bg-amber-500/15", text: "text-amber-400", accent: "border-l-amber-500" },
  low: { bg: "bg-emerald-500/15", text: "text-emerald-400", accent: "border-l-emerald-500" },
};

export default function AlertsPanel({ isOpen, onClose, onAlertClick }) {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [unreadOnly, setUnreadOnly] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getAlerts(unreadOnly);
      setAlerts(data.alerts || data || []);
    } catch (err) {
      console.error("Alerts load error:", err);
    } finally {
      setLoading(false);
    }
  }, [unreadOnly]);

  useEffect(() => {
    if (isOpen) load();
  }, [isOpen, load]);

  if (!isOpen) return null;

  const criticalCount = alerts.filter((a) => a.severity === "critical").length;
  const highCount = alerts.filter((a) => a.severity === "high").length;

  return (
    <div className="fixed top-14 right-4 z-50 w-[380px] max-h-[70vh] bg-[#0a0f1e]/95 backdrop-blur-2xl border border-white/[0.08] rounded-2xl shadow-2xl shadow-black/50 flex flex-col overflow-hidden fade-in">
      {/* Header */}
      <div className="shrink-0 px-5 pt-4 pb-3 border-b border-white/[0.06]">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center">
              <BellRing className="w-4 h-4 text-amber-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">System Alerts</h3>
              <p className="text-[10px] text-slate-500">{alerts.length} alerts</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/[0.05] transition-colors">
            <X className="w-4 h-4 text-slate-500" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          {criticalCount > 0 && (
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/20">
              {criticalCount} Critical
            </span>
          )}
          {highCount > 0 && (
            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-orange-500/15 text-orange-400 border border-orange-500/20">
              {highCount} High
            </span>
          )}
          <div className="flex-1" />
          <button
            onClick={() => setUnreadOnly(!unreadOnly)}
            className={`text-[10px] font-semibold px-2 py-1 rounded-md transition-all ${
              unreadOnly ? "bg-indigo-500/20 text-indigo-300" : "bg-white/[0.03] text-slate-500"
            }`}
          >
            {unreadOnly ? "Unread Only" : "All Alerts"}
          </button>
        </div>
      </div>

      {/* Alert List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {loading ? (
          <div className="flex items-center justify-center gap-2 p-8">
            <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
            <span className="text-sm text-slate-500">Loading alerts…</span>
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center gap-2 p-8 text-center">
            <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            <p className="text-sm text-slate-400">All clear</p>
            <p className="text-xs text-slate-600">No active alerts</p>
          </div>
        ) : (
          alerts.map((alert, i) => {
            const sev = SEV_STYLE[alert.severity] || SEV_STYLE.low;
            const timeAgo = formatTimeAgo(alert.timestamp || alert.created_at);
            return (
              <button
                key={alert.id || i}
                onClick={() => onAlertClick?.(alert)}
                className={`w-full text-left px-4 py-3 border-b border-white/[0.04] border-l-2 ${sev.accent} hover:bg-white/[0.02] transition-all`}
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 w-7 h-7 rounded-lg ${sev.bg} flex items-center justify-center shrink-0`}>
                    {alert.severity === "critical" ? (
                      <ShieldAlert className={`w-3.5 h-3.5 ${sev.text}`} />
                    ) : (
                      <AlertTriangle className={`w-3.5 h-3.5 ${sev.text}`} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className={`text-[10px] font-bold uppercase ${sev.text}`}>{alert.severity}</span>
                      <span className="text-[10px] text-slate-600">{timeAgo}</span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed">{alert.message}</p>
                    {alert.region_id && (
                      <span className="inline-block mt-1 px-1.5 py-0.5 rounded text-[9px] bg-white/[0.04] text-slate-500">
                        {alert.region_id}
                      </span>
                    )}
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-slate-600 mt-1 shrink-0" />
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}

function formatTimeAgo(timestamp) {
  if (!timestamp) return "";
  const diff = Date.now() - new Date(timestamp).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}
