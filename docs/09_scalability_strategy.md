# 9️⃣ Scalability Strategy

## 9.1 Multi-Region Parallel Processing

### 9.1.1 Architecture

```
                    ┌──────────────────────────┐
                    │     Job Orchestrator     │
                    │     (Celery Beat)        │
                    └─────────┬────────────────┘
                              │ Distributes jobs
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
     ┌────────────────┐ ┌────────────┐ ┌────────────────┐
     │ Worker Pool 1  │ │ Worker 2   │ │ Worker Pool N  │
     │ Regions 1–10   │ │ Reg 11–20  │ │ Regions 46–56  │
     │ (GPU-enabled)  │ │            │ │                │
     └────────────────┘ └────────────┘ └────────────────┘
              │               │               │
              ▼               ▼               ▼
     ┌──────────────────────────────────────────────┐
     │            Shared PostGIS Database            │
     │        (with connection pooling — PgBouncer)  │
     └──────────────────────────────────────────────┘
```

### 9.1.2 Parallelism Strategy

| Processing Stage | Parallelism Type | Max Concurrent |
|-----------------|------------------|----------------|
| Satellite ingestion (GEE) | Per-region parallel | 56 (all regions) |
| Cloud masking | Per-image parallel | 10 images/worker |
| NDVI screening | Per-tile parallel | 100 tiles/batch |
| AI segmentation | GPU-batched | 32 tiles/GPU |
| Compliance check | Per-plot parallel | 200 plots/worker |
| Report generation | Per-region parallel | 10 reports/worker |

### 9.1.3 Celery Configuration

```python
# celery_config.py
from celery import Celery

app = Celery('ilmcs')
app.conf.update(
    broker_url='redis://redis:6379/0',
    result_backend='redis://redis:6379/1',
    
    # Route tasks to appropriate queues
    task_routes={
        'tasks.ingest_satellite': {'queue': 'ingest'},
        'tasks.run_segmentation': {'queue': 'gpu'},
        'tasks.check_compliance': {'queue': 'gis'},
        'tasks.generate_report': {'queue': 'report'},
    },
    
    # Concurrency settings
    worker_concurrency=4,        # CPU workers
    worker_prefetch_multiplier=2,
    
    # Rate limiting
    task_annotations={
        'tasks.ingest_satellite': {'rate_limit': '10/m'},  # GEE rate limit
    },
    
    # Retry policy
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Beat schedule for periodic tasks
app.conf.beat_schedule = {
    'sentinel2-ingest': {
        'task': 'tasks.batch_ingest_all_regions',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
    'weekly-compliance': {
        'task': 'tasks.batch_compliance_check',
        'schedule': crontab(hour=6, minute=0, day_of_week=1),  # Monday 6 AM
    },
    'monthly-reports': {
        'task': 'tasks.generate_monthly_reports',
        'schedule': crontab(hour=0, minute=0, day_of_month=1),
    },
}
```

---

## 9.2 Tile-Based Image Monitoring

### 9.2.1 Tiling Strategy

```
Region boundary → split into 256×256 pixel tiles at 10m resolution

Each tile covers: 2.56km × 2.56km = 6.55 km²

For a typical industrial area (~5 km²):
  → Requires ~1-4 tiles for complete coverage

For all 56 regions:
  → Total estimated: ~200-400 tiles
  → Each tile processed independently
  → Only tiles with detected changes proceed to AI inference
```

### 9.2.2 Tile Management

```python
import mercantile
from shapely.geometry import box

def generate_tiles(region_geom, tile_size_m=2560):
    """Generate processing tiles for a region."""
    bounds = region_geom.bounds  # (minx, miny, maxx, maxy)
    
    tiles = []
    x = bounds[0]
    while x < bounds[2]:
        y = bounds[1]
        while y < bounds[3]:
            tile_box = box(x, y, x + tile_size_m/111000, y + tile_size_m/111000)
            if tile_box.intersects(region_geom):
                tiles.append({
                    'geometry': tile_box,
                    'bounds': tile_box.bounds,
                    'region_overlap': tile_box.intersection(region_geom).area / tile_box.area
                })
            y += tile_size_m / 111000
        x += tile_size_m / 111000
    
    return tiles
```

### 9.2.3 Smart Tile Filtering

```
Total Tiles per Cycle: ~350
    │
    ├── Cloud-masked tiles (skip):     ~50  (14%)
    ├── No-change tiles (skip AI):     ~250 (71%)
    │   (compared via pixel hash)
    ├── Changed tiles → AI inference:   ~50  (15%)
    │   └── Violations detected:        ~10  (3%)
    │
    Cost savings: Only 15% of tiles need GPU inference
    GPU time saved: 85% per cycle
```

