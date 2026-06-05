"""Paso 7b: Mapa de similitud semántica - Solo participantes
============================================================
Versión del script 06 que excluye mensajes de facilitadores.
Solo analiza el contenido generado por participantes del programa.

Los chunks se reconstruyen filtrando únicamente mensajes de participantes,
y los embeddings se generan en memoria con sentence-transformers
(no depende de la colección ChromaDB del script 06).

Mismos análisis que 06:
  1. Heatmap de similitud coseno entre chunks (ciudad x semana)
  2. Evolución semántica: trayectorias UMAP + similitud entre semanas consecutivas

Input:
  - data/clean/mensajes_preprocesados.parquet

Output:
  - outputs/figures/06b_similarity_heatmap_participantes.png
  - outputs/figures/06b_semantic_evolution_participantes.png
  - outputs/tables/06b_similarity_matrix_participantes.csv
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import umap
from config_loader import FIGURES_DIR, PROJECT_ROOT, TABLES_DIR, cfg
from matplotlib.lines import Line2D
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
MENSAJES_PATH = PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
OUT_FIGURES = FIGURES_DIR
OUT_TABLES = TABLES_DIR
MODELO_NOMBRE = cfg["models"]["embedding_model"]

CIUDADES_COLORES = cfg["visualization"]["colors"]["cities"]
PROJECT_NAME = cfg["project"]["name"]
COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
CHUNK_GROUPBY = cfg["data"]["chunking"]["groupby"]
IS_LONGITUDINAL = COL_WEEK in CHUNK_GROUPBY
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_THEME = cfg["data"]["columns"]["theme"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]
RANDOM_SEED = cfg["analysis"]["clustering"]["random_seed"]
UMAP_N_NEIGHBORS = cfg["analysis"]["umap"]["n_neighbors"]
UMAP_MIN_DIST = cfg["analysis"]["umap"]["min_dist"]

# ---------------------------------------------------------------------------
# 1. Cargar y filtrar: solo participantes
# ---------------------------------------------------------------------------
print("Cargando mensajes...")
df = pd.read_parquet(MENSAJES_PATH)
df_part = df[df[COL_SENDER] == PARTICIPANT].copy()
print(f"  Total mensajes en dataset: {len(df)}")
print(f"  Mensajes de participantes: {len(df_part)}")
print(f"  Mensajes de facilitadores excluidos: {len(df) - len(df_part)}")

# ---------------------------------------------------------------------------
# 2. Construir chunks (ciudad x semana) solo con mensajes de participantes
# ---------------------------------------------------------------------------
print("\nConstruyendo chunks de participantes (ciudad x semana)...")
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
            **meta,
            COL_THEME: tema,
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

chunks_sorted = chunks.sort_values(CHUNK_GROUPBY).reset_index(drop=True)
order_idx = [ids.index(c) for c in chunks_sorted["chunk_id"]]
sim_ordered = sim_matrix[np.ix_(order_idx, order_idx)]

labels = [
    "_".join(str(r[col]) for col in CHUNK_GROUPBY) for _, r in chunks_sorted.iterrows()
]

sim_df = pd.DataFrame(sim_ordered, index=labels, columns=labels)
sim_df.to_csv(OUT_TABLES / "06b_similarity_matrix_participantes.csv")
print("  Matriz guardada.")

# ---------------------------------------------------------------------------
# 5. Figura 1: Heatmap de similitud
# ---------------------------------------------------------------------------
print("\nGenerando heatmap...")

separadores = []
acum = 0
_primary = CHUNK_GROUPBY[0]
for grp_val in sorted(chunks_sorted[_primary].unique()):
    n = (chunks_sorted[_primary] == grp_val).sum()
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
_primary = CHUNK_GROUPBY[0]
for grp_val in sorted(chunks_sorted[_primary].unique()):
    n = (chunks_sorted[_primary] == grp_val).sum()
    mid = acum + n / 2 - 0.5
    ax.text(
        -1.5,
        mid,
        str(grp_val),
        ha="right",
        va="center",
        fontsize=9,
        fontweight="bold",
        color=CIUDADES_COLORES.get(str(grp_val), "black"),
    )
    acum += n

ax.set_title(
    f"Mapa de similitud semántica entre chunks - Solo participantes\n"
    f"{PROJECT_NAME} ({' x '.join(CHUNK_GROUPBY)})",
    fontsize=13,
    pad=15,
)
plt.tight_layout()
plt.savefig(OUT_FIGURES / "06b_similarity_heatmap_participantes.png", dpi=150)
plt.close()
print("  Heatmap guardado.")

# ---------------------------------------------------------------------------
# 6. Figura 2: Evolución semántica por semana
# ---------------------------------------------------------------------------
if IS_LONGITUDINAL:
    print("\nCalculando evolución semántica...")

    semanas = sorted(chunks[COL_WEEK].unique())
    emb_por_semana = []
    for s in semanas:
        mask = chunks[COL_WEEK] == s
        idx_semana = [ids.index(c) for c in chunks.loc[mask, "chunk_id"]]
        emb_promedio = embeddings[idx_semana].mean(axis=0)
        emb_promedio = emb_promedio / np.linalg.norm(emb_promedio)
        emb_por_semana.append(emb_promedio)

    emb_por_semana = np.array(emb_por_semana)

    reductor = umap.UMAP(
        n_components=cfg["analysis"]["umap"]["n_components"],
        random_state=RANDOM_SEED,
        n_neighbors=UMAP_N_NEIGHBORS,
        min_dist=UMAP_MIN_DIST,
    )
    todos = np.vstack([embeddings, emb_por_semana])
    coords_todos = reductor.fit_transform(todos)
    coords_chunks = coords_todos[: len(embeddings)]

    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    fig.suptitle(
        f"Evolución semántica del programa - Solo participantes - {PROJECT_NAME}",
        fontsize=13,
    )

    ax = axes[0]
    for ciudad, color in CIUDADES_COLORES.items():
        mask = chunks[COL_CITY] == ciudad
        idx_ciudad = [ids.index(c) for c in chunks.loc[mask, "chunk_id"]]
        coords_c = coords_chunks[idx_ciudad]
        semanas_c = chunks.loc[mask, COL_WEEK].values

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

    semanas_pares = [
        f"s{semanas[i]}-s{semanas[i + 1]}" for i in range(len(semanas) - 1)
    ]
    colores_barras = [
        "#D32F2F" if s < np.mean(sim_consecutivas) else "#1976D2"
        for s in sim_consecutivas
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
    plt.savefig(OUT_FIGURES / "06b_semantic_evolution_participantes.png", dpi=150)
    plt.close()
    print("  Figura de evolución guardada.")
else:
    print("  Evolución semántica omitida (datos transversales).")

# ---------------------------------------------------------------------------
# 7. Resumen numérico
# ---------------------------------------------------------------------------
_primary = CHUNK_GROUPBY[0]
grupos = sorted(chunks[_primary].unique())
print(f"\n=== Similitud promedio entre {_primary} (solo participantes) ===")
for g1 in grupos:
    for g2 in grupos:
        if g1 >= g2:
            continue
        idx1 = [ids.index(c) for c in chunks.loc[chunks[_primary] == g1, "chunk_id"]]
        idx2 = [ids.index(c) for c in chunks.loc[chunks[_primary] == g2, "chunk_id"]]
        sim = sim_matrix[np.ix_(idx1, idx2)].mean()
        print(f"  {str(g1):20s} vs {str(g2):20s}: {sim:.3f}")

if IS_LONGITUDINAL:
    print("\n=== Semanas con mayor cambio temático (solo participantes) ===")
    for i, s in sorted(enumerate(sim_consecutivas), key=lambda x: x[1])[:3]:
        print(f"  Semana {semanas[i]} -> {semanas[i + 1]}: similitud {s:.3f}")

print("\nScript 06b completado.")
