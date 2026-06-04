"""Análisis semántico complementario - Programa Apapachar
=======================================================
Script 2b: Buscador de citas por código cualitativo - Solo participantes.

Versión del script 08 que excluye mensajes de facilitadores.
Tanto la búsqueda a nivel chunk como la búsqueda a nivel mensaje
usan únicamente contenido generado por participantes.

Colecciones ChromaDB propias (distintas a las del script 08):
  - apapachar_chunks_part   (chunks reconstruidos solo con participantes)
  - apapachar_mensajes_part (mensajes individuales solo de participantes)

Input:
  - documentation/A+P_2025_Arbol de códigos.xlsx
  - data/clean/mensajes_preprocesados.parquet

Output:
  - outputs/tables/08b_citas_por_codigo_participantes.xlsx
"""

from __future__ import annotations

import chromadb
import pandas as pd
from config_loader import DATA_DIR, PROJECT_ROOT, TABLES_DIR, cfg
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
ARBOL_PATH = PROJECT_ROOT / cfg["data"]["input"]["coding_tree_file"]
MENSAJES_PATH = PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
VECTORSTORE_PATH = DATA_DIR / cfg["data"]["intermediate"]["vectorstore"]
OUT_PATH = TABLES_DIR / "08b_citas_por_codigo_participantes.xlsx"

MODELO_NOMBRE = cfg["models"]["embedding_model"]
N_CHUNKS = cfg["analysis"]["citation_search"]["top_k_chunks"]
N_MENSAJES = cfg["analysis"]["citation_search"]["top_k_messages"]
MIN_MSG_WORDS = cfg["analysis"]["citation_search"]["min_message_words"]
FAMILIAS_REL = cfg["analysis"]["citation_search"]["relevant_families"]

COLECCION_CHUNKS = cfg["vectordb"]["collection_chunks_participants"]
COLECCION_MENSAJES = cfg["vectordb"]["collection_messages_participants"]

CHUNK_GROUPBY = cfg["data"]["chunking"]["groupby"]

COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_THEME = cfg["data"]["columns"]["theme"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_NWORDS = cfg["data"]["columns"]["word_count"]
COL_PARTICIPANT_ID = cfg["data"]["columns"]["participant_id"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]

ARBOL_SHEET = cfg["data"]["input"]["coding_tree_sheet"]
CITATIONS_SHEET = cfg["data"]["input"]["citations_excel_sheet"]

# ---------------------------------------------------------------------------
# 1. Cargar árbol de códigos
# ---------------------------------------------------------------------------
print("Cargando árbol de códigos...")
df_arbol = pd.read_excel(ARBOL_PATH, sheet_name=ARBOL_SHEET)
df_arbol.columns = ["_", "familia", "codigo", "descripcion", "subcod", "cambios"]
df_arbol = df_arbol[["familia", "codigo", "descripcion"]].dropna(subset=["codigo"])
df_arbol = df_arbol[df_arbol["codigo"].str.startswith("[")]
df_arbol["familia"] = df_arbol["familia"].ffill()

print(f"  {len(df_arbol)} códigos cargados.")

mask_relevante = df_arbol["familia"].str.contains(
    "|".join([f[:10] for f in FAMILIAS_REL]), na=False
)
df_relevante = df_arbol[mask_relevante].copy()
print(f"  Códigos en familias relevantes: {len(df_relevante)}")

# ---------------------------------------------------------------------------
# 2. Cargar mensajes y filtrar: solo participantes
# ---------------------------------------------------------------------------
print("\nCargando mensajes...")
df_msgs = pd.read_parquet(MENSAJES_PATH)
df_part = df_msgs[df_msgs[COL_SENDER] == PARTICIPANT].copy()
print(f"  Total mensajes: {len(df_msgs)}")
print(f"  Mensajes de participantes: {len(df_part)}")
print(f"  Mensajes de facilitadores excluidos: {len(df_msgs) - len(df_part)}")

# ---------------------------------------------------------------------------
# 3. Cargar modelo
# ---------------------------------------------------------------------------
print("\nCargando modelo de embeddings...")
modelo = SentenceTransformer(MODELO_NOMBRE)

# ---------------------------------------------------------------------------
# 4. Colección de chunks de participantes
# ---------------------------------------------------------------------------
print("\nConectando a ChromaDB...")
cliente = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))

try:
    coleccion_chunks = cliente.get_collection(COLECCION_CHUNKS)
    print(f"  Colección de chunks existente: {coleccion_chunks.count()} chunks.")
