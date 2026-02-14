# 🏭 ILMCS — Industrial Land Monitoring & Compliance System

## Automated Monitoring and Compliance of Industrial Land Allotments for Financial Efficiency

**Version:** 1.0.0  
**Classification:** Government Production System  
**Jurisdiction:** Chhattisgarh Industrial Development Corporation (CSIDC)  
**Coverage:** 56 Industrial Areas (36 New + 20 Old)

---

## Quick Start

```bash
# 1. Database Setup
cd database/
docker-compose up -d
psql -f schema.sql

# 2. Backend API
cd backend/
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# 3. AI Pipeline
cd ai_pipeline/
python train_segmentation.py
python run_change_detection.py

# 4. Frontend Dashboard
cd frontend/
npm install
npm run dev
```

## Project Structure

```
ILMCS/
├── docs/                        # Technical documentation
│   ├── 01_executive_summary.md
│   ├── 02_system_architecture.md
│   ├── 03_boundary_detection.md
│   ├── 04_change_detection.md
│   ├── 05_database_schema.md
│   ├── 06_dashboard_design.md
│   ├── 07_cost_optimization.md
│   ├── 08_accuracy_explainability.md
│   ├── 09_scalability_strategy.md
│   └── 10_implementation_roadmap.md
├── database/
│   ├── schema.sql
│   ├── spatial_indexes.sql
│   ├── seed_regions.sql
│   └── docker-compose.yml
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── routers/
│   ├── models/
│   ├── services/
│   └── gis_engine/
├── ai_pipeline/
│   ├── segmentation/
│   ├── change_detection/
│   ├── encroachment/
│   └── satellite_ingestion/
├── frontend/
│   ├── src/
│   └── package.json
├── config/
│   └── regions.yaml
└── deployment/
    ├── Dockerfile
    ├── docker-compose.prod.yml
    └── kubernetes/
```

## License

Government of Chhattisgarh — Internal Use Only
