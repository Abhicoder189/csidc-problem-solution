# ILMCS Regions Fix - Summary

## Problem Identified
The regions functionality was not working because:

1. **Routers not integrated**: The database-backed routers in `backend/routers/` were created but never included in the FastAPI app
2. **Schema mismatch**: The database schema (`schema.sql`) didn't match the SQLAlchemy ORM models in `models/database.py`
3. **Conflicting endpoints**: The old mock-data endpoints in `main.py` conflicted with the new database-backed router paths

## Changes Made

### 1. Integrated Database-Backed Routers (`backend/main.py`)
Added router imports and included them in the FastAPI app:
- `regions.router` → `/api/regions`
- `plots.router` → `/api/plots`
- `violations.router` → `/api/violations`
- `dashboard.router` → `/api/dashboard`
- `analysis.router` → `/api/analysis`
- `reports.router` → `/api/reports`

### 2. Renamed Legacy Endpoints
Old mock-data endpoints renamed to avoid conflicts:
- `/api/regions` → `/api/legacy/regions`
- `/api/plots` → `/api/legacy/plots`
- `/api/dashboard` → `/api/legacy/dashboard`
- `/api/violations` → `/api/legacy/violations`

### 3. Fixed Database Schema
Created `database/schema_clean.sql` that matches the SQLAlchemy ORM models:

**Table Name Changes:**
- `industrial_regions` → `industrial_region` (singular)
- `plots` → `plot` (singular)
- `violations` → `violation` (singular)
- `allotment_boundaries` → `allotment_boundary` (singular)
- `satellite_snapshots` → `satellite_snapshot` (singular)

**Column Name Changes:**
- `id` → specific IDs (`region_id`, `plot_id`, `violation_id`, etc.)
- `category` → `type` (for region type: NEW/OLD)
- `center_point` → `centroid_lat` + `centroid_lon`
- `boundary` → `boundary_geom` or `geom`

## Next Steps to Get Regions Working

### 1. Set Up the Database

#### Option A: Using Docker (Recommended)
```powershell
cd database
docker-compose up -d
```

This will:
- Start PostgreSQL with PostGIS extension
- Create the database schema
- Seed the 56 industrial regions

#### Option B: Manual PostgreSQL Setup
```powershell
# Create database
psql -U postgres -c "CREATE DATABASE ilmcs;"

# Run the clean schema
psql -U postgres -d ilmcs -f database/schema_clean.sql

# Seed regions
psql -U postgres -d ilmcs -f database/seed_regions.sql

# Add spatial indexes
psql -U postgres -d ilmcs -f database/spatial_indexes.sql
```

### 2. Set Environment Variables
Create a `.env` file in the `backend/` directory:
```
DATABASE_URL=postgresql://ilmcs_admin:ilmcs_secure_2026@localhost:5432/ilmcs
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
ESRGAN_MODEL_PATH=./models/esrgan_weights.pth
ESRGAN_SCALE_FACTOR=4
UPLOAD_DIR=./uploads
```

### 3. Install Python Dependencies
```powershell
cd backend
pip install -r requirements.txt
```

### 4. Start the Backend
```powershell
cd backend
python main.py
```

Or using uvicorn directly:
```powershell
uvicorn main:app --reload --port 8000
```

### 5. Test the Regions Endpoint
```powershell
# List all regions
curl http://localhost:8000/api/regions/

# Get a specific region
curl http://localhost:8000/api/regions/{region-id}

# Get region summary stats
curl http://localhost:8000/api/regions/summary/stats
```

## Available Endpoints

### Regions (Database-Backed)
- `GET /api/regions/` - List all regions with filters
- `GET /api/regions/{region_id}` - Get region details with boundary
- `GET /api/regions/{region_id}/plots` - List plots in a region
- `GET /api/regions/summary/stats` - Summary statistics

### Plots
- `GET /api/plots/{plot_id}` - Get plot details
- `GET /api/plots/{plot_id}/boundary` - Get plot boundary GeoJSON
- `GET /api/plots/{plot_id}/violations` - List violations for plot

### Violations
- `GET /api/violations/` - List violations with filters
- `GET /api/violations/{violation_id}` - Get violation details
- `PATCH /api/violations/{violation_id}` - Update violation status

### Dashboard
- `GET /api/dashboard/overview` - System-wide statistics
- `GET /api/dashboard/region-summary` - Region-level aggregations

### Legacy Endpoints (Mock Data - for backward compatibility)
- `GET /api/legacy/regions` - Old mock regions data
- `GET /api/legacy/plots` - Old mock plots data
- `GET /api/legacy/dashboard` - Old mock dashboard data

## Database Schema Overview

### industrial_region
Stores the 56 industrial areas (36 NEW + 20 OLD)
- Primary key: `region_id` (UUID)
- Unique: `code` (e.g., 'SILTARA_P1')
- Geometry: `boundary_geom` (MultiPolygon)
- Type: 'NEW' or 'OLD'

### plot
Individual allotments within regions
- Primary key: `plot_id` (UUID)
- Foreign key: `region_id`
- Unique: `(region_id, plot_number)`
- Status: 'ALLOTTED', 'VACANT', etc.

### allotment_boundary
Plot boundaries with versioning
- Primary key: `boundary_id` (UUID)
- Foreign key: `plot_id`
- Geometry: `geom` (Polygon)
- Version control: `version`, `is_active`

### violation
Detected compliance violations
- Primary key: `violation_id` (UUID)
- Foreign keys: `plot_id`, `snapshot_id`
- Types: 'ENCROACHMENT', 'LAND_USE_CHANGE', etc.
- Severity: 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'

## Troubleshooting

### "Table does not exist" error
Make sure you've run the clean schema:
```powershell
psql -U ilmcs_admin -d ilmcs -f database/schema_clean.sql
```

### "No regions found"
Ensure seed data is loaded:
```powershell
psql -U ilmcs_admin -d ilmcs -f database/seed_regions.sql
```

### "Cannot import sqlalchemy" error
Install requirements:
```powershell
pip install -r backend/requirements.txt
```

### Database connection refused
Check if PostgreSQL is running:
```powershell
docker ps  # If using Docker
# OR
Get-Service -Name postgresql*  # If using Windows service
```

## Files Changed
1. `backend/main.py` - Added router imports and includes, renamed legacy endpoints
2. `database/schema_clean.sql` - New schema matching ORM models (created)
3. This README documenting the fixes

## Files to Review/Update
- `database/schema.sql` - Old schema (can be replaced with schema_clean.sql)
- `frontend/src/lib/api.js` - May need to update API endpoints if using new paths
