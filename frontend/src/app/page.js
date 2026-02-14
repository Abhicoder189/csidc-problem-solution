"use client";

import { useState, useCallback, useRef } from "react";
import {
  Satellite,
  LayoutDashboard,
  MapPin,
  Shield,
  Bell,
  Activity,
  ShieldAlert,
  BarChart3,
  BellRing,
  X,
} from "lucide-react";
import dynamic from "next/dynamic";
import Sidebar from "@/components/Sidebar";

const MapView = dynamic(() => import("@/components/MapView"), {
  ssr: false,
  loading: () => (
    <div className="flex-1 flex items-center justify-center bg-[#060a13]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-10 h-10 border-[3px] border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
        <span className="text-xs text-slate-500">Loading map…</span>
      </div>
    </div>
  ),
});
import Dashboard from "@/components/Dashboard";
import ComparisonModal from "@/components/ComparisonModal";
import ChangeDetectionPanel from "@/components/ChangeDetectionPanel";
import EncroachmentPanel from "@/components/EncroachmentPanel";
import PlotInfoPanel from "@/components/PlotInfoPanel";
import ViolationsPanel from "@/components/ViolationsPanel";
import RegionAnalytics from "@/components/RegionAnalytics";
import AlertsPanel from "@/components/AlertsPanel";
import ComplianceHeatmapOverlay from "@/components/ComplianceHeatmapOverlay";
import SatelliteCompare from "@/components/SatelliteCompare";
import { fetchImagery, enhanceImage, detectEncroachment } from "@/lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState("monitor");
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [imagery, setImagery] = useState(null);
  const [enhanced, setEnhanced] = useState(null);
  const [encroachments, setEncroachments] = useState(null);
  const [loading, setLoading] = useState({});
  const [showComparison, setShowComparison] = useState(false);
  const [showChangeDetection, setShowChangeDetection] = useState(false);
  const [selectedPlot, setSelectedPlot] = useState(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [showSideBySide, setShowSideBySide] = useState(false);
  const [showQuickGuide, setShowQuickGuide] = useState(true);
  const mapViewRef = useRef(null);
  const [mapCenter, setMapCenter] = useState({
    lng: 81.63,
    lat: 21.25,
    zoom: 10,
  });

  const setLoadingKey = (key, val) =>
    setLoading((prev) => ({ ...prev, [key]: val }));

  /* ── Handlers ────────────────────────────────────────────────── */
  const handleSelectRegion = useCallback(async (region) => {
    if (!region) {
      setSelectedRegion(null);
      setImagery(null);
      setEnhanced(null);
      setEncroachments(null);
      // Reset map view to default overview
      setMapCenter({ lng: 81.63, lat: 21.25, zoom: 10 });
      return;
    }
    setSelectedRegion(region);
    setImagery(null);
    setEnhanced(null);
    setEncroachments(null);
    setMapCenter({ lng: region.longitude, lat: region.latitude, zoom: 14 });

    setLoadingKey("imagery", true);
    try {
      const img = await fetchImagery({
        region_name: region.region_id,
        latitude: region.latitude,
        longitude: region.longitude,
      });
      setImagery(img);
    } catch (e) {
      console.error("Fetch imagery failed:", e);
    } finally {
      setLoadingKey("imagery", false);
    }

    setLoadingKey("encroachment", true);
    try {
      const enc = await detectEncroachment({
        region_id: region.region_id,
        latitude: region.latitude,
        longitude: region.longitude,
      });
      setEncroachments(enc);
    } catch (e) {
      console.error("Encroachment detection failed:", e);
    } finally {
      setLoadingKey("encroachment", false);
    }
  }, []);

  const handleEnhance = useCallback(async () => {
    if (!imagery?.image_url) return;
    setLoadingKey("enhance", true);
    try {
      const result = await enhanceImage(imagery.image_url);
      setEnhanced(result);
      setShowComparison(true);
    } catch (e) {
      console.error("Enhancement failed:", e);
    } finally {
      setLoadingKey("enhance", false);
    }
  }, [imagery]);

  const navTabs = [
    { key: "monitor", label: "Monitor", icon: Satellite },
    { key: "violations", label: "Violations", icon: ShieldAlert },
    { key: "analytics", label: "Analytics", icon: BarChart3 },
    { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  ];

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-[#060a13]">
      {/* ── Top Nav ──────────────────────────────────────────────── */}
      <header className="shrink-0 h-14 border-b border-white/[0.06] bg-[#0a0f1e]/80 backdrop-blur-xl flex items-center px-5 gap-4 z-50">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-[#0a0f1e] dot-pulse" />
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-white text-sm tracking-tight leading-none">
              ILMCS
            </span>
            <span className="text-[10px] text-slate-500 leading-none mt-0.5">
              Industrial Land Monitoring
            </span>
          </div>
        </div>

        <div className="w-px h-6 bg-white/[0.06] mx-1" />

        {/* Nav Tabs */}
        <div className="flex gap-1 bg-white/[0.04] rounded-xl p-1 border border-white/[0.06]">
          {navTabs.map(({ key, label, icon: Icon }) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 ${activeTab === key
                ? "bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md shadow-indigo-500/25"
                : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
                }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
            </button>
          ))}
        </div>

        {/* Side-by-Side Compare Button */}
        {selectedRegion && (
          <button
            onClick={() => setShowSideBySide(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/20 hover:bg-blue-500/25 transition-all"
            title="Compare current vs historical satellite imagery"
          >
            <Satellite className="w-3.5 h-3.5" />
            Compare Imagery
          </button>
        )}

        <div className="flex-1" />

        {/* Status indicators */}
        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={() => setShowAlerts(!showAlerts)}
            className={`relative p-2 rounded-lg transition-all ${showAlerts ? "bg-amber-500/15 text-amber-400" : "hover:bg-white/[0.04] text-slate-500 hover:text-slate-300"}`}
          >
            <BellRing className="w-4 h-4" />
            <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-amber-500 rounded-full border-2 border-[#0a0f1e] dot-pulse" />
          </button>
          <div className="w-px h-4 bg-white/[0.06]" />
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Activity className="w-3 h-3 text-emerald-400" />
            <span>Live</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <MapPin className="w-3 h-3 text-indigo-400" />
            <span>56 Regions</span>
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <Bell className="w-3 h-3 text-amber-400" />
            <span>Chhattisgarh</span>
          </div>
        </div>
      </header>

      {/* ── Main Content ─────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0">
        {activeTab === "monitor" ? (
          <>
            <Sidebar
              selectedRegion={selectedRegion}
              imagery={imagery}
              encroachments={encroachments}
              loading={loading}
              onSelectRegion={handleSelectRegion}
              onEnhance={handleEnhance}
              onShowChangeDetection={() => setShowChangeDetection(true)}
            />
            <div className="flex-1 relative min-h-0" style={{ minHeight: 0 }}>
              <MapView
                ref={mapViewRef}
                center={mapCenter}
                imagery={imagery}
                encroachments={encroachments}
                selectedRegion={selectedRegion}
                onPlotClick={(plot) => setSelectedPlot(plot)}
                selectedPlotId={selectedPlot?.plot_id}
              />
              {/* Compliance heatmap overlay */}
              <ComplianceHeatmapOverlay
                mapRef={mapViewRef}
                visible={showHeatmap}
                onToggle={() => setShowHeatmap(!showHeatmap)}
              />
              {/* Floating encroachment panel */}
              {encroachments && !selectedPlot && (
                <div className="absolute bottom-4 right-4 z-20 w-96 max-h-[50vh]">
                  <EncroachmentPanel data={encroachments} />
                </div>
              )}
            </div>

            {/* Right-side Plot Info Panel */}
            {selectedPlot && (
              <div className="shrink-0 w-[380px] border-l border-white/[0.06] bg-[#0a0f1e]/95 backdrop-blur-xl overflow-hidden">
                <PlotInfoPanel
                  plot={selectedPlot}
                  onClose={() => setSelectedPlot(null)}
                />
              </div>
            )}
          </>
        ) : activeTab === "violations" ? (
          <div className="flex flex-1 overflow-hidden">
            {/* Sidebar for region navigation */}
            <Sidebar
              selectedRegion={selectedRegion}
              imagery={imagery}
              encroachments={encroachments}
              loading={loading}
              onSelectRegion={handleSelectRegion}
              onEnhance={handleEnhance}
              onShowChangeDetection={() => setShowChangeDetection(true)}
            />
            {/* Violations main */}
            <div className="flex-1 border-l border-white/[0.06] overflow-hidden">
              <ViolationsPanel
                regionId={selectedRegion?.region_id}
                onSelectViolation={(v) => console.log("Selected violation:", v)}
              />
            </div>
          </div>
        ) : activeTab === "analytics" ? (
          <div className="flex flex-1 overflow-hidden">
            <Sidebar
              selectedRegion={selectedRegion}
              imagery={imagery}
              encroachments={encroachments}
              loading={loading}
              onSelectRegion={handleSelectRegion}
              onEnhance={handleEnhance}
              onShowChangeDetection={() => setShowChangeDetection(true)}
            />
            <div className="flex-1 border-l border-white/[0.06] overflow-hidden">
              <RegionAnalytics regionId={selectedRegion?.region_id} />
            </div>
          </div>
        ) : (
          <div className="flex-1 overflow-hidden">
            <Dashboard />
          </div>
        )}
      </div>

      {/* ── Alerts Dropdown ──────────────────────────────────────── */}
      <AlertsPanel
        isOpen={showAlerts}
        onClose={() => setShowAlerts(false)}
        onAlertClick={(alert) => {
          setShowAlerts(false);
          if (alert.region_id) {
            setActiveTab("violations");
          }
        }}
      />

      {/* ── Modals ────────────────────────────────────────────────── */}
      {showComparison && enhanced && (
        <ComparisonModal
          original={imagery}
          enhanced={enhanced}
          onClose={() => setShowComparison(false)}
        />
      )}
      {showChangeDetection && selectedRegion && (
        <ChangeDetectionPanel
          region={selectedRegion}
          onClose={() => setShowChangeDetection(false)}
        />
      )}
      {showSideBySide && selectedRegion && (
        <SatelliteCompare
          region={selectedRegion}
          plotsData={encroachments} // Pass current plots
          onClose={() => setShowSideBySide(false)}
        />
      )}

      {/* ── Quick Guide ───────────────────────────────────────── */}
      {showQuickGuide && !selectedRegion && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-[#0a0f1e] to-[#060a13] border border-white/[0.1] rounded-2xl shadow-2xl max-w-lg p-6 m-4">
            <div className="flex items-start gap-4 mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
                <Shield className="w-6 h-6 text-white" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-white">Welcome to ILMCS</h3>
                <p className="text-sm text-slate-400 mt-1">Industrial Land Monitoring & Compliance System</p>
              </div>
              <button
                onClick={() => setShowQuickGuide(false)}
                className="text-slate-500 hover:text-white transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-sm text-slate-300">
              <div className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
                <div className="w-6 h-6 rounded-full bg-indigo-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-indigo-400">1</span>
                </div>
                <div>
                  <p className="font-semibold text-white">Select a Region</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Search and select from 56 industrial areas in the left sidebar
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
                <div className="w-6 h-6 rounded-full bg-blue-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-blue-400">2</span>
                </div>
                <div>
                  <p className="font-semibold text-white">Compare Historical Imagery</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Click "Compare Imagery" button to view current vs historical satellite images
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
                <div className="w-6 h-6 rounded-full bg-emerald-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-emerald-400">3</span>
                </div>
                <div>
                  <p className="font-semibold text-white">View Analytics</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Switch to Analytics tab to see GIS analysis, IoU scores, and compliance grades
                  </p>
                </div>
              </div>
            </div>

            <button
              onClick={() => setShowQuickGuide(false)}
              className="w-full mt-6 px-4 py-2.5 rounded-lg bg-gradient-to-r from-indigo-600 to-indigo-500 text-white font-semibold hover:from-indigo-500 hover:to-indigo-400 transition-all"
            >
              Get Started
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
