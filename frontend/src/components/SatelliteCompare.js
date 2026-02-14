"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar,
  X,
  Loader2,
  SplitSquareHorizontal,
  Download,
  Maximize2,
  Clock,
  MapPin,
  Satellite,
  ArrowLeftRight,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SatelliteCompare({ region, onClose }) {
  const [historicalDate, setHistoricalDate] = useState("2020-01-15");
  const [currentImg, setCurrentImg] = useState(null);
  const [historicalImg, setHistoricalImg] = useState(null);
  const [loadingCurrent, setLoadingCurrent] = useState(false);
  const [loadingHistorical, setLoadingHistorical] = useState(false);
  const [fullscreen, setFullscreen] = useState(null); // "current" | "historical" | null
  const [bboxKm, setBboxKm] = useState(2.0);
  const [imageSource, setImageSource] = useState("osm"); // "osm", "esri", or "mapbox"

  const today = new Date().toISOString().split("T")[0];

  // Fetch current image
  const fetchCurrentImage = useCallback(async () => {
    if (!region) return;
    console.log('Fetching current image for:', region.name, 'source:', imageSource);
    setLoadingCurrent(true);
    try {
      const url = `${API}/api/satellite-image?lat=${region.latitude}&lon=${region.longitude}&bbox_km=${bboxKm}&source=${imageSource}`;
      console.log('Current image URL:', url);
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        console.log('Current image loaded:', data);
        setCurrentImg(data);
      } else {
        console.error('Current image fetch failed:', res.status, res.statusText);
      }
    } catch (e) {
      console.error("Current image fetch failed:", e);
    } finally {
      setLoadingCurrent(false);
    }
  }, [region, bboxKm, imageSource]);

  // Fetch historical image
  const fetchHistoricalImage = useCallback(async () => {
    if (!region || !historicalDate) return;
    console.log('Fetching historical image for:', region.name, 'date:', historicalDate, 'source:', imageSource);
    setLoadingHistorical(true);
    try {
      const url = `${API}/api/satellite-image?lat=${region.latitude}&lon=${region.longitude}&date=${historicalDate}&bbox_km=${bboxKm}&source=${imageSource}`;
      console.log('Historical image URL:', url);
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        console.log('Historical image loaded:', data);
        setHistoricalImg(data);
      } else {
        console.error('Historical image fetch failed:', res.status, res.statusText);
      }
    } catch (e) {
      console.error("Historical image fetch failed:", e);
    } finally {
      setLoadingHistorical(false);
    }
  }, [region, historicalDate, bboxKm, imageSource]);

  // Auto-fetch on mount and region change
  useEffect(() => {
    fetchCurrentImage();
    fetchHistoricalImage();
  }, [fetchCurrentImage, fetchHistoricalImage]);

  // Date presets
  const datePresets = [
    { label: "2024", value: "2024-01-15" },
    { label: "2022", value: "2022-01-15" },
    { label: "2020", value: "2020-01-15" },
    { label: "2018", value: "2018-01-15" },
    { label: "2015", value: "2015-06-15" },
  ];

  // Fullscreen overlay
  if (fullscreen) {
    const img = fullscreen === "current" ? currentImg : historicalImg;
    const label = fullscreen === "current" ? `Current (${today})` : `Historical (${historicalDate})`;
    return (
      <div className="fixed inset-0 z-[70] bg-black flex flex-col">
        <div className="flex items-center justify-between p-4 bg-[#0a0f1e]">
          <span className="text-white font-bold">{region?.name} — {label}</span>
          <button onClick={() => setFullscreen(null)} className="text-white hover:text-red-400 transition">
            <X className="w-6 h-6" />
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          {img?.image_url ? (
            <img src={img.image_url} alt={label} className="max-w-full max-h-full object-contain rounded-lg" />
          ) : (
            <span className="text-slate-500">No image available</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="bg-[#0a0f1e] border border-white/[0.08] rounded-2xl shadow-2xl w-[95vw] max-w-[1400px] max-h-[92vh] flex flex-col overflow-hidden">
        {/* ── Header ── */}
        <div className="shrink-0 flex items-center justify-between px-6 py-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
              <SplitSquareHorizontal className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Satellite Imagery Comparison</h2>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <MapPin className="w-3 h-3" />
                <span>{region?.name}</span>
                <span className="text-slate-700">•</span>
                <span>{region?.district}</span>
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-white/[0.06] text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* ── Controls Bar ── */}
        <div className="shrink-0 flex items-center gap-4 px-6 py-3 border-b border-white/[0.06] bg-white/[0.02]">
          {/* Date Picker */}
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-slate-400 font-medium">Historical Date:</span>
            <input
              type="date"
              value={historicalDate}
              onChange={(e) => setHistoricalDate(e.target.value)}
              max={today}
              min="2010-01-01"
              className="bg-white/[0.06] border border-white/[0.1] rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500 transition"
            />
          </div>

          {/* Quick Presets */}
          <div className="flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5 text-slate-500" />
            {datePresets.map((preset) => (
              <button
                key={preset.value}
                onClick={() => setHistoricalDate(preset.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
                  historicalDate === preset.value
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "bg-white/[0.04] text-slate-500 hover:text-slate-300 border border-transparent hover:border-white/[0.08]"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>

          <div className="flex-1" />

          {/* Image Source Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Source:</span>
            {[
              { value: "osm", label: "OSM" },
              { value: "esri", label: "Satellite" },
            ].map((src) => (
              <button
                key={src.value}
                onClick={() => setImageSource(src.value)}
                className={`px-2.5 py-1 rounded-md text-xs font-semibold transition ${
                  imageSource === src.value
                    ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                    : "bg-white/[0.04] text-slate-500 hover:text-slate-300 border border-transparent"
                }`}
              >
                {src.label}
              </button>
            ))}
          </div>

          {/* Zoom/BBox Control */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-500">Range:</span>
            {[1, 2, 3, 5].map((km) => (
              <button
                key={km}
                onClick={() => setBboxKm(km)}
                className={`px-2 py-1 rounded-md text-xs font-semibold transition ${
                  bboxKm === km
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                    : "bg-white/[0.04] text-slate-500 hover:text-slate-300 border border-transparent"
                }`}
              >
                {km}km
              </button>
            ))}
          </div>
        </div>

        {/* ── Side by Side Images ── */}
        <div className="flex-1 flex min-h-0 overflow-hidden">
          {/* Current Image */}
          <div className="flex-1 flex flex-col border-r border-white/[0.06]">
            <div className="shrink-0 flex items-center justify-between px-4 py-2.5 bg-emerald-500/[0.06] border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 dot-pulse" />
                <span className="text-sm font-bold text-emerald-400">CURRENT</span>
                <span className="text-xs text-slate-500">{today}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setFullscreen("current")}
                  className="p-1.5 rounded-md hover:bg-white/[0.06] text-slate-500 hover:text-white transition"
                  title="Fullscreen"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
                {currentImg?.image_url && (
                  <a
                    href={currentImg.image_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-md hover:bg-white/[0.06] text-slate-500 hover:text-white transition"
                    title="Download"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
            <div className="flex-1 flex items-center justify-center p-3 bg-black/30">
              {loadingCurrent ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
                  <span className="text-xs text-slate-500">Loading current imagery…</span>
                </div>
              ) : currentImg?.image_url ? (
                <div className="relative w-full h-full flex items-center justify-center">
                  <img
                    src={currentImg.image_url}
                    alt={`Current satellite view of ${region?.name}`}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
                    onLoad={() => console.log('Current image loaded successfully')}
                    onError={(e) => {
                      console.error('Current image failed to load:', currentImg.image_url);
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div style={{ display: 'none' }} className="flex flex-col items-center gap-2">
                    <Satellite className="w-8 h-8 text-red-600" />
                    <span className="text-xs text-red-400">Failed to load image</span>
                    <a 
                      href={currentImg.image_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:underline"
                    >
                      Open in new tab
                    </a>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Satellite className="w-8 h-8 text-slate-600" />
                  <span className="text-xs text-slate-500">No imagery available</span>
                </div>
              )}
            </div>
          </div>

          {/* Divider Arrow */}
          <div className="shrink-0 flex items-center justify-center w-0 relative z-10">
            <div className="absolute w-10 h-10 rounded-full bg-[#0a0f1e] border-2 border-white/[0.1] flex items-center justify-center shadow-xl">
              <ArrowLeftRight className="w-4 h-4 text-blue-400" />
            </div>
          </div>

          {/* Historical Image */}
          <div className="flex-1 flex flex-col">
            <div className="shrink-0 flex items-center justify-between px-4 py-2.5 bg-amber-500/[0.06] border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
                <span className="text-sm font-bold text-amber-400">HISTORICAL</span>
                <span className="text-xs text-slate-500">{historicalDate}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setFullscreen("historical")}
                  className="p-1.5 rounded-md hover:bg-white/[0.06] text-slate-500 hover:text-white transition"
                  title="Fullscreen"
                >
                  <Maximize2 className="w-3.5 h-3.5" />
                </button>
                {historicalImg?.image_url && (
                  <a
                    href={historicalImg.image_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-1.5 rounded-md hover:bg-white/[0.06] text-slate-500 hover:text-white transition"
                    title="Download"
                  >
                    <Download className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
            </div>
            <div className="flex-1 flex items-center justify-center p-3 bg-black/30">
              {loadingHistorical ? (
                <div className="flex flex-col items-center gap-3">
                  <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
                  <span className="text-xs text-slate-500">Loading historical imagery…</span>
                </div>
              ) : historicalImg?.image_url ? (
                <div className="relative w-full h-full flex items-center justify-center">
                  <img
                    src={historicalImg.image_url}
                    alt={`Historical satellite view of ${region?.name} on ${historicalDate}`}
                    className="max-w-full max-h-full object-contain rounded-lg shadow-2xl"
                    onLoad={() => console.log('Historical image loaded successfully')}
                    onError={(e) => {
                      console.error('Historical image failed to load:', historicalImg.image_url);
                      e.target.style.display = 'none';
                      e.target.nextSibling.style.display = 'flex';
                    }}
                  />
                  <div style={{ display: 'none' }} className="flex flex-col items-center gap-2">
                    <Satellite className="w-8 h-8 text-red-600" />
                    <span className="text-xs text-red-400">Failed to load image</span>
                    <a 
                      href={historicalImg.image_url} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-xs text-blue-400 hover:underline"
                    >
                      Open in new tab
                    </a>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-2">
                  <Satellite className="w-8 h-8 text-slate-600" />
                  <span className="text-xs text-slate-500">Select a date to load historical imagery</span>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── Footer Info ── */}
        <div className="shrink-0 px-6 py-3 border-t border-white/[0.06] bg-white/[0.02]">
          <div className="flex items-center justify-between text-xs text-slate-500">
            <div className="flex items-center gap-4">
              <span>Source: {currentImg?.source || (imageSource === "osm" ? "OpenStreetMap" : "ESRI World Imagery")}</span>
              <span className="text-slate-700">•</span>
              <span>Coverage: {bboxKm}km radius</span>
              <span className="text-slate-700">•</span>
              <span>Coords: {region?.latitude?.toFixed(4)}°N, {region?.longitude?.toFixed(4)}°E</span>
            </div>
            <div className="flex items-center gap-2 text-blue-400">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
              <span className="text-xs">
                {imageSource === "osm" ? "OpenStreetMap street view" : "Latest satellite imagery"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
