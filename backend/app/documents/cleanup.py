"""Removing uploaded files once their rows are gone.

Always after the database commit, never before. The two stores cannot be
deleted atomically, so the ordering is a choice about which inconsistency to
prefer: a file with no row is invisible to the application and costs disk, a
row with no file is a document that opens to nothing. The first is a cleanup
problem, the second is data loss, so files go second and a failure to remove
one is logged rather than raised.
"""

import logging
import shutil
from pathlib import Path

from app.core.config import settings
from app.core.storage import resolve_storage_path


logger = logging.getLogger(__name__)


def _is_inside_upload_root(path: Path) -> bool:
    """Whether a path really is under the configured upload directory.

    `file_path` is a column, and a column is data. Resolving it and checking
    containment means a bad value deletes nothing instead of reaching outside
    the upload tree.
    """
    root = resolve_storage_path(settings.upload_dir)
    return path == root or root in path.parents


def remove_files(file_paths: list[str]) -> None:
    for file_path in file_paths:
        if not file_path:
            continue
        resolved = resolve_storage_path(file_path)
        if not _is_inside_upload_root(resolved):
            logger.warning(
                "Refusing to delete a file outside the upload directory",
                extra={"path": str(resolved)},
            )
            continue
        try:
            resolved.unlink(missing_ok=True)
        except OSError:
            logger.warning(
                "Could not delete uploaded file",
                exc_info=True,
                extra={"path": str(resolved)},
            )


def remove_directory(*parts: str) -> None:
    """Remove an upload subtree — one knowledge base's, or one organization's.

    Cheaper than unlinking thousands of files individually, and it takes the
    now-empty directories with it.
    """
    target = resolve_storage_path(Path(settings.upload_dir).joinpath(*parts))
    if not _is_inside_upload_root(target) or target == resolve_storage_path(
        settings.upload_dir
    ):
        logger.warning(
            "Refusing to delete a directory outside the upload directory",
            extra={"path": str(target)},
        )
        return
    try:
        shutil.rmtree(target, ignore_errors=True)
    except OSError:
        logger.warning(
            "Could not delete upload directory",
            exc_info=True,
            extra={"path": str(target)},
        )
