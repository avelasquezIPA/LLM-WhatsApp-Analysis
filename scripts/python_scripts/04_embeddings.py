"""Paso 4: Embeddings y almacenamiento vectorial - Programa Apapachar
===================================================================
Genera embeddings para cada chunk usando sentence-transformers
(modelo multilingüe, corre localmente, sin enviar datos a servidores)
y los almacena en ChromaDB (base vectorial local en disco).

Modelo: paraphrase-multilingual-mpnet-base-v2
  - Gratuito, local (~400MB descarga única)
  - Entrenado en 50+ idiomas incluyendo español
  - Dimensión del vector: 768

Input:  data/clean/chunks.parquet
Output: data/vectorstore/  (ChromaDB persistente en disco)

Privacidad: 100% local. Ningún dato sale a servidores externos.
"""

from __future__ import annotations

import chromadb
import pandas as pd
from config_loader import DATA_DIR, cfg
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
DATA_PATH = DATA_DIR / "clean" / "chunks.parquet"
VECTORSTORE_PATH = DATA_DIR / cfg["data"]["intermediate"]["vectorstore"]

MODELO_NOMBRE = cfg["models"]["embedding_model"]
COLECCION_NOMBRE = cfg["vectordb"]["collection_chunks"]
BATCH_SIZE = cfg["analysis"]["embedding_batch_size"]
DISTANCE_METRIC = cfg["vectordb"]["distance_metric"]

COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_THEME = cfg["data"]["columns"]["theme"]

VECTORSTORE_PATH.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Carga de chunks
# ---------------------------------------------------------------------------
print("Cargando chunks...")
chunks = pd.read_parquet(DATA_PATH)
print(f"  Total chunks: {len(chunks)}")
print(f"  Tokens totales: {chunks['tokens_aprox'].sum():,}")

# ---------------------------------------------------------------------------
# 2. Modelo de embeddings
# ---------------------------------------------------------------------------
print(f"\nCargando modelo '{MODELO_NOMBRE}'...")
print("  (Primera vez: descarga ~400MB. Siguientes veces: carga local instantánea)")
modelo = SentenceTransformer(MODELO_NOMBRE)
print("  Modelo listo.")

# ---------------------------------------------------------------------------
# 3. Generar embeddings
# ---------------------------------------------------------------------------
print("\nGenerando embeddings...")
print("  Cada chunk se convierte en un vector de 768 dimensiones.")

embeddings = modelo.encode(
    chunks["texto_chunk"].tolist(),
    show_progress_bar=True,
    batch_size=BATCH_SIZE,
)
print(f"  Shape de la matriz de embeddings: {embeddings.shape}")

# ---------------------------------------------------------------------------
# 4. Almacenar en ChromaDB
# ---------------------------------------------------------------------------
print("\nAlmacenando en ChromaDB...")

cliente = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))

# Eliminar colección anterior si existe (para re-runs limpios)
try:
    cliente.delete_collection(COLECCION_NOMBRE)
    print("  Colección anterior eliminada.")
except Exception:
    pass

coleccion = cliente.create_collection(
    name=COLECCION_NOMBRE,
    metadata={"hnsw:space": DISTANCE_METRIC},
)

coleccion.add(
    documents=chunks["texto_chunk"].tolist(),
    embeddings=embeddings.tolist(),
    metadatas=[
        {
            "chunk_id": row["chunk_id"],
            COL_CITY: str(row[COL_CITY]),
            COL_WEEK: int(row[COL_WEEK]),
            COL_THEME: str(row[COL_THEME]),
            "n_mensajes": int(row["n_mensajes"]),
            "n_participante": int(row["n_participante"]),
            "tokens_aprox": int(row["tokens_aprox"]),
        }
        for _, row in chunks.iterrows()
    ],
    ids=chunks["chunk_id"].tolist(),
)

print(f"  {coleccion.count()} chunks almacenados en ChromaDB.")
print(f"  Vectorstore guardado en: {VECTORSTORE_PATH}")

# ---------------------------------------------------------------------------
# 5. Verificación: búsqueda semántica de prueba
# ---------------------------------------------------------------------------
print("\n=== Verificación: búsqueda semántica de prueba ===")
consultas = [
    "crianza positiva y emociones",
    "violencia intrafamiliar",
    "participación de los padres",
]

for consulta in consultas:
    embedding_consulta = modelo.encode([consulta])
    resultados = coleccion.query(
        query_embeddings=embedding_consulta.tolist(),
        n_results=2,
    )
    print(f"\nConsulta: '{consulta}'")
    for chunk_id, meta, distancia in zip(
        resultados["ids"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        print(f"  -> {chunk_id} | {meta['tema'][:50]} | similitud: {1 - distancia:.3f}")

print("\nPaso 4 completado.")
