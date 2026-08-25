"""Ollama model advisor — recommend, pull, run, and manage local models."""

from .colab import setup_colab_ollama
from .core import recommend
from .ctl import (
    list_installed,
    list_running,
    pull_model,
    remove_model,
    run_model,
    stop_model,
)
from .system import get_system_specs

__all__ = [
    "recommend",
    "setup_colab_ollama",
    "pull_model",
    "run_model",
    "stop_model",
    "list_installed",
    "list_running",
    "remove_model",
    "get_system_specs",
]

__version__ = "0.1.4"
