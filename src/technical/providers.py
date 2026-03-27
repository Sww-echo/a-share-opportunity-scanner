from __future__ import annotations

from pathlib import Path

from .csv_store import load_technical_snapshot
from .interfaces import TechnicalSnapshotProvider
from .models import TechnicalSnapshotRecord

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE_TECHNICAL_SNAPSHOT_PATH = (
    REPO_ROOT / "data" / "seeds" / "sample_technical_snapshot_cn.csv"
)


class SampleTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "sample"

    def __init__(self, sample_path: Path | None = None) -> None:
        self._sample_path = sample_path or DEFAULT_SAMPLE_TECHNICAL_SNAPSHOT_PATH

    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        return load_technical_snapshot(self._sample_path)


class CSVTechnicalSnapshotProvider(TechnicalSnapshotProvider):
    provider_name = "csv"

    def __init__(self, source_path: Path) -> None:
        self._source_path = source_path

    def fetch_snapshot(self) -> list[TechnicalSnapshotRecord]:
        return load_technical_snapshot(self._source_path)


def create_technical_snapshot_provider(
    name: str,
    *,
    source_path: Path | None = None,
    sample_path: Path | None = None,
) -> TechnicalSnapshotProvider:
    """Create a normalized technical snapshot provider."""

    normalized_name = name.strip().lower()

    if normalized_name == "sample":
        return SampleTechnicalSnapshotProvider(sample_path=sample_path)
    if normalized_name == "csv":
        if source_path is None:
            raise ValueError("source_path is required when provider=csv")
        return CSVTechnicalSnapshotProvider(source_path=source_path)

    raise ValueError(f"unsupported technical snapshot provider: {name}")
