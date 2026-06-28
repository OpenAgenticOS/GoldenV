from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional


@dataclass(frozen=True)
class InspectionRecord:
    id: int
    captured_at: str
    inner_diameter_mm: Optional[float]
    weight_g: Optional[float]
    camera_id: str
    scale_id: str
    image_path: str
    overlay_path: str
    notes: str
    error: Optional[str]


class RecordStore:
    def __init__(self, database_path: str):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS inspection_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    captured_at TEXT NOT NULL,
                    inner_diameter_mm REAL,
                    weight_g REAL,
                    camera_id TEXT NOT NULL,
                    scale_id TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    overlay_path TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    error TEXT
                )
                """
            )

    def add_record(
        self,
        captured_at: datetime,
        inner_diameter_mm: Optional[float],
        weight_g: Optional[float],
        camera_id: str,
        scale_id: str,
        image_path: str,
        overlay_path: str,
        notes: str = "",
        error: Optional[str] = None,
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inspection_records (
                    captured_at, inner_diameter_mm, weight_g,
                    camera_id, scale_id, image_path, overlay_path, notes, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    captured_at.isoformat(),
                    inner_diameter_mm,
                    weight_g,
                    camera_id,
                    scale_id,
                    image_path,
                    overlay_path,
                    notes,
                    error,
                ),
            )
            return int(cursor.lastrowid)

    def list_records(self, limit: int = 200) -> List[InspectionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, captured_at, inner_diameter_mm, weight_g,
                       camera_id, scale_id, image_path, overlay_path, notes, error
                FROM inspection_records
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            InspectionRecord(
                id=row[0],
                captured_at=row[1],
                inner_diameter_mm=row[2],
                weight_g=row[3],
                camera_id=row[4],
                scale_id=row[5],
                image_path=row[6],
                overlay_path=row[7],
                notes=row[8] or "",
                error=row[9],
            )
            for row in rows
        ]

    def export_csv(self, output_path: Path, limit: int = 10000) -> int:
        records = self.list_records(limit=limit)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh)
            writer.writerow(["编号", "时间", "内径(mm)", "重量(g)", "相机", "电子秤", "备注", "错误"])
            for r in records:
                writer.writerow(
                    [
                        r.id,
                        r.captured_at,
                        r.inner_diameter_mm if r.inner_diameter_mm is not None else "",
                        r.weight_g if r.weight_g is not None else "",
                        r.camera_id,
                        r.scale_id,
                        r.notes,
                        r.error or "",
                    ]
                )
        return len(records)
