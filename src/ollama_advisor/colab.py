"""Google Colab helpers for installing and starting Ollama in-notebook."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from .ctl import OLLAMA_HOST, OllamaError, is_ollama_installed
from .system import is_colab

INSTALL_SCRIPT = "curl -fsSL https://ollama.com/install.sh | sh"


def is_server_running(timeout: float = 3.0) -> bool:
    """Return True if Ollama responds on localhost:11434."""
    req = urllib_request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=timeout):
            return True
    except (urllib_error.URLError, OSError, TimeoutError):
        return False


def setup_colab_ollama(
    wait_seconds: float = 5.0,
    force_install: bool = False,
    log_path: str | Path = "ollama.log",
) -> dict[str, Any]:
    """
    Install and start Ollama inside the current Google Colab runtime.

    Only callable from Colab. Runs the official install script and starts
    ``ollama serve`` in the background, then waits until the API is reachable.

    Parameters
    ----------
    wait_seconds
        Seconds to wait after starting the server before checking readiness.
    force_install
        Re-run the install script even if ``ollama`` is already on PATH.
    log_path
        File path for ``ollama serve`` stdout/stderr in the Colab VM.

    Returns
    -------
    dict
        Keys: ready (bool), steps (list[str]), log_path (str), host (str)
    """
    if not is_colab():
        raise RuntimeError(
            "setup_colab_ollama() is only for Google Colab. "
            "On desktop, install Ollama from https://ollama.com/download and run `ollama serve`."
        )

    steps: list[str] = []
    log_file = Path(log_path)

    if force_install or not is_ollama_installed():
        result = subprocess.run(
            ["bash", "-c", INSTALL_SCRIPT],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise OllamaError(
                "Failed to install Ollama in Colab.\n"
                f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        steps.append("installed")

    if is_server_running():
        return {
            "ready": True,
            "steps": steps or ["already_running"],
            "log_path": str(log_file),
            "host": OLLAMA_HOST,
        }

    log_file.parent.mkdir(parents=True, exist_ok=True)
    with log_file.open("a", encoding="utf-8") as logfh:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=logfh,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    steps.append("started")

    deadline = time.time() + max(wait_seconds, 1.0)
    while time.time() < deadline:
        if is_server_running():
            break
        time.sleep(0.5)

    if not is_server_running():
        raise OllamaError(
            "Ollama server did not become ready in Colab.\n"
            f"Check log: {log_file}\n"
            "Try: setup_colab_ollama(wait_seconds=15, force_install=True)"
        )

    return {
        "ready": True,
        "steps": steps,
        "log_path": str(log_file),
        "host": OLLAMA_HOST,
    }
