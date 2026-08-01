from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_storage_path(file_path: str | Path) -> Path:
    path = Path(file_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()
