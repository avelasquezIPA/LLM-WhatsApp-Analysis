"""Paso 6: Summarización con Claude API - Programa Apapachar
==========================================================
Genera resúmenes estructurados de los mensajes de WhatsApp usando Claude.

Tres modalidades:
  6a. Summarización directa: un resumen por chunk (ciudad x semana)
  6b. RAG: ver 05b_semantic_search.py
  6c. Summarización jerárquica: resumen ejecutivo del programa completo
      usando los resúmenes del 6a (map-reduce)

Requiere: ANTHROPIC_API_KEY en .env

Costo estimado (claude-sonnet-4-6):
  - 6a (48 chunks): ~$1.10 USD
  - 6c (resumen ejecutivo): ~$0.05 USD

Input:  data/clean/chunks.parquet
Output:
  - outputs/tables/06a_resumenes_chunks.csv
  - outputs/tables/06c_resumen_ejecutivo.txt
"""

from __future__ import annotations

import os
import time

import anthropic
import pandas as pd
from config_loader import DATA_DIR, PROJECT_ROOT, TABLES_DIR, cfg
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
CHUNKS_PATH = DATA_DIR / "clean" / "chunks.parquet"
OUT_TABLES = TABLES_DIR

load_dotenv(PROJECT_ROOT / ".env")

MODELO = cfg["models"]["claude_model"]
PAUSA_ENTRE_LLAMADAS = cfg["api"]["pause_between_calls"]
MAX_TOKENS_SUMMARY = cfg["api"]["max_tokens_summary"]
MAX_TOKENS_EXECUTIVE = cfg["api"]["max_tokens_executive"]

PROJECT_NAME = cfg["project"]["name"]
PROJECT_DESC = cfg["project"]["description"]
PROJECT_FOCUS = cfg["project"]["target_population"]
N_WEEKS = cfg["project"]["duration_weeks"]
CITIES = cfg["project"]["cities"]

COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_THEME = cfg["data"]["columns"]["theme"]
CHUNK_GROUPBY = cfg["data"]["chunking"]["groupby"]

# ---------------------------------------------------------------------------
# Cliente Claude
# ---------------------------------------------------------------------------
cliente = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# 6a. Summarización directa por chunk
# ---------------------------------------------------------------------------
_PROMPT_RESUMEN_TEMPLATE = cfg["prompts"]["chunk_summary"]


def resumir_chunk(row: pd.Series) -> str:
    """Genera un resumen para un chunk individual."""
    kwargs = {
        "project_name": PROJECT_NAME,
        "project_description": PROJECT_DESC,
        "project_focus": PROJECT_FOCUS,
        "tema": row.get(COL_THEME, ""),
        "texto_chunk": row["texto_chunk"],
        # Aliases de compatibilidad para prompts estilo Apapachar
        "ciudad": row.get(COL_CITY, ""),
        "semana": row.get(COL_WEEK, ""),
    }
    for col in CHUNK_GROUPBY:
        kwargs.setdefault(col, row.get(col, ""))
    prompt = _PROMPT_RESUMEN_TEMPLATE.format(**kwargs)
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS_SUMMARY,
        messages=[{"role": "user", "content": prompt}],
    )
    return respuesta.content[0].text.strip()


