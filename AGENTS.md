# Repository Guidelines

## Project Structure & Module Organization
- Code lives under `doctranslate/`:
  - `workflow/` (pipelines for each format), `translator/` (LLM adapters), `converter/` (PDF/Doc → Markdown), `exporter/` (HTML/MD/DOCX/XLSX/… outputs), `agents/`, `utils/`, `static/`, `template/`.
  - Entrypoints: `doctranslate/cli.py` (CLI) and `doctranslate/app.py` (Web UI).
- Supporting folders: `examples/` (sample inputs), `docs/` and `images/` (docs/assets).
- Build config: `pyproject.toml` (Python 3.11+, `doctranslate` console script).

## Build, Test, and Development Commands
- Environment (recommended):
  - `uv venv .venv && source .venv/bin/activate`
  - `uv sync --group dev-light` (fast) or `uv sync --group dev` (includes docling and heavy deps)
- Build/install locally:
  - `uv build`
  - `uv pip install dist/doctranslate-*.whl`
- Run CLI:
  - `doctranslate -h` | `doctranslate version`
  - `doctranslate translate examples/2206.01062v1.md --skip-translate --formats markdown --out-dir output`
- Run Web UI/API:
  - `pip install "doctranslate[webui]" && doctranslate gui -p 8010`

## Coding Style & Naming Conventions
- Python 3.11+, PEP 8, 4-space indent. Use type hints and `pathlib.Path` for I/O.
- Naming: modules/functions `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE`.
- Public functions/classes require docstrings; keep CLI help text concise and clear.

## Testing Guidelines
- Preferred: `pytest`. Place tests in `tests/` named `test_*.py`.
- Mock network/LLM calls; for deterministic runs use `--skip-translate` and sample files in `examples/`.
- Run tests with `pytest -q`. Focus on workflows, exporters, and CLI argument handling.

## Commit & Pull Request Guidelines
- Use Conventional Commits when possible (bilingual allowed), e.g. `feat(workflow): add docx export`.
- Subject ≤ 72 chars; imperative mood. Include rationale, links to issues, and verification steps.
- PRs: clear description, reproduction/verification commands, screenshots or CLI output for UI/UX changes, and docs updates (`README.md`, `examples/`) when flags/behavior change.

## Security & Configuration Tips
- Never commit secrets. Configure via env vars (auto-loaded from `.env` if present):
  - `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `MINERU_TOKEN`, `DOCTRANSLATE_PORT`.
- Example file: `.env.example` → copy to `.env` and fill values.
- Disable auto-loading with `--no-env` or set a custom path via `--env-file` or `DOCTRANSLATE_ENV_FILE`.
- Prefer `--group dev-light` for quick iteration; use `--group dev` only when validating docling paths.

## Agent-Specific Notes
- Language: default English; switch with `--lang en|zh` or `DOCTRANSLATE_LANG`.
- Orchestration: use `--emit-manifest` and `--progress jsonl` for machine-readable outputs.
- Upstream conversion: if using an external converter (e.g., docling CLI), pass its output directory with `--docpkg`.