except Exception:
    print("  Creando colección de chunks de participantes...")

    # Reconstruir chunks solo con mensajes de participantes
    registros = []
    for keys, grupo in df_part.groupby(CHUNK_GROUPBY, observed=True):
        if not isinstance(keys, tuple):
            keys = (keys,)
        meta = dict(zip(CHUNK_GROUPBY, keys))
        chunk_id = "_".join(str(v) for v in keys)
        grupo = grupo.sort_values(COL_DATETIME).reset_index(drop=True)
        lineas = [f"[{i + 1}] {row[COL_TEXT]}" for i, row in grupo.iterrows()]
        texto_chunk = "\n".join(lineas)
        tema = grupo[COL_THEME].iloc[0] if COL_THEME in grupo.columns else ""
        registros.append(
            {
                "chunk_id": chunk_id,
                **{k: str(v) for k, v in meta.items()},
                COL_THEME: str(tema),
                "n_mensajes": len(grupo),
                "texto_chunk": texto_chunk,
            }
        )

    df_chunks = pd.DataFrame(registros)
    print(f"  {len(df_chunks)} chunks construidos.")

    print("  Generando embeddings de chunks (puede tomar ~30 seg)...")
    emb_chunks = modelo.encode(
        df_chunks["texto_chunk"].tolist(),
        show_progress_bar=True,
        batch_size=8,
    )

    coleccion_chunks = cliente.create_collection(
        name=COLECCION_CHUNKS,
        metadata={"hnsw:space": "cosine"},
    )
    coleccion_chunks.add(
        documents=df_chunks["texto_chunk"].tolist(),
        embeddings=emb_chunks.tolist(),
        metadatas=[
            {
                "chunk_id": r["chunk_id"],
                **{col: r[col] for col in CHUNK_GROUPBY},
                COL_THEME: r[COL_THEME],
            }
            for _, r in df_chunks.iterrows()
        ],
        ids=df_chunks["chunk_id"].tolist(),
    )
    print(f"  {coleccion_chunks.count()} chunks indexados.")


# ---------------------------------------------------------------------------
# 5. Colección de mensajes individuales de participantes
# ---------------------------------------------------------------------------
def _inferir_genero(id_f: str) -> str:
    if str(id_f).endswith("H"):
        return "Hombre"
    if str(id_f).endswith("M"):
        return "Mujer"
    return ""


# Recrear la colección si no tiene COL_PARTICIPANT_ID en metadata (migración de esquema)
_necesita_recrear = False
try:
    coleccion_mensajes = cliente.get_collection(COLECCION_MENSAJES)
    _sample = coleccion_mensajes.get(limit=1, include=["metadatas"])
    if _sample["metadatas"] and COL_PARTICIPANT_ID not in _sample["metadatas"][0]:
        print("  Colección de mensajes desactualizada. Recreando...")
        cliente.delete_collection(COLECCION_MENSAJES)
        _necesita_recrear = True
    else:
        print(
            f"  Colección de mensajes existente: {coleccion_mensajes.count()} mensajes."
        )
except Exception:
    _necesita_recrear = True

if _necesita_recrear:
    print("\n  Creando colección de mensajes individuales de participantes...")

    df_part_min = df_part.copy()
    df_part_min[COL_NWORDS] = df_part_min[COL_TEXT].str.split().str.len()
    df_part_min = df_part_min[df_part_min[COL_NWORDS] >= MIN_MSG_WORDS].reset_index(
        drop=True
    )
    df_part_min["genero"] = df_part_min[COL_PARTICIPANT_ID].apply(_inferir_genero)
    print(
        f"  Mensajes de participantes con >={MIN_MSG_WORDS} palabras: {len(df_part_min)}"
    )

    print("  Generando embeddings de mensajes (puede tomar 1-2 min)...")
    emb_msgs = modelo.encode(
        df_part_min[COL_TEXT].tolist(),
        show_progress_bar=True,
        batch_size=64,
    )

    coleccion_mensajes = cliente.create_collection(
        name=COLECCION_MENSAJES,
        metadata={"hnsw:space": "cosine"},
    )

    batch_size = cfg["analysis"]["vectordb_batch_size"]
    for i in range(0, len(df_part_min), batch_size):
        batch = df_part_min.iloc[i : i + batch_size]
        emb_batch = emb_msgs[i : i + batch_size]
        coleccion_mensajes.add(
            documents=batch[COL_TEXT].tolist(),
            embeddings=emb_batch.tolist(),
            metadatas=[
                {
                    COL_PARTICIPANT_ID: str(r[COL_PARTICIPANT_ID]),
                    "genero": str(r["genero"]),
                    COL_CITY: str(r[COL_CITY]),
                    COL_WEEK: int(r[COL_WEEK]),
                    COL_THEME: str(r[COL_THEME]),
                    COL_DATETIME: str(r[COL_DATETIME]),
                }
                for _, r in batch.iterrows()
            ],
            ids=[f"msg_part_{i + j}" for j in range(len(batch))],
        )
    print(f"  {coleccion_mensajes.count()} mensajes indexados.")