def paso_6a(chunks: pd.DataFrame) -> pd.DataFrame:
    """Genera resúmenes para todos los chunks."""
    print("\n=== PASO 6a: Summarización por chunk ===")
    print(f"  Chunks a procesar: {len(chunks)}")

    # Estimar costo
    tokens_input_est = chunks["tokens_aprox"].sum() + len(chunks) * 300
    tokens_output_est = len(chunks) * 300
    costo_est = (tokens_input_est * 3 + tokens_output_est * 15) / 1_000_000
    print(f"  Costo estimado: ~${costo_est:.2f} USD")
    print()

    resumenes = []

    for i, (_, row) in enumerate(chunks.iterrows(), 1):
        print(f"  [{i:02d}/{len(chunks)}] {row['chunk_id']}...", end=" ", flush=True)
        try:
            resumen = resumir_chunk(row)
            resumenes.append(resumen)
            print("OK")
        except Exception as e:
            print(f"ERROR: {e}")
            resumenes.append("")
        time.sleep(PAUSA_ENTRE_LLAMADAS)

    chunks = chunks.copy()
    chunks["resumen"] = resumenes

    # Guardar — solo columnas que existen en el DataFrame
    cols = [
        "chunk_id",
        *CHUNK_GROUPBY,
        COL_THEME,
        "n_mensajes",
        "n_participante",
        "tokens_aprox",
        "resumen",
    ]
    cols = [c for c in cols if c in chunks.columns]
    chunks[cols].to_csv(OUT_TABLES / "06a_resumenes_chunks.csv", index=False)
    print("\n  Resúmenes guardados en outputs/tables/06a_resumenes_chunks.csv")

    return chunks


# ---------------------------------------------------------------------------
# 6c. Summarización jerárquica (map-reduce)
# ---------------------------------------------------------------------------
_PROMPT_EJECUTIVO_TEMPLATE = cfg["prompts"]["executive_summary"]


def paso_6c(chunks_con_resumenes: pd.DataFrame) -> str:
    """Genera resumen ejecutivo a partir de los resúmenes individuales."""
    print("\n=== PASO 6c: Resumen ejecutivo (map-reduce) ===")

    # Organizar resúmenes por columna primaria del groupby
    _primary = CHUNK_GROUPBY[0]
    _secondary = CHUNK_GROUPBY[1:]
    lineas = []
    for grp_val in sorted(chunks_con_resumenes[_primary].unique()):
        lineas.append(f"\n## {grp_val}")
        subset = chunks_con_resumenes[chunks_con_resumenes[_primary] == grp_val]
        if _secondary:
            subset = subset.sort_values(_secondary)
        for _, row in subset.iterrows():
            if row["resumen"]:
                sec_label = " - ".join(str(row.get(c, "")) for c in _secondary)
                tema_str = f" - {row[COL_THEME]}" if row.get(COL_THEME) else ""
                lineas.append(f"\n{sec_label}{tema_str}:\n{row['resumen']}")

    texto_resumenes = "\n".join(lineas)
    primary_vals = sorted(chunks_con_resumenes[_primary].unique())
    prompt = _PROMPT_EJECUTIVO_TEMPLATE.format(
        project_name=PROJECT_NAME,
        project_description=PROJECT_DESC,
        n_chunks=len(chunks_con_resumenes),
        n_cities=len(primary_vals),  # alias backward-compat
        cities_list=", ".join(str(v) for v in primary_vals),
        n_weeks=N_WEEKS,
        resumenes=texto_resumenes,
    )

    print("  Generando resumen ejecutivo...", end=" ", flush=True)
    respuesta = cliente.messages.create(
        model=MODELO,
        max_tokens=MAX_TOKENS_EXECUTIVE,
        messages=[{"role": "user", "content": prompt}],
    )
    resumen_ejecutivo = respuesta.content[0].text.strip()
    print("OK")

    # Guardar
    ruta = OUT_TABLES / "06c_resumen_ejecutivo.txt"
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(resumen_ejecutivo)
    print("  Resumen ejecutivo guardado en outputs/tables/06c_resumen_ejecutivo.txt")

    return resumen_ejecutivo


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Cargando chunks...")
    chunks = pd.read_parquet(CHUNKS_PATH)
    print(f"  {len(chunks)} chunks cargados.")

    # Verificar API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\nERROR: ANTHROPIC_API_KEY no está configurada en .env")
        print("Agrega tu key en el archivo .env:")
        print("  ANTHROPIC_API_KEY=sk-ant-...")
        exit(1)

    # 6a: Resumir todos los chunks
    chunks_con_resumenes = paso_6a(chunks)

    # 6c: Resumen ejecutivo
    resumen_ejecutivo = paso_6c(chunks_con_resumenes)

    print("\n=== RESUMEN EJECUTIVO ===")
    print(resumen_ejecutivo)
    print("\nPaso 6 completado.")
