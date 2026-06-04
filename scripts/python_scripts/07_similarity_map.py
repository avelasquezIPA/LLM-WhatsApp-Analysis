"""Análisis semántico complementario - Programa Apapachar
=======================================================
Script 1 de 2: Mapa de similitud entre chunks y evolución semántica.

1. Heatmap de similitud coseno entre los 48 chunks (ciudad x semana)
   ¿Qué semanas/ciudades hablan de cosas parecidas?

2. Evolución semántica por semana
   ¿Cómo cambia el contenido temático a lo largo del programa?
   ¿Convergen las ciudades hacia el final?

Input:  data/vectorstore/ (ChromaDB)
Output:
  - outputs/figures/07_similarity_heatmap.png
  - outputs/figures/07_semantic_evolution.png
  - outputs/tables/07_similarity_matrix.csv
"""

from __future__ import annotations

from pathlib import Path

import chromadb
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from matplotlib.lines import Line2D
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
VECTORSTORE_PATH = ROOT / "data" / "vectorstore"
CHUNKS_PATH = ROOT / "data" / "clean" / "chunks.parquet"
OUT_FIGURES = ROOT / "outputs" / "figures"
OUT_TABLES = ROOT / "outputs" / "tables"

CIUDADES_COLORES = {
    "Bogota": "#1976D2",
    "Soacha": "#388E3C",
    "Neiva": "#F57C00",
    "Valledupar": "#7B1FA2",
}

# ---------------------------------------------------------------------------
# 1. Cargar embeddings
# ---------------------------------------------------------------------------
print("Cargando embeddings...")
cliente = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
coleccion = cliente.get_collection("apapachar_chunks")
resultado = coleccion.get(include=["embeddings", "metadatas"])

embeddings = normalize(np.array(resultado["embeddings"]))
ids = resultado["ids"]

chunks = pd.read_parquet(CHUNKS_PATH)
chunks = chunks.set_index("chunk_id").loc[ids].reset_index()

print(f"  {len(chunks)} chunks cargados.")

# ---------------------------------------------------------------------------
# 2. Matriz de similitud coseno (48 x 48)
# ---------------------------------------------------------------------------
print("\nCalculando matriz de similitud...")
sim_matrix = cosine_similarity(embeddings)

# Ordenar por ciudad + semana para que el heatmap tenga sentido
chunks_sorted = chunks.sort_values(["city_grupo", "n_week"]).reset_index(drop=True)
order_idx = [ids.index(c) for c in chunks_sorted["chunk_id"]]
sim_ordered = sim_matrix[np.ix_(order_idx, order_idx)]

# Etiquetas cortas para los ejes
labels = [
    f"{r['city_grupo'][:3]}_s{r['n_week']:02d}" for _, r in chunks_sorted.iterrows()
]

# Guardar matriz
sim_df = pd.DataFrame(sim_ordered, index=labels, columns=labels)
sim_df.to_csv(OUT_TABLES / "07_similarity_matrix.csv")
print("  Matriz guardada.")

# ---------------------------------------------------------------------------
# 3. Figura 1: Heatmap de similitud
# ---------------------------------------------------------------------------
print("\nGenerando heatmap...")

# Separadores entre ciudades
ciudad_counts = chunks_sorted["city_grupo"].value_counts().sort_index()
separadores = []
acum = 0
for ciudad in sorted(chunks_sorted["city_grupo"].unique()):
    n = (chunks_sorted["city_grupo"] == ciudad).sum()
    acum += n
    separadores.append(acum)

fig, ax = plt.subplots(figsize=(14, 12))
im = ax.imshow(sim_ordered, cmap="YlOrRd", vmin=0.0, vmax=1.0, aspect="auto")
plt.colorbar(im, ax=ax, label="Similitud coseno", shrink=0.8)

# Líneas divisoras entre ciudades
for sep in separadores[:-1]:
    ax.axhline(sep - 0.5, color="white", linewidth=2)
    ax.axvline(sep - 0.5, color="white", linewidth=2)

ax.set_xticks(range(len(labels)))
ax.set_yticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=90, fontsize=7)
ax.set_yticklabels(labels, fontsize=7)

# Etiquetas de ciudad en los ejes
acum = 0
for ciudad in sorted(chunks_sorted["city_grupo"].unique()):
    n = (chunks_sorted["city_grupo"] == ciudad).sum()
    mid = acum + n / 2 - 0.5
    ax.text(
        -1.5,
        mid,
        ciudad,
        ha="right",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=CIUDADES_COLORES.get(ciudad, "black"),
    )
    acum += n

ax.set_title(
    "Mapa de similitud semántica entre chunks\nPrograma Apapachar (ciudad x semana)",
    fontsize=13,
    pad=15,
)
plt.tight_layout()
plt.savefig(OUT_FIGURES / "07_similarity_heatmap.png", dpi=150)
plt.close()
print("  Heatmap guardado.")

# ---------------------------------------------------------------------------
# 4. Figura 2: Evolución semántica por semana
# ---------------------------------------------------------------------------
print("\nCalculando evolución semántica...")

# Embedding promedio por semana (promedio entre ciudades)
semanas = sorted(chunks["n_week"].unique())
emb_por_semana = []
for s in semanas:
    mask = chunks["n_week"] == s
    idx_semana = [ids.index(c) for c in chunks.loc[mask, "chunk_id"]]
    emb_promedio = embeddings[idx_semana].mean(axis=0)
    emb_promedio = emb_promedio / np.linalg.norm(emb_promedio)
    emb_por_semana.append(emb_promedio)

