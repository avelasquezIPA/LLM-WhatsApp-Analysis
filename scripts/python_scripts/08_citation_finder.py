"""Análisis semántico complementario - Programa Apapachar
=======================================================
Script 2 de 2: Buscador de citas por código cualitativo.

Para cada código del árbol de análisis, encuentra los mensajes
de WhatsApp más semánticamente relevantes como citas potenciales.

Dos niveles de búsqueda:
  - Chunk: grupo completo (ciudad x semana) más relevante
  - Mensaje: mensajes individuales más relevantes

100% local. No requiere API key.

Input:
  - documentation/A+P_2025_Arbol de códigos.xlsx
  - data/vectorstore/ (ChromaDB - chunks)
  - data/clean/mensajes_preprocesados.parquet (mensajes individuales)

Output:
  - outputs/tables/08_citas_por_codigo.xlsx
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
VECTORSTORE_PATH = DATA_DIR / cfg["data"]["intermediate"]["vectorstore"]
MENSAJES_PATH = PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
OUT_PATH = TABLES_DIR / "08_citas_por_codigo.xlsx"

MODELO_NOMBRE = cfg["models"]["embedding_model"]
N_CHUNKS = cfg["analysis"]["citation_search"]["top_k_chunks"]
N_MENSAJES = cfg["analysis"]["citation_search"]["top_k_messages"]
MIN_MSG_WORDS = cfg["analysis"]["citation_search"]["min_message_words"]
FAMILIAS_REL = cfg["analysis"]["citation_search"]["relevant_families"]

COLECCION_CHUNKS = cfg["vectordb"]["collection_chunks"]
COLECCION_MENSAJES = cfg["vectordb"]["collection_messages"]

COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_THEME = cfg["data"]["columns"]["theme"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_NWORDS = cfg["data"]["columns"]["word_count"]

ARBOL_SHEET = cfg["data"]["input"]["coding_tree_sheet"]

# ---------------------------------------------------------------------------
# 1. Cargar árbol de códigos
# ---------------------------------------------------------------------------
print("Cargando árbol de códigos...")
df_arbol = pd.read_excel(ARBOL_PATH, sheet_name=ARBOL_SHEET)
df_arbol.columns = ["_", "familia", "codigo", "descripcion", "subcod", "cambios"]
df_arbol = df_arbol[["familia", "codigo", "descripcion"]].dropna(subset=["codigo"])

# Excluir encabezados y llenar familia hacia abajo
df_arbol = df_arbol[df_arbol["codigo"].str.startswith("[")]
df_arbol["familia"] = df_arbol["familia"].ffill()

print(f"  {len(df_arbol)} códigos cargados.")
print(f"  Familias: {df_arbol['familia'].nunique()}")

# Filtrar solo familias relevantes para mensajes de WA
mask_relevante = df_arbol["familia"].str.contains(
    "|".join([f[:10] for f in FAMILIAS_REL]), na=False
)
df_relevante = df_arbol[mask_relevante].copy()
print(f"  Códigos en familias relevantes: {len(df_relevante)}")

# ---------------------------------------------------------------------------
# 2. Cargar modelo y embeddings de chunks
# ---------------------------------------------------------------------------
print("\nCargando modelo de embeddings...")
modelo = SentenceTransformer(MODELO_NOMBRE)

print("Conectando a ChromaDB...")
cliente = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
coleccion_chunks = cliente.get_collection(COLECCION_CHUNKS)

# ---------------------------------------------------------------------------
# 3. Crear colección de mensajes individuales (si no existe)
# ---------------------------------------------------------------------------
try:
    coleccion_mensajes = cliente.get_collection(COLECCION_MENSAJES)
    print(f"Colección de mensajes existente: {coleccion_mensajes.count()} mensajes.")
except Exception:
    print("Creando colección de mensajes individuales...")
    df_msgs = pd.read_parquet(MENSAJES_PATH)

    # Solo mensajes con contenido suficiente
    df_msgs[COL_NWORDS] = df_msgs[COL_TEXT].str.split().str.len()
    df_msgs = df_msgs[df_msgs[COL_NWORDS] >= MIN_MSG_WORDS].reset_index(drop=True)
    print(f"  Mensajes a indexar: {len(df_msgs)}")

    # Generar embeddings por lotes
    print("  Generando embeddings de mensajes (puede tomar 1-2 min)...")
    emb_msgs = modelo.encode(
        df_msgs[COL_TEXT].tolist(),
        show_progress_bar=True,
        batch_size=64,
    )

    # Guardar en ChromaDB
    coleccion_mensajes = cliente.create_collection(
        name=COLECCION_MENSAJES,
        metadata={"hnsw:space": "cosine"},
    )

    # Insertar en lotes
    batch_size = cfg["analysis"]["vectordb_batch_size"]
    for i in range(0, len(df_msgs), batch_size):
        batch = df_msgs.iloc[i : i + batch_size]
        emb_batch = emb_msgs[i : i + batch_size]
        coleccion_mensajes.add(
            documents=batch[COL_TEXT].tolist(),
            embeddings=emb_batch.tolist(),
            metadatas=[
                {
                    COL_SENDER: str(r[COL_SENDER]),
                    COL_CITY: str(r[COL_CITY]),
                    COL_WEEK: int(r[COL_WEEK]),
                    COL_THEME: str(r[COL_THEME]),
                    COL_DATETIME: str(r[COL_DATETIME]),
                }
                for _, r in batch.iterrows()
            ],
            ids=[f"msg_{i + j}" for j in range(len(batch))],
        )
    print(f"  {coleccion_mensajes.count()} mensajes indexados.")

# ---------------------------------------------------------------------------
# 4. Buscar citas por código
# ---------------------------------------------------------------------------
print(f"\nBuscando citas para {len(df_relevante)} códigos...")
print(f"  Nivel chunk: top {N_CHUNKS} | Nivel mensaje: top {N_MENSAJES}")

resultados_chunks = []
resultados_mensajes = []

for i, (_, row) in enumerate(df_relevante.iterrows(), 1):
    codigo = row["codigo"]
    descripcion = str(row["descripcion"])
    familia = str(row["familia"])

    print(f"  [{i:02d}/{len(df_relevante)}] {codigo} - {descripcion[:50]}...")

    # Embedding de la descripción del código
    emb_codigo = modelo.encode([descripcion])

    # --- Búsqueda a nivel CHUNK ---
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
        # Extracto del chunk (primeras 300 chars para no saturar el Excel)
        extracto = doc[:300] + "..." if len(doc) > 300 else doc
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
                "extracto_chunk": extracto,
            }
        )

    # --- Búsqueda a nivel MENSAJE ---
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
                "remitente": meta[COL_SENDER],
                "ciudad": meta[COL_CITY],
                "semana": meta[COL_WEEK],
                "tema": meta[COL_THEME],
                "similitud": round(1 - dist, 3),
                "mensaje": doc,
            }
        )

# ---------------------------------------------------------------------------
# 5. Guardar en Excel con dos hojas
# ---------------------------------------------------------------------------
print("\nGuardando resultados...")
df_chunks_out = pd.DataFrame(resultados_chunks).sort_values(
    ["codigo", "similitud"], ascending=[True, False]
)
df_msgs_out = pd.DataFrame(resultados_mensajes).sort_values(
    ["codigo", "similitud"], ascending=[True, False]
)

with pd.ExcelWriter(OUT_PATH, engine="openpyxl") as writer:
    df_chunks_out.to_excel(writer, sheet_name="Citas_Chunks", index=False)
    df_msgs_out.to_excel(writer, sheet_name="Citas_Mensajes", index=False)

print(f"  Guardado en: {OUT_PATH}")
print(f"  Hoja Citas_Chunks:   {len(df_chunks_out)} filas")
print(f"  Hoja Citas_Mensajes: {len(df_msgs_out)} filas")

# Vista previa
print("\n=== Vista previa - top mensajes por familia ===")
for familia in df_msgs_out["familia"].unique():
    top = df_msgs_out[df_msgs_out["familia"] == familia].head(2)
    print(f"\n{familia[:50]}")
    for _, r in top.iterrows():
        print(
            f"  [{r['codigo']}] sim={r['similitud']} | {r['ciudad']} s{r['semana']} | {r['remitente']}"
        )
        print(f'  "{r["mensaje"][:100]}"')

print("\nScript 08 completado.")