# ---------------------------------------------------------------------------
# 6. Buscar citas por código
# ---------------------------------------------------------------------------
print(f"\nBuscando citas para {len(df_relevante)} códigos (solo participantes)...")
print(f"  Nivel chunk: top {N_CHUNKS} | Nivel mensaje: top {N_MENSAJES}")

resultados_chunks = []
resultados_mensajes = []

for i, (_, row) in enumerate(df_relevante.iterrows(), 1):
    codigo = row["codigo"]
    descripcion = str(row["descripcion"])
    familia = str(row["familia"])

    print(f"  [{i:02d}/{len(df_relevante)}] {codigo} - {descripcion[:50]}...")

    emb_codigo = modelo.encode([descripcion])

    # --- Búsqueda a nivel CHUNK (participantes) ---
    res_chunks = coleccion_chunks.query(
        query_embeddings=emb_codigo.tolist(),
        n_results=N_CHUNKS,
        include=["documents", "metadatas", "distances"],
    )
    for doc, meta, dist in zip(
        res_chunks["documents"][0],
        res_chunks["metadatas"][0],
        res_chunks["distances"][0],
    ):
        resultados_chunks.append(
            {
                "familia": familia,
                "codigo": codigo,
                "descripcion_codigo": descripcion,
                "chunk_id": meta["chunk_id"],
                "ciudad": meta[COL_CITY],
                "semana": meta[COL_WEEK],
                "tema": meta[COL_THEME],
                "similitud": round(1 - dist, 3),
                "texto_chunk_completo": doc,
            }
        )

    # --- Búsqueda a nivel MENSAJE (participantes) ---
    res_msgs = coleccion_mensajes.query(
        query_embeddings=emb_codigo.tolist(),
        n_results=N_MENSAJES,
        include=["documents", "metadatas", "distances"],
    )
    for doc, meta, dist in zip(
        res_msgs["documents"][0],
        res_msgs["metadatas"][0],
        res_msgs["distances"][0],
    ):
        resultados_mensajes.append(
            {
                "familia": familia,
                "codigo": codigo,
                "descripcion_codigo": descripcion,
                "id_participante": meta.get(COL_PARTICIPANT_ID, ""),
                "genero": meta.get("genero", ""),
                "ciudad": meta[COL_CITY],
                "semana": meta[COL_WEEK],
                "tema": meta[COL_THEME],
                "similitud": round(1 - dist, 3),
                "mensaje": doc,
            }
        )

# ---------------------------------------------------------------------------
# 7. Guardar en Excel con dos hojas
# ---------------------------------------------------------------------------
print("\nGuardando resultados...")
df_chunks_out = pd.DataFrame(resultados_chunks).sort_values(
    ["codigo", "similitud"], ascending=[True, False]
)
df_msgs_out = pd.DataFrame(resultados_mensajes).sort_values(
    ["codigo", "similitud"], ascending=[True, False]
)

with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
    df_chunks_out.to_excel(writer, sheet_name="Citas_Chunks_Part", index=False)
    df_msgs_out.to_excel(writer, sheet_name=CITATIONS_SHEET, index=False)
    # Ajustar ancho de columna de texto largo para legibilidad
    for sheet_name in ["Citas_Chunks_Part", CITATIONS_SHEET]:
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            max_len = max(
                (len(str(cell.value)) if cell.value else 0 for cell in col), default=0
            )
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 80)

print(f"  Guardado en: {OUT_PATH}")
print(f"  Hoja Citas_Chunks_Part:   {len(df_chunks_out)} filas")
print(f"  Hoja {CITATIONS_SHEET}: {len(df_msgs_out)} filas")

# Vista previa
print("\n=== Vista previa - top mensajes de participantes por familia ===")
for familia in df_msgs_out["familia"].unique():
    top = df_msgs_out[df_msgs_out["familia"] == familia].head(2)
    print(f"\n{familia[:60]}")
    for _, r in top.iterrows():
        print(
            f"  [{r['codigo']}] sim={r['similitud']} | "
            f"{r['ciudad']} s{r['semana']} | {r['tema'][:40]}"
        )
        print(f'  "{r["mensaje"][:100]}"')

print("\nScript 08b completado.")
