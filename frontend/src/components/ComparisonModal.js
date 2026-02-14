"use client";

import { ReactCompareSlider, ReactCompareSliderImage } from "react-compare-slider";

export default function ComparisonModal({ original, enhanced, onClose }) {
  const originalSrc = enhanced.original_b64
    ? `data:image/png;base64,${enhanced.original_b64}`
    : original.image_url;

  const enhancedSrc = enhanced.enhanced_b64
    ? `data:image/png;base64,${enhanced.enhanced_b64}`
    : null;

  if (!enhancedSrc) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="glass rounded-2xl p-6 max-w-4xl w-full mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold">
              ESRGAN Super-Resolution Comparison
            </h2>
            <p className="text-sm text-gray-400">
              {enhanced.original_resolution?.[0]}×{enhanced.original_resolution?.[1]}
              {" → "}
              {enhanced.enhanced_resolution?.[0]}×{enhanced.enhanced_resolution?.[1]}
              {" · "}
              {enhanced.scale_factor}× upscale
              {" · "}
              {enhanced.processing_time_ms}ms
              {" · "}
              {enhanced.model}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-100 text-2xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Comparison Slider */}
        <div className="rounded-xl overflow-hidden border border-gray-700">
          <ReactCompareSlider
            itemOne={
              <ReactCompareSliderImage
                src={originalSrc}
                alt="Original Satellite Image"
                style={{ objectFit: "contain" }}
              />
            }
            itemTwo={
              <ReactCompareSliderImage
                src={enhancedSrc}
                alt="ESRGAN Enhanced Image"
                style={{ objectFit: "contain" }}
              />
            }
            style={{ height: "500px" }}
          />
        </div>

        {/* Labels */}
        <div className="flex justify-between mt-3 text-sm">
          <span className="text-gray-400">← Original</span>
          <span className="text-brand-400">Enhanced (ESRGAN) →</span>
        </div>
      </div>
    </div>
  );
}
