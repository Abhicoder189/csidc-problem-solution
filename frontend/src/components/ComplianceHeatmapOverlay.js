"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Flame, Eye, EyeOff, Sliders, ChevronDown, Loader2,
} from "lucide-react";
import { getComplianceHeatmap } from "@/lib/api";

/**
 * ComplianceHeatmapOverlay — attaches to an existing maplibre-gl map instance
 * to render a heatmap layer showing compliance risk intensity.
 *
 * Props:
 *  - mapRef: React ref containing the maplibre-gl map instance
 *  - visible: boolean controlling visibility
 *  - onToggle: callback to toggle visibility
 */
export default function ComplianceHeatmapOverlay({ mapRef, visible, onToggle }) {
  const [heatmapData, setHeatmapData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [opacity, setOpacity] = useState(0.6);

  // Fetch heatmap data
  useEffect(() => {
    if (!visible) return;
    setLoading(true);
    getComplianceHeatmap()
      .then((data) => setHeatmapData(data))
      .catch((err) => console.error("Heatmap fetch error:", err))
      .finally(() => setLoading(false));
  }, [visible]);

  // Render heatmap layer on map
  useEffect(() => {
    const map = mapRef?.current;
    if (!map || !heatmapData?.regions || !visible) return;

    const removeExisting = () => {
      if (map.getLayer("compliance-heatmap")) map.removeLayer("compliance-heatmap");
      if (map.getLayer("compliance-circles")) map.removeLayer("compliance-circles");
      if (map.getSource("compliance-heat")) map.removeSource("compliance-heat");
    };

    const addHeatmap = () => {
      removeExisting();

      const features = heatmapData.regions.map((r) => ({
        type: "Feature",
        geometry: {
          type: "Point",
          coordinates: [r.longitude, r.latitude],
        },
        properties: {
          intensity: 1 - (r.compliance_score || 50) / 100,  // Higher intensity = lower compliance
          score: r.compliance_score || 50,
          violations: r.violations || 0,
          name: r.region || r.name || "",
        },
      }));

      map.addSource("compliance-heat", {
        type: "geojson",
        data: { type: "FeatureCollection", features },
      });

      // Heatmap layer
      map.addLayer({
        id: "compliance-heatmap",
        type: "heatmap",
        source: "compliance-heat",
        paint: {
          "heatmap-weight": ["get", "intensity"],
          "heatmap-intensity": [
            "interpolate", ["linear"], ["zoom"],
            8, 1. ,
            13, 3,
          ],
          "heatmap-radius": [
            "interpolate", ["linear"], ["zoom"],
            8, 25,
            13, 50,
          ],
          "heatmap-opacity": opacity,
          "heatmap-color": [
            "interpolate", ["linear"], ["heatmap-density"],
            0, "rgba(0,0,0,0)",
            0.1, "rgba(16,185,129,0.2)",
            0.3, "rgba(245,158,11,0.4)",
            0.5, "rgba(249,115,22,0.6)",
            0.7, "rgba(239,68,68,0.75)",
            1, "rgba(220,38,38,0.9)",
          ],
        },
      });

      // Circle overlay for labels at higher zoom
      map.addLayer({
        id: "compliance-circles",
        type: "circle",
        source: "compliance-heat",
        minzoom: 11,
        paint: {
          "circle-radius": 8,
          "circle-color": [
            "interpolate", ["linear"], ["get", "score"],
            0, "#ef4444",
            50, "#f59e0b",
            80, "#10b981",
            100, "#22c55e",
          ],
          "circle-stroke-color": "#fff",
          "circle-stroke-width": 1.5,
          "circle-opacity": 0.85,
        },
      });
    };

    if (map.isStyleLoaded()) addHeatmap();
    else map.once("style.load", addHeatmap);

    return () => {
      if (map && map.getStyle()) removeExisting();
    };
  }, [heatmapData, visible, opacity, mapRef]);

  // Clean up heatmap when hidden
  useEffect(() => {
    if (visible) return;
    const map = mapRef?.current;
    if (!map) return;
    if (map.getLayer("compliance-heatmap")) map.removeLayer("compliance-heatmap");
    if (map.getLayer("compliance-circles")) map.removeLayer("compliance-circles");
    if (map.getSource("compliance-heat")) map.removeSource("compliance-heat");
  }, [visible, mapRef]);

  return (
    <div className="absolute top-3 right-16 z-20 flex items-center gap-2">
      {/* Toggle button */}
      <button
        onClick={onToggle}
        className={`flex items-center gap-2 px-3 py-2 rounded-xl backdrop-blur-xl border shadow-xl text-xs font-medium transition-all ${
          visible
            ? "bg-red-500/15 border-red-500/25 text-red-300"
            : "bg-[#0a0f1e]/85 border-white/[0.08] text-slate-300 hover:text-white"
        }`}
      >
        <Flame className="w-3.5 h-3.5" />
        {visible ? "Heatmap On" : "Heatmap"}
        {loading && <Loader2 className="w-3 h-3 animate-spin ml-1" />}
      </button>

      {/* Opacity slider (visible when heatmap is on) */}
      {visible && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#0a0f1e]/85 backdrop-blur-xl border border-white/[0.08] shadow-xl fade-in">
          <Eye className="w-3 h-3 text-slate-400" />
          <input
            type="range"
            min="0.1"
            max="1"
            step="0.1"
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="w-20 h-1 accent-red-500"
          />
          <span className="text-[10px] text-slate-500 w-6">{(opacity * 100).toFixed(0)}%</span>
        </div>
      )}
    </div>
  );
}
