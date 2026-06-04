"""Paso 5a: Clustering temático - Programa Apapachar
==================================================
Agrupa los 48 chunks (ciudad x semana) por similitud semántica usando
KMeans sobre los embeddings del Paso 4. Visualiza con UMAP en 2D.

Con 48 chunks el número óptimo de clusters se determina con el método
del codo (inercia) y el silhouette score.

Input:  data/vectorstore/ (ChromaDB) + data/clean/chunks.parquet
Output:
  - outputs/figures/05a_umap_clusters.png
  - outputs/figures/05a_elbow.png
  - outputs/tables/05a_clusters.csv
"""

from __future__ import annotations

import chromadb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from config_loader import DATA_DIR, FIGURES_DIR, TABLES_DIR, cfg
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
VECTORSTORE_PATH = DATA_DIR / cfg["data"]["intermediate"]["vectorstore"]
CHUNKS_PATH = DATA_DIR / "clean" / "chunks.parquet"
OUT_FIGURES = FIGURES_DIR
OUT_TABLES = TABLES_DIR

COLECCION_NOMBRE = cfg["vectordb"]["collection_chunks"]
KMEANS_RANGE = range(
    cfg["analysis"]["clustering"]["kmeans_range"][0],
    cfg["analysis"]["clustering"]["kmeans_range"][1] + 1,
)
KMEANS_N_INIT = cfg["analysis"]["clustering"]["kmeans_n_init"]
RANDOM_SEED = cfg["analysis"]["clustering"]["random_seed"]
UMAP_N_NEIGHBORS = cfg["analysis"]["umap"]["n_neighbors"]
UMAP_MIN_DIST = cfg["analysis"]["umap"]["min_dist"]

# ---------------------------------------------------------------------------
# 1. Cargar embeddings desde ChromaDB
# ---------------------------------------------------------------------------
print("Cargando embeddings desde ChromaDB...")
cliente = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
coleccion = cliente.get_collection(COLECCION_NOMBRE)

resultado = coleccion.get(include=["embeddings", "metadatas"])
embeddings = np.array(resultado["embeddings"])
metadatas = resultado["metadatas"]
ids = resultado["ids"]

print(f"  {len(ids)} chunks cargados. Shape: {embeddings.shape}")

# Normalizar para distancia coseno
embeddings_norm = normalize(embeddings)

# Cargar metadata completa desde parquet (tiene texto_chunk)
chunks = pd.read_parquet(CHUNKS_PATH)
chunks = chunks.set_index("chunk_id").loc[ids].reset_index()

# ---------------------------------------------------------------------------
# 2. Método del codo + silhouette para elegir k
# ---------------------------------------------------------------------------
print(
    f"\nCalculando método del codo y silhouette (k={KMEANS_RANGE.start} a {KMEANS_RANGE.stop - 1})..."
)
rango_k = KMEANS_RANGE
inercias = []
silhouettes = []

for k in rango_k:
    km = KMeans(n_clusters=k, random_state=RANDOM_SEED, n_init=KMEANS_N_INIT)
    etiquetas = km.fit_predict(embeddings_norm)
    inercias.append(km.inertia_)
    silhouettes.append(silhouette_score(embeddings_norm, etiquetas))
    print(
        f"  k={k}: inercia={km.inertia_:.3f}, silhouette={silhouette_score(embeddings_norm, etiquetas):.3f}"
    )

k_optimo = rango_k[silhouettes.index(max(silhouettes))]
print(f"\n  k optimo por silhouette: {k_optimo}")

# Figura: método del codo
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
axes[0].plot(list(rango_k), inercias, "o-", color="#1976D2")
axes[0].set_xlabel("Número de clusters (k)")
axes[0].set_ylabel("Inercia")
axes[0].set_title("Método del codo")
axes[0].axvline(
    k_optimo, color="#D32F2F", linestyle="--", label=f"k óptimo = {k_optimo}"
)
axes[0].legend()

