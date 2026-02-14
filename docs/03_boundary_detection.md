# 3️⃣ Boundary Detection Logic (Mathematical)

## 3.1 Core Geometric Operations

### 3.1.1 Polygon Intersection Algorithm

The system uses the **Sutherland-Hodgman algorithm** (implemented via GEOS/PostGIS) for polygon clipping, and the **Weiler-Atherton algorithm** for arbitrary polygon intersection.

**Formal Definition:**

Given two polygons:
- **A** = Allotment boundary (official sanctioned polygon)
- **B** = Detected structure footprint (from satellite AI segmentation)

The intersection polygon is:

```
I = A ∩ B = { p ∈ ℝ² : p ∈ A AND p ∈ B }
```

**PostGIS Implementation:**

```sql
SELECT ST_Intersection(
    a.boundary_geom,
    b.detected_geom
) AS intersection_geom
FROM allotment_boundary a, detected_structures b
WHERE ST_Intersects(a.boundary_geom, b.detected_geom);
```

### 3.1.2 Intersection over Union (IoU) Calculation

**Mathematical Formula:**

```
            Area(A ∩ B)
IoU = ─────────────────────
            Area(A ∪ B)

            Area(A ∩ B)
    = ─────────────────────────────────────
      Area(A) + Area(B) − Area(A ∩ B)
```

**IoU Interpretation for Compliance:**

| IoU Range | Interpretation | Action |
|-----------|---------------|--------|
| 0.90–1.00 | Excellent compliance | No action |
| 0.75–0.90 | Minor deviation | Log, monitor |
| 0.50–0.75 | Significant deviation | Investigation |
| 0.25–0.50 | Major violation | Enforcement |
| 0.00–0.25 | Critical / No overlap | Legal action |

**PostGIS SQL:**

```sql
CREATE OR REPLACE FUNCTION compute_iou(
    geom_a GEOMETRY,
    geom_b GEOMETRY
) RETURNS FLOAT AS $$
DECLARE
    intersection_area FLOAT;
    union_area FLOAT;
BEGIN
    -- Transform to UTM Zone 44N for accurate area in sq meters
    intersection_area := ST_Area(
        ST_Intersection(
            ST_Transform(geom_a, 32644),
            ST_Transform(geom_b, 32644)
        )
    );
    
    union_area := ST_Area(ST_Transform(geom_a, 32644))
                + ST_Area(ST_Transform(geom_b, 32644))
                - intersection_area;
    
    IF union_area = 0 THEN
        RETURN 0;
    END IF;
    
    RETURN intersection_area / union_area;
END;
$$ LANGUAGE plpgsql IMMUTABLE;
```

---

## 3.2 Area Deviation Formula

### 3.2.1 Absolute Deviation

```
ΔA = |Area(B) − Area(A)|

Where:
  A = Allotted boundary polygon
  B = Detected structure polygon
```

### 3.2.2 Percentage Deviation

```
            Area(B) − Area(A)
D% = ──────────────────────────── × 100
              Area(A)

Positive D% → Structure exceeds allotment (encroachment)
Negative D% → Structure smaller than allotment (partial utilization / vacancy)
```

### 3.2.3 Directional Deviation (Per Edge)

For each edge $e_i$ of the allotment polygon:

```
d_i = signed_distance(centroid(B), e_i)

If d_i < 0 → encroachment beyond edge e_i
```

**PostGIS Implementation:**

```sql
SELECT 
    p.plot_id,
    ST_Area(ST_Transform(p.allotment_geom, 32644)) AS allotted_area_sqm,
    ST_Area(ST_Transform(d.detected_geom, 32644)) AS detected_area_sqm,
    (ST_Area(ST_Transform(d.detected_geom, 32644)) - 
     ST_Area(ST_Transform(p.allotment_geom, 32644))) /
     ST_Area(ST_Transform(p.allotment_geom, 32644)) * 100 
        AS deviation_percent
FROM plot p
JOIN detected_structures d ON p.plot_id = d.plot_id;
```

---

## 3.3 Buffer-Based Tolerance Logic

### 3.3.1 Tolerance Buffer

To account for satellite georeferencing error (±5m for Sentinel-2), a **tolerance buffer** is applied before declaring violations:

```
A_buffered = ST_Buffer(A, tolerance_meters)

tolerance_meters:
  - Sentinel-2:  5.0m  (half-pixel at 10m resolution)
  - Landsat-8:   15.0m (half-pixel at 30m resolution)
  - Drone:       0.5m  (half-pixel at ~1m resolution)
  - Survey GPS:  0.1m
```

