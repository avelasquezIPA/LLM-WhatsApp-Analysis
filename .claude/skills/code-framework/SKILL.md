---
name: code-framework
description: Use this skill when the user wants to apply a qualitative coding framework to WhatsApp message data using Claude API. This is a generalized version of script 10c_codificacion.py that works with any indicator framework defined in config.yaml — not just the Dedios-Sanguineti Apapachar framework. Invoked with /code-framework or /code-framework <config_path>.
---

# Code Framework Skill

Applies any qualitative coding framework (defined in `config.yaml`) to WhatsApp message chunks using Claude API.

## Usage

```
/code-framework
/code-framework path/to/config.yaml
```

## What This Skill Does

Runs `scripts/python_scripts/10c_codificacion.py`, which:

1. Reads the coding indicators from `config.yaml > coding.indicators`
2. Selects representative chunks per group (configurable sample)
3. Sends each chunk to Claude with the coding framework as context
4. Returns structured Excel output with codes, evidence, and scoring

The framework is **fully config-driven** — to adapt it to a new project, only `config.yaml` needs to change.

## Framework Configuration

The coding framework lives in `config.yaml` under `coding:`:

```yaml
coding:
  indicators:
    - id: I1
      name: "Nombre del indicador"
      level: "Nivel de análisis"       # e.g. "Programa", "Grupo", "Individual"
      description: "Descripción"
      adaptation: "Texto de adaptación específica al proyecto"
      positive_codes: ["[COD1]", "[COD2]"]
      negative_codes: ["[COD3]"]

  # Column names for the output Excel
  general_indicator_codes: ["[COD1]", "[COD2]", "[COD3]"]
  specific_indicator_codes: ["[COD4]", "[COD5]"]
```

### Levels of Analysis

The `level` field controls how the indicator is measured:

| Level | Meaning | Aggregated at |
|-------|---------|---------------|
| `"Programa"` | Applies to whole program | All chunks |
| `"Grupo"` | Per facilitation group | City/group groupby |
| `"Individual"` | Per participant | Participant ID |
| `"Específico <proyecto>"` | Project-specific | Configurable |

### Indicator Structure (Dedios-Sanguineti example)

The default Apapachar config has 8 indicators (I1-I8) from Dedios-Sanguineti et al. (2025):

| ID | Name | Level |
|----|------|-------|
| I1 | Alcance del programa | Programa |
| I2 | Retención | Programa |
| I3 | Fidelidad de implementación | Grupo |
| I4 | Involucramiento facilitador | Grupo |
| I5 | Participación activa | Grupo |
| I6 | Cambio de actitudes | Individual |
| I7 | Identidades compartidas | Grupo |
| I8 | Adopción de práctica reportada | Específico |

## Workflow

### 1. Validate configuration

```bash
uv run python -c "
from scripts.python_scripts.config_loader import cfg
indicators = cfg['coding']['indicators']
print(f'Framework: {len(indicators)} indicators')
for ind in indicators:
    print(f'  {ind[\"id\"]}: {ind[\"name\"]} [{ind[\"level\"]}]')
"
```

### 2. Check required inputs

- `data/clean/chunks.parquet` — output of step 03
- `data/clean/mensajes_preprocesados.parquet` — output of step 02
- `ANTHROPIC_API_KEY` in `.env`

### 3. Run the coding

```bash
cd scripts/python_scripts && uv run python 10c_codificacion.py
```

### 4. Output

The script generates:

- `outputs/tables/10c_chunk1.xlsx` — First sample batch
- `outputs/tables/10c_chunk2.xlsx` — Second sample batch
- `outputs/tables/10c_grupos_representativos.csv` — Which chunks were sampled

## Adapting to a New Framework

To replace Dedios-Sanguineti with a different coding framework:

1. Define your indicators in `config.yaml` under `coding.indicators`
2. Update `coding.general_indicator_codes` and `coding.specific_indicator_codes`
3. Update the system prompt in `config.yaml > prompts.coding_system` if needed
4. Run `/code-framework`

The script will automatically:

- Build the guide sheet with your indicator names and descriptions
- Use your `adaptation` text in the specific column
- Apply your positive/negative code lists for scoring

## Cost Estimation

Claude API costs for coding (approximate, claude-sonnet-4-6):

| Dataset size | Chunks sampled | Estimated cost |
|-------------|---------------|---------------|
| 48 chunks | ~10 | ~$0.30 USD |
| 100 chunks | ~20 | ~$0.60 USD |
| 200 chunks | ~30 | ~$0.90 USD |

Costs depend on chunk token length and `config.yaml > api.max_tokens_coding`.

## Related Scripts

- `10b_piloto_codificacion.py` — Pilot run on a small sample before full coding
- `09_analisis_citas_participantes.py` — Analyze citation distribution after coding
- `08_citation_finder.py` / `08b` — Find supporting quotes per code (uses ChromaDB)
