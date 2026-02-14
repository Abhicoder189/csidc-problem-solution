"""
ILMCS — Change Detection Pipeline
Hybrid: NDVI screening + Siamese UNet for confirmation
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import rasterio
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


# ================================================================
# STAGE 1: Spectral Index Change Screening (Fast, CPU-only)
# ================================================================

class SpectralChangeScreener:
    """Fast NDVI/NDBI-based change screening to filter tiles for AI inference."""

    def __init__(self, ndvi_threshold: float = 0.25, ndbi_threshold: float = 0.15):
        self.ndvi_threshold = ndvi_threshold
        self.ndbi_threshold = ndbi_threshold

    def compute_ndvi(self, image: np.ndarray) -> np.ndarray:
        """NDVI from (H, W, C) array where C includes R(idx=2) and NIR(idx=3)."""
        red = image[:, :, 2].astype(np.float32)
        nir = image[:, :, 3].astype(np.float32)
        return (nir - red) / (nir + red + 1e-10)

    def compute_ndbi(self, image: np.ndarray) -> np.ndarray:
        """NDBI from (H, W, C) where SWIR(idx=4) and NIR(idx=3)."""
        nir = image[:, :, 3].astype(np.float32)
        swir = image[:, :, 4].astype(np.float32)
        return (swir - nir) / (swir + nir + 1e-10)

    def screen_change(
        self,
        image_t1: np.ndarray,
        image_t2: np.ndarray,
    ) -> dict:
        """Screen for spectral changes between two dates."""
        ndvi_t1 = self.compute_ndvi(image_t1)
        ndvi_t2 = self.compute_ndvi(image_t2)
        delta_ndvi = ndvi_t2 - ndvi_t1

        ndbi_t1 = self.compute_ndbi(image_t1)
        ndbi_t2 = self.compute_ndbi(image_t2)
        delta_ndbi = ndbi_t2 - ndbi_t1

        # Detect vegetation removal (possible new construction)
        veg_cleared = delta_ndvi < -self.ndvi_threshold
        # Detect new built-up areas
        new_buildup = delta_ndbi > self.ndbi_threshold
        # Combined change mask
        change_mask = veg_cleared | new_buildup

        change_fraction = change_mask.sum() / change_mask.size

        return {
            'has_change': change_fraction > 0.01,  # >1% of tile changed
            'change_fraction': float(change_fraction),
            'change_mask': change_mask,
            'delta_ndvi': delta_ndvi,
            'delta_ndbi': delta_ndbi,
            'veg_cleared_pixels': int(veg_cleared.sum()),
            'new_buildup_pixels': int(new_buildup.sum()),
        }


# ================================================================
# STAGE 2: Siamese UNet for Precise Change Detection
# ================================================================

class ConvBlock(nn.Module):
    """Double convolution block for UNet."""
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_ch, out_ch, 3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.conv(x)


class SiameseEncoder(nn.Module):
    """Shared encoder for bi-temporal images."""
    def __init__(self, in_channels=4):
        super().__init__()
        self.enc1 = ConvBlock(in_channels, 64)
        self.enc2 = ConvBlock(64, 128)
        self.enc3 = ConvBlock(128, 256)
        self.enc4 = ConvBlock(256, 512)
        self.pool = nn.MaxPool2d(2)

    def forward(self, x):
        e1 = self.enc1(x)
        e2 = self.enc2(self.pool(e1))
        e3 = self.enc3(self.pool(e2))
        e4 = self.enc4(self.pool(e3))
        return [e1, e2, e3, e4]


class SiameseUNet(nn.Module):
    """
    Siamese UNet for bi-temporal change detection.
    
    Takes two co-registered images (T1, T2) and outputs binary change map.
    """
    def __init__(self, in_channels=4, out_channels=1):
        super().__init__()
        self.encoder = SiameseEncoder(in_channels)

        # Decoder takes concatenated difference features
        self.up4 = nn.ConvTranspose2d(512, 256, 2, stride=2)
        self.dec4 = ConvBlock(512, 256)
        self.up3 = nn.ConvTranspose2d(256, 128, 2, stride=2)
        self.dec3 = ConvBlock(256, 128)
        self.up2 = nn.ConvTranspose2d(128, 64, 2, stride=2)
        self.dec2 = ConvBlock(128, 64)

        self.final = nn.Conv2d(64, out_channels, 1)

    def forward(self, t1: torch.Tensor, t2: torch.Tensor) -> torch.Tensor:
        """
        Args:
            t1: Image at time 1, shape (B, C, H, W)
            t2: Image at time 2, shape (B, C, H, W)
        Returns:
            Change probability map, shape (B, 1, H, W)
        """
        # Shared encoder (same weights)
        feats_t1 = self.encoder(t1)
        feats_t2 = self.encoder(t2)

        # Feature difference at each scale
        diffs = [torch.abs(f1 - f2) for f1, f2 in zip(feats_t1, feats_t2)]

        # Decoder with skip connections from differences
        x = self.up4(diffs[3])
        x = self.dec4(torch.cat([x, diffs[2]], dim=1))
        x = self.up3(x)
        x = self.dec3(torch.cat([x, diffs[1]], dim=1))
        x = self.up2(x)
        x = self.dec2(torch.cat([x, diffs[0]], dim=1))

        return torch.sigmoid(self.final(x))


# ================================================================
# STAGE 3: Change Detection Pipeline
# ================================================================

class ChangeDetectionPipeline:
    """
    Hybrid change detection pipeline.
    Stage 1: Fast spectral screening (CPU)
    Stage 2: AI-based precise detection (GPU, only on flagged tiles)
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
    ):
        self.screener = SpectralChangeScreener()
        self.device = device

        if model_path:
            self.siamese_model = SiameseUNet(in_channels=4).to(device)
            self.siamese_model.load_state_dict(
                torch.load(model_path, map_location=device)
            )
            self.siamese_model.eval()
        else:
            self.siamese_model = None

    def detect_changes(
        self,
        tile_t1: np.ndarray,
        tile_t2: np.ndarray,
        use_ai: bool = True,
    ) -> dict:
        """
        Full change detection on a tile pair.
        
        Args:
            tile_t1: Image at time 1, (H, W, C) with C ≥ 5 bands
            tile_t2: Image at time 2, (H, W, C)
            use_ai: Whether to run Siamese UNet on flagged tiles
        
        Returns:
            Dictionary with change results
        """
        # Stage 1: Fast spectral screening
        screening = self.screener.screen_change(tile_t1, tile_t2)

        if not screening['has_change']:
            return {
                'stage': 'screening',
                'has_change': False,
                'change_fraction': screening['change_fraction'],
                'change_mask': None,
                'confidence': 0.95,  # High confidence in no-change
            }

        # Stage 2: AI-based detection (only if change detected)
        if use_ai and self.siamese_model is not None:
            ai_result = self._run_siamese(tile_t1[:, :, :4], tile_t2[:, :, :4])
            combined_mask = screening['change_mask'] & (ai_result > 0.5)

            return {
                'stage': 'ai_confirmed',
                'has_change': True,
                'change_fraction': float(combined_mask.sum() / combined_mask.size),
                'change_mask': combined_mask,
                'ai_probability_map': ai_result,
                'confidence': float(ai_result[combined_mask].mean()) if combined_mask.any() else 0,
                'screening': screening,
            }

        return {
            'stage': 'screening_only',
            'has_change': True,
            'change_fraction': screening['change_fraction'],
            'change_mask': screening['change_mask'],
            'confidence': 0.65,  # Lower confidence without AI confirmation
            'screening': screening,
        }

    def _run_siamese(self, t1: np.ndarray, t2: np.ndarray) -> np.ndarray:
        """Run Siamese UNet on RGBNIR tile pair."""
        with torch.no_grad():
            x1 = torch.from_numpy(t1).permute(2, 0, 1).unsqueeze(0).float() / 10000.0
            x2 = torch.from_numpy(t2).permute(2, 0, 1).unsqueeze(0).float() / 10000.0
            x1, x2 = x1.to(self.device), x2.to(self.device)
            prob_map = self.siamese_model(x1, x2).squeeze().cpu().numpy()
        return prob_map


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("Change Detection Pipeline initialized.")
    print(f"Device: {torch.cuda.get_device_name() if torch.cuda.is_available() else 'CPU'}")
    
    # Quick model test
    model = SiameseUNet(in_channels=4)
    t1 = torch.randn(1, 4, 256, 256)
    t2 = torch.randn(1, 4, 256, 256)
    output = model(t1, t2)
    print(f"Model output shape: {output.shape}")  # (1, 1, 256, 256)
