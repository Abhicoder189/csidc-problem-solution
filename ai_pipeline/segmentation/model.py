"""
ILMCS — Semantic Segmentation Model
DeepLabV3+ with ResNet-101 backbone for land-use classification
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision.models.segmentation import deeplabv3_resnet101
from torch.utils.data import Dataset, DataLoader
import numpy as np
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Land-use classification classes for industrial monitoring
CLASSES = {
    0: 'Background',
    1: 'Built-up / Construction',
    2: 'Paved / Road',
    3: 'Vacant Land',
    4: 'Vegetation',
    5: 'Water Body',
    6: 'Industrial Active',
    7: 'Under Construction',
}
NUM_CLASSES = len(CLASSES)


class IndustrialLandDataset(Dataset):
    """Dataset for industrial land-use segmentation."""

    def __init__(
        self,
        image_dir: str,
        mask_dir: str,
        transform=None,
        tile_size: int = 256,
    ):
        self.image_dir = Path(image_dir)
        self.mask_dir = Path(mask_dir)
        self.transform = transform
        self.tile_size = tile_size
        self.images = sorted(self.image_dir.glob('*.npy'))

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_path = self.images[idx]
        mask_path = self.mask_dir / img_path.name

        image = np.load(img_path).astype(np.float32)  # (H, W, 4) RGBNIR
        mask = np.load(mask_path).astype(np.int64)     # (H, W) class labels

        # Normalize to [0, 1]
        image = image / 10000.0
        image = np.clip(image, 0, 1)

        if self.transform:
            augmented = self.transform(image=image, mask=mask)
            image = augmented['image']
            mask = augmented['mask']

        # Convert to (C, H, W) for PyTorch
        image = torch.from_numpy(image).permute(2, 0, 1).float()
        mask = torch.from_numpy(mask).long()

        return image, mask


class DeepLabV3Segmentor(nn.Module):
    """DeepLabV3+ adapted for 4-channel input (RGBNIR) and N land-use classes."""

    def __init__(self, num_classes: int = NUM_CLASSES, in_channels: int = 4):
        super().__init__()
        self.model = deeplabv3_resnet101(
            weights=None,
            num_classes=num_classes,
        )
        # Modify first conv layer to accept 4 channels (RGBNIR)
        old_conv = self.model.backbone.conv1
        self.model.backbone.conv1 = nn.Conv2d(
            in_channels, 64,
            kernel_size=7, stride=2, padding=3, bias=False
        )
        # Copy RGB weights and initialize NIR channel
        with torch.no_grad():
            self.model.backbone.conv1.weight[:, :3] = old_conv.weight
            self.model.backbone.conv1.weight[:, 3] = old_conv.weight[:, 0]

    def forward(self, x):
        return self.model(x)['out']


def train_segmentation_model(
    train_dir: str,
    val_dir: str,
    output_dir: str = './models',
    epochs: int = 50,
    batch_size: int = 16,
    lr: float = 1e-4,
    device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
):
    """Train the DeepLabV3+ segmentation model."""
    logger.info(f"Training on device: {device}")

    model = DeepLabV3Segmentor(num_classes=NUM_CLASSES).to(device)

    train_dataset = IndustrialLandDataset(
        image_dir=f'{train_dir}/images',
        mask_dir=f'{train_dir}/masks',
    )
    val_dataset = IndustrialLandDataset(
        image_dir=f'{val_dir}/images',
        mask_dir=f'{val_dir}/masks',
    )

    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=4
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=4
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    # Class-weighted cross-entropy (industrial areas have imbalanced classes)
    class_weights = torch.FloatTensor([
        0.5, 2.0, 1.5, 1.0, 0.8, 1.5, 2.5, 3.0
    ]).to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    best_miou = 0.0

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for images, masks in train_loader:
            images, masks = images.to(device), masks.to(device)
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, masks)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        scheduler.step()

        # Validation
        model.eval()
        val_miou = compute_miou(model, val_loader, device, NUM_CLASSES)
        avg_loss = train_loss / len(train_loader)

        logger.info(
            f"Epoch {epoch+1}/{epochs} | "
            f"Loss: {avg_loss:.4f} | Val mIoU: {val_miou:.4f}"
        )

        if val_miou > best_miou:
            best_miou = val_miou
            torch.save(model.state_dict(), output_path / 'best_deeplabv3.pth')
            logger.info(f"New best model saved (mIoU: {best_miou:.4f})")

    logger.info(f"Training complete. Best mIoU: {best_miou:.4f}")
    return model


def compute_miou(
    model: nn.Module,
    dataloader: DataLoader,
    device: str,
    num_classes: int,
) -> float:
    """Compute mean Intersection over Union across all classes."""
    confusion = torch.zeros(num_classes, num_classes, dtype=torch.long)

    with torch.no_grad():
        for images, masks in dataloader:
            images = images.to(device)
            outputs = model(images)
            preds = outputs.argmax(dim=1).cpu()

            for pred, mask in zip(preds, masks):
                for c in range(num_classes):
                    pred_c = (pred == c)
                    mask_c = (mask == c)
                    confusion[c, c] += (pred_c & mask_c).sum().item()
                    confusion[c, :] += pred_c.sum().item() - (pred_c & mask_c).sum().item()

    ious = []
    for c in range(num_classes):
        intersection = confusion[c, c].item()
        union = confusion[c, :].sum().item() + confusion[:, c].sum().item() - intersection
        if union > 0:
            ious.append(intersection / union)

    return np.mean(ious) if ious else 0.0


def predict_tile(
    model: nn.Module,
    tile: np.ndarray,
    device: str = 'cuda',
) -> np.ndarray:
    """Run segmentation on a single tile. Returns class label map."""
    model.eval()
    with torch.no_grad():
        x = torch.from_numpy(tile).permute(2, 0, 1).unsqueeze(0).float().to(device)
        x = x / 10000.0
        output = model(x)
        pred = output.argmax(dim=1).squeeze().cpu().numpy()
    return pred


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    print("DeepLabV3+ Segmentation Model for Industrial Land-Use Classification")
    print(f"Classes: {CLASSES}")
    print(f"Device: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
