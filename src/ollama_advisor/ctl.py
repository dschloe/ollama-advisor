"""Ollama server control via the official Python client."""

from __future__ import annotations

import json
import shutil
import sys
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from .system import is_colab

OLLAMA_HOST = "http://localhost:11434"


class OllamaError(RuntimeError):
    """Raised when Ollama is unavailable or an operation fails."""


def is_ollama_installed() -> bool:
    """Return True if the `ollama` CLI binary is on PATH."""
    return shutil.which("ollama") is not None


def install_hint() -> str:
    """Platform-specific guidance for installing and running Ollama."""
    if is_colab():
        return (
            "Google Colab에서는 Ollama가 공식적으로 백그라운드 서비스 지속 실행을 "
            "지원하지 않습니다. 임시 실행 예:\n"
            "  !curl -fsSL https://ollama.ai/install.sh | sh\n"
            "  !nohup ollama serve > ollama.log 2>&1 &\n"
            "런타임이 종료되면 다운로드한 모델과 서버 상태가 초기화됩니다."
        )
    if sys.platform == "darwin":
        return (
            "Ollama가 설치되어 있지 않거나 서버가 실행 중이 아닙니다.\n"
            "  brew install ollama\n"
            "  또는 https://ollama.com/download/mac 에서 설치 후 `ollama serve` 실행"
        )
    if sys.platform == "win32":
        return (
            "Ollama가 설치되어 있지 않거나 서버가 실행 중이 아닙니다.\n"
            "  https://ollama.com/download/windows 에서 설치 후 앱을 실행하세요."
        )
    return (
        "Ollama가 설치되어 있지 않거나 서버가 실행 중이 아닙니다.\n"
        "  curl -fsSL https://ollama.com/install.sh | sh\n"
        "  ollama serve"
    )


def _ensure_client():
    try:
        import ollama
    except ImportError as exc:
        raise OllamaError(
            "공식 `ollama` Python 패키지가 설치되어 있지 않습니다. "
            "`pip install ollama` 로 설치하세요."
        ) from exc
    return ollama


def _check_server() -> None:
    req = urllib_request.Request(f"{OLLAMA_HOST}/api/tags", method="GET")
    try:
        with urllib_request.urlopen(req, timeout=3):
            return
    except (urllib_error.URLError, OSError, TimeoutError) as exc:
        raise OllamaError(
            "Ollama 서버(localhost:11434)에 연결할 수 없습니다.\n"
            f"{install_hint()}"
        ) from exc


def _normalize_model_list(raw: Any) -> list[dict[str, Any]]:
    models = getattr(raw, "models", None)
    if models is None and isinstance(raw, dict):
        models = raw.get("models", [])
    if models is None:
        models = raw if isinstance(raw, list) else []

    result: list[dict[str, Any]] = []
    for item in models:
        if hasattr(item, "model"):
            name = item.model
            size = getattr(item, "size", None)
            modified = getattr(item, "modified_at", None)
        elif isinstance(item, dict):
            name = item.get("name") or item.get("model", "")
            size = item.get("size")
            modified = item.get("modified_at")
        else:
            continue
        result.append(
            {
                "name": name,
                "size": size,
                "modified_at": str(modified) if modified is not None else "",
            }
        )
    return result


def pull_model(name: str, stream: bool = True) -> None:
    """Download a model from the Ollama registry."""
    _check_server()
    ollama = _ensure_client()
    try:
        if stream:
            for chunk in ollama.pull(name, stream=True):
                status = chunk.get("status", "")
                if status:
                    print(status, file=sys.stderr)
                completed = chunk.get("completed")
                total = chunk.get("total")
                if completed is not None and total:
                    pct = 100 * completed / total
                    print(f"  {pct:.1f}%", file=sys.stderr)
        else:
            ollama.pull(name)
    except Exception as exc:
        raise OllamaError(f"모델 다운로드 실패 ({name}): {exc}\n{install_hint()}") from exc


def run_model(name: str, prompt: str, **kwargs: Any) -> str:
    """Run a single non-interactive prompt against a model."""
    _check_server()
    ollama = _ensure_client()
    try:
        response = ollama.generate(model=name, prompt=prompt, **kwargs)
        if isinstance(response, dict):
            return response.get("response", "")
        return getattr(response, "response", str(response))
    except Exception as exc:
        raise OllamaError(f"모델 실행 실패 ({name}): {exc}\n{install_hint()}") from exc


def stop_model(name: str) -> None:
    """Unload a running model from memory."""
    _check_server()
    ollama = _ensure_client()
    try:
        ollama.generate(model=name, prompt="", keep_alive=0)
    except Exception:
        payload = json.dumps({"model": name, "keep_alive": 0}).encode()
        req = urllib_request.Request(
            f"{OLLAMA_HOST}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib_request.urlopen(req, timeout=30):
                return
        except Exception as exc:
            raise OllamaError(
                f"모델 중지 실패 ({name}): {exc}\n{install_hint()}"
            ) from exc


def list_installed() -> list[dict[str, Any]]:
    """List locally installed models."""
    _check_server()
    ollama = _ensure_client()
    try:
        return _normalize_model_list(ollama.list())
    except Exception as exc:
        raise OllamaError(f"설치된 모델 목록 조회 실패: {exc}\n{install_hint()}") from exc


def list_running() -> list[dict[str, Any]]:
    """List models currently loaded in memory."""
    _check_server()
    ollama = _ensure_client()
    try:
        return _normalize_model_list(ollama.ps())
    except Exception as exc:
        raise OllamaError(f"실행 중 모델 조회 실패: {exc}\n{install_hint()}") from exc


def remove_model(name: str) -> None:
    """Delete a model from local storage."""
    _check_server()
    ollama = _ensure_client()
    try:
        ollama.delete(name)
    except Exception as exc:
        raise OllamaError(f"모델 삭제 실패 ({name}): {exc}\n{install_hint()}") from exc
