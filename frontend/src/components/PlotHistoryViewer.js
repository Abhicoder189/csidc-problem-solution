"use client";

import { useState, useEffect } from "react";
import { analyzePlotTimeline } from "@/lib/api";
import {
  X,
  Calendar,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Activity,
  Home,
  Trees,
  BarChart3,
} from "lucide-react";

export default function PlotHistoryViewer({ plot, onClose }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [comparing, setComparing] = useState(false);
  const [compareIndex, setCompareIndex] = useState(null);
  
  // Default dates
  const today = new Date().toISOString().split("T")[0];
  const fiveYearsAgo = new Date(Date.now() - 5 * 365 * 24 * 60 * 60 * 1000)
    .toISOString()
    .split("T")[0];
  
  const [startDate, setStartDate] = useState(fiveYearsAgo);
  const [endDate, setEndDate] = useState(today);
  const [numSnapshots, setNumSnapshots] = useState(6);

  const handleAnalyze = async () => {
    if (!plot || !plot.boundary) {
      alert("No plot boundary available for analysis");
      return;
    }

    setLoading(true);
    try {
      const res = await analyzePlotTimeline({
        plot_id: plot.id || plot.plot_id || "unknown",
        plot_geojson: plot.boundary,
        start_date: startDate,
        end_date: endDate,
        num_snapshots: numSnapshots,
      });
      setResult(res);
      setCurrentIndex(0);
      setCompareIndex(null);
      setComparing(false);
    } catch (e) {
      console.error("Timeline analysis error:", e);
      alert("Failed to analyze plot timeline. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handlePrevious = () => {
    if (currentIndex > 0) setCurrentIndex(currentIndex - 1);
  };

  const handleNext = () => {
    if (result && currentIndex < result.snapshots.length - 1) {
      setCurrentIndex(currentIndex + 1);
    }
  };

  const toggleCompare = (index) => {
    if (comparing && compareIndex === index) {
      setComparing(false);
      setCompareIndex(null);
    } else {
      setComparing(true);
      setCompareIndex(index);
    }
  };

  const currentSnapshot = result?.snapshots?.[currentIndex];
  const compareSnapshot = comparing && compareIndex !== null ? result?.snapshots?.[compareIndex] : null;

  return (
    <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 backdrop-blur-md">
      <div className="glass rounded-2xl w-[95vw] max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="shrink-0 px-6 py-4 border-b border-white/[0.08] flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-400" />
              Plot Historical Timeline — {plot?.plot_number || plot?.id || "Unknown"}
            </h2>
            <p className="text-sm text-gray-400 mt-0.5">
              Multi-temporal change detection and trend analysis
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] flex items-center justify-center transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Configuration Panel */}
        {!result && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-2xl mx-auto space-y-6">
              <div className="glass-light rounded-xl p-6">
                <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-blue-400" />
                  Configuration
                </h3>

                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div>
                    <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wide">
                      Start Date
                    </label>
                    <input
                      type="date"
                      value={startDate}
                      onChange={(e) => setStartDate(e.target.value)}
                      max={endDate}
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wide">
                      End Date
                    </label>
                    <input
                      type="date"
                      value={endDate}
                      onChange={(e) => setEndDate(e.target.value)}
                      min={startDate}
                      max={today}
                      className="w-full bg-gray-800/50 border border-gray-700 rounded-lg px-3 py-2.5 text-sm text-gray-100 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
                    />
                  </div>
                </div>

                <div className="mb-6">
                  <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wide">
                    Number of Snapshots: {numSnapshots}
                  </label>
                  <input
                    type="range"
                    min="2"
                    max="12"
                    value={numSnapshots}
                    onChange={(e) => setNumSnapshots(parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer slider"
                  />
                  <div className="flex justify-between text-xs text-gray-500 mt-1">
                    <span>2</span>
                    <span>6</span>
                    <span>12</span>
                  </div>
                </div>

                <button
                  onClick={handleAnalyze}
                  disabled={loading}
                  className="w-full py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:from-gray-700 disabled:to-gray-800 font-medium transition-all shadow-lg shadow-blue-500/20"
                >
                  {loading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      Analyzing Timeline...
                    </span>
                  ) : (
                    "Start Timeline Analysis"
                  )}
                </button>
              </div>

              {/* Info Panel */}
              <div className="glass-light rounded-xl p-5">
                <h4 className="text-sm font-medium text-gray-300 mb-3">Analysis Features</h4>
                <ul className="space-y-2 text-sm text-gray-400">
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5" />
                    Multi-temporal satellite imagery comparison
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5" />
                    NDVI vegetation index trend analysis
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5" />
                    Built-up area detection and tracking
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5" />
                    Automated change point identification
                  </li>
                  <li className="flex items-start gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5" />
                    Anomaly detection in time-series data
                  </li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Results View */}
        {result && result.success && (
          <div className="flex-1 overflow-hidden flex flex-col">
            {/* Summary Stats */}
            <div className="shrink-0 px-6 py-4 bg-gradient-to-b from-white/[0.02] to-transparent border-b border-white/[0.05]">
              <div className="grid grid-cols-4 gap-4">
                <StatCard
                  icon={Calendar}
                  label="Total Snapshots"
                  value={result.snapshots.length}
                  color="blue"
                />
                <StatCard
                  icon={TrendingUp}
                  label="NDVI Trend"
                  value={result.summary.ndvi_trend >= 0 ? `+${result.summary.ndvi_trend}` : result.summary.ndvi_trend}
                  color={result.summary.ndvi_trend >= 0 ? "green" : "red"}
                  trend={result.summary.ndvi_trend >= 0}
                />
                <StatCard
                  icon={Home}
                  label="Built-up Change"
                  value={`${result.summary.built_up_trend >= 0 ? "+" : ""}${result.summary.built_up_trend}%`}
                  color={result.summary.built_up_trend > 10 ? "amber" : "gray"}
                />
                <StatCard
                  icon={AlertCircle}
                  label="Change Points"
                  value={result.change_points.length}
                  color="purple"
                />
              </div>
            </div>

            {/* Main View Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {/* Image Viewer */}
              <div className="glass-light rounded-xl p-5">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium">Timeline Viewer</h3>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handlePrevious}
                      disabled={currentIndex === 0}
                      className="p-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-sm text-gray-400 min-w-[100px] text-center">
                      {currentIndex + 1} / {result.snapshots.length}
                    </span>
                    <button
                      onClick={handleNext}
                      disabled={currentIndex === result.snapshots.length - 1}
                      className="p-2 rounded-lg bg-white/[0.04] hover:bg-white/[0.08] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>

                <div className={`grid ${comparing && compareSnapshot ? "grid-cols-2" : "grid-cols-1"} gap-4`}>
                  {/* Current Image */}
                  {currentSnapshot && (
                    <ImageCard
                      snapshot={currentSnapshot}
                      label="Current"
                      showMetrics
                    />
                  )}

                  {/* Compare Image */}
                  {comparing && compareSnapshot && (
                    <ImageCard
                      snapshot={compareSnapshot}
                      label="Compare"
                      showMetrics
                      showDiff={currentSnapshot}
                    />
                  )}
                </div>

                {/* Timeline Selector */}
                <div className="mt-6">
                  <div className="flex items-center gap-2 overflow-x-auto pb-2">
                    {result.snapshots.map((snapshot, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          if (comparing) {
                            toggleCompare(idx);
                          } else {
                            setCurrentIndex(idx);
                          }
                        }}
                        className={`shrink-0 px-4 py-2 rounded-lg text-xs font-medium transition-all ${
                          idx === currentIndex
                            ? "bg-blue-600 text-white shadow-lg shadow-blue-500/30"
                            : idx === compareIndex && comparing
                              ? "bg-purple-600 text-white shadow-lg shadow-purple-500/30"
                              : "bg-white/[0.04] hover:bg-white/[0.08] text-gray-300"
                        }`}
                      >
                        {snapshot.actual_date}
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setComparing(!comparing)}
                    className="mt-3 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    {comparing ? "Exit Compare Mode" : "Enter Compare Mode"}
                  </button>
                </div>
              </div>

              {/* Change Points */}
              {result.change_points.length > 0 && (
                <div className="glass-light rounded-xl p-5">
                  <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-amber-400" />
                    Detected Change Points
                  </h3>
                  <div className="space-y-3">
                    {result.change_points.map((cp, idx) => (
                      <ChangePointCard key={idx} changePoint={cp} />
                    ))}
                  </div>
                </div>
              )}

              {/* Anomalies */}
              {result.anomalies && result.anomalies.length > 0 && (
                <div className="glass-light rounded-xl p-5">
                  <h3 className="text-lg font-medium mb-4 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-red-400" />
                    Detected Anomalies
                  </h3>
                  <div className="space-y-3">
                    {result.anomalies.map((anomaly, idx) => (
                      <AnomalyCard key={idx} anomaly={anomaly} />
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error State */}
        {result && !result.success && (
          <div className="flex-1 flex items-center justify-center p-6">
            <div className="text-center">
              <AlertCircle className="w-16 h-16 text-red-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-300 mb-2">Analysis Failed</h3>
              <p className="text-sm text-gray-400 mb-6">{result.error || "An error occurred"}</p>
              <button
                onClick={() => setResult(null)}
                className="px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ icon: Icon, label, value, color, trend }) {
  const colors = {
    blue: "text-blue-400 bg-blue-500/10",
    green: "text-green-400 bg-green-500/10",
    red: "text-red-400 bg-red-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    purple: "text-purple-400 bg-purple-500/10",
    gray: "text-gray-400 bg-gray-500/10",
  };

  return (
    <div className="glass-light rounded-xl p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2 rounded-lg ${colors[color]}`}>
          <Icon className="w-5 h-5" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs text-gray-500 uppercase tracking-wide">{label}</p>
          <p className={`text-lg font-semibold ${colors[color].split(" ")[0]} flex items-center gap-1`}>
            {value}
            {trend !== undefined && (
              <span className="text-xs">
                {trend ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
              </span>
            )}
          </p>
        </div>
      </div>
    </div>
  );
}

function ImageCard({ snapshot, label, showMetrics, showDiff }) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className="text-xs text-gray-500">
          {snapshot.actual_date}
          {snapshot.days_diff > 0 && ` (±${snapshot.days_diff}d)`}
        </span>
      </div>
      <div className="relative rounded-lg overflow-hidden bg-gray-900 aspect-square">
        <img
          src={snapshot.image_url}
          alt={`Snapshot ${snapshot.date}`}
          className="w-full h-full object-cover"
        />
      </div>
      {showMetrics && (
        <div className="mt-3 grid grid-cols-3 gap-2">
          <MetricBadge icon={Trees} label="NDVI" value={snapshot.ndvi.toFixed(3)} color="green" />
          <MetricBadge icon={Home} label="Built-up" value={`${snapshot.built_up_percentage.toFixed(1)}%`} color="amber" />
          <MetricBadge icon={Trees} label="Vegetation" value={`${snapshot.vegetation_percentage.toFixed(1)}%`} color="emerald" />
        </div>
      )}
      {showDiff && (
        <div className="mt-2 p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
          <p className="text-xs text-purple-300">
            Δ NDVI: {(snapshot.ndvi - showDiff.ndvi).toFixed(3)} | 
            Δ Built-up: {(snapshot.built_up_percentage - showDiff.built_up_percentage).toFixed(1)}%
          </p>
        </div>
      )}
    </div>
  );
}

function MetricBadge({ icon: Icon, label, value, color }) {
  const colors = {
    green: "text-green-400 bg-green-500/10",
    amber: "text-amber-400 bg-amber-500/10",
    emerald: "text-emerald-400 bg-emerald-500/10",
  };

  return (
    <div className={`px-2 py-1.5 rounded-lg ${colors[color]} flex items-center gap-1.5`}>
      <Icon className="w-3 h-3 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-[10px] text-gray-400 uppercase tracking-wide truncate">{label}</p>
        <p className="text-xs font-semibold truncate">{value}</p>
      </div>
    </div>
  );
}

function ChangePointCard({ changePoint }) {
  const isSignificant = changePoint.significance === "high";

  return (
    <div className={`p-4 rounded-lg border ${isSignificant ? "bg-amber-500/10 border-amber-500/30" : "bg-white/[0.02] border-white/[0.05]"}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-gray-200">
            {changePoint.from_date} → {changePoint.to_date}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">
            {isSignificant ? "Significant Change Detected" : "Moderate Change"}
          </p>
        </div>
        {isSignificant && (
          <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 text-[10px] font-medium uppercase tracking-wide">
            High
          </span>
        )}
      </div>
      <div className="flex items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <Trees className="w-3.5 h-3.5 text-green-400" />
          <span className="text-gray-400">NDVI:</span>
          <span className={changePoint.ndvi_change >= 0 ? "text-green-400" : "text-red-400"}>
            {changePoint.ndvi_change >= 0 ? "+" : ""}{changePoint.ndvi_change}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <Home className="w-3.5 h-3.5 text-amber-400" />
          <span className="text-gray-400">Built-up:</span>
          <span className={changePoint.built_up_change >= 0 ? "text-amber-400" : "text-blue-400"}>
            {changePoint.built_up_change >= 0 ? "+" : ""}{changePoint.built_up_change}%
          </span>
        </div>
      </div>
    </div>
  );
}

function AnomalyCard({ anomaly }) {
  const isHigh = anomaly.severity === "high";

  return (
    <div className={`p-4 rounded-lg border ${isHigh ? "bg-red-500/10 border-red-500/30" : "bg-orange-500/10 border-orange-500/30"}`}>
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="text-sm font-medium text-gray-200">{anomaly.date}</p>
          <p className="text-xs text-gray-400 mt-0.5">{anomaly.description}</p>
        </div>
        <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium uppercase tracking-wide ${
          isHigh ? "bg-red-500/20 text-red-300" : "bg-orange-500/20 text-orange-300"
        }`}>
          {anomaly.severity}
        </span>
      </div>
      <p className="text-xs text-gray-500">Type: {anomaly.type.replace("_", " ")}</p>
    </div>
  );
}