**Decision Logic:**

```
IF B ⊂ A_buffered THEN
    status = 'COMPLIANT'  -- within tolerance
ELSE IF B ⊂ A THEN
    status = 'PERFECT_COMPLIANCE'
ELSE
    encroachment_polygon = B − A_buffered  -- difference
    status = 'VIOLATION'
END IF
```

**PostGIS:**

```sql
CREATE OR REPLACE FUNCTION check_compliance_with_tolerance(
    allotment_geom GEOMETRY,
    detected_geom GEOMETRY,
    tolerance_m FLOAT DEFAULT 5.0
) RETURNS TABLE(
    status TEXT,
    encroachment_geom GEOMETRY,
    encroachment_area_sqm FLOAT
) AS $$
DECLARE
    buffered GEOMETRY;
    encroachment GEOMETRY;
    enc_area FLOAT;
BEGIN
    -- Buffer allotment by tolerance in UTM
    buffered := ST_Transform(
        ST_Buffer(ST_Transform(allotment_geom, 32644), tolerance_m),
        4326
    );
    
    IF ST_Contains(allotment_geom, detected_geom) THEN
        RETURN QUERY SELECT 'PERFECT_COMPLIANCE'::TEXT, NULL::GEOMETRY, 0.0::FLOAT;
    ELSIF ST_Contains(buffered, detected_geom) THEN
        RETURN QUERY SELECT 'WITHIN_TOLERANCE'::TEXT, NULL::GEOMETRY, 0.0::FLOAT;
    ELSE
        encroachment := ST_Difference(
            ST_Transform(detected_geom, 32644),
            ST_Transform(buffered, 32644)
        );
        enc_area := ST_Area(encroachment);
        encroachment := ST_Transform(encroachment, 4326);
        RETURN QUERY SELECT 'VIOLATION'::TEXT, encroachment, enc_area;
    END IF;
END;
$$ LANGUAGE plpgsql;
```

---

## 3.4 Encroachment Polygon Extraction

### 3.4.1 Mathematical Definition

```
E = B \ A = B − (A ∩ B)

Where:
  E = Encroachment polygon (parts of detected structure outside allotment)
  B = Detected structure footprint
  A = Allotted boundary
```

### 3.4.2 Multi-Plot Encroachment

When a structure encroaches into an adjacent plot:

```
E_ij = B_i ∩ A_j   where i ≠ j

Encroachment of plot i's structure into plot j's allotment
```

**PostGIS Query for Multi-Plot Encroachment Detection:**

```sql
-- Find all plots where detected structures cross into neighboring allotments
SELECT 
    p1.plot_id AS source_plot,
    p2.plot_id AS encroached_plot,
    ST_Area(ST_Transform(
        ST_Intersection(d.detected_geom, p2.allotment_geom),
        32644
    )) AS encroachment_area_sqm,
    ST_AsGeoJSON(
        ST_Intersection(d.detected_geom, p2.allotment_geom)
    ) AS encroachment_geojson
FROM detected_structures d
JOIN plot p1 ON d.plot_id = p1.plot_id
JOIN plot p2 ON ST_Intersects(d.detected_geom, p2.allotment_geom)
    AND p1.plot_id != p2.plot_id
WHERE ST_Area(ST_Transform(
    ST_Intersection(d.detected_geom, p2.allotment_geom), 32644
)) > 1.0;  -- More than 1 sq meter to filter noise
```

---

## 3.5 Risk Score Computation

### 3.5.1 Composite Risk Score Formula

```
Risk_Score = w₁·S_area + w₂·S_iou + w₃·S_boundary + w₄·S_temporal + w₅·S_vacancy

Where:
  S_area      = min(1, |D%| / 50)           -- Area deviation severity (0–1)
  S_iou       = 1 − IoU                     -- Lower IoU = higher risk (0–1)
  S_boundary  = min(1, max_encroach_m / 20) -- Max encroachment in meters (0–1)
  S_temporal  = trend_slope × months         -- Rate of encroachment growth (0–1)
  S_vacancy   = months_vacant / 36           -- Vacancy duration severity (0–1)

Weights (tunable):
  w₁ = 0.25  (area deviation)
  w₂ = 0.25  (IoU compliance)
  w₃ = 0.20  (boundary violation depth)
  w₄ = 0.15  (growth trend)
  w₅ = 0.15  (vacancy)

Risk_Score ∈ [0, 1]
```

