"""Paso 2: Limpieza y preprocesamiento - Programa Apapachar
=========================================================
Aplica limpieza mínima necesaria sobre los mensajes de texto:
  - Elimina espacios múltiples
  - Filtra a mensajes de tipo "Mensaje en Texto"

No se encontraron: vacíos, NaN, saltos de línea ni mensajes de sistema.

Input:  data/raw/full_base_WA_clean_NOPII.dta
Output: data/clean/mensajes_preprocesados.parquet
"""

from __future__ import annotations

import re

import pandas as pd
from config_loader import DATA_DIR, PROJECT_ROOT, cfg

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
DATA_PATH = PROJECT_ROOT / cfg["data"]["input"]["raw_stata_file"]
OUT_PATH = DATA_DIR / "clean" / "mensajes_preprocesados.parquet"

COL_TYPE = cfg["data"]["columns"]["message_type"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
TEXT_TYPE = cfg["data"]["values"]["text_message_type"]

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Carga y filtro
# ---------------------------------------------------------------------------
print("Cargando datos...")
df = pd.read_stata(DATA_PATH)
print(f"  Total filas: {len(df)}")

txt = df[df[COL_TYPE] == TEXT_TYPE].copy()
print(f"  Mensajes de texto: {len(txt)}")


# ---------------------------------------------------------------------------
# 2. Limpieza
# ---------------------------------------------------------------------------
def limpiar_mensaje(texto: str) -> str:
    texto = re.sub(r" +", " ", texto)  # espacios múltiples -> uno
    return texto.strip()


antes = txt[COL_TEXT].str.contains(r"  +", regex=True).sum()
txt[COL_TEXT] = txt[COL_TEXT].apply(limpiar_mensaje)
despues = txt[COL_TEXT].str.contains(r"  +", regex=True).sum()

print(f"\n  Mensajes con espacios múltiples corregidos: {antes} -> {despues}")

# ---------------------------------------------------------------------------
# 3. Guardar
# ---------------------------------------------------------------------------
txt.to_parquet(OUT_PATH, index=False)
print(f"\nGuardado en: {OUT_PATH}")
print(f"Total mensajes limpios: {len(txt)}")
print("\nPaso 2 completado.")
