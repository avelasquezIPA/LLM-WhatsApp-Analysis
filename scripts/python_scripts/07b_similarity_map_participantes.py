"""Paso 7b: Mapa de similitud semántica - Solo participantes
============================================================
Versión del script 07 que excluye mensajes de facilitadores.
Solo analiza el contenido generado por participantes del programa.

Los chunks se reconstruyen filtrando únicamente mensajes de participantes,
y los embeddings se generan en memoria con sentence-transformers
(no depende de la colección ChromaDB del script 07).

Mismos análisis que 07:
  1. Heatmap de similitud coseno entre chunks (ciudad x semana)
  2. Evolución semántica: trayectorias UMAP + similitud entre semanas consecutivas

Input:
  - data/clean/mensajes_preprocesados.parquet

Output:
  - outputs/figures/07b_similarity_heatmap_participantes.png
  - outputs/figures/07b_semantic_evolution_participantes.png
  - outputs/tables/07b_similarity_matrix_participantes.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from matplotlib.lines import Line2D
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
MENSAJES_PATH = ROOT / "data" / "clean" / "mensajes_preprocesados.parquet"
OUT_FIGURES = ROOT / "outputs" / "figures"
OUT_TABLES = ROOT / "outputs" / "tables"
MODELO_NOMBRE = "paraphrase-multilingual-mpnet-base-v2"

CIUDADES_COLORES = {
    "Bogota": "#1976D2",
    "Soacha": "#388E3C",
    "Neiva": "#F57C00",
    "Valledupar": "#7B1FA2",
}

# ---------------------------------------------------------------------------
# 1. Cargar y filtrar: solo participantes
# ---------------------------------------------------------------------------
print("Cargando mensajes...")
df = pd.read_parquet(MENSAJES_PATH)
df_part = df[df["remitente"] == "Participante"].copy()
print(f"  Total mensajes en dataset: {len(df)}")
print(f"  Mensajes de participantes: {len(df_part)}")
print(f"  Mensajes de facilitadores excluidos: {len(df) - len(df_part)}")

# ---------------------------------------------------------------------------
# 2. Construir chunks (ciudad x semana) solo con mensajes de participantes
# ---------------------------------------------------------------------------
print("\nConstruyendo chunks de participantes (ciudad x semana)...")
registros = []
for (ciudad, semana), grupo in df_part.groupby(["city_grupo", "n_week"], observed=True):
    grupo = grupo.sort_values("datetime").reset_index(drop=True)
    lineas = [f"[{i + 1}] {row['texto']}" for i, row in grupo.iterrows()]
    texto_chunk = "\n".join(lineas)
    tema = grupo["tema"].iloc[0] if "tema" in grupo.columns else ""
    registros.append(
        {
            "chunk_id": f"{ciudad}_s{semana:02d}",
            "city_grupo": ciudad,
            "n_week": semana,
            "tema": tema,
            "n_mensajes": len(grupo),
            "texto_chunk": texto_chunk,
        }
    )

chunks = pd.DataFrame(registros)
print(f"  Total chunks: {len(chunks)}")
print(
    f"  Mensajes por chunk: min={chunks['n_mensajes'].min()}, "
    f"mediana={chunks['n_mensajes'].median():.0f}, "
    f"max={chunks['n_mensajes'].max()}"
)

# ---------------------------------------------------------------------------
# 3. Generar embeddings (en memoria, sin ChromaDB)
# ---------------------------------------------------------------------------
print("\nCargando modelo de embeddings...")
modelo = SentenceTransformer(MODELO_NOMBRE)

print("Generando embeddings de chunks de participantes...")
embeddings_raw = modelo.encode(
    chunks["texto_chunk"].tolist(),
    show_progress_bar=True,
    batch_size=8,
)
embeddings = normalize(np.array(embeddings_raw))
ids = chunks["chunk_id"].tolist()
print(f"  {len(ids)} embeddings generados ({embeddings.shape[1]} dimensiones).")

# ---------------------------------------------------------------------------
# 4. Matriz de similitud coseno (48 x 48)
# ---------------------------------------------------------------------------
print("\nCalculando matriz de similitud...")
sim_matrix = cosine_similarity(embeddings)

chunks_sorted = chunks.sort_values(["city_grupo", "n_week"]).reset_index(drop=True)
order_idx = [ids.index(c) for c in chunks_sorted["chunk_id"]]
sim_ordered = sim_matrix[np.ix_(order_idx, order_idx)]

labels = [
    f"{r['city_grupo'][:3]}_s{r['n_week']:02d}" for _, r in chunks_sorted.iterrows()
]

sim_df = pd.DataFrame(sim_ordered, index=labels, columns=labels)
sim_df.to_csv(OUT_TABLES / "07b_similarity_matrix_participantes.csv")
print("  Matriz guardada.")

# ---------------------------------------------------------------------------
# 5. Figura 1: Heatmap de similitud
# ---------------------------------------------------------------------------
print("\nGenerando heatmap...")

separadores = []
acum = 0
for ciudad in sorted(chunks_sorted["city_grupo"].unique()):
    n = (chunks_sorted["city_grupo"] == ciudad).sum()
    acum += n
    separadores.append(acum)

fig, ax = plt.subplots(figsize=(14, 12))
im = ax.imshow(sim_ordered, cmap="YlOrRd", vmin=0.0, vmax=1.0, aspect="auto")
plt.colorbar(im, ax=ax, label="Similitud coseno", shrink=0.8)

for sep in separadores[:-1]:
    ax.axhline(sep - 0.5, color="white", linewidth=2)
    ax.axvline(sep - 0.5, color="white", linewidth=2)

ax.set_xticks(range(len(labels)))
ax.set_yticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=90, fontsize=7)
ax.set_yticklabels(labels, fontsize=7)

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
    "Mapa de similitud semántica entre chunks - Solo participantes\n"
    "Programa Apapachar (ciudad x semana)",
    fontsize=13,
    pad=15,
)
plt.tight_layout()
plt.savefig(OUT_FIGURES / "07b_similarity_heatmap_participantes.png", dpi=150)
plt.close()
print("  Heatmap guardado.")

# ---------------------------------------------------------------------------
# 6. Figura 2: Evolución semántica por semana
# ---------------------------------------------------------------------------
print("\nCalculando evolución semántica...")

semanas = sorted(chunks["n_week"].unique())
emb_por_semana = []
for s in semanas:
    mask = chunks["n_week"] == s
    idx_semana = [ids.index(c) for c in chunks.loc[mask, "chunk_id"]]
    emb_promedio = embeddings[idx_semana].mean(axis=0)
    emb_promedio = emb_promedio / np.linalg.norm(emb_promedio)
    emb_por_semana.append(emb_promedio)

emb_por_semana = np.array(emb_por_semana)

reductor = umap.UMAP(n_components=2, random_state=42, n_neighbors=8, min_dist=0.2)
todos = np.vstack([embeddings, emb_por_semana])
coords_todos = reductor.fit_transform(todos)
coords_chunks = coords_todos[: len(embeddings)]

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle(
    "Evolución semántica del programa - Solo participantes - Apapachar",
    fontsize=13,
)

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
ax.set_title("Trayectoria semántica por ciudad\n(solo participantes)")
ax.set_xlabel("UMAP dim 1")
ax.set_ylabel("UMAP dim 2")

legend_elements = [
    Line2D([0], [0], color=c, linewidth=2, label=ciudad)
    for ciudad, c in CIUDADES_COLORES.items()
]
ax.legend(handles=legend_elements, fontsize=8, loc="upper right")

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
    "Similitud semántica entre semanas consecutivas\n"
    "(solo participantes, promedio entre ciudades)"
)
ax2.set_ylim(0, 1)
ax2.legend(fontsize=8)

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
plt.savefig(OUT_FIGURES / "07b_semantic_evolution_participantes.png", dpi=150)
plt.close()
print("  Figura de evolución guardada.")

# ---------------------------------------------------------------------------
# 7. Resumen numérico
# ---------------------------------------------------------------------------
print("\n=== Similitud promedio entre ciudades (solo participantes) ===")
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

print("\n=== Semanas con mayor cambio temático (solo participantes) ===")
for i, s in sorted(enumerate(sim_consecutivas), key=lambda x: x[1])[:3]:
    print(f"  Semana {semanas[i]} -> {semanas[i + 1]}: similitud {s:.3f}")

print("\nScript 07b completado.")
