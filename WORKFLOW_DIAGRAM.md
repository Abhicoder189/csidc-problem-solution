# ILMCS System Workflow Diagram

![Workflow Diagram](workflow_diagram.png)

## Interactive Mermaid Diagram

```mermaid
flowchart TD
    Start([New Monitoring Request]) --> Select[Select Region & Time Period]
    
    Select --> Fetch[Fetch Satellite Imagery<br/>via Google Earth Engine]
    
    Fetch --> Cloud{Cloud Coverage<br/>> 20%?}
    Cloud -->|Yes| Fetch
    Cloud -->|No| Preprocess
    
    Preprocess[Preprocessing<br/>• Cloud masking<br/>• Radiometric correction<br/>• Orthorectification]
    
    Preprocess --> AIProcess[AI Processing Pipeline]
    
    AIProcess --> Segment[Semantic Segmentation<br/>Identify land use types]
    Segment --> Change[Change Detection<br/>Compare with baseline]
    Change --> Classify[Classify Encroachments]
    
    Classify --> GIS[GIS Analysis]
    
    GIS --> IoU[Calculate IoU<br/>Polygon Overlay]
    IoU --> Area[Compute Area Deviation]
    Area --> Risk[Generate Risk Scores]
    
    Risk --> Store[(Store in PostGIS<br/>with Spatial Indexes)]
    
    Store --> Check{Violation<br/>Detected?}
    
    Check -->|Yes| Alert[Send Alerts<br/>SMS/Email/Dashboard]
    Check -->|No| Update[Update Compliance Status]
    
    Alert --> Report[Generate Legal Report<br/>with Evidence]
    Update --> Report
    
    Report --> Dashboard[Display on<br/>Interactive Dashboard]
    
    Dashboard --> End([Monitor Continuously])
    
    End -.->|Every 5 days| Fetch

    style Start fill:#a5d6a7
    style End fill:#a5d6a7
    style Fetch fill:#90caf9
    style AIProcess fill:#ce93d8
    style GIS fill:#ffcc80
    style Alert fill:#ef5350,color:#fff
    style Report fill:#fff59d
    style Dashboard fill:#b39ddb
```

## Workflow Steps

### Phase 1: Data Acquisition
1. User selects region and time period
2. System fetches satellite imagery from Google Earth Engine
3. Validates cloud coverage before processing

### Phase 2: AI Processing
4. Preprocessing: cloud masking, normalization
5. Semantic segmentation to identify land features
6. Change detection comparing with baseline
7. Classification of potential encroachments

### Phase 3: GIS Analysis
8. Calculate Intersection over Union (IoU)
9. Compute area deviations from allotted plots
10. Generate risk scores based on violations

### Phase 4: Action & Reporting
11. Store results in PostGIS with spatial indexing
12. Trigger alerts for detected violations
13. Generate legal reports with satellite evidence
14. Display on interactive dashboard

### Continuous Monitoring
- System automatically re-runs every 5 days (Sentinel-2 revisit)
- Maintains historical baseline for trend analysis
