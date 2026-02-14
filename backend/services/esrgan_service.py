"""
ILMCS — ESRGAN Super-Resolution Service
Enhance Sentinel-2 imagery using Real-ESRGAN (PyTorch).
"""

import os
import io
import uuid
import time
import base64
import logging
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)

# ── Lazy PyTorch import (deferred to first use to avoid blocking startup) ──
torch = None
nn = None
F = None
TORCH_AVAILABLE = False
_torch_checked = False

def _ensure_torch():
    global torch, nn, F, TORCH_AVAILABLE, _torch_checked
    if _torch_checked:
        return TORCH_AVAILABLE
    _torch_checked = True
    try:
        import torch as _torch
        import torch.nn as _nn
        import torch.nn.functional as _F
        torch = _torch
        nn = _nn
        F = _F
        TORCH_AVAILABLE = True
        logger.info("PyTorch loaded successfully")
    except ImportError:
        TORCH_AVAILABLE = False
        logger.warning("PyTorch not installed — ESRGAN will use bicubic upscaling fallback")
    return TORCH_AVAILABLE

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════
# ESRGAN Model Architecture — built lazily on first use
# ══════════════════════════════════════════════════════════════════════

def _build_model_classes():
    """Build ESRGAN model classes (requires torch to be loaded)."""
    if not TORCH_AVAILABLE:
        return None, None, None

    class ResidualDenseBlock(nn.Module):
        """Residual Dense Block with 5 convolution layers."""
        def __init__(self, nf: int = 64, gc: int = 32):
            super().__init__()
            self.conv1 = nn.Conv2d(nf, gc, 3, 1, 1)
            self.conv2 = nn.Conv2d(nf + gc, gc, 3, 1, 1)
            self.conv3 = nn.Conv2d(nf + 2 * gc, gc, 3, 1, 1)
            self.conv4 = nn.Conv2d(nf + 3 * gc, gc, 3, 1, 1)
            self.conv5 = nn.Conv2d(nf + 4 * gc, nf, 3, 1, 1)
            self.lrelu = nn.LeakyReLU(0.2, inplace=True)

        def forward(self, x):
            x1 = self.lrelu(self.conv1(x))
            x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
            x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
            x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
            x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
            return x5 * 0.2 + x

    class RRDB(nn.Module):
        """Residual-in-Residual Dense Block."""
        def __init__(self, nf: int = 64):
            super().__init__()
            self.rdb1 = ResidualDenseBlock(nf)
            self.rdb2 = ResidualDenseBlock(nf)
            self.rdb3 = ResidualDenseBlock(nf)

        def forward(self, x):
            out = self.rdb1(x)
            out = self.rdb2(out)
            out = self.rdb3(out)
            return out * 0.2 + x

    class ESRGANModel(nn.Module):
        def __init__(self, in_channels=3, out_channels=3, nf=64, nb=23, scale=4):
            super().__init__()
            self.scale = scale
            self.conv_first = nn.Conv2d(in_channels, nf, 3, 1, 1)
            self.body = nn.Sequential(*[RRDB(nf) for _ in range(nb)])
            self.conv_body = nn.Conv2d(nf, nf, 3, 1, 1)
            self.upconv1 = nn.Conv2d(nf, nf, 3, 1, 1)
            self.upconv2 = nn.Conv2d(nf, nf, 3, 1, 1)
            if scale == 8:
                self.upconv3 = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_hr = nn.Conv2d(nf, nf, 3, 1, 1)
            self.conv_last = nn.Conv2d(nf, out_channels, 3, 1, 1)
            self.lrelu = nn.LeakyReLU(0.2, inplace=True)

        def forward(self, x):
            feat = self.conv_first(x)
            body = self.conv_body(self.body(feat))
            feat = feat + body
            feat = self.lrelu(self.upconv1(F.interpolate(feat, scale_factor=2, mode="nearest")))
            feat = self.lrelu(self.upconv2(F.interpolate(feat, scale_factor=2, mode="nearest")))
            if self.scale == 8:
                feat = self.lrelu(self.upconv3(F.interpolate(feat, scale_factor=2, mode="nearest")))
            return self.conv_last(self.lrelu(self.conv_hr(feat)))

    return ResidualDenseBlock, RRDB, ESRGANModel


