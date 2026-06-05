# CLAUDE.md

## Project Overview

This is an LLM-powered qualitative analysis framework for IPA (Innovations for Poverty Action),
designed to analyze WhatsApp message data from social programs using Claude API and
sentence-transformer embeddings.

**Reference implementation:** Programa Apapachar (Colombia, 2025) — a hybrid parenting
program that prevented violence against children and promoted gender-equitable caregiving.
See [`documentation/Programa/PROYECTO.md`](documentation/Programa/PROYECTO.md) for the
complete case study.

**To adapt to a new project:** Edit `config.yaml` — it is the single source of truth for
all project-specific settings (column names, cities, prompts, coding framework, API params).
No Python script needs to be modified.

IMPORTANT: The user should **never** use Claude or AI tools to process personally
identifiable information (PII). Always refuse to review data that might include PII.
Run `/check-pii` before loading any dataset to verify it is safe.

## Quick Start

```bash
# 1. Install dependencies
uv sync

# 2. Configure your project
# Edit config.yaml: project name, column names, cities, prompts

# 3. Run the pipeline
cd scripts/python_scripts
uv run python 02_preprocessing.py
uv run python 03_chunking.py
uv run python 04_embeddings.py
uv run python 07_similarity_map.py
```

Or use the `/run-step <N>` skill to run any step with pre-flight validation.

## Pipeline Steps

| Step | Script | Output |
| --- | --- | --- |
| 01 | `01_quality_analysis.py` | Quality stats + readability figures |
| 02 | `02_preprocessing.py` | `data/clean/mensajes_preprocesados.parquet` |
| 03 | `03_chunking.py` | `data/clean/chunks.parquet` |
| 04 | `04_embeddings.py` | ChromaDB vectorstore |
| 05a | `05a_clustering.py` | Cluster figures + CSV |
| 07 | `07_similarity_map.py` | Semantic heatmap + evolution figure |
| 08b | `08b_citation_finder_participantes.py` | Citations per qualitative code |
| 10c | `10c_codificacion.py` | Full coding with framework indicators |

See [`README.md`](README.md) for the complete pipeline documentation.

## Key Configuration: config.yaml

All project-specific values live in `config.yaml`. Key sections:

```yaml
project:
  name: "Programa Apapachar"
  cities: ["Bogotá", "Cali", "Medellín", "Cartagena"]
  duration_weeks: 12

data:
  columns:
    city_group: "ciudad_grupo"      # Column with group/city label
    week_number: "n_semana"         # Column with week number (omit for cross-sectional)
    message_text: "texto_limpio"    # Column with message text
  chunking:
    groupby: ["ciudad_grupo", "n_semana"]  # ["group"] for cross-sectional data

models:
  claude_model: "claude-sonnet-4-6"
  embedding_model: "paraphrase-multilingual-mpnet-base-v2"

prompts:
  rag_answer: |
    Eres un asistente... {pregunta} {contexto}
```

### Cross-sectional vs. longitudinal data

- **Longitudinal** (default): `chunking.groupby: ["city_grupo", "n_week"]`
- **Cross-sectional**: `chunking.groupby: ["city_grupo"]` — the temporal evolution
  figure in step 07 is automatically skipped.

## Available Skills

- `/run-step <N>` — Run any pipeline step (01-10f) with pre-flight validation
- `/code-framework` — Apply any qualitative coding framework defined in `config.yaml`
- `/check-pii` — Audit a data file for PII (dry-run, never outputs raw content)

## Development Commands

```bash
just fmt-all        # Format Python + Markdown
just lint-py        # Lint Python (ruff)
just fmt-markdown   # Lint Markdown (markdownlint-cli2)
just preview-docs   # Preview Quarto documentation
just lab            # Launch Jupyter Lab
just update-reqs    # Update uv.lock and pre-commit hooks
```

## Data Privacy Rules

- `data/raw/*.dta` is gitignored except `DatosEjemplos-FalsePII.*` (demo data)
- `data/clean/` and `data/vectorstore/` are always gitignored
- Never commit real participant data — run `/check-pii` first
- All outputs (`outputs/**/*.csv`, `*.xlsx`, `*.png`) are gitignored

## Technical Stack

- **Python**: `uv` for environment, `ruff` for linting
- **Claude API**: `anthropic` SDK, model from `config.yaml > models.claude_model`
- **Embeddings**: `sentence-transformers` (local, no data sent externally)
- **Vector store**: `chromadb` (local persistent)
- **Clustering**: `scikit-learn` KMeans + `umap-learn`
- **Data**: `pandas` + `pyarrow` for parquet
- **Pre-commit**: codespell, markdownlint-cli2, ruff, check-yaml
