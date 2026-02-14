"use client";
import { useState, useEffect } from "react";
import {
  Factory,
  Grid3X3,
  AlertTriangle,
  ShieldAlert,
  BarChart3,
  Building2,
  TrendingUp,
  ShieldCheck,
  Loader2,
} from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  PieChart, Pie, Cell,
  LineChart, Line, Area, AreaChart
} from "recharts";
import { getDashboard, getTrendAnalytics } from "@/lib/api";

const SEVERITY_COLORS = {
  critical: "#ef4444",
  high: "#f97316",
  medium: "#eab308",
  low: "#22c55e",
};

const COMPLIANCE_COLORS = {
  compliant: "#10b981",
  minor_issues: "#f59e0b",
  non_compliant: "#f97316",
  critical: "#ef4444",
};

const COMPLIANCE_LABELS = {
  compliant: "Compliant",
  minor_issues: "Minor Issues",
  non_compliant: "Non-Compliant",
  critical: "Critical",
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [trends, setTrends] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    async function load() {
      try {
        const [dashData, trendData] = await Promise.all([
          getDashboard(),
          getTrendAnalytics(),
        ]);
        setStats(dashData);
        setTrends(trendData);
      } catch (err) {
        console.error("Dashboard load error:", err);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full bg-[#060a13]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
          <span className="text-sm text-slate-500 font-medium">Loading dashboard…</span>
        </div>
      </div>
    );
  }

  if (!stats) return <p className="text-red-400 p-6">Failed to load dashboard data.</p>;

  const kpis = [
    { label: "Regions Monitored", value: stats.total_regions, icon: Factory, color: "from-indigo-600 to-violet-600", iconColor: "text-indigo-400", shadow: "shadow-indigo-500/15" },
    { label: "Total Plots", value: stats.total_plots, icon: Grid3X3, color: "from-blue-600 to-cyan-600", iconColor: "text-blue-400", shadow: "shadow-blue-500/15" },
    { label: "Active Alerts", value: stats.active_alerts, icon: AlertTriangle, color: "from-orange-600 to-amber-600", iconColor: "text-orange-400", shadow: "shadow-orange-500/15" },
    { label: "Critical Alerts", value: stats.critical_alerts, icon: ShieldAlert, color: "from-red-600 to-rose-600", iconColor: "text-red-400", shadow: "shadow-red-500/15" },
    { label: "Avg Utilization", value: `${stats.avg_utilization_pct}%`, icon: BarChart3, color: "from-emerald-600 to-teal-600", iconColor: "text-emerald-400", shadow: "shadow-emerald-500/15" },
    { label: "New Structures", value: stats.newly_detected_structures, icon: Building2, color: "from-purple-600 to-fuchsia-600", iconColor: "text-purple-400", shadow: "shadow-purple-500/15" },
  ];

  // Compliance breakdown for donut chart
  const complianceData = stats.compliance_breakdown
    ? Object.entries(stats.compliance_breakdown).map(([key, val]) => ({
      name: COMPLIANCE_LABELS[key] || key,
      value: val,
      color: COMPLIANCE_COLORS[key] || "#888",
    }))
    : [];

  // Monthly trend for line chart
  const monthlyTrend = stats.monthly_trend || [];

  // Severity breakdown for pie chart
  const severityData = stats.severity_breakdown
    ? Object.entries(stats.severity_breakdown).map(([key, val]) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      value: val,
      color: SEVERITY_COLORS[key] || "#888",
    }))
    : [];

  // Top utilization regions (bar chart data — show top 20)
  const utilizationData = (stats.utilization_by_region || []).slice(0, 20).map((r) => ({
    name: r.region.length > 12 ? r.region.slice(0, 12) + "…" : r.region,
    utilization: r.utilization_pct,
    plots: r.plots,
    encroachments: r.encroachments,
  }));

  // Trend analytics data
  const trendHistorical = trends?.historical?.slice(-12) || [];
  const trendForecasts = trends?.forecasts || [];

  const tabs = [
    { key: "overview", label: "Overview", icon: BarChart3 },
    { key: "trends", label: "Trends", icon: TrendingUp },
    { key: "compliance", label: "Compliance", icon: ShieldCheck },
  ];

  return (
    <div className="h-full overflow-y-auto bg-[#060a13] p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-extrabold bg-gradient-to-r from-indigo-400 via-violet-400 to-purple-400 bg-clip-text text-transparent">
            ILMCS Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Industrial Land Monitoring & Compliance — Chhattisgarh
          </p>
        </div>
        <div className="flex gap-1.5 bg-white/[0.03] rounded-xl p-1 border border-white/[0.06]">
          {tabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${
                activeTab === key
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/25"
                  : "text-slate-500 hover:text-slate-300 hover:bg-white/[0.04] border border-transparent"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-6">
        {kpis.map((kpi, i) => (
          <div
            key={i}
            className={`relative rounded-xl bg-white/[0.03] border border-white/[0.06] p-4 overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:shadow-lg ${kpi.shadow} group`}
          >
            <div className={`absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r ${kpi.color}`} />
            <div className={`w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center mb-3 group-hover:scale-110 transition-transform`}>
              <kpi.icon className={`w-4 h-4 ${kpi.iconColor}`} />
            </div>
            <div className="text-xl font-extrabold text-slate-100">{kpi.value}</div>
            <div className="text-[10px] text-slate-500 mt-1 uppercase tracking-widest">{kpi.label}</div>
          </div>
        ))}
      </div>

      {/* === OVERVIEW TAB === */}
      {activeTab === "overview" && (
        <>
          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr_1fr] gap-4 mb-6">
            {/* Utilization Bar Chart */}
            <div className="card-glass p-5">
              <h3 className="card-header">Land Utilization by Region</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={utilizationData} margin={{ top: 5, right: 20, left: -10, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 10 }} angle={-45} textAnchor="end" />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Bar dataKey="utilization" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Severity Pie */}
            <div className="card-glass p-5">
              <h3 className="card-header">Alert Severity</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={severityData} cx="50%" cy="50%" outerRadius={90} innerRadius={40} paddingAngle={3} dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}>
                    {severityData.map((entry, i) => (<Cell key={i} fill={entry.color} />))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Compliance Donut */}
            <div className="card-glass p-5">
              <h3 className="card-header">Compliance Status</h3>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie data={complianceData} cx="50%" cy="50%" outerRadius={90} innerRadius={50} paddingAngle={4} dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}>
                    {complianceData.map((entry, i) => (<Cell key={i} fill={entry.color} />))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Monthly Trend Area Chart */}
          {monthlyTrend.length > 0 && (
            <div className="card-glass p-5 mb-6">
              <h3 className="card-header">Monthly Violation Trend</h3>
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={monthlyTrend} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="violationGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="resolvedGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Area type="monotone" dataKey="violations" stroke="#ef4444" fill="url(#violationGrad)" strokeWidth={2} dot={false} />
                  <Area type="monotone" dataKey="resolved" stroke="#10b981" fill="url(#resolvedGrad)" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Alerts Table */}
          <div className="card-glass p-5">
            <h3 className="card-header">Recent Encroachment Alerts</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-[13px]" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-white/[0.08]">
                    {["Region", "Plot", "Type", "Severity", "Area (m²)", "Confidence"].map(h => (
                      <th key={h} className="px-3 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(stats.encroachment_alerts || []).slice(0, 12).map((a, i) => (
                    <tr key={i} className="border-b border-white/[0.04] hover:bg-indigo-500/[0.04] transition-colors">
                      <td className="px-3 py-2.5 text-slate-200">{a.region}</td>
                      <td className="px-3 py-2.5 text-slate-400 font-mono text-xs">{a.plot_id}</td>
                      <td className="px-3 py-2.5 text-slate-300">{a.type?.replace("_", " ")}</td>
                      <td className="px-3 py-2.5">
                        <span className="px-2 py-0.5 rounded-md text-[10px] font-bold" style={{
                          background: `${SEVERITY_COLORS[a.severity]}18`,
                          color: SEVERITY_COLORS[a.severity],
                          border: `1px solid ${SEVERITY_COLORS[a.severity]}30`,
                        }}>{a.severity?.toUpperCase()}</span>
                      </td>
                      <td className="px-3 py-2.5 text-slate-200 font-mono">{a.area_sqm?.toLocaleString()}</td>
                      <td className="px-3 py-2.5 text-slate-400">{(a.confidence * 100).toFixed(0)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* === TRENDS TAB === */}
      {activeTab === "trends" && trendHistorical.length > 0 && (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
            <div className="card-glass p-5">
              <h3 className="card-header">Violations Over Time</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={trendHistorical} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="period" tick={{ fill: "#64748b", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="violations_detected" stroke="#ef4444" strokeWidth={2} dot={{ r: 3, fill: "#ef4444" }} name="Detected" />
                  <Line type="monotone" dataKey="violations_resolved" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: "#10b981" }} name="Resolved" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="card-glass p-5">
              <h3 className="card-header">Utilization Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={trendHistorical} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <defs>
                    <linearGradient id="utilGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="period" tick={{ fill: "#64748b", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 100]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Area type="monotone" dataKey="utilization_pct" stroke="#6366f1" fill="url(#utilGrad)" strokeWidth={2} name="Utilization %" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {trendForecasts.length > 0 && (
            <div className="card-glass p-5">
              <h3 className="card-header">
                Predictive Risk Forecast
                <span className="text-xs text-slate-500 font-normal ml-3">AI-powered 6-month projection</span>
              </h3>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={trendForecasts} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="period" tick={{ fill: "#64748b", fontSize: 11 }} />
                  <YAxis tick={{ fill: "#64748b", fontSize: 11 }} domain={[0, 1]} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend />
                  <Line type="monotone" dataKey="predicted_risk_score" stroke="#f59e0b" strokeWidth={2} strokeDasharray="8 4" dot={{ r: 4, fill: "#f59e0b" }} name="Predicted Risk" />
                  <Line type="monotone" dataKey="confidence" stroke="#6366f1" strokeWidth={1.5} dot={{ r: 3, fill: "#6366f1" }} name="Confidence" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </>
      )}

      {/* === COMPLIANCE TAB === */}
      {activeTab === "compliance" && (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
            {complianceData.map((cat, i) => (
              <div key={i} className="card-glass p-6 text-center" style={{ borderLeft: `4px solid ${cat.color}` }}>
                <div className="text-3xl font-extrabold" style={{ color: cat.color }}>{cat.value}</div>
                <div className="text-xs text-slate-400 mt-2">{cat.name}</div>
              </div>
            ))}
          </div>

          <div className="card-glass p-5">
            <h3 className="card-header">Region-wise Compliance Overview</h3>
            <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
              <table className="w-full text-[13px]" style={{ borderCollapse: "collapse" }}>
                <thead>
                  <tr className="border-b border-white/[0.08] sticky top-0 bg-[#0a0f1e]/95 backdrop-blur-sm z-10">
                    {["Region", "Category", "Utilization", "Plots", "Violations"].map(h => (
                      <th key={h} className="px-3 py-2.5 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(stats.utilization_by_region || []).map((r, i) => (
                    <tr key={i} className="border-b border-white/[0.04] hover:bg-indigo-500/[0.04] transition-colors">
                      <td className="px-3 py-2.5 text-slate-200 font-medium">{r.region}</td>
                      <td className="px-3 py-2.5">
                        <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase ${
                          r.category === "new"
                            ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20"
                            : "bg-amber-500/15 text-amber-400 border border-amber-500/20"
                        }`}>
                          {r.category}
                        </span>
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                            <div className="h-full rounded-full transition-all duration-500" style={{
                              width: `${Math.min(100, r.utilization_pct)}%`,
                              background: r.utilization_pct > 80 ? "#10b981" : r.utilization_pct > 50 ? "#f59e0b" : "#ef4444",
                            }} />
                          </div>
                          <span className="text-xs text-slate-400 min-w-[32px] text-right">{r.utilization_pct}%</span>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-slate-400">{r.plots}</td>
                      <td className="px-3 py-2.5">
                        <span className={`font-semibold ${r.encroachments > 3 ? "text-red-400" : r.encroachments > 1 ? "text-amber-400" : "text-emerald-400"}`}>
                          {r.encroachments}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Shared Styles ────────────────────────────────────────────── */
const tooltipStyle = {
  background: "rgba(10,15,30,0.95)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 10,
  color: "#e2e8f0",
  fontSize: 12,
  boxShadow: "0 8px 32px rgba(0,0,0,0.4)",
};
