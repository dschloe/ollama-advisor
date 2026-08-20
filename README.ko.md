# ollama-advisor

컴퓨터 사양(RAM, GPU VRAM)과 용도(코딩/추론/비전/임베딩/오디오/일반)를 기반으로, 현재 환경에서 실행 가능한 [Ollama](https://ollama.com) 모델을 추천하고 다운로드·실행·중지까지 지원하는 Python 라이브러리입니다.

Mac, Windows, Linux, Google Colab에서 동작합니다.

> English documentation: [README.md](README.md)

## 설치

```bash
pip install ollama-advisor
```

개발(로컬) 설치:

```bash
git clone https://github.com/dschloe/ollama-advisor.git
cd ollama-advisor
pip install -e ".[dev]"
```

## Quick Start

```python
import ollama_advisor as oa

oa.recommend()                       # 전체 추천 (DataFrame 반환)
oa.recommend(purpose="coding")       # 코딩용만 필터링
oa.pull_model("qwen2.5-coder:7b")    # 모델 다운로드
oa.run_model("qwen2.5-coder:7b", prompt="hello")  # 비대화식 실행
oa.stop_model("qwen2.5-coder:7b")    # 실행 중지
oa.list_installed()                  # 로컬에 설치된 모델 목록
```

### purpose 예시

| `purpose=` | 용도 | 예시 모델 (RAM이 허용할 때) |
|------------|------|---------------------------|
| `"all"` | 전체 추천 | (기본값) |
| `"general"` | 일반 대화·글쓰기 | `llama3.2`, `gemma2`, `mistral` |
| `"coding"` | 코드 생성·디버깅 | `qwen2.5-coder`, `codellama` |
| `"reasoning"` | 수학·논리·추론 | `deepseek-r1`, `qwq` |
| `"vision"` | 이미지 이해 | `llava`, `llama3.2-vision` |
| `"embedding"` | 벡터 검색 / RAG | `nomic-embed-text` |
| `"audio"` | 음성 인식 | `whisper` |

```python
oa.recommend(purpose="coding", top_n=5)
oa.recommend(purpose="reasoning", as_dataframe=False)
oa.recommend(purpose="vision", force_refresh=True)
oa.recommend(purpose="embedding")
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

### 일일 카탈로그 스냅샷

GitHub Actions(`catalog-daily.yml`)가 매일 [ollama.com/library](https://ollama.com/library)를 크롤해 [`data/catalog/`](data/catalog/)에 CSV/JSON을 커밋합니다.

```bash
ollama-advisor snapshot --output data/catalog --force-refresh
```

## 전제 조건: Ollama 설치

`recommend()`와 `get_system_specs()`는 Ollama 없이도 동작합니다.  
`pull_model`, `run_model`, `stop_model`, `list_installed` 등은 **로컬 Ollama 서버**가 필요합니다.

- 다운로드: [https://ollama.com/download](https://ollama.com/download)
- macOS: `brew install ollama` 후 `ollama serve` (또는 앱 실행)
- Windows: 설치 프로그램 실행 후 트레이 앱 기동
- Linux: `curl -fsSL https://ollama.com/install.sh | sh`

Ollama가 꺼져 있으면 한국어 안내 메시지와 함께 `OllamaError`가 발생합니다.

## Google Colab

`recommend()`는 Ollama 없이 동작합니다. `pull`/`run`/`list`는 런타임마다 **`setup_colab_ollama()`** 한 번 호출:

```python
!pip install -q ollama-advisor

import ollama_advisor as oa

oa.recommend(purpose="coding", top_n=5)   # Ollama 불필요
oa.setup_colab_ollama()                     # Colab 전용 — zstd + Ollama 설치 + serve

oa.pull_model("qwen2.5-coder:0.5b")
print(oa.run_model("qwen2.5-coder:0.5b", prompt="hello"))
```

런타임 종료 시 모델·서버 상태는 초기화됩니다. 노트북/Colab에서는 `recommend()`가 스크롤 HTML 테이블을 표시합니다.

## 동작 방식

| 모듈 | 역할 |
|------|------|
| `system.py` | RAM/GPU/플랫폼 감지, usable 메모리(80%) 계산 |
| `catalog.py` | [ollama.com/library](https://ollama.com/library) 크롤링 + `~/.ollama_advisor_cache.json` 캐시 (TTL 6시간) |
| `purpose.py` | coding/reasoning/vision/embedding/audio/general 분류 |
| `core.py` | `recommend()` — 사양·카탈로그·용도 조합 |
| `colab.py` | `setup_colab_ollama()` — Google Colab에서만 Ollama 설치/기동 |
| `ctl.py` | 공식 `ollama` Python 클라이언트 래핑 |

메모리 추정식(4bit 양자화 근사): `required_gb = billions × 0.6 + 1.0`

## 개발 & 테스트

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

CI(`test.yml`)는 Ubuntu / Windows / macOS × Python 3.9 / 3.11에서 실행되며, 네트워크 크롤링은 mock 처리합니다.

## PyPI 배포 (메인테이너용)

### 1. PyPI 프로젝트 등록

1. [pypi.org](https://pypi.org) 계정 생성
2. 프로젝트 이름 `ollama-advisor` 사용 가능 여부 확인 (이미 사용 중이면 `ollama-model-advisor` 등 대체)
3. 첫 업로드 시 프로젝트가 자동 생성되거나, Trusted Publisher로 배포 가능

### 2. Trusted Publisher (OIDC) 연결

1. PyPI → Account settings → Publishing → Add a new pending publisher
2. 설정:
   - **PyPI project name**: `ollama-advisor`
   - **Owner**: GitHub 사용자/조직
   - **Repository name**: `ollama-advisor`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi` (GitHub repo Settings → Environments에서 `pypi` 환경 생성 권장)
3. GitHub 저장소 Settings → Environments → `pypi` → Deployment protection rules 설정(선택)

API 토큰 없이 `.github/workflows/publish.yml`의 `pypa/gh-action-pypi-publish`가 OIDC로 배포합니다.

### 3. 릴리스 발행

**자동(권장):** `pyproject.toml`의 `version`(및 `__version__`)을 올린 뒤 `main`에 merge.  
`release-on-version.yml`이 `vX.Y.Z` Release를 만들고 → `publish.yml`이 PyPI에 업로드합니다.

**수동:**

```bash
git tag v0.1.2
git push origin v0.1.2
```

GitHub Releases에서 Publish(또는 자동 워크플로) 후:

1. `publish.yml`이 `pytest` 게이트 실행
2. 통과 시 PyPI에 wheel/sdist 업로드

로컬 수동 배포(비권장, 디버깅용):

```bash
python -m build
twine upload dist/*
```

## 라이선스

MIT — [LICENSE](LICENSE)

## 📦 Download Stats

| Metric | Count |
|--------|------:|
| **Today** (2026-08-20) | 22 |
| **Total (cumulative)** | 1,296 |

> Updated daily via GitHub Actions