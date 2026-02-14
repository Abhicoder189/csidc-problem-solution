"use client";

import { useState, useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from "react";
import { Crosshair, Layers, Map as MapIcon, Satellite, Eye, EyeOff, TreePine, Car, Square, Droplets, Shield } from "lucide-react";

const ESRI_SATELLITE =
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const OSM_TILE = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

const PLOT_COLORS = {
  Allotted: "#ef4444",
  Available: "#22c55e",
  "Under Construction": "#f59e0b",
  Encroached: "#a855f7",
  Disputed: "#f43f5e",
  Reserved: "#3b82f6",
};

const ZONE_COLORS = {
  "Green Area": "#6b8e23",
  "Parking": "#c4a35a",
  "Other Land": "#b8a070",
  "Water Tank": "#5b9bd5",
  "Guard Room": "#8b7d6b",
  "ETP": "#708090",
  "Road": "#a09070",
};

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

const MapViewInner = forwardRef(function MapViewInner({
  center,
  imagery,
  encroachments,
  selectedRegion,
  onPlotClick,
  selectedPlotId,
}, ref) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const mlRef = useRef(null);
  const markersRef = useRef([]);
  const labelMarkersRef = useRef([]);
  const [mapReady, setMapReady] = useState(false);
  const [mapError, setMapError] = useState(null);
  const [isSatellite, setIsSatellite] = useState(true); // Default to Satellite (ESRI)
  const [plotsData, setPlotsData] = useState(null);
  const [hoveredPlot, setHoveredPlot] = useState(null);
  const [layerVisibility, setLayerVisibility] = useState({
    plots: true,
    zones: true,
    boundary: true,
    labels: true,
    roads: true,
  });
  const regionLabelRef = useRef(null);

  const onPlotClickRef = useRef(onPlotClick);
  useEffect(() => { onPlotClickRef.current = onPlotClick; }, [onPlotClick]);

  // Expose mapRef to parent for heatmap overlay
  useImperativeHandle(ref, () => mapRef, []);

  /* ── Build map style ──────────────────────────────────────────── */
  const buildStyle = useCallback((sat) => {
    const glyphs = "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf";
    if (sat) {
      return {
        version: 8, name: "Satellite",
        sources: { esri: { type: "raster", tiles: [ESRI_SATELLITE], tileSize: 256, attribution: "&copy; Esri", maxzoom: 19 } },
        layers: [{ id: "esri", type: "raster", source: "esri" }],
        glyphs,
      };
    }
    return {
      version: 8, name: "OSM",
      sources: { osm: { type: "raster", tiles: [OSM_TILE], tileSize: 256, attribution: "&copy; OpenStreetMap", maxzoom: 19 } },
      layers: [{ id: "osm", type: "raster", source: "osm" }],
      glyphs,
    };
  }, []);

  /* ── Init map ─────────────────────────────────────────────────── */
  useEffect(() => {
    if (mapRef.current) return;
    let cancelled = false;

    (async () => {
      try {
        console.log('Initializing map...');
        const maplibregl = (await import("maplibre-gl")).default;
        if (cancelled) return;
        mlRef.current = maplibregl;
        console.log('MapLibre GL loaded');

        if (!containerRef.current || containerRef.current.clientWidth === 0) {
          console.log('Waiting for container...');
          await new Promise((r) => setTimeout(r, 150));
        }
        if (cancelled || !containerRef.current) return;

        console.log('Container ready:', containerRef.current.clientWidth, 'x', containerRef.current.clientHeight);

        const m = new maplibregl.Map({
          container: containerRef.current,
          style: buildStyle(true),
          center: [center.lng, center.lat],
          zoom: center.zoom || 10,
          attributionControl: false,
          failIfMajorPerformanceCaveat: false,
        });

        console.log('Map instance created');

        m.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
        m.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");

        m.on("load", () => {
          console.log('Map loaded successfully');
          if (!cancelled) { mapRef.current = m; setMapReady(true); }
        });

        m.on("error", (e) => {
          console.error('Map error:', e);
        });

        setTimeout(() => {
          if (!cancelled && !mapRef.current && m) {
            console.log('Map ready via timeout');
            mapRef.current = m; setMapReady(true);
          }
        }, 3000);
      } catch (err) {
        console.error("Map init error:", err);
        if (!cancelled) setMapError(err.message);
      }
    })();

    return () => { cancelled = true; if (mapRef.current) { mapRef.current.remove(); mapRef.current = null; } setMapReady(false); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ── Toggle satellite / base ──────────────────────────────────── */
  const toggleStyle = useCallback(() => {
    if (!mapRef.current) return;
    const next = !isSatellite;
    setIsSatellite(next);
    mapRef.current.setStyle(buildStyle(next));
    mapRef.current.once("style.load", () => {
      if (plotsData) drawPlots(plotsData);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSatellite, buildStyle, plotsData]);

  /* ── Fly to center ────────────────────────────────────────────── */
  useEffect(() => {
    if (!mapRef.current || !mapReady) return;
    mapRef.current.flyTo({ center: [center.lng, center.lat], zoom: center.zoom || 14, duration: 1800, essential: true });
  }, [center, mapReady]);

  /* ── Fetch plots when region changes ──────────────────────────── */
  useEffect(() => {
    if (!selectedRegion) { setPlotsData(null); return; }
    (async () => {
      try {
        const res = await fetch(`${API}/legacy/plots?region=${selectedRegion.region_id}`);
        if (!res.ok) throw new Error("Failed");
        setPlotsData(await res.json());
      } catch (err) { console.error("Plot fetch:", err); }
    })();
  }, [selectedRegion]);

  /* ── Helper: remove plot layers ───────────────────────────────── */
  function clearPlotLayers(map) {
    [
      "plots-fill", "plots-line", "plots-highlight-line",
      "region-boundary-fill", "region-boundary-line",
      "zones-fill", "zones-line", "zones-label",
      "roads-fill", "roads-line",
      "encroach-fill", "encroach-line",
    ].forEach((id) => { if (map.getLayer(id)) map.removeLayer(id); });
    ["plots", "region-boundary", "zones", "roads", "encroach"]
      .forEach((s) => { if (map.getSource(s)) map.removeSource(s); });
    labelMarkersRef.current.forEach((m) => m.remove());
    labelMarkersRef.current = [];
    markersRef.current.forEach((m) => m.remove());
    markersRef.current = [];
    if (regionLabelRef.current) { regionLabelRef.current.remove(); regionLabelRef.current = null; }
  }

  /* ── Draw all plot layers ─────────────────────────────────────── */
  function drawPlots(data) {
    const map = mapRef.current;
    const ml = mlRef.current;
    if (!map || !ml || !data) return;

    clearPlotLayers(map);

    // ── Region boundary source (add source early, line layer added LAST so it's on top) ──
    if (data.region_boundary) {
      map.addSource("region-boundary", { type: "geojson", data: data.region_boundary });
      map.addLayer({
        id: "region-boundary-fill", type: "fill", source: "region-boundary",
        paint: { "fill-color": "#ef4444", "fill-opacity": 0.03 },
      });
    }

    // ── Land-use zones (Green Area, Parking, Other Land, etc.) ──
    if (data.zones_geojson?.features?.length) {
      // Separate roads from other zones
      const roadFeatures = data.zones_geojson.features.filter(f => f.properties.zone_type === "Road");
      const otherZones = data.zones_geojson.features.filter(f => f.properties.zone_type !== "Road");

      // Non-road zones
      if (otherZones.length) {
        otherZones.forEach((f, i) => { f.id = 1000 + i; });
        map.addSource("zones", {
          type: "geojson",
          data: { type: "FeatureCollection", features: otherZones },
        });
        map.addLayer({
          id: "zones-fill", type: "fill", source: "zones",
          paint: {
            "fill-color": ["get", "zone_color"],
            "fill-opacity": 0.65,
          },
        });
        map.addLayer({
          id: "zones-line", type: "line", source: "zones",
          paint: {
            "line-color": ["get", "zone_color"],
            "line-width": 2,
            "line-opacity": 0.9,
          },
        });

        // Zone labels as RED text markers (government GIS style)
        otherZones.forEach((feat) => {
          const coords = feat.geometry.coordinates[0];
          const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length;
          const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length;
          const el = document.createElement("div");
          el.style.cssText = `
            font-size:11px;font-weight:900;color:#ef4444;
            text-shadow:1px 1px 3px rgba(0,0,0,0.9),-1px -1px 3px rgba(0,0,0,0.9),1px -1px 3px rgba(0,0,0,0.9),-1px 1px 3px rgba(0,0,0,0.9);
            pointer-events:none;user-select:none;white-space:nowrap;
            text-transform:uppercase;letter-spacing:0.06em;
            font-family:'Arial Black','Inter',system-ui,sans-serif;
          `;
          el.textContent = feat.properties.label;
          const marker = new ml.Marker({ element: el, anchor: "center" })
            .setLngLat([cx, cy]).addTo(map);
          labelMarkersRef.current.push(marker);
        });
      }

      // Road zones
      if (roadFeatures.length) {
        roadFeatures.forEach((f, i) => { f.id = 2000 + i; });
        map.addSource("roads", {
          type: "geojson",
          data: { type: "FeatureCollection", features: roadFeatures },
        });
        map.addLayer({
          id: "roads-fill", type: "fill", source: "roads",
          paint: { "fill-color": "#d4c5a0", "fill-opacity": 0.35 },
        });
        map.addLayer({
          id: "roads-line", type: "line", source: "roads",
          paint: { "line-color": "#a0906b", "line-width": 1.5, "line-opacity": 0.7 },
        });

        // Road labels in RED
        roadFeatures.forEach((feat) => {
          const coords = feat.geometry.coordinates[0];
          const cx = coords.reduce((s, c) => s + c[0], 0) / coords.length;
          const cy = coords.reduce((s, c) => s + c[1], 0) / coords.length;
          const el = document.createElement("div");
          el.style.cssText = `
            font-size:10px;font-weight:900;color:#ef4444;
            text-shadow:1px 1px 2px rgba(0,0,0,0.9),-1px -1px 2px rgba(0,0,0,0.9);
            pointer-events:none;user-select:none;white-space:nowrap;
            text-transform:uppercase;letter-spacing:0.05em;
            font-family:'Arial Black','Inter',system-ui,sans-serif;
          `;
          el.textContent = "ROAD";
          const marker = new ml.Marker({ element: el, anchor: "center" })
            .setLngLat([cx, cy]).addTo(map);
          labelMarkersRef.current.push(marker);
        });
      }
    }

    // ── Plot polygons ──
    if (data.plots_geojson) {
      data.plots_geojson.features?.forEach((f, i) => { f.id = i; });

      map.addSource("plots", { type: "geojson", data: data.plots_geojson });

      map.addLayer({
        id: "plots-fill", type: "fill", source: "plots",
        paint: {
          "fill-color": [
            "match", ["get", "status"],
            "Allotted", PLOT_COLORS["Allotted"],
            "Available", PLOT_COLORS["Available"],
            "Under Construction", PLOT_COLORS["Under Construction"],
            "Encroached", PLOT_COLORS["Encroached"],
            "Disputed", PLOT_COLORS["Disputed"],
            "Reserved", PLOT_COLORS["Reserved"],
            "#6b7280",
          ],
          "fill-opacity": ["case", ["boolean", ["feature-state", "hover"], false], 1.0, 0.92],
        },
      });

      map.addLayer({
        id: "plots-line", type: "line", source: "plots",
        paint: {
          "line-color": "#1a1a1a",
          "line-width": ["case", ["boolean", ["feature-state", "hover"], false], 3, 1.5],
          "line-opacity": 1,
        },
      });

      // White highlight for selected plot
      map.addLayer({
        id: "plots-highlight-line", type: "line", source: "plots",
        paint: { "line-color": "#ffffff", "line-width": 3.5, "line-opacity": 0.95 },
        filter: ["==", ["get", "plot_id"], ""],
      });
    }

    // ── Region boundary line ON TOP of everything (red dashed) ──
    if (data.region_boundary && map.getSource("region-boundary")) {
      map.addLayer({
        id: "region-boundary-line", type: "line", source: "region-boundary",
        paint: { "line-color": "#ef4444", "line-width": 4, "line-opacity": 1, "line-dasharray": [6, 4] },
      });
    }

    // ── Plot number labels (bold white text directly on solid blocks) ──
    data.plots?.forEach((plot) => {
      const el = document.createElement("div");
      el.style.cssText = `
        font-size:12px;font-weight:900;color:#fff;
        text-shadow:1px 1px 2px rgba(0,0,0,0.9),-1px -1px 2px rgba(0,0,0,0.9),1px -1px 2px rgba(0,0,0,0.9),-1px 1px 2px rgba(0,0,0,0.9);
        pointer-events:none;user-select:none;
        font-family:'Arial Black','Inter',system-ui,sans-serif;
        line-height:1;
      `;
      el.textContent = plot.plot_number;
      const marker = new ml.Marker({ element: el, anchor: "center" })
        .setLngLat([plot.longitude, plot.latitude])
        .addTo(map);
      labelMarkersRef.current.push(marker);
    });

    // ── Region name label (large RED text like govt GIS portal) ──
    if (data.region_label) {
      const el = document.createElement("div");
      el.style.cssText = `
        font-size:18px;font-weight:900;color:#ef4444;
        text-shadow:2px 2px 4px rgba(0,0,0,0.9),-2px -2px 4px rgba(0,0,0,0.9),2px -2px 4px rgba(0,0,0,0.9),-2px 2px 4px rgba(0,0,0,0.9);
        pointer-events:none;user-select:none;
        font-family:'Arial Black','Impact',system-ui,sans-serif;
        text-transform:uppercase;letter-spacing:0.08em;
        white-space:nowrap;
      `;
      el.textContent = data.region_label.text;
      const marker = new ml.Marker({ element: el, anchor: "center" })
        .setLngLat([data.region_label.longitude, data.region_label.latitude])
        .addTo(map);
      regionLabelRef.current = marker;
    }

    // ── Click ──
    if (map.getSource("plots")) {
      map.on("click", "plots-fill", (e) => {
        if (!e.features?.length) return;
        const props = e.features[0].properties;
        const detail = data.plots?.find((p) => p.plot_id === props.plot_id);
        if (detail && onPlotClickRef.current) onPlotClickRef.current(detail);
        map.setFilter("plots-highlight-line", ["==", ["get", "plot_id"], props.plot_id]);
      });

      // ── Hover ──
      let hovId = null;
      map.on("mousemove", "plots-fill", (e) => {
        map.getCanvas().style.cursor = "pointer";
        if (e.features?.length) {
          if (hovId !== null) map.setFeatureState({ source: "plots", id: hovId }, { hover: false });
          hovId = e.features[0].id;
          map.setFeatureState({ source: "plots", id: hovId }, { hover: true });
          setHoveredPlot(e.features[0].properties);
        }
      });
      map.on("mouseleave", "plots-fill", () => {
        map.getCanvas().style.cursor = "";
        if (hovId !== null) { map.setFeatureState({ source: "plots", id: hovId }, { hover: false }); hovId = null; }
        setHoveredPlot(null);
      });
    }
  }

  /* ── Render plots when data arrives ───────────────────────────── */
  useEffect(() => {
    if (!mapRef.current || !mapReady) return;
    const map = mapRef.current;
    if (!plotsData) { clearPlotLayers(map); return; }
    if (map.isStyleLoaded()) drawPlots(plotsData);
    else map.once("style.load", () => drawPlots(plotsData));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plotsData, mapReady]);

  /* ── Highlight selected plot ──────────────────────────────────── */
  useEffect(() => {
    if (!mapRef.current || !mapReady) return;
    const map = mapRef.current;
    if (map.getLayer("plots-highlight-line")) {
      map.setFilter("plots-highlight-line", ["==", ["get", "plot_id"], selectedPlotId || ""]);
    }
  }, [selectedPlotId, mapReady]);

  /* ── Encroachment overlay ─────────────────────────────────────── */
  useEffect(() => {
    if (!mapRef.current || !mapReady) return;
    const map = mapRef.current;
    if (map.getLayer("encroach-fill")) map.removeLayer("encroach-fill");
    if (map.getLayer("encroach-line")) map.removeLayer("encroach-line");
    if (map.getSource("encroach")) map.removeSource("encroach");
    if (!encroachments?.boundary_geojson) return;

    map.addSource("encroach", { type: "geojson", data: encroachments.boundary_geojson });
    map.addLayer({
      id: "encroach-fill", type: "fill", source: "encroach",
      paint: {
        "fill-color": ["match", ["get", "status"], "outside_boundary", "#ef4444", "partial_construction", "#f59e0b", "vacant_plot", "#6b7280", "#22c55e"],
        "fill-opacity": 0.2,
      },
    });
    map.addLayer({
      id: "encroach-line", type: "line", source: "encroach",
      paint: {
        "line-color": ["match", ["get", "status"], "outside_boundary", "#ef4444", "partial_construction", "#f59e0b", "vacant_plot", "#6b7280", "#22c55e"],
        "line-width": 2,
      },
    });
  }, [encroachments, mapReady]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="absolute inset-0" style={{ width: "100%", height: "100%" }} />

      {/* Loading */}
      {!mapReady && !mapError && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#060a13]/90">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-[3px] border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
            <span className="text-xs text-slate-500 font-medium">Loading satellite imagery…</span>
          </div>
        </div>
      )}

      {/* Error */}
      {mapError && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#060a13]">
          <div className="flex flex-col items-center gap-3 text-center px-8">
            <Crosshair className="w-8 h-8 text-red-400" />
            <p className="text-sm font-medium text-red-400">Map failed to load</p>
            <p className="text-xs text-slate-500 max-w-xs">{mapError}</p>
          </div>
        </div>
      )}

      {/* Empty state */}
      {mapReady && !selectedRegion && (
        <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.04] border border-white/[0.08] flex items-center justify-center">
              <Crosshair className="w-7 h-7 text-indigo-400/60" />
            </div>
            <p className="text-sm font-medium text-slate-400">Select a region to view plots</p>
            <p className="text-xs text-slate-600">56 industrial areas across Chhattisgarh</p>
          </div>
        </div>
      )}

      {/* Style toggle - REMOVED (Forced to Satellite) */}
      {/* {mapReady && (
        <div className="absolute top-3 left-3 z-20">
           ...
        </div>
      )} */}

      {/* Region badge */}
      {selectedRegion && mapReady && (
        <div className="absolute top-3 left-32 z-20 fade-in">
          <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-[#0a0f1e]/85 backdrop-blur-xl border border-white/[0.08] shadow-xl">
            <div className="w-2 h-2 rounded-full bg-emerald-400 dot-pulse" />
            <span className="text-xs font-semibold text-white">{selectedRegion.name}</span>
            {plotsData && (
              <span className="text-[10px] text-slate-500 ml-1">
                {plotsData.total_plots} plots • {plotsData.total_zones || 0} zones
              </span>
            )}
          </div>
        </div>
      )}

      {/* Hover tooltip */}
      {hoveredPlot && (
        <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-20 pointer-events-none fade-in">
          <div className="flex items-center gap-3 px-4 py-2.5 rounded-xl bg-[#0a0f1e]/90 backdrop-blur-xl border border-white/[0.1] shadow-2xl">
            <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: PLOT_COLORS[hoveredPlot.status] || "#6b7280" }} />
            <span className="text-xs font-semibold text-white">{hoveredPlot.plot_id}</span>
            <span className="text-[10px] text-slate-400">{hoveredPlot.status}</span>
            <span className="text-[10px] text-slate-500">{hoveredPlot.plot_type}</span>
            <span className="text-[10px] text-slate-600">Sec {hoveredPlot.sector}</span>
          </div>
        </div>
      )}

      {/* Legend */}
      {plotsData && mapReady && (
        <div className="absolute bottom-10 left-3 z-20 fade-in">
          <div className="px-3 py-2.5 rounded-xl bg-[#0a0f1e]/85 backdrop-blur-xl border border-white/[0.08] shadow-xl max-h-[45vh] overflow-y-auto scrollbar-thin">
            {/* Plot Status Section */}
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Layers className="w-3 h-3" /> Plot Status
            </div>
            <div className="flex flex-col gap-1.5">
              {Object.entries(PLOT_COLORS).map(([status, color]) => (
                <div key={status} className="flex items-center gap-2 text-[11px] text-slate-400">
                  <div className="w-3 h-3 rounded-sm border border-white/10" style={{ backgroundColor: color }} />
                  {status}
                  {plotsData.status_summary?.[status] != null && (
                    <span className="text-slate-600 ml-auto">{plotsData.status_summary[status]}</span>
                  )}
                </div>
              ))}
            </div>

            {/* Zone Section */}
            {plotsData.zone_summary && Object.keys(plotsData.zone_summary).length > 0 && (
              <>
                <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-3 mb-2 pt-2 border-t border-white/[0.06] flex items-center gap-1.5">
                  <TreePine className="w-3 h-3" /> Land Use Zones
                </div>
                <div className="flex flex-col gap-1.5">
                  {Object.entries(plotsData.zone_summary).map(([zoneType, count]) => (
                    <div key={zoneType} className="flex items-center gap-2 text-[11px] text-slate-400">
                      <div className="w-3 h-3 rounded-sm border border-white/10" style={{ backgroundColor: ZONE_COLORS[zoneType] || "#6b7280" }} />
                      {zoneType}
                      <span className="text-slate-600 ml-auto">{count}</span>
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Boundary */}
            <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-2 pt-2 border-t border-white/[0.06]">
              <div className="w-3 h-3 rounded-sm border-2 border-dashed border-red-400" />
              Region Boundary
            </div>
          </div>
        </div>
      )}
    </div>
  );
});

export default MapViewInner;