emb_por_semana = np.array(emb_por_semana)

# Embedding por ciudad x semana para UMAP
reductor = umap.UMAP(n_components=2, random_state=42, n_neighbors=8, min_dist=0.2)
# Reducir todos los embeddings juntos para consistencia
todos = np.vstack([embeddings, emb_por_semana])
coords_todos = reductor.fit_transform(todos)
coords_chunks = coords_todos[: len(embeddings)]
coords_semanas = coords_todos[len(embeddings) :]

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Evolución semántica del programa - Apapachar", fontsize=13)

# Panel izq: trayectoria por ciudad
ax = axes[0]
for ciudad, color in CIUDADES_COLORES.items():
    mask = chunks["city_grupo"] == ciudad
    idx_ciudad = [ids.index(c) for c in chunks.loc[mask, "chunk_id"]]
    coords_c = coords_chunks[idx_ciudad]
    semanas_c = chunks.loc[mask, "n_week"].values

    order = np.argsort(semanas_c)
    x, y = coords_c[order, 0], coords_c[order, 1]
    s_ord = semanas_c[order]

    ax.plot(x, y, "-", color=color, alpha=0.5, linewidth=1.2)
    sc = ax.scatter(
        x,
        y,
        c=s_ord,
        cmap="plasma",
        s=80,
        edgecolors=color,
        linewidths=1.5,
        zorder=3,
        vmin=1,
        vmax=12,
    )
    # Etiquetar semana 1 y 12
    ax.annotate(
        f"{ciudad[:3]} s1",
        (x[0], y[0]),
        fontsize=7,
        xytext=(4, 4),
        textcoords="offset points",
        color=color,
    )
    ax.annotate(
        "s12",
        (x[-1], y[-1]),
        fontsize=7,
        xytext=(4, -8),
        textcoords="offset points",
        color=color,
    )

plt.colorbar(sc, ax=ax, label="Semana")
ax.set_title("Trayectoria semántica por ciudad")
ax.set_xlabel("UMAP dim 1")
ax.set_ylabel("UMAP dim 2")

# Leyenda de ciudades
legend_elements = [
    Line2D([0], [0], color=c, linewidth=2, label=ciudad)
    for ciudad, c in CIUDADES_COLORES.items()
]
ax.legend(handles=legend_elements, fontsize=8, loc="upper right")

# Panel derecho: similitud entre semanas consecutivas
ax2 = axes[1]
sim_consecutivas = []
for i in range(len(emb_por_semana) - 1):
    s = cosine_similarity([emb_por_semana[i]], [emb_por_semana[i + 1]])[0][0]
    sim_consecutivas.append(s)

semanas_pares = [f"s{semanas[i]}-s{semanas[i + 1]}" for i in range(len(semanas) - 1)]
colores_barras = [
    "#D32F2F" if s < np.mean(sim_consecutivas) else "#1976D2" for s in sim_consecutivas
]

ax2.bar(
    range(len(sim_consecutivas)),
    sim_consecutivas,
    color=colores_barras,
    edgecolor="white",
)
ax2.axhline(
    np.mean(sim_consecutivas),
    color="gray",
    linestyle="--",
    linewidth=1,
    label=f"Media: {np.mean(sim_consecutivas):.3f}",
)
ax2.set_xticks(range(len(semanas_pares)))
ax2.set_xticklabels(semanas_pares, rotation=45, fontsize=8)
ax2.set_ylabel("Similitud coseno")
ax2.set_title(
    "Similitud semántica entre semanas consecutivas\n(promedio entre ciudades)"
)
ax2.set_ylim(0, 1)
ax2.legend(fontsize=8)

# Anotar caídas notables
for i, s in enumerate(sim_consecutivas):
    if s < np.mean(sim_consecutivas) - np.std(sim_consecutivas):
        ax2.annotate(
            "cambio\ntemático",
            (i, s),
            fontsize=7,
            ha="center",
            va="top",
            xytext=(0, -25),
            textcoords="offset points",
            color="#D32F2F",
        )

plt.tight_layout()
plt.savefig(OUT_FIGURES / "07_semantic_evolution.png", dpi=150)
plt.close()
print("  Figura de evolución guardada.")

# ---------------------------------------------------------------------------
# 5. Resumen numérico
# ---------------------------------------------------------------------------
print("\n=== Similitud promedio entre ciudades ===")
for c1 in sorted(CIUDADES_COLORES):
    for c2 in sorted(CIUDADES_COLORES):
        if c1 >= c2:
            continue
        idx1 = [
            ids.index(c) for c in chunks.loc[chunks["city_grupo"] == c1, "chunk_id"]
        ]
        idx2 = [
            ids.index(c) for c in chunks.loc[chunks["city_grupo"] == c2, "chunk_id"]
        ]
        sim = sim_matrix[np.ix_(idx1, idx2)].mean()
        print(f"  {c1:12s} vs {c2:12s}: {sim:.3f}")

print("\n=== Semanas con mayor cambio temático ===")
for i, s in sorted(enumerate(sim_consecutivas), key=lambda x: x[1])[:3]:
    print(f"  Semana {semanas[i]} -> {semanas[i + 1]}: similitud {s:.3f}")

print("\nScript 07 completado.")
