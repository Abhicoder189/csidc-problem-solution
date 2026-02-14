"""
ILMCS — Satellite Imagery Ingestion Pipeline
Automated ingestion from Google Earth Engine (Sentinel-2, Landsat-8/9, Sentinel-1)
"""

import ee
import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize Earth Engine
try:
    ee.Initialize(opt_url='https://earthengine-highvolume.googleapis.com')
except Exception:
    ee.Authenticate()
    ee.Initialize()


class SatelliteIngestionPipeline:
    """Ingests satellite imagery for all industrial regions via Google Earth Engine."""

    SOURCES = {
        'SENTINEL2': {
            'collection': 'COPERNICUS/S2_SR_HARMONIZED',
            'cloud_field': 'CLOUDY_PIXEL_PERCENTAGE',
            'max_cloud': 20,
            'resolution': 10,
            'bands_rgb': ['B4', 'B3', 'B2'],
            'bands_nir': ['B8'],
            'bands_swir': ['B11', 'B12'],
        },
        'LANDSAT8': {
            'collection': 'LANDSAT/LC08/C02/T1_L2',
            'cloud_field': 'CLOUD_COVER',
            'max_cloud': 20,
            'resolution': 30,
            'bands_rgb': ['SR_B4', 'SR_B3', 'SR_B2'],
            'bands_nir': ['SR_B5'],
            'bands_swir': ['SR_B6', 'SR_B7'],
        },
        'SENTINEL1': {
            'collection': 'COPERNICUS/S1_GRD',
            'resolution': 10,
            'bands': ['VV', 'VH'],
        },
    }

    def __init__(self, output_dir: str = './data/satellite'):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def mask_clouds_sentinel2(self, image: ee.Image) -> ee.Image:
        """Cloud masking using Scene Classification Layer (SCL)."""
        scl = image.select('SCL')
        clear_sky = (scl.neq(3)   # Cloud shadow
                     .And(scl.neq(7))   # Unclassified
                     .And(scl.neq(8))   # Cloud medium prob
                     .And(scl.neq(9))   # Cloud high prob
                     .And(scl.neq(10))) # Cirrus
        return image.updateMask(clear_sky).divide(10000)

    def mask_clouds_landsat(self, image: ee.Image) -> ee.Image:
        """Cloud masking using QA_PIXEL bitmask for Landsat."""
        qa = image.select('QA_PIXEL')
        cloud = qa.bitwiseAnd(1 << 3).eq(0)
        shadow = qa.bitwiseAnd(1 << 4).eq(0)
        return image.updateMask(cloud.And(shadow))

    def get_region_geometry(self, boundary_geojson: dict) -> ee.Geometry:
        """Convert GeoJSON boundary to Earth Engine Geometry."""
        return ee.Geometry(boundary_geojson)

    def fetch_sentinel2(
        self,
        region_geom: ee.Geometry,
        start_date: str,
        end_date: str,
        region_code: str,
    ) -> Optional[str]:
        """Fetch cloud-free Sentinel-2 composite for an industrial region."""
        logger.info(f"Fetching Sentinel-2 for {region_code}: {start_date} to {end_date}")

        collection = (
            ee.ImageCollection(self.SOURCES['SENTINEL2']['collection'])
            .filterBounds(region_geom)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
            .map(self.mask_clouds_sentinel2)
        )

        count = collection.size().getInfo()
        if count == 0:
            logger.warning(f"No cloud-free Sentinel-2 images for {region_code}")
            return None

        composite = collection.median().clip(region_geom)
        bands = ['B2', 'B3', 'B4', 'B8', 'B11', 'B12']
        composite = composite.select(bands)

        output_path = (
            self.output_dir / region_code /
            f"S2_{region_code}_{start_date}_{end_date}.tif"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        task = ee.batch.Export.image.toDrive(
            image=composite,
            description=f"S2_{region_code}",
            folder='ILMCS_Satellite',
            fileNamePrefix=f"S2_{region_code}_{start_date}",
            region=region_geom,
            scale=10,
            crs='EPSG:32644',
            maxPixels=1e9,
        )
        task.start()
        logger.info(f"Export task started: {task.id}")
        return task.id

    def compute_ndvi(self, image: ee.Image, source: str = 'SENTINEL2') -> ee.Image:
        """Compute NDVI from satellite image."""
        if source == 'SENTINEL2':
            nir = image.select('B8')
            red = image.select('B4')
        elif source == 'LANDSAT8':
            nir = image.select('SR_B5')
            red = image.select('SR_B4')
        else:
            raise ValueError(f"Unsupported source: {source}")

        ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
        return ndvi

    def compute_ndbi(self, image: ee.Image) -> ee.Image:
        """Compute Normalized Difference Built-up Index."""
        swir = image.select('B11')
        nir = image.select('B8')
        ndbi = swir.subtract(nir).divide(swir.add(nir)).rename('NDBI')
        return ndbi

    def compute_all_indices(self, image: ee.Image) -> ee.Image:
        """Compute all spectral indices for industrial monitoring."""
        ndvi = self.compute_ndvi(image)
        ndbi = self.compute_ndbi(image)

        b2, b3, b4, b8, b11 = (
            image.select('B2'), image.select('B3'),
            image.select('B4'), image.select('B8'), image.select('B11')
        )

        bsi = ((b11.add(b4)).subtract(b8.add(b2))).divide(
            (b11.add(b4)).add(b8.add(b2))
        ).rename('BSI')

        ndwi = b3.subtract(b8).divide(b3.add(b8)).rename('NDWI')

        return image.addBands([ndvi, ndbi, bsi, ndwi])

    def batch_ingest_all_regions(
        self,
        regions: list[dict],
        start_date: str,
        end_date: str,
    ) -> dict:
        """Ingest satellite imagery for all regions in batch."""
        results = {}
        for region in regions:
            try:
                geom = self.get_region_geometry(region['boundary_geojson'])
                task_id = self.fetch_sentinel2(
                    geom, start_date, end_date, region['code']
                )
                results[region['code']] = {
                    'status': 'submitted' if task_id else 'no_data',
                    'task_id': task_id,
                }
            except Exception as e:
                logger.error(f"Failed for {region['code']}: {e}")
                results[region['code']] = {'status': 'error', 'error': str(e)}
        return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    pipeline = SatelliteIngestionPipeline()
    print("Satellite Ingestion Pipeline initialized.")
    print("Use batch_ingest_all_regions() to start processing.")
