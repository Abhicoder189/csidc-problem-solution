# ILMCS System Architecture Diagram

```mermaid
graph TB
    subgraph "Data Sources"
        S2[Sentinel-2 Satellite]
        L8[Landsat-8/9]
        PDF[Allotment Maps PDF/CAD]
        REV[Revenue Records]
    end

    subgraph "Ingestion Layer"
        GEE[Google Earth Engine]
        VEC[Vectorizer & Georeferencing]
        IMP[Data Importer]
    end

    subgraph "Processing & AI Layer"
        PRE[Preprocessing<br/>Cloud Mask, Normalization]
        SEG[Semantic Segmentation<br/>DeepLabV3+]
        CHG[Change Detection<br/>Siamese Network]
        ENC[Encroachment Classifier]
    end

    subgraph "GIS Engine"
        PG[(PostGIS Database)]
        SPA[Spatial Analysis<br/>IoU, Overlay, Buffer]
    end

    subgraph "Backend API"
        API[FastAPI REST API]
        AUTH[JWT Auth & Rate Limiting]
    end

    subgraph "Frontend"
        MAP[Interactive Map<br/>MapLibre GL]
        DASH[Analytics Dashboard]
        REP[Report Generator]
    end

    subgraph "Storage"
        S3[Object Storage<br/>Images & Reports]
        REDIS[Redis Cache<br/>Tiles & Sessions]
    end

    S2 --> GEE
    L8 --> GEE
    PDF --> VEC
    REV --> IMP
    
    GEE --> PRE
    VEC --> PG
    IMP --> PG
    
    PRE --> SEG
    PRE --> CHG
    SEG --> ENC
    CHG --> ENC
    
    ENC --> SPA
    SPA --> PG
    PG --> API
    
    API --> AUTH
    AUTH --> MAP
    AUTH --> DASH
    AUTH --> REP
    
    API --> S3
    API --> REDIS
    S3 --> MAP
    REDIS --> MAP

    style S2 fill:#e3f2fd
    style L8 fill:#e3f2fd
    style PDF fill:#fff3e0
    style REV fill:#fff3e0
    style PG fill:#c8e6c9
    style API fill:#f8bbd0
    style MAP fill:#d1c4e9
    style DASH fill:#d1c4e9
    style REP fill:#d1c4e9
```

## System Layers

### 1. **Data Sources**
- Satellite imagery (Sentinel-2, Landsat)
- Allotment maps and administrative records

### 2. **Ingestion & Processing**
- Google Earth Engine for satellite data
- AI/ML models for segmentation and change detection
- GIS engine for spatial analysis

### 3. **API & Storage**
- FastAPI backend with JWT authentication
- PostGIS for spatial database
- Redis & Object Storage for caching

### 4. **Frontend Applications**
- Interactive maps with violation overlays
- Analytics dashboards
- PDF report generation
