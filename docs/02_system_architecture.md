# 2️⃣ Full System Architecture

## Layer-by-Layer Technical Design

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ILMCS SYSTEM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ Sentinel-2  │  │ Landsat-8/9 │  │ Sentinel-1   │  │ Allotment Maps   │ │
│  │ (10m, 5d)   │  │ (30m, 16d)  │  │ SAR (rain)   │  │ (SHP/GeoJSON/PDF)│ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘ │
│         │                │                │                     │           │
│  ═══════╪════════════════╪════════════════╪═════════════════════╪═══════    │
│         ▼                ▼                ▼                     ▼           │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    1. DATA INGESTION LAYER                          │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ GEE Python   │ │ STAC API     │ │ CAD/PDF    │ │ Shapefile   │ │   │
│  │  │ Client       │ │ Catalog      │ │ Vectorizer │ │ Importer    │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ │   │
│  └─────────┼────────────────┼───────────────┼───────────────┼─────────┘   │
│            ▼                ▼               ▼               ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    2. PROCESSING LAYER                              │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ Cloud Mask   │ │ Ortho-       │ │ Radiometric│ │ Tile         │ │   │
│  │  │ (SCL/QA)     │ │ rectify      │ │ Normalize  │ │ Generator   │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ │   │
│  └─────────┼────────────────┼───────────────┼───────────────┼─────────┘   │
│            ▼                ▼               ▼               ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    3. AI / ML LAYER                                  │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ Semantic Seg │ │ Change Det.  │ │ Encroach.  │ │ Vacancy     │ │   │
│  │  │ DeepLabV3+   │ │ Siamese Net  │ │ Classifier │ │ Detector    │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ │   │
│  └─────────┼────────────────┼───────────────┼───────────────┼─────────┘   │
│            ▼                ▼               ▼               ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    4. GIS ENGINE (PostGIS)                           │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ Polygon      │ │ IoU Compute  │ │ Spatial    │ │ Buffer &    │ │   │
│  │  │ Overlay      │ │ Engine       │ │ Index      │ │ Tolerance   │ │   │
│  │  └──────┬───────┘ └──────┬───────┘ └─────┬──────┘ └──────┬──────┘ │   │
│  └─────────┼────────────────┼───────────────┼───────────────┼─────────┘   │
│            ▼                ▼               ▼               ▼             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    5. BACKEND API (FastAPI)                          │   │
│  │  /api/v1/regions  /api/v1/plots  /api/v1/violations  /api/v1/reports│   │
│  └────────────────────────────┬────────────────────────────────────────┘   │
│                               ▼                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    6. FRONTEND (React + Leaflet/Mapbox)             │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ Region Map   │ │ Violation    │ │ Time       │ │ PDF Report  │ │   │
│  │  │ Heatmap      │ │ Overlay      │ │ Slider     │ │ Generator   │ │   │
│  │  └──────────────┘ └──────────────┘ └────────────┘ └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    7. REPORTING & ALERT SYSTEM                       │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌────────────┐ ┌─────────────┐ │   │
│  │  │ SMS/Email    │ │ Legal PDF    │ │ Audit Log  │ │ Escalation  │ │   │
│  │  │ Alerts       │ │ Generator    │ │ Trail      │ │ Engine      │ │   │
│  │  └──────────────┘ └──────────────┘ └────────────┘ └─────────────┘ │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2.1 Data Ingestion Layer

### 2.1.1 Satellite Imagery Sources

| Source | Resolution | Revisit | Bands | Use Case |
|--------|-----------|---------|-------|----------|
| Sentinel-2 L2A | 10m (RGBNIR), 20m (SWIR) | 5 days | 13 | Primary optical monitoring |
| Landsat-8/9 OLI | 30m | 16 days | 11 | Long-term baseline & NDVI |
| Sentinel-1 GRD | 10m SAR | 6 days | VV/VH | All-weather, monsoon monitoring |
| Planet (optional) | 3m | Daily | 4 | High-res verification (paid) |

### 2.1.2 GEE Integration Pipeline

```python
# Automated ingestion via Google Earth Engine
import ee
ee.Initialize()

def get_sentinel2_composite(region_geometry, start_date, end_date):
    """Fetch cloud-free Sentinel-2 composite for an industrial region."""
    collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
        .filterBounds(region_geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
        .map(mask_clouds_sentinel2)
        .median())
    return collection

def mask_clouds_sentinel2(image):
    """Use Scene Classification Layer (SCL) for cloud masking."""
    scl = image.select('SCL')
    clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return image.updateMask(clear)
```