### 3.5.2 Risk Classification

| Risk Score | Category | Color | Action |
|------------|----------|-------|--------|
| 0.00–0.20 | LOW | 🟢 Green | Routine monitoring |
| 0.20–0.40 | MODERATE | 🟡 Yellow | Flag for review |
| 0.40–0.60 | HIGH | 🟠 Orange | Field inspection |
| 0.60–0.80 | CRITICAL | 🔴 Red | Enforcement notice |
| 0.80–1.00 | SEVERE | ⚫ Black | Legal proceedings |

---

## 3.6 Shapely/GeoPandas Workflow

```python
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
import numpy as np

class BoundaryAnalyzer:
    """Complete boundary analysis workflow using GeoPandas/Shapely."""
    
    TOLERANCE_METERS = 5.0  # Sentinel-2 tolerance
    
    def __init__(self, allotment_gdf: gpd.GeoDataFrame, detection_gdf: gpd.GeoDataFrame):
        # Ensure UTM CRS for accurate metric calculations
        self.allotment = allotment_gdf.to_crs(epsg=32644)
        self.detection = detection_gdf.to_crs(epsg=32644)
    
    def compute_iou(self, allotment_geom, detected_geom):
        """Compute Intersection over Union."""
        if not allotment_geom.intersects(detected_geom):
            return 0.0
        intersection = allotment_geom.intersection(detected_geom)
        union = allotment_geom.union(detected_geom)
        return intersection.area / union.area if union.area > 0 else 0.0
    
    def compute_deviation(self, allotment_geom, detected_geom):
        """Compute area deviation percentage."""
        allotted_area = allotment_geom.area
        detected_area = detected_geom.area
        return ((detected_area - allotted_area) / allotted_area) * 100
    
    def extract_encroachment(self, allotment_geom, detected_geom):
        """Extract encroachment polygon with buffer tolerance."""
        buffered = allotment_geom.buffer(self.TOLERANCE_METERS)
        if buffered.contains(detected_geom):
            return None  # Within tolerance
        encroachment = detected_geom.difference(buffered)
        if encroachment.is_empty:
            return None
        return encroachment
    
    def analyze_plot(self, plot_id):
        """Full analysis for a single plot."""
        allot = self.allotment[self.allotment['plot_id'] == plot_id].geometry.iloc[0]
        detect = self.detection[self.detection['plot_id'] == plot_id].geometry.iloc[0]
        
        iou = self.compute_iou(allot, detect)
        deviation = self.compute_deviation(allot, detect)
        encroachment = self.extract_encroachment(allot, detect)
        
        risk_area = min(1, abs(deviation) / 50)
        risk_iou = 1 - iou
        risk_boundary = 0
        if encroachment and not encroachment.is_empty:
            max_dist = max(allot.exterior.distance(
                Polygon([p]).centroid
            ) for p in encroachment.exterior.coords) if hasattr(encroachment, 'exterior') else 0
            risk_boundary = min(1, max_dist / 20)
        
        risk_score = 0.30 * risk_area + 0.30 * risk_iou + 0.25 * risk_boundary + 0.15 * 0
        
        return {
            'plot_id': plot_id,
            'iou': round(iou, 4),
            'deviation_pct': round(deviation, 2),
            'encroachment_area_sqm': round(encroachment.area, 2) if encroachment else 0,
            'encroachment_geom': encroachment,
            'risk_score': round(risk_score, 4),
            'risk_category': self._classify_risk(risk_score),
            'allotted_area_sqm': round(allot.area, 2),
            'detected_area_sqm': round(detect.area, 2),
        }
    
    def _classify_risk(self, score):
        if score < 0.2: return 'LOW'
        if score < 0.4: return 'MODERATE'
        if score < 0.6: return 'HIGH'
        if score < 0.8: return 'CRITICAL'
        return 'SEVERE'
    
    def batch_analyze(self):
        """Analyze all plots and return results GeoDataFrame."""
        results = []
        common_plots = set(self.allotment['plot_id']) & set(self.detection['plot_id'])
        for plot_id in common_plots:
            results.append(self.analyze_plot(plot_id))
        return gpd.GeoDataFrame(results, geometry='encroachment_geom', crs='EPSG:32644')
```
