"use client";

import { useState } from "react";
import { detectChange } from "@/lib/api";

export default function ChangeDetectionPanel({ region, onClose }) {
  const [dateBefore, setDateBefore] = useState("2024-01-01");
  const [dateAfter, setDateAfter] = useState("2025-01-01");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleDetect = async () => {
    setLoading(true);
    try {
      const res = await detectChange({
        latitude: region.latitude,
        longitude: region.longitude,
        date_before: dateBefore,
        date_after: dateAfter,
        bbox_km: 2,
        methods: ["image_diff", "ndvi", "built_up"],
      });
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass rounded-2xl p-6 max-w-3xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">
            🔍 Change Detection — {region.name}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-100 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Date pickers */}
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Before</label>
            <input
              type="date"
              value={dateBefore}
              onChange={(e) => setDateBefore(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">After</label>
            <input
              type="date"
              value={dateAfter}
              onChange={(e) => setDateAfter(e.target.value)}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-100"
            />
          </div>
        </div>

        <button
          onClick={handleDetect}
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:bg-gray-700 text-sm font-medium transition-colors mb-6"
        >
          {loading ? "Analysing…" : "Run Change Detection"}
        </button>

        {/* Results */}
        {result && (
          <div className="space-y-4">
            {/* Summary stats */}
            <div className="grid grid-cols-4 gap-3">
              <StatCard
                label="Changed"
                value={`${result.change_percentage?.toFixed(1) || 0}%`}
              />
              <StatCard
                label="New Structures"
                value={result.new_construction_count || 0}
              />
              <StatCard
                label="NDVI Before"
                value={result.ndvi_before?.toFixed(3) || "—"}
              />
              <StatCard
                label="NDVI After"
                value={result.ndvi_after?.toFixed(3) || "—"}
              />
            </div>

            {/* Before / After images */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-gray-400 mb-1">Before ({dateBefore})</div>
                <img
                  src={result.image_before_url}
                  alt="Before"
                  className="w-full h-48 object-cover rounded-lg border border-gray-700"
                />
              </div>
              <div>
                <div className="text-xs text-gray-400 mb-1">After ({dateAfter})</div>
                <img
                  src={result.image_after_url}
                  alt="After"
                  className="w-full h-48 object-cover rounded-lg border border-gray-700"
                />
              </div>
            </div>

            {/* Change overlay */}
            {result.change_overlay_b64 && (
              <div>
                <div className="text-xs text-gray-400 mb-1">Change Heatmap Overlay</div>
                <img
                  src={`data:image/png;base64,${result.change_overlay_b64}`}
                  alt="Change overlay"
                  className="w-full h-48 object-contain rounded-lg border border-gray-700 bg-gray-900"
                />
              </div>
            )}

            {/* GeoJSON changes */}
            {result.change_geojson?.features?.length > 0 && (
              <div>
                <h4 className="text-sm font-medium mb-2">
                  Detected Change Zones ({result.change_geojson.features.length})
                </h4>
                <div className="max-h-40 overflow-y-auto space-y-1">
                  {result.change_geojson.features.map((f, i) => (
                    <div
                      key={i}
                      className="bg-gray-800/60 rounded-lg px-3 py-2 text-xs flex justify-between"
                    >
                      <span>{f.properties?.type || "change"}</span>
                      <span className="text-gray-400">
                        {f.properties?.area_sqm?.toFixed(0) || "?"} m²
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-3 text-center">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-lg font-semibold mt-0.5">{value}</div>
    </div>
  );
}