### 2.1.3 Allotment Map Digitization Pipeline

```
Input Formats Supported:
├── Shapefile (.shp + .dbf + .prj + .shx)    → Direct PostGIS import via ogr2ogr
├── GeoJSON (.geojson)                        → Direct PostGIS import
├── CAD Drawing (.dwg / .dxf)                 → GDAL/OGR conversion → PostGIS
├── PDF Allotment Map                         → Georeferencing → Vectorization → PostGIS
└── Scanned Image + Control Points           → QGIS georeferencer → Digitize → PostGIS
```

**PDF Vectorization Pipeline:**
1. Extract raster layer from PDF using `pdf2image`
2. Georeference using known control points (road intersections, survey markers)
3. Apply affine transformation to map pixel coordinates → geographic coordinates
4. Run edge detection (Canny) to extract boundary lines
5. Vectorize using `rasterio.features.shapes()`
6. Clean topology using `shapely.ops.unary_union`
7. Import polygons to PostGIS with SRID 4326

---

## 2.2 Processing Layer

### 2.2.1 Cloud Masking

| Satellite | Method | Implementation |
|-----------|--------|----------------|
| Sentinel-2 | Scene Classification Layer (SCL Band) | Filter classes 3,8,9,10,11 |
| Landsat-8/9 | QA_PIXEL bitmask | Bits 3,4 for cloud & shadow |
| Sentinel-1 | N/A (SAR penetrates clouds) | No masking needed |

### 2.2.2 Orthorectification

Sentinel-2 L2A products are **pre-orthorectified** using Copernicus DEM at 90m. For sub-pixel accuracy:
- Apply co-registration using AROSICS (Automated and Robust Open-Source Image Co-Registration Software)
- Target RMSE < 0.5 pixel (5m for Sentinel-2)

### 2.2.3 Image Normalization

```python
def normalize_sentinel2(image_array):
    """Radiometric normalization to [0,1] surface reflectance."""
    # Sentinel-2 L2A values are already BOA reflectance × 10000
    normalized = image_array.astype(np.float32) / 10000.0
    normalized = np.clip(normalized, 0, 1)
    return normalized

def histogram_match(source, reference):
    """Match source image histogram to reference for temporal consistency."""
    from skimage.exposure import match_histograms
    return match_histograms(source, reference, channel_axis=-1)
```

---

## 2.3 AI / Machine Learning Layer

### 2.3.1 Model Architecture Selection

| Task | Model | Input | Output | Accuracy Target |
|------|-------|-------|--------|-----------------|
| Land-use segmentation | DeepLabV3+ (ResNet-101) | 256×256×4 (RGBNIR) | 256×256×C (classes) | mIoU > 0.82 |
| Change detection | Siamese UNet | 256×256×4 (T1+T2) | 256×256×1 (binary) | F1 > 0.85 |
| Encroachment classification | Random Forest + CNN | Plot polygon + imagery | Encroachment probability | Precision > 0.90 |
| Vacancy detection | NDVI threshold + CNN | Plot polygon + NDVI | Vacant/Active | Accuracy > 0.88 |

### 2.3.2 Land-Use Classification Classes

```
Class ID | Class Name              | Description
---------|-------------------------|----------------------------------
0        | Background              | Outside industrial area
1        | Built-up / Construction | Structures, buildings, sheds
2        | Paved / Road            | Roads, parking, concrete surfaces
3        | Vacant Land             | Empty plots, bare soil
4        | Vegetation              | Trees, grass, agricultural
5        | Water Body              | Ponds, drainage
6        | Industrial Active       | Operating facilities with activity
7        | Under Construction      | Partially constructed
```

### 2.3.3 Training Data Strategy

- **Source:** Manual annotation on high-resolution imagery (Google Earth Pro / Planet)
- **Volume:** 5,000 annotated 256×256 tiles across 10 representative industrial areas
- **Augmentation:** Rotation, flip, random crop, color jitter, Gaussian noise
- **Validation:** 70/15/15 train/val/test split, stratified by region

---

## 2.4 GIS Engine (PostGIS)

### 2.4.1 Core Capabilities

| Capability | PostGIS Function | Usage |
|------------|-----------------|-------|
| Polygon intersection | `ST_Intersection(A, B)` | Compute overlap between allotment and detected building |
| Area calculation | `ST_Area(geom::geography)` | Square meters of any polygon |
| IoU computation | Custom function | Intersection area / Union area |
| Buffer tolerance | `ST_Buffer(geom, tolerance)` | 2m tolerance for boundary matching |
| Contains check | `ST_Contains(allotment, building)` | Is building fully within plot? |
| Distance | `ST_Distance(A::geography, B::geography)` | Meters between encroachment and boundary |
| Spatial index | GiST index on geometry columns | Sub-second spatial queries |

