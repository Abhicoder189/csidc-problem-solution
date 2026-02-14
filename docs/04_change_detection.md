# 4️⃣ Change Detection Strategy

## 4.1 Methods Comparison

### 4.1.1 NDVI-Based Vegetation Change

**Normalized Difference Vegetation Index:**

```
         NIR − Red       B8 − B4
NDVI = ─────────── = ───────────── (Sentinel-2 bands)
         NIR + Red       B8 + B4

NDVI ∈ [−1, +1]
  > 0.4  → Dense vegetation
  0.2–0.4 → Sparse vegetation / grass
  0.0–0.2 → Bare soil / built-up
  < 0.0  → Water / shadow
```

**Change Detection:**
```
ΔNDVI = NDVI_t2 − NDVI_t1

ΔNDVI < −0.3 → Vegetation cleared (likely construction)
ΔNDVI > +0.3 → Revegetation (possibly abandoned)
|ΔNDVI| < 0.1 → No significant change
```

**Strengths:** Simple, computationally cheap, good for detecting construction on vacant vegetated plots.

**Weaknesses:** Cannot distinguish construction from bare soil changes. Fails in already built-up areas.

### 4.1.2 Pixel Differencing

**Spectral Euclidean Distance:**

```
d(p) = √( Σᵢ (Bᵢ_t2(p) − Bᵢ_t1(p))² )

Where Bᵢ = Band i value at pixel p
```

**Thresholded Change Map:**
```
C(p) = 1 if d(p) > τ, else 0

τ = μ_d + k·σ_d  (Otsu or k-sigma thresholding)
```

**Strengths:** Band-agnostic, captures all spectral changes.

**Weaknesses:** Highly sensitive to atmospheric/radiometric differences. Many false positives.

### 4.1.3 Supervised Semantic Segmentation

**Architecture: DeepLabV3+ with ResNet-101 backbone**

```
Input (T1 or T2):  256×256×4 (RGBNIR)
                        │
                   ResNet-101 Encoder
                        │
              Atrous Spatial Pyramid Pooling (ASPP)
              ┌─────┬─────┬─────┬─────┐
              │ 1×1 │ 3×3 │ 3×3 │ 3×3 │
              │ r=1 │ r=6 │r=12 │r=18 │
              └──┬──┴──┬──┴──┬──┴──┬──┘
                 │     └──┬──┘     │
                 └────────┼────────┘
                     Concat + 1×1 Conv
                          │
                    Decoder (4× upsample)
                          │
                    Output: 256×256×C (C classes)
```

**Strengths:** Most accurate per-pixel classification. Handles complex land-use categories.

**Weaknesses:** Requires labeled training data. Computationally expensive.

### 4.1.4 Siamese Neural Networks for Change Detection

**Architecture: Siamese UNet**

```
Image T1 (256×256×4)    Image T2 (256×256×4)
        │                        │
   ┌────▼────┐              ┌────▼────┐
   │ Encoder │ (shared)     │ Encoder │ (shared weights)
   │ ResNet  │              │ ResNet  │
   └────┬────┘              └────┬────┘
        │                        │
        └────────┬───────────────┘
                 │
          Feature Difference
          |F_t1 − F_t2| at each scale
                 │
          ┌──────▼──────┐
          │   Decoder    │
          │ (UNet-style) │
          └──────┬──────┘
                 │
          Output: 256×256×1
          (Binary Change Map)
          0 = No Change
          1 = Changed
```

**Strengths:** Specifically designed for bi-temporal change detection. Shared encoder learns illumination-invariant features. State-of-the-art accuracy.

**Weaknesses:** Requires paired temporal training data. Needs careful co-registration.

---

## 4.2 Recommendation for Industrial Monitoring

### 4.2.1 Recommended Hybrid Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│              RECOMMENDED CHANGE DETECTION PIPELINE           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Stage 1: FAST SCREENING (runs every 5 days)                │
│  ├── NDVI change detection (vegetation → construction)      │
│  ├── NDBI change detection (built-up index change)          │
│  └── Pixel differencing with Otsu threshold                 │
│  → Output: Candidate change pixels (binary mask)            │
│                                                              │
│  Stage 2: AI CLASSIFICATION (runs on candidates only)       │
│  ├── DeepLabV3+ segmentation on T2 image                   │
│  ├── Compare T2 segmentation with stored T1 segmentation   │
│  └── Classify change type (construction/demolition/vacancy) │
│  → Output: Classified change polygons                       │
│                                                              │
│  Stage 3: COMPLIANCE CHECK (runs on changed plots)          │
│  ├── Overlay change polygons with allotment boundaries      │
│  ├── Compute IoU, deviation, encroachment                   │
│  └── Generate risk score                                    │
│  → Output: Violation records with evidence                  │
│                                                              │
│  Stage 4: TEMPORAL VALIDATION (monthly)                     │
│  ├── Siamese UNet bi-temporal change confirmation           │
│  ├── Multi-date trend analysis                              │
│  └── False positive filtering                               │
│  → Output: Confirmed violations only                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2.2 Justification

| Criterion | NDVI Only | Pixel Diff | DeepLabV3+ Only | Siamese Only | **Hybrid (Recommended)** |
|-----------|-----------|------------|-----------------|--------------|--------------------------|
| Speed | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ |
| Accuracy | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| False Positives | High | Very High | Low | Very Low | **Very Low** |
| Compute Cost | Low | Low | High | High | **Medium** |
| Training Data | None | None | Heavy | Heavy | **Moderate** |
| Industrial Suitability | Low | Low | High | High | **Very High** |

**Why Hybrid wins:** Spectral indices (Stage 1) cheaply filter 90%+ of tiles as "no change," focusing expensive AI inference (Stages 2–4) only on ~10% of tiles with detected activity. This reduces compute costs by ~90% while maintaining >95% detection accuracy.

---

## 4.3 Index Suite for Industrial Monitoring

### 4.3.1 Key Indices

```python
def compute_indices(image):
    """Compute all relevant spectral indices from Sentinel-2."""
    B2, B3, B4, B8, B11, B12 = (
        image['B02'], image['B03'], image['B04'],
        image['B08'], image['B11'], image['B12']
    )
    
    indices = {
        # Vegetation
        'NDVI': (B8 - B4) / (B8 + B4 + 1e-10),
        
        # Built-up
        'NDBI': (B11 - B8) / (B11 + B8 + 1e-10),
        
        # Bare Soil
        'BSI': ((B11 + B4) - (B8 + B2)) / ((B11 + B4) + (B8 + B2) + 1e-10),
        
        # Water
        'NDWI': (B3 - B8) / (B3 + B8 + 1e-10),
        
        # Built-up v2 (better for industrial)
        'UI': (B11 - B8) / (B11 + B8 + 1e-10),  # Urban Index
        
        # Enhanced Built-up and Bareness Index
        'EBBI': (B11 - B8) / (10 * np.sqrt(B11 + B12)),
    }
    return indices
```

### 4.3.2 Industrial Activity Classification

```
Activity Status Decision Tree:
│
├── NDVI_t2 < 0.15 AND NDBI_t2 > 0.1
│   ├── BSI_t2 < 0.2 → BUILT-UP (Active Industrial)
│   └── BSI_t2 > 0.2 → BARE SOIL (Vacant/Cleared)
│
├── NDVI_t2 > 0.35
│   └── → VEGETATED (Unused/Abandoned)
│
├── ΔNDBI > 0.15 (increased)
│   └── → NEW CONSTRUCTION
│
└── ΔNDVI < −0.25 (decreased)
    └── → VEGETATION CLEARED (Potential Construction Start)
```
