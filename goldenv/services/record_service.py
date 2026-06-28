from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from goldenv.config import AppConfig
from goldenv.storage import RecordStore
from goldenv.services.vision_service import VisionService


class RecordService:
    def __init__(self, config: AppConfig, base_dir: Path):
        self.config = config
        self.base_dir = base_dir
        db_path = base_dir / config.storage.database_path
        self.store = RecordStore(str(db_path))
        self.image_dir = base_dir / config.storage.image_dir
        self.overlay_dir = base_dir / config.storage.overlay_dir

    def save_inspection(
        self,
        vision: VisionService,
        inner_diameter_mm: Optional[float],
        weight_g: Optional[float],
        overlay: Optional[np.ndarray],
        raw_image: Optional[np.ndarray],
        notes: str = "",
        error: Optional[str] = None,
    ) -> int:
        captured_at = datetime.now()
        prefix = captured_at.strftime("%Y%m%d_%H%M%S")
        image_path = ""
        overlay_path = ""
        if raw_image is not None:
            image_path = str(vision.save_image(raw_image, self.image_dir, f"img_{prefix}"))
        if overlay is not None:
            overlay_path = str(self._save_overlay(overlay, prefix))
        return self.store.add_record(
            captured_at=captured_at,
            inner_diameter_mm=inner_diameter_mm,
            weight_g=weight_g,
            camera_id=vision.camera_config.id,
            scale_id=vision.config.scales[0].id if vision.config.scales else "",
            image_path=image_path,
            overlay_path=overlay_path,
            notes=notes,
            error=error,
        )

    def _save_overlay(self, overlay: np.ndarray, prefix: str) -> Path:
        self.overlay_dir.mkdir(parents=True, exist_ok=True)
        path = self.overlay_dir / f"overlay_{prefix}.png"
        cv2.imwrite(str(path), overlay)
        return path

    def export_csv(self, output_path: Path) -> int:
        return self.store.export_csv(output_path)