### 2.4.2 Spatial Reference System

- **Storage SRID:** EPSG:4326 (WGS84 geographic)
- **Computation SRID:** EPSG:32644 (UTM Zone 44N — covers Chhattisgarh)
- **All area/distance calculations** transform to UTM for metric accuracy

---

## 2.5 Backend (FastAPI)

### 2.5.1 API Design

```
/api/v1/
├── /regions                    GET, POST — CRUD for industrial regions
│   └── /{region_id}/plots      GET — All plots in a region
├── /plots
│   ├── /{plot_id}              GET — Plot details + compliance
│   ├── /{plot_id}/boundary     GET, PUT — Allotment boundary
│   ├── /{plot_id}/violations   GET — Violation history
│   └── /{plot_id}/snapshots    GET — Satellite snapshots
├── /violations
│   ├── /                       GET — Filterable violation list
│   └── /{violation_id}         GET, PATCH — Details + status update
├── /analysis
│   ├── /trigger                POST — Trigger analysis for a region
│   ├── /status/{job_id}        GET — Job progress
│   └── /results/{job_id}       GET — Analysis results
├── /reports
│   ├── /compliance/{region_id} GET — Generate compliance report
│   └── /pdf/{report_id}       GET — Download PDF
├── /dashboard
│   ├── /overview               GET — System-wide stats
│   ├── /heatmap                GET — GeoJSON heatmap data
│   └── /timeline/{region_id}  GET — Temporal analysis
└── /auth
    ├── /login                  POST — JWT login
    └── /refresh                POST — Token refresh
```

### 2.5.2 Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| API Framework | FastAPI (Python 3.11) | Async, auto-docs, type-safe |
| ORM | SQLAlchemy + GeoAlchemy2 | PostGIS integration |
| Task Queue | Celery + Redis | Async satellite processing |
| Auth | JWT + OAuth2 | Government SSO compatible |
| PDF Generation | WeasyPrint / ReportLab | Legal-grade PDF reports |
| Storage | MinIO / S3-compatible | GeoTIFF and artifact storage |

---

## 2.6 Frontend (React + Leaflet)

### 2.6.1 Core Components

| Component | Technology | Function |
|-----------|-----------|----------|
| Interactive Map | React-Leaflet + Mapbox GL | Pannable/zoomable industrial area maps |
| Satellite Overlay | Leaflet.TileLayer | WMS/WMTS satellite tiles |
| Polygon Renderer | Leaflet.GeoJSON | Plot boundaries with color-coded compliance |
| Heatmap Layer | Leaflet.heat | Violation density heatmap |
| Time Slider | Custom React slider | Compare satellite imagery over time |
| Dashboard Charts | Recharts / Apache ECharts | Compliance stats visualization |
| PDF Viewer | react-pdf | In-browser report viewing |

---

## 2.7 Reporting & Alert System

### 2.7.1 Alert Escalation Matrix

```
Severity  │ Trigger                          │ Notification          │ SLA
──────────┼──────────────────────────────────┼───────────────────────┼──────
CRITICAL  │ >20% area encroachment           │ SMS + Email + Dashboard│ 4 hrs
HIGH      │ 10–20% area deviation            │ Email + Dashboard      │ 24 hrs
MEDIUM    │ 5–10% deviation or vacancy >1yr  │ Dashboard + Weekly     │ 72 hrs
LOW       │ <5% deviation (within tolerance) │ Monthly report         │ 30 days
INFO      │ No change detected               │ Quarterly summary      │ —
```

### 2.7.2 Legal PDF Report Structure

```
COMPLIANCE VIOLATION REPORT
├── Header: Report ID, Date, Region, Plot Number
├── Section 1: Allotment Details (Owner, Area, Date, Lease Terms)
├── Section 2: Satellite Evidence
│   ├── Allotment boundary overlay on satellite image
│   ├── Detected building footprint overlay
│   └── Encroachment polygon highlighted in red
├── Section 3: Quantitative Analysis
│   ├── Allotted area vs detected area
│   ├── IoU score
│   ├── Encroachment area (sq.m)
│   └── Deviation percentage
├── Section 4: Temporal Evidence (multi-date comparison)
├── Section 5: Risk Score & Classification
├── Section 6: Recommended Action
└── Footer: Digital signature, timestamp, system version
```
