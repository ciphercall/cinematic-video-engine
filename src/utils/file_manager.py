"""File I/O helpers — directory creation, temp file management."""

import shutil
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating parents if needed."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def clean_dir(path: Path) -> None:
    """Remove all contents of a directory (but not the directory itself)."""
    if path.exists():
        for child in path.iterdir():
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()


def temp_path(base_dir: Path, name: str, suffix: str = "") -> Path:
    """Generate a temp file path within base_dir."""
    ensure_dir(base_dir)
    return base_dir / f"{name}{suffix}"


def safe_filename(name: str) -> str:
    """Sanitize a string for use as a filename."""
    import re
    return re.sub(r'[^\w\-.]', '_', name)[:120]
