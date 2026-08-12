"""System specification and platform detection."""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
from typing import Any

import psutil

USABLE_RATIO = 0.8


def is_colab() -> bool:
    """Return True when running inside Google Colab."""
    try:
        import google.colab  # noqa: F401

        return True
    except ImportError:
        return False


def _detect_platform() -> str:
    if is_colab():
        return "colab"
    system = platform.system().lower()
    if system == "darwin":
        return "mac"
    if system == "windows":
        return "windows"
    return "linux"


def _parse_nvidia_smi() -> dict[str, Any] | None:
    if not shutil.which("nvidia-smi"):
        return None
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return None

    name, memory = lines[0].split(",", 1)
    try:
        vram_gb = float(memory.strip()) / 1024
    except ValueError:
        return None

    return {"type": "nvidia", "name": name.strip(), "vram_gb": round(vram_gb, 2)}


def _detect_apple_silicon_gpu(ram_gb: float) -> dict[str, Any] | None:
    if platform.system() != "Darwin":
        return None
    if platform.machine().lower() not in {"arm64", "aarch64"}:
        return None
    return {
        "type": "apple",
        "name": "Apple Silicon (unified memory)",
        "vram_gb": round(ram_gb, 2),
    }


def get_system_specs() -> dict[str, Any]:
    """
    Detect RAM, GPU, usable memory budget, and platform.

    Returns
    -------
    dict
        Keys: ram_gb, gpu, usable_gb, platform
    """
    ram_gb = round(psutil.virtual_memory().total / (1024**3), 2)
    gpu = _parse_nvidia_smi()
    if gpu is None:
        gpu = _detect_apple_silicon_gpu(ram_gb)

    if gpu and gpu.get("vram_gb"):
        base_gb = float(gpu["vram_gb"])
    else:
        gpu = {"type": "cpu", "name": "CPU only", "vram_gb": 0.0}
        base_gb = ram_gb

    usable_gb = round(base_gb * USABLE_RATIO, 2)

    return {
        "ram_gb": ram_gb,
        "gpu": gpu,
        "usable_gb": usable_gb,
        "platform": _detect_platform(),
    }


def format_specs_summary(specs: dict[str, Any]) -> str:
    """Human-readable one-line summary of system specs."""
    gpu = specs["gpu"]
    gpu_label = gpu.get("name", "unknown")
    if gpu.get("type") == "cpu":
        return f"RAM {specs['ram_gb']} GB (CPU only, usable ~{specs['usable_gb']} GB)"
    return (
        f"RAM {specs['ram_gb']} GB, GPU {gpu_label} "
        f"({gpu.get('vram_gb', 0)} GB VRAM, usable ~{specs['usable_gb']} GB)"
    )
