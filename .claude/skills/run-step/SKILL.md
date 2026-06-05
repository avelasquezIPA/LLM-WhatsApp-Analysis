---
name: run-step
description: Use this skill when the user wants to execute one or more steps of the LLM WhatsApp analysis pipeline. Invoked with /run-step <N> where N is a step number (1-10f) or a script name. Validates config.yaml and environment before running. Examples: /run-step 3, /run-step 04, /run-step 10c.
---

# Run Pipeline Step

Executes a step of the LLM WhatsApp analysis pipeline with pre-flight validation.

## Usage

```
/run-step <step>
```

Where `<step>` is one of:

- A step number: `1`, `3`, `04`, `10c`
- A partial script name: `chunking`, `embeddings`

## Step Map

| Step | Script | Description | Requires |
|------|--------|-------------|---------|
| 01 | `01_quality_analysis.py` | Quality metrics + readability stats | `mensajes_preprocesados.parquet` |
| 02 | `02_preprocessing.py` | Clean and normalize raw messages | `data/raw/*.dta` |
| 03 | `03_chunking.py` | Group messages into chunks | `mensajes_preprocesados.parquet` |
| 04 | `04_embeddings.py` | Generate sentence embeddings (ChromaDB) | `mensajes_preprocesados.parquet` |
| 05a | `05a_clustering.py` | KMeans clustering + UMAP visualization | `mensajes_preprocesados.parquet` |
| 05b | `05b_semantic_search.py` | RAG search (interactive) | ChromaDB vectorstore, Claude API |
| 07 | `07_similarity_map.py` | Semantic similarity heatmap + evolution | ChromaDB vectorstore |
| 07b | `07b_similarity_map_participantes.py` | Same, participants only | ChromaDB vectorstore |
| 08 | `08_citation_finder.py` | Find quotes per qualitative code | Coding tree Excel, ChromaDB |
| 08b | `08b_citation_finder_participantes.py` | Same, participants only | Same as 08 |
| 09 | `09_analisis_citas_participantes.py` | Analyze citations by gender/city | `08b_citas_*.xlsx` |
| 10a | `10a_cadenas_interaccion.py` | Interaction chains analysis | `mensajes_preprocesados.parquet` |
| 10b | `10b_piloto_codificacion.py` | Pilot coding with Claude | `mensajes_preprocesados.parquet`, Claude API |
| 10c | `10c_codificacion.py` | Full coding framework with Claude | `chunks.parquet`, Claude API |
| 10d | `10d_analisis_interaccion.py` | Interaction hypothesis analysis | `mensajes_preprocesados.parquet` |
| 10e | `10e_escalabilidad.py` | Scalability + facilitator engagement | `mensajes_preprocesados.parquet` |
| 10f | `10f_monitoreo_inicio_semana.py` | Weekly monitoring report | `mensajes_preprocesados.parquet` |

## Workflow

### 1. Parse the requested step

Match the user's input to the correct script name:

- `3` or `03` or `chunking` → `03_chunking.py`
- `10c` or `codificacion` → `10c_codificacion.py`

### 2. Pre-flight validation

Before running, check:

```bash
# 1. config.yaml exists and is valid
uv run python -c "from scripts.python_scripts.config_loader import cfg; print('config OK')"

# 2. Required input files exist
# (check based on step map above)

# 3. Claude API access (for steps 05b, 10b, 10c) — via enterprise plan
python -c "import os; from dotenv import load_dotenv; load_dotenv(); assert os.getenv('ANTHROPIC_API_KEY'), 'ANTHROPIC_API_KEY missing — add to .env or use Claude Code'"
```

If validation fails, report clearly what is missing and how to fix it. Do NOT run the script.

### 3. Execute the step

```bash
cd scripts/python_scripts && uv run python <script_name>.py
```

### 4. Report results

After the script completes:

- Report which output files were generated (from the step map)
- Report any errors or warnings
- Suggest the logical next step in the pipeline

## Error Handling

| Error | Likely Cause | Fix |
|-------|-------------|-----|
| `ModuleNotFoundError` | venv not activated | Run `uv sync` first |
| `FileNotFoundError: chunks.parquet` | Step 03 not run | Run `/run-step 3` first |
| `ANTHROPIC_API_KEY not set` | Missing .env | Add enterprise key to `.env` |
| `chromadb` errors | Step 04 not run | Run `/run-step 4` first |
| `KeyError` in config | config.yaml missing field | Check config.yaml against template |

## Full Pipeline Order

For a complete run from scratch:

```
02 → 03 → 04 → 05a → 07 → 07b → 08 → 08b → 09 → 10a → 10c → 10e → 10f
```

Steps 01, 05b, 10b, 10d are optional/supplementary.
