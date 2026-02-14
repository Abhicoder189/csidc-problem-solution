"use client";

import { useState, useEffect } from "react";
import {
  Activity, Ruler, Target, ShieldCheck, AlertTriangle, BarChart3,
  TrendingUp, MapPin, Loader2, ChevronDown, CheckCircle2, XCircle,
  Scale, Building2,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, PieChart, Pie, Cell, Legend,
} from "recharts";
import { getGISAnalysis, getRegionSummary, getComplianceScore } from "@/lib/api";

const GRADE_STYLES = {
  A: { bg: "from-emerald-500 to-emerald-600", text: "text-emerald-400", label: "Excellent" },
  B: { bg: "from-blue-500 to-blue-600", text: "text-blue-400", label: "Good" },
  C: { bg: "from-amber-500 to-amber-600", text: "text-amber-400", label: "Moderate" },
  D: { bg: "from-orange-500 to-orange-600", text: "text-orange-400", label: "Poor" },
  F: { bg: "from-red-500 to-red-600", text: "text-red-400", label: "Critical" },
};

const tooltipStyle = {
  background: "rgba(10,15,30,0.95)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10, color: "#e2e8f0", fontSize: 12,
  boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
};

export default function RegionAnalytics({ regionId }) {
  const [gis, setGIS] = useState(null);
  const [summary, setSummary] = useState(null);
  const [compliance, setCompliance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("overview");

  useEffect(() => {
    if (!regionId) return;
    console.log('RegionAnalytics: Loading data for region:', regionId);
    setLoading(true);
    Promise.all([
      getGISAnalysis(regionId).catch((err) => { console.error('GIS Analysis error:', err); return null; }),
      getRegionSummary(regionId).catch((err) => { console.error('Region Summary error:', err); return null; }),
      getComplianceScore(regionId).catch((err) => { console.error('Compliance Score error:', err); return null; }),
    ]).then(([g, s, c]) => {
      console.log('RegionAnalytics: Data loaded', { gis: !!g, summary: !!s, compliance: !!c });
      setGIS(g);
      setSummary(s);
      setCompliance(c);
    }).finally(() => setLoading(false));
  }, [regionId]);

  if (!regionId) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-center p-8 bg-gradient-to-br from-[#060a13] via-[#0a0f1e] to-[#060a13]">
        <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center border border-indigo-500/20">
          <Target className="w-10 h-10 text-indigo-400" />
        </div>
        <div className="space-y-2">
          <p className="text-base font-bold text-white">Select a Region to View Analytics</p>
          <p className="text-sm text-slate-400 max-w-md">
            Choose a region from the sidebar to view detailed GIS spatial analysis, 
            IoU scores, and compliance grades
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-600 mt-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            <MapPin className="w-3 h-3 text-indigo-400" />
            <span>56 Industrial Regions Available</span>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full gap-3">
        <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
        <span className="text-sm text-slate-500">Analyzing region…</span>
      </div>
    );
  }

  const grade = summary?.compliance_grade || compliance?.grade || "C";
  const gradeStyle = GRADE_STYLES[grade] || GRADE_STYLES.C;
  const compScore = compliance?.compliance_score ?? summary?.compliance?.score ?? 0;

  // Plot analysis data for charts
  const plotAnalysis = gis?.plot_analysis || [];
  const riskDistribution = plotAnalysis.reduce((acc, p) => {
    const sev = p.severity || "low";
    acc[sev] = (acc[sev] || 0) + 1;
    return acc;
  }, {});
  const riskPieData = Object.entries(riskDistribution).map(([k, v]) => ({
    name: k.charAt(0).toUpperCase() + k.slice(1),
    value: v,
    color: { critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#22c55e" }[k] || "#888",
  }));

  // IoU bar chart data (top 20 with lowest IoU)
  const iouData = [...plotAnalysis]
    .sort((a, b) => (a.iou ?? 1) - (b.iou ?? 1))
    .slice(0, 20)
    .map((p) => ({
      plot: p.plot_id?.replace(/_/g, " ").slice(-8) || "?",
      iou: +(p.iou ?? 0).toFixed(3),
      deviation: +(Math.abs(p.area_deviation_pct ?? 0)).toFixed(1),
      risk: +(p.risk_score ?? 0).toFixed(2),
    }));

  // Status distribution
  const statusDist = summary?.status_distribution || {};

  const sections = [
    { key: "overview", label: "Overview", icon: BarChart3 },
    { key: "spatial", label: "Spatial Analysis", icon: Ruler },
    { key: "risk", label: "Risk Assessment", icon: AlertTriangle },
  ];

  return (
    <div className="h-full overflow-y-auto bg-[#060a13] p-5 space-y-5">
      {/* Header with Grade */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-extrabold text-white">{summary?.region_name || regionId}</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {summary?.district || "Chhattisgarh"} • {summary?.category || "Industrial"} • {summary?.total_plots || plotAnalysis.length} plots
          </p>
        </div>
        <div className="flex flex-col items-center">
          <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${gradeStyle.bg} flex items-center justify-center shadow-lg`}>
            <span className="text-2xl font-black text-white">{grade}</span>
          </div>
          <span className={`text-[10px] font-bold mt-1 ${gradeStyle.text}`}>{gradeStyle.label}</span>
        </div>
      </div>

      {/* Score Bar */}
      <div className="card-glass p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-slate-400 font-semibold">Compliance Score</span>
          <span className="text-sm font-extrabold text-white">{compScore}%</span>
        </div>
        <div className="h-3 rounded-full bg-white/[0.06] overflow-hidden">
          <div className="h-full rounded-full transition-all duration-1000 ease-out" style={{
            width: `${compScore}%`,
            background: compScore >= 80 ? "linear-gradient(90deg, #10b981, #34d399)"
              : compScore >= 60 ? "linear-gradient(90deg, #f59e0b, #fbbf24)"
              : "linear-gradient(90deg, #ef4444, #f87171)",
          }} />
        </div>
        <div className="flex justify-between mt-1.5 text-[10px] text-slate-600">
          <span>0</span><span>25</span><span>50</span><span>75</span><span>100</span>
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Avg IoU", value: gis?.summary?.average_iou?.toFixed(3) || "—", icon: Target, color: "text-indigo-400" },
          { label: "Avg Deviation", value: `${(gis?.summary?.average_deviation_pct ?? 0).toFixed(1)}%`, icon: Ruler, color: "text-amber-400" },
          { label: "Avg Risk", value: `${((gis?.summary?.average_risk_score ?? 0) * 100).toFixed(0)}%`, icon: Activity, color: "text-red-400" },
          { label: "High Risk", value: gis?.summary?.high_risk_count ?? 0, icon: AlertTriangle, color: "text-orange-400" },
          { label: "Compliant", value: statusDist["Allotted"] ?? "—", icon: CheckCircle2, color: "text-emerald-400" },
          { label: "Disputed", value: (statusDist["Encroached"] ?? 0) + (statusDist["Disputed"] ?? 0), icon: XCircle, color: "text-red-400" },
        ].map((s, i) => (
          <div key={i} className="card-glass p-3 text-center">
            <s.icon className={`w-4 h-4 mx-auto mb-1 ${s.color}`} />
            <div className="text-lg font-extrabold text-white">{s.value}</div>
            <div className="text-[9px] text-slate-500 uppercase tracking-widest">{s.label}</div>
          </div>
        ))}
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 bg-white/[0.03] rounded-xl p-1 border border-white/[0.06]">
        {sections.map(({ key, label, icon: Icon }) => (
          <button key={key} onClick={() => setActiveSection(key)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeSection === key
                ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/25"
                : "text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] border border-transparent"
            }`}>
            <Icon className="w-3.5 h-3.5" />{label}
          </button>
        ))}
      </div>

      {/* OVERVIEW SECTION */}
      {activeSection === "overview" && (
        <>
          {/* Status distribution */}
          {Object.keys(statusDist).length > 0 && (
            <div className="card-glass p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Building2 className="w-3.5 h-3.5 text-indigo-400" /> Plot Status Distribution
              </h3>
              <div className="space-y-2">
                {Object.entries(statusDist).map(([status, count]) => {
                  const total = Object.values(statusDist).reduce((a, b) => a + b, 0);
                  const pct = total > 0 ? (count / total * 100) : 0;
                  const color = { Allotted: "#ef4444", Available: "#22c55e", "Under Construction": "#f59e0b", Encroached: "#a855f7", Disputed: "#f43f5e" }[status] || "#6b7280";
                  return (
                    <div key={status}>
                      <div className="flex justify-between mb-1">
                        <span className="text-[11px] text-slate-400">{status}</span>
                        <span className="text-[11px] text-slate-300 font-semibold">{count} ({pct.toFixed(0)}%)</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Risk Severity Pie */}
          {riskPieData.length > 0 && (
            <div className="card-glass p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Risk Severity Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie data={riskPieData} cx="50%" cy="50%" outerRadius={75} innerRadius={35}
                    paddingAngle={3} dataKey="value" label={({ name, value }) => `${name}: ${value}`}>
                    {riskPieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* SPATIAL ANALYSIS SECTION */}
      {activeSection === "spatial" && (
        <>
          {/* IoU bar chart */}
          {iouData.length > 0 && (
            <div className="card-glass p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Target className="w-3.5 h-3.5 text-indigo-400" /> IoU Scores (Lowest 20 Plots)
              </h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={iouData} margin={{ top: 5, right: 10, left: -15, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="plot" tick={{ fill: "#64748b", fontSize: 9 }} angle={-45} textAnchor="end" />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} domain={[0, 1]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="iou" fill="#6366f1" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Area deviation chart */}
          {iouData.length > 0 && (
            <div className="card-glass p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <Ruler className="w-3.5 h-3.5 text-amber-400" /> Area Deviation %
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={iouData} margin={{ top: 5, right: 10, left: -15, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="plot" tick={{ fill: "#64748b", fontSize: 9 }} angle={-45} textAnchor="end" />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="deviation" fill="#f59e0b" radius={[3, 3, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* RISK ASSESSMENT SECTION */}
      {activeSection === "risk" && (
        <>
          {/* High-risk plots table */}
          <div className="card-glass p-4">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400" /> Highest Risk Plots
            </h3>
            <div className="overflow-x-auto max-h-[350px] overflow-y-auto">
              <table className="w-full text-[12px]" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-white/[0.08] sticky top-0 bg-[#0a0f1e]/95">
                    {["Plot", "IoU", "Dev %", "Risk", "Severity"].map((h) => (
                      <th key={h} className="px-2 py-2 text-left text-[10px] font-semibold text-slate-500 uppercase">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[...plotAnalysis]
                    .sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
                    .slice(0, 25)
                    .map((p, i) => {
                      const sevColor = { critical: "text-red-400", high: "text-orange-400", medium: "text-amber-400", low: "text-emerald-400" }[p.severity] || "text-slate-400";
                      return (
                        <tr key={i} className="border-b border-white/[0.04] hover:bg-indigo-500/[0.03]">
                          <td className="px-2 py-2 text-slate-300 font-mono">{p.plot_id?.slice(-10)}</td>
                          <td className="px-2 py-2 text-slate-200">{(p.iou ?? 0).toFixed(3)}</td>
                          <td className="px-2 py-2 text-slate-200">{Math.abs(p.area_deviation_pct ?? 0).toFixed(1)}%</td>
                          <td className="px-2 py-2">
                            <div className="flex items-center gap-1">
                              <div className="w-12 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                                <div className="h-full rounded-full" style={{
                                  width: `${(p.risk_score ?? 0) * 100}%`,
                                  background: (p.risk_score ?? 0) > 0.7 ? "#ef4444" : (p.risk_score ?? 0) > 0.4 ? "#f59e0b" : "#22c55e",
                                }} />
                              </div>
                              <span className="text-[10px] text-slate-400">{((p.risk_score ?? 0) * 100).toFixed(0)}%</span>
                            </div>
                          </td>
                          <td className={`px-2 py-2 font-bold text-[10px] uppercase ${sevColor}`}>{p.severity}</td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Risk score distribution */}
          {iouData.length > 0 && (
            <div className="card-glass p-4">
              <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
                <TrendingUp className="w-3.5 h-3.5 text-red-400" /> Risk Score Distribution
              </h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={iouData} margin={{ top: 5, right: 10, left: -15, bottom: 50 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="plot" tick={{ fill: "#64748b", fontSize: 9 }} angle={-45} textAnchor="end" />
                  <YAxis tick={{ fill: "#64748b", fontSize: 10 }} domain={[0, 1]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="risk" radius={[3, 3, 0, 0]}>
                    {iouData.map((entry, i) => (
                      <Cell key={i} fill={entry.risk > 0.7 ? "#ef4444" : entry.risk > 0.4 ? "#f59e0b" : "#22c55e"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* Compliance factors (from compliance score endpoint) */}
      {compliance?.factors && (
        <div className="card-glass p-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3 flex items-center gap-2">
            <Scale className="w-3.5 h-3.5 text-indigo-400" /> Compliance Factors
          </h3>
          <div className="space-y-2">
            {Object.entries(compliance.factors).map(([key, val]) => (
              <div key={key}>
                <div className="flex justify-between mb-1">
                  <span className="text-[11px] text-slate-400 capitalize">{key.replace(/_/g, " ")}</span>
                  <span className="text-[11px] text-slate-300 font-semibold">{(val * 100).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 rounded-full bg-white/[0.04] overflow-hidden">
                  <div className="h-full rounded-full bg-indigo-500" style={{ width: `${val * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
