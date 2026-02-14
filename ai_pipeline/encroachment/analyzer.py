"""
ILMCS — Encroachment Detection & Compliance Analysis Engine
Combines AI detections with GIS boundary logic for violation assessment.
"""

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union
from typing import Optional
import logging
import json

logger = logging.getLogger(__name__)


class EncroachmentAnalyzer:
    """
    Analyzes AI-detected structures against official allotment boundaries.
    Computes IoU, area deviation, encroachment polygons, and risk scores.
    """

    # Tolerance per source resolution (meters)
    TOLERANCE = {
        'SENTINEL2': 5.0,
        'LANDSAT8': 15.0,
        'DRONE': 0.5,
        'SURVEY_GPS': 0.1,
    }

    # Risk weighting factors
    WEIGHTS = {
        'area_deviation': 0.25,
        'iou': 0.25,
        'boundary_depth': 0.20,
        'temporal_trend': 0.15,
        'vacancy': 0.15,
    }

    def __init__(self, source: str = 'SENTINEL2', computation_crs: int = 32644):
        self.tolerance_m = self.TOLERANCE.get(source, 5.0)
        self.crs = computation_crs

    def compute_iou(
        self, allotment: Polygon, detected: Polygon
    ) -> float:
        """Compute Intersection over Union between two polygons."""
        if not allotment.intersects(detected):
            return 0.0
        intersection = allotment.intersection(detected)
        union = allotment.union(detected)
        return intersection.area / union.area if union.area > 0 else 0.0

    def compute_area_deviation(
        self, allotment: Polygon, detected: Polygon
    ) -> float:
        """Compute percentage area deviation. Positive = exceeds allotment."""
        allotted = allotment.area
        if allotted == 0:
            return 0.0
        return ((detected.area - allotted) / allotted) * 100.0

    def extract_encroachment(
        self, allotment: Polygon, detected: Polygon
    ) -> Optional[Polygon]:
        """
        Extract encroachment polygon — part of detected structure
        that falls outside the buffered allotment boundary.
        """
        buffered = allotment.buffer(self.tolerance_m)
        if buffered.contains(detected):
            return None  # Within tolerance

        encroachment = detected.difference(buffered)
        if encroachment.is_empty or encroachment.area < 1.0:
            return None  # Less than 1 sqm — noise
        return encroachment

    def compute_max_encroachment_depth(
        self, allotment: Polygon, encroachment
    ) -> float:
        """Maximum perpendicular distance of encroachment beyond boundary."""
        if encroachment is None or encroachment.is_empty:
            return 0.0

        max_dist = 0.0
        boundary = allotment.exterior
        coords = []
        if hasattr(encroachment, 'exterior'):
            coords = list(encroachment.exterior.coords)
        elif hasattr(encroachment, 'geoms'):
            for geom in encroachment.geoms:
                if hasattr(geom, 'exterior'):
                    coords.extend(geom.exterior.coords)

        from shapely.geometry import Point
        for coord in coords:
            dist = boundary.distance(Point(coord))
            max_dist = max(max_dist, dist)

        return max_dist

    def compute_risk_score(
        self,
        iou: float,
        deviation_pct: float,
        max_depth_m: float,
        months_vacant: int = 0,
        trend_slope: float = 0.0,
    ) -> float:
        """
        Compute composite risk score [0, 1].
        
        Risk_Score = w₁·S_area + w₂·S_iou + w₃·S_boundary + w₄·S_temporal + w₅·S_vacancy
        """
        s_area = min(1.0, abs(deviation_pct) / 50.0)
        s_iou = 1.0 - iou
        s_boundary = min(1.0, max_depth_m / 20.0)
        s_temporal = min(1.0, abs(trend_slope) * 6)  # Normalized over 6 months
        s_vacancy = min(1.0, months_vacant / 36.0)

        risk = (
            self.WEIGHTS['area_deviation'] * s_area +
            self.WEIGHTS['iou'] * s_iou +
            self.WEIGHTS['boundary_depth'] * s_boundary +
            self.WEIGHTS['temporal_trend'] * s_temporal +
            self.WEIGHTS['vacancy'] * s_vacancy
        )
        return round(min(1.0, max(0.0, risk)), 4)

    def classify_risk(self, score: float) -> str:
        """Classify risk score into severity category."""
        if score < 0.20:
            return 'LOW'
        elif score < 0.40:
            return 'MODERATE'
        elif score < 0.60:
            return 'HIGH'
        elif score < 0.80:
            return 'CRITICAL'
        return 'SEVERE'

    def classify_violation_type(
        self,
        deviation_pct: float,
        encroachment,
        detected_class: str,
        allotment_class: str = 'industrial',
    ) -> str:
        """Determine violation type based on analysis results."""
        if encroachment is not None and not encroachment.is_empty:
            if deviation_pct > 10:
                return 'BOUNDARY_EXCEED'
            return 'ENCROACHMENT'

        if detected_class == 'VACANT' and allotment_class == 'industrial':
            return 'VACANCY'

        if detected_class != allotment_class:
            return 'LAND_USE_CHANGE'

        if deviation_pct < -30:
            return 'PARTIAL_UTILIZATION'

        return 'UNAUTHORIZED_CONSTRUCTION'

    def analyze_plot(
        self,
        allotment_geom: Polygon,
        detected_geom: Polygon,
        detected_class: str = 'BUILT_UP',
        model_confidence: float = 0.85,
        months_vacant: int = 0,
    ) -> dict:
        """
        Complete compliance analysis for a single plot.
        
        Returns violation details including IoU, deviation, encroachment,
        risk score, and classification.
        """
        iou = self.compute_iou(allotment_geom, detected_geom)
        deviation = self.compute_area_deviation(allotment_geom, detected_geom)
        encroachment = self.extract_encroachment(allotment_geom, detected_geom)
        max_depth = self.compute_max_encroachment_depth(allotment_geom, encroachment)

        risk_score = self.compute_risk_score(
            iou=iou,
            deviation_pct=deviation,
            max_depth_m=max_depth,
            months_vacant=months_vacant,
        )

        severity = self.classify_risk(risk_score)
        violation_type = self.classify_violation_type(
            deviation, encroachment, detected_class
        )

        # Compliance score (inverse of risk)
        compliance_score = max(0, (1 - risk_score) * 100)

        result = {
            'iou_score': round(iou, 4),
            'area_deviation_pct': round(deviation, 2),
            'allotted_area_sqm': round(allotment_geom.area, 2),
            'detected_area_sqm': round(detected_geom.area, 2),
            'encroachment_area_sqm': round(
                encroachment.area if encroachment else 0, 2
            ),
            'encroachment_geom': mapping(encroachment) if encroachment else None,
            'max_encroachment_depth_m': round(max_depth, 2),
            'risk_score': risk_score,
            'severity': severity,
            'violation_type': violation_type,
            'compliance_score': round(compliance_score, 1),
            'confidence': model_confidence,
            'tolerance_applied_m': self.tolerance_m,
        }

        logger.info(
            f"Plot analysis: IoU={iou:.3f} Dev={deviation:+.1f}% "
            f"Risk={risk_score:.3f} ({severity})"
        )
        return result

    def batch_analyze(
        self,
        allotments_gdf: gpd.GeoDataFrame,
        detections_gdf: gpd.GeoDataFrame,
        plot_id_col: str = 'plot_id',
    ) -> gpd.GeoDataFrame:
        """
        Analyze all plots in a region.
        Both GeoDataFrames must be in the computation CRS (UTM).
        """
        allotments = allotments_gdf.to_crs(epsg=self.crs)
        detections = detections_gdf.to_crs(epsg=self.crs)

        results = []
        common_ids = set(allotments[plot_id_col]) & set(detections[plot_id_col])

        for pid in common_ids:
            allot = allotments[allotments[plot_id_col] == pid].geometry.iloc[0]
            detect = detections[detections[plot_id_col] == pid].geometry.iloc[0]
            result = self.analyze_plot(allot, detect)
            result[plot_id_col] = pid
            results.append(result)

        # Also flag allotted plots with no detected structure (vacancy)
        vacant_ids = set(allotments[plot_id_col]) - set(detections[plot_id_col])
        for pid in vacant_ids:
            allot = allotments[allotments[plot_id_col] == pid].geometry.iloc[0]
            results.append({
                plot_id_col: pid,
                'iou_score': 0.0,
                'area_deviation_pct': -100.0,
                'allotted_area_sqm': round(allot.area, 2),
                'detected_area_sqm': 0,
                'encroachment_area_sqm': 0,
                'encroachment_geom': None,
                'max_encroachment_depth_m': 0,
                'risk_score': 0.15 * min(1, 12 / 36),  # Vacancy risk
                'severity': 'LOW',
                'violation_type': 'VACANCY',
                'compliance_score': 85.0,
                'confidence': 0.90,
                'tolerance_applied_m': self.tolerance_m,
            })

        logger.info(
            f"Batch analysis: {len(common_ids)} matched, {len(vacant_ids)} vacant, "
            f"{len(results)} total results"
        )
        return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Demo with synthetic polygons
    allotment = Polygon([
        (500, 500), (600, 500), (600, 600), (500, 600), (500, 500)
    ])
    detected = Polygon([
        (495, 498), (610, 498), (610, 605), (495, 605), (495, 498)
    ])

    analyzer = EncroachmentAnalyzer(source='SENTINEL2')
    result = analyzer.analyze_plot(allotment, detected)

    print("\n=== DEMO ANALYSIS RESULT ===")
    for k, v in result.items():
        if k != 'encroachment_geom':
            print(f"  {k}: {v}")
