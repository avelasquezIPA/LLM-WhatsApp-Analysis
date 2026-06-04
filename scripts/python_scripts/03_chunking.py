"""Paso 3: Chunking - Programa Apapachar
======================================
Agrupa los mensajes por city_grupo + n_week y construye los chunks
de texto que se enviarán a Claude en el Paso 6.

Estrategia: un chunk = todos los mensajes de una ciudad en una semana.
Sin truncación: los chunks van completos (rango: 2,656 - 21,771 tokens).

Input:  data/clean/mensajes_preprocesados.parquet
Output: data/clean/chunks.parquet
"""

from __future__ import annotations

import pandas as pd
from config_loader import DATA_DIR, cfg

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
DATA_PATH = DATA_DIR / "clean" / "mensajes_preprocesados.parquet"
OUT_PATH = DATA_DIR / "clean" / "chunks.parquet"

COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_THEME = cfg["data"]["columns"]["theme"]
FACILITATOR = cfg["data"]["values"]["facilitator_sender"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]
TOKENS_RATIO = cfg["analysis"]["words_to_tokens_ratio"]

# ---------------------------------------------------------------------------
# 1. Carga
# ---------------------------------------------------------------------------
print("Cargando datos preprocesados...")
df = pd.read_parquet(DATA_PATH)
print(f"  Mensajes: {len(df)}")

# ---------------------------------------------------------------------------
# 2. Construir chunks
# ---------------------------------------------------------------------------
print("Construyendo chunks city_grupo x n_week...")

registros = []
for (ciudad, semana), grupo in df.groupby([COL_CITY, COL_WEEK], observed=True):
    grupo = grupo.sort_values(COL_DATETIME).reset_index(drop=True)

    # Texto del chunk: mensajes numerados con remitente
    lineas = [
        f"[{i + 1}] {row[COL_SENDER]}: {row[COL_TEXT]}" for i, row in grupo.iterrows()
    ]
    texto_chunk = "\n".join(lineas)

    # Metadata del chunk
    tema = grupo[COL_THEME].iloc[0] if COL_THEME in grupo.columns else ""
    n_palabras = grupo[COL_TEXT].str.split().str.len().sum()
    tokens_aprox = round(n_palabras / TOKENS_RATIO)
    n_facilitador = (grupo[COL_SENDER] == FACILITATOR).sum()
    n_participante = (grupo[COL_SENDER] == PARTICIPANT).sum()
    fecha_inicio = grupo[COL_DATETIME].min()
    fecha_fin = grupo[COL_DATETIME].max()

    registros.append(
        {
            "chunk_id": f"{ciudad}_s{semana:02d}",
            COL_CITY: ciudad,
            COL_WEEK: semana,
            COL_THEME: tema,
            "n_mensajes": len(grupo),
            "n_facilitador": n_facilitador,
            "n_participante": n_participante,
            "n_palabras": n_palabras,
            "tokens_aprox": tokens_aprox,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "texto_chunk": texto_chunk,
        }
    )

chunks = pd.DataFrame(registros)

# ---------------------------------------------------------------------------
# 3. Resumen
# ---------------------------------------------------------------------------
print(f"\n  Total chunks: {len(chunks)}")
print("  Tokens por chunk:")
print(f"    min:    {chunks['tokens_aprox'].min():,}")
print(f"    mediana:{chunks['tokens_aprox'].median():,.0f}")
print(f"    max:    {chunks['tokens_aprox'].max():,}")
print(f"    total:  {chunks['tokens_aprox'].sum():,}")
print()
print("  Primeros 5 chunks:")
print(
    chunks[["chunk_id", "n_mensajes", "n_participante", "tokens_aprox", "tema"]]
    .head(5)
    .to_string(index=False)
)

# ---------------------------------------------------------------------------
# 4. Guardar
# ---------------------------------------------------------------------------
chunks.to_parquet(OUT_PATH, index=False)
print(f"\nGuardado en: {OUT_PATH}")
print("\nPaso 3 completado.")
