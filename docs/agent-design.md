# Agent Design

## Goals

  - Keep the agent light: no hard dependency on Docling/MinerU.
  - Let realtimex.ai orchestrate pipelines: Docling CLI runs upstream if needed.
  - Standardize I/O contracts so nodes compose cleanly.
  - Preserve all existing non-PDF workflows (txt/json/xlsx/docx/srt/epub/html/md).

## High-Level Topology

  - Node A (optional): Docling Convert
      - Input: PDF (and similar)
      - Output: Markdown + assets (directory or zip), plus a small manifest.
  - Node B: doctranslate Agent (this repo)
      - Input: file or pre-converted Markdown (from Node A).
      - Action: translate (LLM optional), export results, emit artifacts + metrics.
  - Node C (optional): Post-process or publish
      - E.g., storage, viewers, delivery.

  doctranslate should not import Docling/MinerU packages in its base. Those become upstream responsibilities or optional extras.

## Agent Boundaries

  - Keep doctranslate as:
      - Core library: translators, IR, exporters, minimal dependencies.
      - CLI Agent: a thin wrapper exposing a stable contract to realtimex.ai.
      - Optional extras (install when needed): docling/mineru converters, webui.

## I/O Contract (Agent Mode)

  - Request (stdin JSON or file path args):
      - task_id
      - input:
          - type: md|txt|json|xlsx|docx|srt|epub|html|auto
          - path: file path OR docling output dir/zip (when using identity flow)
      - translate:
          - to_lang, skip_translate, model_id, base_url, api_key, temperature, concurrent, timeout, retry, system_proxy_enable
      - export:
          - out_dir, formats [markdown, markdown_zip, html, json, xlsx, csv, docx, srt, epub]
          - save_attachments: bool
  - Response (stdout JSON):
      - task_id, status: completed|failed|canceled
      - artifacts: [{type, path, mime}]
      - attachments: [{id, path}]
      - metrics: {duration_s, tokens_in/out/cached/reasoning}
      - errors/logs (if any)

  This matches the current CLI capabilities while making the interface machine-friendly.

## Docling Hand-off (Upstream Node)

  - Docling CLI node produces:
      - docling_out/
          - full.md (or configurable)
          - assets/…
          - optional manifest.json (source info)
  - doctranslate Agent consumes:
      - --workflow markdown_based --convert-engine identity
      - --input docling_out/full.md
      - Optionally --save-attachments to capture docling_raw.md (already supported by our attachments system).

  No Docling Python deps in the agent. If desired later, we keep an optional “pdf-docling” extra to re-enable in-process conversion.

## CLI Additions (small refinements)

  - Add an “agent mode”:
      - doctranslate agent --stdio (JSON-RPC over stdio) or --input-json <path> for batch mode.
      - Same capabilities as translate, but I/O is JSON-first.
  - Add an explicit “docling input” convenience:
      - --docling-out <dir_or_zip> as sugar for --workflow markdown_based --convert-engine identity --input <md>. The agent scans the docling output for the main md.
  - Ensure outputs include a tiny artifacts.json manifest for downstream nodes.

## Packaging and Dependencies

  - Base package: no docling/mineru/torch in install_requires.
  - Extras:
      - pdf-docling: docling, opencv, hf-xet (optional)
      - pdf-mineru: mineru client (optional)
      - webui: FastAPI (optional)
  - Dev groups:
      - dev-light: empty or minimal (used by CI and agent runtime)
      - dev: includes heavy extras if needed by contributors
  - Keep uv lock(s) aligned with this split; avoid heavy extras in default sync.

## Scaling, Caching, Reliability

  - Concurrency: configurable; default conservative for runtime.
  - Caching:
      - Keep current on-disk cache for md conversions; allow runtime to inject a workspace path (so cache survives across stages).
  - Rate limiting and retry: already present; expose via config.
  - Observability:
      - Structured logs on stdout/stderr, plus event progress lines (optional).
      - Token usage metrics extracted and returned in response.

## Security

  - Tokens via env or flags; never logged.
  - No network except LLM endpoints; honor system_proxy_enable.

## Migration Plan

  - Add agent mode to CLI (stdio/batch JSON).
  - Add --docling-out sugar (optional).
  - Refactor dependency groups/extras as above (we already added dev-light; next is extras naming).
  - Provide artifacts.json manifest alongside outputs.
  - Document the agent contract in README and a docs/agent.md.

## Why this works well

  - Keeps doctranslate agent shippable, fast to install, and independent of heavy CV/ML stacks.
  - Lets realtimex.ai compose Docling (or any other converter) upstream.
  - Provides a stable, automation-friendly contract with clear artifacts and metrics.