# ══════════════════════════════════════════════════════════════════════
# Service Class
# ══════════════════════════════════════════════════════════════════════

class ESRGANService:
    """Handles image super-resolution via ESRGAN or bicubic fallback."""

    def __init__(self, model_path: Optional[str] = None, scale: int = 4):
        self.scale = scale
        self.model = None
        self.device = "cpu"
        self._initialized = False
        self._model_path = model_path

    def _lazy_init(self):
        """Load PyTorch and model on first use instead of blocking startup."""
        if self._initialized:
            return
        self._initialized = True
        if not _ensure_torch():
            return
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        _, _, ESRGANModel = _build_model_classes()
        if ESRGANModel is None:
            return
        self.model = ESRGANModel(scale=self.scale)
        if self._model_path and Path(self._model_path).exists():
            state = torch.load(self._model_path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state, strict=False)
            logger.info(f"Loaded ESRGAN weights from {self._model_path}")
        else:
            logger.info("No pretrained weights — using randomly initialized ESRGAN (demo)")
        self.model = self.model.to(self.device).eval()

    def enhance(self, image_bytes: bytes) -> Dict:
        """
        Enhance an image.
        Returns dict with original/enhanced base64, sizes, timing.
        """
        self._lazy_init()
        start = time.time()

        if not PIL_AVAILABLE:
            raise RuntimeError("Pillow is required for image processing")

        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        orig_w, orig_h = img.size

        if TORCH_AVAILABLE and self.model is not None:
            enhanced = self._esrgan_enhance(img)
        else:
            enhanced = self._bicubic_enhance(img)

        enh_w, enh_h = enhanced.size
        elapsed = int((time.time() - start) * 1000)

        # Encode to base64
        orig_b64 = self._to_base64(img)
        enh_b64 = self._to_base64(enhanced)

        return {
            "original_b64": orig_b64,
            "enhanced_b64": enh_b64,
            "original_resolution": f"{orig_w}x{orig_h}",
            "enhanced_resolution": f"{enh_w}x{enh_h}",
            "scale_factor": self.scale,
            "processing_time_ms": elapsed,
            "model": "ESRGAN" if (TORCH_AVAILABLE and self.model) else "Bicubic",
        }

    def enhance_from_url(self, url: str) -> Dict:
        """Download image from URL and enhance it."""
        import httpx
        resp = httpx.get(url, timeout=30, follow_redirects=True)
        resp.raise_for_status()
        return self.enhance(resp.content)

    def _esrgan_enhance(self, img: Image.Image) -> Image.Image:
        """Run ESRGAN model on PIL image."""
        arr = np.array(img).astype(np.float32) / 255.0
        tensor = torch.from_numpy(arr).permute(2, 0, 1).unsqueeze(0).to(self.device)

        with torch.no_grad():
            output = self.model(tensor)

        output = output.squeeze(0).permute(1, 2, 0).cpu().clamp(0, 1).numpy()
        return Image.fromarray((output * 255).astype(np.uint8))

    def _bicubic_enhance(self, img: Image.Image) -> Image.Image:
        """Bicubic upscale fallback when PyTorch is unavailable."""
        w, h = img.size
        return img.resize((w * self.scale, h * self.scale), Image.BICUBIC)

    @staticmethod
    def _to_base64(img: Image.Image) -> str:
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return base64.b64encode(buf.getvalue()).decode()


# ── Module-level singleton ─────────────────────────────────────────
_service: Optional[ESRGANService] = None

def get_esrgan_service(model_path: Optional[str] = None, scale: int = 4) -> ESRGANService:
    global _service
    if _service is None:
        _service = ESRGANService(model_path=model_path, scale=scale)
    return _service
