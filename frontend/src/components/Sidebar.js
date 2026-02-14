"use client";

import { useState, useEffect, useRef } from "react";
import {
  Search,
  MapPin,
  Factory,
  ChevronLeft,
  Satellite,
  Zap,
  ScanSearch,
  FileText,
  AlertTriangle,
  BarChart3,
  Grid3X3,
  Loader2,
  Sparkles,
} from "lucide-react";
import { searchRegions, generateReport } from "@/lib/api";

export default function Sidebar({
  selectedRegion,
  imagery,
  encroachments,
  loading,
  onSelectRegion,
  onEnhance,
  onShowChangeDetection,
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [reportLoading, setReportLoading] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("all");
  const debounceRef = useRef(null);

  /* ── Load all regions on mount ──────────────────────── */
  useEffect(() => {
    async function loadInitialRegions() {
      try {
        console.log('Loading initial regions...');
        const r = await searchRegions('');
        console.log('Initial load:', r?.length, 'regions');
        setResults(r || []);
      } catch (error) {
        console.error('Initial load error:', error);
        setResults([]);
      }
    }
    loadInitialRegions();
  }, []);

  /* ── Search with debounce ─────────────────────────────── */
  useEffect(() => {
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSearching(true);
      try {
        console.log('Searching for:', query);
        const r = await searchRegions(query);
        console.log('Search results:', r?.length, 'regions');
        setResults(r);
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
      } finally {
        setSearching(false);
      }
    }, 300);
  }, [query]);

  const handleReport = async () => {
    setReportLoading(true);
    try {
      await generateReport({
        region_name: selectedRegion?.region_id || "",
        include_encroachment: true,
        include_change_detection: true,
      });
    } catch (e) {
      console.error("Report failed:", e);
    } finally {
      setReportLoading(false);
    }
  };

  const filtered = results.filter(
    (r) => categoryFilter === "all" || r.category === categoryFilter
  );

  return (
    <aside className="w-[360px] shrink-0 h-full bg-[#0a0f1e]/90 backdrop-blur-xl border-r border-white/[0.06] flex flex-col overflow-hidden">
      {/* ── Header Section ───────────────────────────────────── */}
      <div className="p-4 border-b border-white/[0.06]">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search Siltara, Urla, Tilda…"
            className="w-full bg-white/[0.04] border border-white/[0.08] rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/40 focus:outline-none transition-all"
          />
          {searching && (
            <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-indigo-400 animate-spin" />
          )}
        </div>

        {/* Category filter pills */}
        <div className="flex gap-1.5 mt-3">
          {[
            { key: "all", label: "All", count: 56 },
            { key: "new", label: "New", count: 36 },
            { key: "old", label: "Old", count: 20 },
          ].map((cat) => (
            <button
              key={cat.key}
              onClick={() => setCategoryFilter(cat.key)}
              className={`flex items-center gap-1.5 text-[11px] font-semibold px-3 py-1.5 rounded-lg transition-all duration-200 ${categoryFilter === cat.key
                  ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 shadow-sm shadow-indigo-500/10"
                  : "bg-white/[0.03] text-slate-500 border border-transparent hover:bg-white/[0.06] hover:text-slate-400"
                }`}
            >
              {cat.label}
              <span
                className={`px-1.5 py-0.5 rounded-md text-[10px] ${categoryFilter === cat.key
                    ? "bg-indigo-500/30 text-indigo-200"
                    : "bg-white/[0.06] text-slate-600"
                  }`}
              >
                {cat.count}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* ── Content Area ─────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto scrollbar-thin">
        {!selectedRegion ? (
          /* ── Region List ─────────────────────────────── */
          <div>
            {searching && (
              <div className="flex items-center justify-center gap-2 p-6 text-sm text-slate-500">
                <Loader2 className="w-4 h-4 animate-spin" />
                Searching regions…
              </div>
            )}
            {!searching && filtered.length === 0 && (
              <div className="flex flex-col items-center gap-2 p-8 text-center">
                <MapPin className="w-8 h-8 text-slate-700" />
                <p className="text-sm text-slate-500">No regions found</p>
              </div>
            )}
            {filtered.map((r, idx) => (
              <button
                key={r.region_id}
                onClick={() => onSelectRegion(r)}
                className="w-full text-left px-4 py-3.5 border-b border-white/[0.04] hover:bg-white/[0.03] transition-all duration-150 group"
                style={{ animationDelay: `${idx * 30}ms` }}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${r.category === "new"
                        ? "bg-indigo-500/10 text-indigo-400"
                        : "bg-emerald-500/10 text-emerald-400"
                      }`}
                  >
                    <Factory className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm text-slate-200 truncate group-hover:text-white transition-colors">
                        {r.name}
                      </span>
                      <span
                        className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded-md uppercase tracking-wider ${r.category === "new"
                            ? "bg-indigo-500/15 text-indigo-400 border border-indigo-500/20"
                            : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/20"
                          }`}
                      >
                        {r.category}
                      </span>
                    </div>
                    <div className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
                      <MapPin className="w-3 h-3" />
                      {r.district}
                      <span className="text-slate-700">·</span>
                      <Grid3X3 className="w-3 h-3" />
                      {r.total_plots} plots
                    </div>
                    <div className="text-[11px] text-slate-600 mt-0.5 font-mono">
                      {r.latitude.toFixed(4)}°N, {r.longitude.toFixed(4)}°E
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>
        ) : (
          /* ── Region Detail ─────────────────────────── */
          <div className="p-4 space-y-3 fade-in">
            {/* Back button + region info */}
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-bold text-base text-white flex items-center gap-2">
                  <Factory className="w-4 h-4 text-indigo-400" />
                  {selectedRegion.name}
                </h3>
                <button
                  onClick={() => {
                    onSelectRegion(null);
                    setQuery("");
                  }}
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-indigo-300 transition-colors bg-white/[0.04] hover:bg-white/[0.08] px-2.5 py-1.5 rounded-lg"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Back
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: "District", value: selectedRegion.district },
                  { label: "Plots", value: selectedRegion.total_plots },
                  { label: "Code", value: selectedRegion.code },
                  {
                    label: "Area",
                    value: `${selectedRegion.area_hectares} ha`,
                  },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="bg-white/[0.03] rounded-lg px-3 py-2"
                  >
                    <div className="text-[10px] text-slate-500 uppercase tracking-wider">
                      {item.label}
                    </div>
                    <div className="text-sm font-semibold text-slate-200 mt-0.5">
                      {item.value}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Imagery card */}
            <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
              <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2 uppercase tracking-wider">
                <Satellite className="w-3.5 h-3.5 text-indigo-400" />
                Satellite Imagery
              </h4>
              {loading.imagery ? (
                <div className="flex items-center gap-2 text-sm text-slate-500 py-4">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                  Fetching Sentinel-2 imagery…
                </div>
              ) : imagery ? (
                <div>
                  <div className="relative rounded-lg overflow-hidden mb-3 group">
                    <img
                      src={imagery.thumbnail_url || imagery.image_url}
                      alt="Satellite"
                      className="w-full h-40 object-cover transition-transform duration-300 group-hover:scale-105"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-[11px]">
                    {[
                      { label: "Date", value: imagery.acquisition_date },
                      { label: "Cloud", value: `${imagery.cloud_cover}%` },
                      {
                        label: "Bands",
                        value: imagery.bands?.join(", ") || "RGB",
                      },
                    ].map((item) => (
                      <div
                        key={item.label}
                        className="bg-white/[0.03] rounded-md px-2 py-1.5 text-center"
                      >
                        <div className="text-slate-600 text-[9px] uppercase">
                          {item.label}
                        </div>
                        <div className="text-slate-300 font-medium mt-0.5">
                          {item.value}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-600 py-3 text-center">
                  No imagery loaded yet
                </div>
              )}
            </div>

            {/* Action buttons */}
            <div className="space-y-2">
              <button
                onClick={onEnhance}
                disabled={!imagery || loading.enhance}
                className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 text-sm font-semibold transition-all duration-200 shadow-lg shadow-indigo-500/20 disabled:shadow-none"
              >
                {loading.enhance ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Enhancing with ESRGAN…
                  </>
                ) : (
                  <>
                    <Zap className="w-4 h-4" />
                    AI Super-Resolution (4x)
                  </>
                )}
              </button>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={onShowChangeDetection}
                  className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold transition-all border border-white/[0.06] hover:border-white/[0.12] text-slate-300"
                >
                  <ScanSearch className="w-3.5 h-3.5" />
                  Change Detection
                </button>
                <button
                  onClick={handleReport}
                  disabled={reportLoading}
                  className="flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-white/[0.04] hover:bg-white/[0.08] text-xs font-semibold transition-all border border-white/[0.06] hover:border-white/[0.12] text-slate-300 disabled:text-slate-600"
                >
                  {reportLoading ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  ) : (
                    <FileText className="w-3.5 h-3.5" />
                  )}
                  Report
                </button>
              </div>
            </div>

            {/* Encroachment summary */}
            {loading.encroachment && (
              <div className="flex items-center gap-2 text-sm text-slate-500 py-2">
                <Loader2 className="w-4 h-4 animate-spin text-amber-400" />
                Detecting encroachments…
              </div>
            )}
            {encroachments && (
              <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] p-4">
                <h4 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-2 uppercase tracking-wider">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                  Encroachment Summary
                </h4>
                <div className="grid grid-cols-2 gap-2">
                  <MiniStat
                    label="Total Plots"
                    value={encroachments.total_plots}
                    icon={Grid3X3}
                  />
                  <MiniStat
                    label="Alerts"
                    value={encroachments.encroachments?.length || 0}
                    icon={AlertTriangle}
                    danger
                  />
                  <MiniStat
                    label="Utilization"
                    value={`${encroachments.overall_utilization_pct}%`}
                    icon={BarChart3}
                  />
                  <MiniStat
                    label="Affected"
                    value={`${(
                      encroachments.total_affected_area_sqm || 0
                    ).toFixed(0)} m²`}
                    icon={Sparkles}
                  />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </aside>
  );
}

function MiniStat({ label, value, icon: Icon, danger }) {
  return (
    <div className="bg-white/[0.03] rounded-lg p-2.5 flex items-center gap-2.5">
      <div
        className={`w-7 h-7 rounded-md flex items-center justify-center shrink-0 ${danger
            ? "bg-red-500/10 text-red-400"
            : "bg-indigo-500/10 text-indigo-400"
          }`}
      >
        <Icon className="w-3.5 h-3.5" />
      </div>
      <div>
        <div
          className={`text-sm font-bold ${danger ? "text-red-400" : "text-slate-200"
            }`}
        >
          {value}
        </div>
        <div className="text-[10px] text-slate-500">{label}</div>
      </div>
    </div>
  );
}