---

## 9.3 Cloud-Native Horizontal Scaling

### 9.3.1 Kubernetes Architecture

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ilmcs-api
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    spec:
      containers:
      - name: ilmcs-api
        image: ilmcs/api:latest
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          periodSeconds: 10
---
# GPU worker for AI inference
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ilmcs-gpu-worker
spec:
  replicas: 1  # Scale to 2-4 during processing windows
  template:
    spec:
      containers:
      - name: gpu-worker
        image: ilmcs/gpu-worker:latest
        resources:
          limits:
            nvidia.com/gpu: 1
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
---
# Horizontal Pod Autoscaler
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ilmcs-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ilmcs-api
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 9.3.2 Scaling Dimensions

| Component | Scaling Type | Trigger | Scale Range |
|-----------|-------------|---------|-------------|
| API Server | Horizontal (pods) | CPU > 70% | 2–8 pods |
| Celery Workers | Horizontal (pods) | Queue depth > 100 | 2–16 workers |
| GPU Workers | Scheduled scaling | Processing window | 1–4 GPUs |
| PostgreSQL | Vertical + Read replicas | Connection count | 1 primary + 2 read |
| Redis | Vertical | Memory > 80% | 2–8 GB |
| MinIO/S3 | Auto (managed) | N/A | Unlimited |

---

## 9.4 Storage Optimization

### 9.4.1 Tiered Storage

```
┌─────────────────────────────────────────────────┐
│              STORAGE TIERS                       │
├─────────────────────────────────────────────────┤
│                                                  │
│  HOT (SSD — frequently accessed)                │
│  ├── Last 30 days of satellite imagery          │
│  ├── Active violation evidence                   │
│  ├── Current compliance snapshots                │
│  └── Size: ~50 GB | Cost: ₹2/GB/month          │
│                                                  │
│  WARM (HDD — periodic access)                   │
│  ├── 1–12 months satellite archive              │
│  ├── Resolved violation records                  │
│  ├── Historical reports                          │
│  └── Size: ~500 GB | Cost: ₹0.5/GB/month       │
│                                                  │
│  COLD (Archive — rarely accessed)               │
│  ├── 1–5 year imagery archive                   │
│  ├── Audit logs                                  │
│  ├── Legal case archives                         │
│  └── Size: ~2 TB | Cost: ₹0.1/GB/month         │
│                                                  │
│  Total monthly storage cost: ~₹800              │
└─────────────────────────────────────────────────┘
```

### 9.4.2 Data Lifecycle Policy

```python
LIFECYCLE_RULES = {
    'satellite_imagery': {
        'hot_days': 30,
        'warm_days': 365,
        'cold_days': 1825,   # 5 years
        'delete_after_days': None,  # Never delete (government data)
        'compression': 'COG',  # Cloud Optimized GeoTIFF
    },
    'violation_evidence': {
        'hot_days': 90,
        'warm_days': 730,    # 2 years
        'cold_days': 3650,   # 10 years
        'delete_after_days': None,
    },
    'analysis_artifacts': {
        'hot_days': 7,
        'warm_days': 30,
        'cold_days': 90,
        'delete_after_days': 365,  # Regenerable
    },
    'audit_logs': {
        'hot_days': 90,
        'warm_days': 365,
        'cold_days': 3650,
        'delete_after_days': None,
    },
}
```

### 9.4.3 Image Compression

| Format | Use Case | Compression | Access Pattern |
|--------|----------|-------------|----------------|
| Cloud Optimized GeoTIFF (COG) | Satellite imagery | LZW, 60% reduction | Range requests, tiling |
| JPEG2000 | Archive imagery | 80% reduction | Sequential read |
| PNG | Evidence overlays | Lossless | Web display |
| WebP | Dashboard thumbnails | 90% reduction | Rapid loading |

---

## 9.5 Future Scaling: 200+ Industrial Regions

```
Current: 56 regions → System designed for 10× headroom (560 regions)

Scaling approach:
├── Database: Partitioning by region_id already in place
├── Processing: Add worker nodes linearly (1 worker per 10 regions)
├── Storage: S3/MinIO scales horizontally
├── GPU: Spot instances for burst processing
├── API: Auto-scaling behind load balancer
└── Monitoring: Prometheus + Grafana with per-region dashboards

Estimated cost at 200 regions: ₹25 Lakh/year (2.6× current)
Linear cost scaling validated by architecture design.
```
