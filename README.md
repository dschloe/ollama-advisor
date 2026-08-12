# ollama-advisor

A Python library that recommends [Ollama](https://ollama.com) models you can run on your machine, based on system specs (RAM, GPU VRAM) and use case (coding, reasoning, vision, embedding, audio, general). It also supports downloading, running, and stopping models.

Works on Mac, Windows, Linux, and Google Colab.

> Korean documentation: [README.ko.md](README.ko.md)

## Installation

```bash
pip install ollama-advisor
```

Local development install:

```bash
git clone https://github.com/dschloe/ollama-advisor.git
cd ollama-advisor
pip install -e ".[dev]"
```

## Quick Start

```python
import ollama_advisor as oa

oa.recommend()                       # Full recommendations (returns a DataFrame)
oa.recommend(purpose="coding")       # Filter for coding models only
oa.pull_model("qwen2.5-coder:7b")    # Download a model
oa.run_model("qwen2.5-coder:7b", prompt="hello")  # Single-shot (non-interactive) run
oa.stop_model("qwen2.5-coder:7b")    # Stop / unload a running model
oa.list_installed()                  # List locally installed models
```

CLI:

```bash
ollama-advisor recommend --purpose coding
ollama-advisor pull qwen2.5-coder:7b
ollama-advisor run qwen2.5-coder:7b --prompt "hello"
ollama-advisor stop qwen2.5-coder:7b
ollama-advisor list
ollama-advisor ps
ollama-advisor specs
ollama-advisor snapshot --force-refresh
```

### Daily catalog snapshot

GitHub Actions (`catalog-daily.yml`) crawls [ollama.com/library](https://ollama.com/library) once per day and commits CSV/JSON under [`data/catalog/`](data/catalog/).

```bash
ollama-advisor snapshot --output data/catalog --force-refresh
```

## Prerequisites: Ollama

`recommend()` and `get_system_specs()` work without Ollama installed.  
`pull_model`, `run_model`, `stop_model`, `list_installed`, and related commands require a **local Ollama server**.

- Download: [https://ollama.com/download](https://ollama.com/download)
- macOS: `brew install ollama`, then `ollama serve` (or launch the app)
- Windows: run the installer, then start the tray app
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`

If the Ollama server is not running, an `OllamaError` is raised with platform-specific setup instructions (error messages in the library may be localized).

## Google Colab limitations

Colab does **not** officially support keeping Ollama running as a persistent background service. You can start it temporarily:

```python
!curl -fsSL https://ollama.ai/install.sh | sh
!nohup ollama serve > ollama.log 2>&1 &
```

When the runtime shuts down, downloaded models and server state are reset.

In notebooks and Colab, `recommend()` automatically displays a scrollable HTML table.

## How it works

| Module | Role |
|--------|------|
| `system.py` | Detect RAM/GPU/platform; compute usable memory (80% of available) |
| `catalog.py` | Crawl [ollama.com/library](https://ollama.com/library); cache at `~/.ollama_advisor_cache.json` (6h TTL) |
| `purpose.py` | Classify models: coding / reasoning / vision / embedding / audio / general |
| `core.py` | `recommend()` — combine specs, catalog, and purpose |
| `ctl.py` | Wrapper around the official `ollama` Python client |

Memory estimate (approx. 4-bit quantization): `required_gb = billions × 0.6 + 1.0`

## Development & testing

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

CI (`test.yml`) runs on Ubuntu / Windows / macOS with Python 3.9 and 3.11. Network crawling is mocked in tests.

## PyPI publishing (maintainers)

### 1. PyPI project

1. Create an account at [pypi.org](https://pypi.org)
2. Confirm the name `ollama-advisor` is available (alternatives: `ollama-model-advisor`)
3. The project is created on first upload, or when using Trusted Publisher

### 2. Trusted Publisher (OIDC)

1. PyPI → Account settings → Publishing → Add a new pending publisher
2. Configure:
   - **PyPI project name**: `ollama-advisor`
   - **Owner**: GitHub user or organization
   - **Repository name**: `ollama-advisor`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi` (create a `pypi` environment in GitHub repo Settings → Environments)
3. Optionally add deployment protection rules under GitHub → Settings → Environments → `pypi`

The workflow in `.github/workflows/publish.yml` uses `pypa/gh-action-pypi-publish` with OIDC—no API token required in CI.

### 3. Release

```bash
git tag v0.1.1
git push origin v0.1.1
```

Publish a GitHub Release for tag `v0.1.1`. Then:

1. `publish.yml` runs `pytest` as a gate
2. On success, uploads wheel/sdist to PyPI

Manual local upload (debugging only):

```bash
python -m build
twine upload dist/*
```

## License

MIT — see [LICENSE](LICENSE)