axes[1].plot(list(rango_k), silhouettes, "o-", color="#388E3C")
axes[1].set_xlabel("Número de clusters (k)")
axes[1].set_ylabel("Silhouette score")
axes[1].set_title("Silhouette score")
axes[1].axvline(
    k_optimo, color="#D32F2F", linestyle="--", label=f"k óptimo = {k_optimo}"
)
axes[1].legend()

plt.tight_layout()
plt.savefig(OUT_FIGURES / "05a_elbow.png", dpi=150)
plt.close()
print("  Figura del codo guardada.")

# ---------------------------------------------------------------------------
# 3. KMeans con k óptimo
# ---------------------------------------------------------------------------
print(f"\nAplicando KMeans con k={k_optimo}...")
kmeans = KMeans(n_clusters=k_optimo, random_state=RANDOM_SEED, n_init=KMEANS_N_INIT)
chunks["cluster"] = kmeans.fit_predict(embeddings_norm)

print("\n=== Distribución de chunks por cluster ===")
for c in sorted(chunks["cluster"].unique()):
    grupo = chunks[chunks["cluster"] == c]
    temas = grupo["tema"].value_counts().index[:2].tolist()
    print(f"  Cluster {c} ({len(grupo)} chunks): {' | '.join([t[:40] for t in temas])}")

# ---------------------------------------------------------------------------
# 4. UMAP: reducir a 2D para visualizar
# ---------------------------------------------------------------------------
print("\nReduciendo a 2D con UMAP...")
reductor = umap.UMAP(
    n_components=cfg["analysis"]["umap"]["n_components"],
    random_state=RANDOM_SEED,
    n_neighbors=UMAP_N_NEIGHBORS,
    min_dist=UMAP_MIN_DIST,
)
coords_2d = reductor.fit_transform(embeddings_norm)

chunks["umap_x"] = coords_2d[:, 0]
chunks["umap_y"] = coords_2d[:, 1]

# ---------------------------------------------------------------------------
# 5. Figura UMAP con clusters
# ---------------------------------------------------------------------------
colores = [
    "#1976D2",
    "#388E3C",
    "#F57C00",
    "#7B1FA2",
    "#D32F2F",
    "#0097A7",
    "#795548",
    "#FBC02D",
    "#455A64",
    "#E91E63",
]

fig, ax = plt.subplots(figsize=(13, 8))

for c in sorted(chunks["cluster"].unique()):
    mask = chunks["cluster"] == c
    ax.scatter(
        chunks.loc[mask, "umap_x"],
        chunks.loc[mask, "umap_y"],
        c=colores[c % len(colores)],
        label=f"Cluster {c}",
        s=120,
        alpha=0.85,
        edgecolors="white",
        linewidths=0.5,
    )

# Etiquetar cada punto con chunk_id
for _, row in chunks.iterrows():
    ax.annotate(
        row["chunk_id"],
        (row["umap_x"], row["umap_y"]),
        fontsize=6.5,
        ha="center",
        va="bottom",
        xytext=(0, 5),
        textcoords="offset points",
    )

ax.set_title(
    "Clustering temático de chunks - Programa Apapachar\n"
    f"KMeans k={k_optimo} | UMAP 2D | 48 chunks (ciudad x semana)",
    fontsize=12,
)
ax.set_xlabel("UMAP dimensión 1")
ax.set_ylabel("UMAP dimensión 2")
ax.legend(title="Cluster", loc="upper right", fontsize=9)
plt.tight_layout()
plt.savefig(OUT_FIGURES / "05a_umap_clusters.png", dpi=150)
plt.close()
print("  Figura UMAP guardada.")

# ---------------------------------------------------------------------------
# 6. Guardar tabla de clusters
# ---------------------------------------------------------------------------
cols_guardar = [
    "chunk_id",
    "city_grupo",
    "n_week",
    "tema",
    "n_mensajes",
    "n_participante",
    "tokens_aprox",
    "cluster",
    "umap_x",
    "umap_y",
]
chunks[cols_guardar].to_csv(OUT_TABLES / "05a_clusters.csv", index=False)
print("  Tabla guardada en outputs/tables/05a_clusters.csv")

print("\nPaso 5a completado.")
