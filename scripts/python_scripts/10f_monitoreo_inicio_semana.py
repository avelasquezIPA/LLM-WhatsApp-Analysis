"""10f_monitoreo_inicio_semana.py
=================================
Analiza si la rapidez de la primera respuesta de participantes al
inicio de cada semana predice el nivel de interaccion P-P de esa semana.

Logica: el facilitador abre la semana con el primer mensaje. Si los
participantes responden rapido (pocas horas), la semana tiene mas
sesiones P-P. Si no responden el mismo dia, el engagement cae.

Esto NO es circular: el tiempo de respuesta se mide ANTES de que
ocurran (o no) las sesiones P-P. Es un predictor temporal genuino.

Outputs:
  - outputs/figures/10f_monitoreo_inicio_semana.png
  - outputs/tables/10f_latencia_respuesta.csv

Uso:
  uv run python scripts/python_scripts/10f_monitoreo_inicio_semana.py
"""

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from config_loader import FIGURES_DIR, PROJECT_ROOT, TABLES_DIR, cfg
from scipy.stats import kruskal, mannwhitneyu

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
TABLES = TABLES_DIR
FIGURES = FIGURES_DIR

COL_TYPE = cfg["data"]["columns"]["message_type"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_GROUP = cfg["data"]["columns"]["group_id"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
TEXT_TYPE = cfg["data"]["values"]["text_message_type"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]
FACILITATOR = cfg["data"]["values"]["facilitator_sender"]

_lat_cats = cfg["analysis"]["latency_categories"]
ORDEN = [c["label"] for c in _lat_cats] + ["Sin respuesta\nesa semana"]
COLORES = cfg["visualization"]["colors"]["latency"]

matplotlib.rcParams.update(
    {
        "font.family": cfg["visualization"]["font_family"],
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": cfg["visualization"]["dpi"],
    }
)

# ── Cargar datos ───────────────────────────────────────────────────────────────
df = pd.read_parquet(
    PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
)
df[COL_DATETIME] = pd.to_datetime(df[COL_DATETIME])
df = df[df[COL_TYPE] == TEXT_TYPE].copy()

df_10a = pd.read_csv(TABLES / "10a_resumen_grupos.csv")

# ── Calcular latencia de primera respuesta por grupo-semana ────────────────────
registros = []
for (grupo, semana), gdf in df.groupby([COL_GROUP, COL_WEEK]):
    fac = gdf[gdf[COL_SENDER] == FACILITATOR].sort_values(COL_DATETIME)
    part = gdf[gdf[COL_SENDER] == PARTICIPANT].sort_values(COL_DATETIME)

    if len(fac) == 0:
        continue

    t_apertura = fac[COL_DATETIME].iloc[0]

    # Solo mensajes de participantes DESPUES de la apertura del facilitador
    part_despues = part[part[COL_DATETIME] > t_apertura]

    if len(part_despues) == 0:
        horas = np.nan
    else:
        t_primera = part_despues[COL_DATETIME].iloc[0]
        horas = (t_primera - t_apertura).total_seconds() / 3600

    registros.append(
        {
            "v_grupo": grupo,
            "n_week": semana,
            "t_apertura": t_apertura,
            "horas_primera_resp": horas,
            "n_msgs_part_total": len(part_despues),
        }
    )

df_lat = pd.DataFrame(registros)

# Unir con sesiones P-P
df_merged = df_lat.merge(
    df_10a[["v_grupo", "n_week", "n_sesiones_pp", "genero_grupo", "city_grupo"]],
    on=["v_grupo", "n_week"],
    how="left",
)
df_merged["n_sesiones_pp"] = df_merged["n_sesiones_pp"].fillna(0)


# ── Categorizar latencia ────────────────────────────────────────────────────────
def categorizar(h):
    if pd.isna(h):
        return "Sin respuesta\nesa semana"
    for cat in _lat_cats:
        if cat["max_hours"] is not None and h <= cat["max_hours"]:
            return cat["label"]
    return _lat_cats[-1]["label"]


df_merged["categoria"] = df_merged["horas_primera_resp"].apply(categorizar)

# Estadísticas
print("=== Latencia de primera respuesta → Sesiones P-P ===\n")
stats = (
    df_merged.groupby("categoria")["n_sesiones_pp"]
    .agg(
        n="count",
        media="mean",
        mediana="median",
        pct_cero=lambda x: (x == 0).mean() * 100,
    )
    .reindex(ORDEN)
    .round(2)
)
print(stats.to_string())

# Test Kruskal-Wallis
grupos_kw = [
    df_merged[df_merged["categoria"] == c]["n_sesiones_pp"].values for c in ORDEN
]
stat_kw, p_kw = kruskal(*[g for g in grupos_kw if len(g) > 0])
print(f"\nKruskal-Wallis: H = {stat_kw:.2f}, p = {p_kw:.4f}")

# Mann-Whitney: primera categoría vs "Sin respuesta"
a = df_merged[df_merged["categoria"] == ORDEN[0]]["n_sesiones_pp"].values
b = df_merged[df_merged["categoria"] == "Sin respuesta\nesa semana"][
    "n_sesiones_pp"
].values
if len(a) > 0 and len(b) > 0:
    stat_mw, p_mw = mannwhitneyu(a, b, alternative="greater")
    print(f"Mann-Whitney {ORDEN[0]} vs Sin respuesta: p = {p_mw:.4f}")

# Guardar CSV
df_merged.to_csv(TABLES / "10f_latencia_respuesta.csv", index=False)

# ── Figura ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
fig.patch.set_alpha(0)

# Panel izquierdo — Media de sesiones P-P por categoría de latencia
ax = axes[0]
ax.patch.set_alpha(0)

medias = [df_merged[df_merged["categoria"] == c]["n_sesiones_pp"].mean() for c in ORDEN]
errores = [df_merged[df_merged["categoria"] == c]["n_sesiones_pp"].sem() for c in ORDEN]
ns = [len(df_merged[df_merged["categoria"] == c]) for c in ORDEN]

_xlabels = [
    o.replace("\nesa semana", "\nesa\nsemana") if "\n" in o else o for o in ORDEN
]

bars = ax.bar(
    range(len(ORDEN)),
    medias,
    color=COLORES,
    alpha=0.85,
    width=0.6,
    yerr=errores,
    capsize=5,
    error_kw=dict(linewidth=1.5, ecolor="#444"),
)

ax.set_xticks(range(len(ORDEN)))
ax.set_xticklabels(_xlabels, fontsize=10)
ax.set_ylabel("Media de sesiones de participación", fontsize=11, fontweight="bold")
ax.set_xlabel(
    "Tiempo hasta primera respuesta de participantes\n(desde apertura del facilitador)",
    fontsize=10,
    fontweight="bold",
)
ax.set_title(
    "Sesiones de participación según\nrapidez de respuesta inicial",
    fontsize=12,
    fontweight="bold",
    pad=10,
)

for i, (bar, n, m) in enumerate(zip(bars, ns, medias)):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(errores) * 0.6,
        f"n={n}",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#444",
    )

sig = f"p {'< 0.001' if p_kw < 0.001 else f'= {p_kw:.3f}'} (Kruskal-Wallis)"
ax.text(
    0.98,
    0.97,
    sig,
    transform=ax.transAxes,
    ha="right",
    va="top",
    fontsize=9,
    style="italic",
    color="#555",
)

# Panel derecho — % grupo-semanas CON al menos 1 sesión P-P
ax2 = axes[1]
ax2.patch.set_alpha(0)

pct_activas = [
    (df_merged[df_merged["categoria"] == c]["n_sesiones_pp"] > 0).mean() * 100
    for c in ORDEN
]

bars2 = ax2.bar(
    range(len(ORDEN)),
    pct_activas,
    color=COLORES,
    alpha=0.85,
    width=0.6,
)

ax2.set_xticks(range(len(ORDEN)))
ax2.set_xticklabels(_xlabels, fontsize=10)
ax2.set_ylabel(
    "% semanas con ≥1 sesión de participación", fontsize=11, fontweight="bold"
)
ax2.set_xlabel(
    "Tiempo hasta primera respuesta de participantes\n(desde apertura del facilitador)",
    fontsize=10,
    fontweight="bold",
)
ax2.set_title(
    "Probabilidad de participación según\nrapidez de respuesta inicial",
    fontsize=12,
    fontweight="bold",
    pad=10,
)
ax2.set_ylim(0, 105)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))

for i, (bar, pct) in enumerate(zip(bars2, pct_activas)):
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1.5,
        f"{pct:.0f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        color=COLORES[i],
    )

fig.tight_layout(pad=2.5)

out = FIGURES / "10f_monitoreo_inicio_semana.png"
fig.savefig(out, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"\nFigura guardada: {out}")

# ── Figuras individuales ────────────────────────────────────────────────────────

# Panel A — Media de sesiones de participación
fig_a, ax_a = plt.subplots(figsize=(7, 5.5))
fig_a.patch.set_alpha(0)
ax_a.patch.set_alpha(0)

bars_a = ax_a.bar(
    range(len(ORDEN)),
    medias,
    color=COLORES,
    alpha=0.85,
    width=0.6,
    yerr=errores,
    capsize=5,
    error_kw=dict(linewidth=1.5, ecolor="#444"),
)
ax_a.set_xticks(range(len(ORDEN)))
ax_a.set_xticklabels(_xlabels, fontsize=10)
ax_a.set_ylabel("Media de sesiones de participación", fontsize=11, fontweight="bold")
ax_a.set_xlabel(
    "Tiempo hasta primera respuesta de participantes\n(desde apertura del facilitador)",
    fontsize=10,
    fontweight="bold",
)
ax_a.set_title(
    "Sesiones de participación según\nrapidez de respuesta inicial",
    fontsize=12,
    fontweight="bold",
    pad=10,
)
for bar, n, m in zip(bars_a, ns, medias):
    ax_a.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + max(errores) * 0.6,
        f"n={n}",
        ha="center",
        va="bottom",
        fontsize=9,
        color="#444",
    )
ax_a.text(
    0.98,
    0.97,
    sig,
    transform=ax_a.transAxes,
    ha="right",
    va="top",
    fontsize=9,
    style="italic",
    color="#555",
)
fig_a.tight_layout(pad=2.5)
out_a = FIGURES / "10f_monitoreo_inicio_semana_a.png"
fig_a.savefig(out_a, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"Figura guardada: {out_a}")

# Panel B — % semanas con >= 1 sesion de participacion
fig_b, ax_b = plt.subplots(figsize=(7, 5.5))
fig_b.patch.set_alpha(0)
ax_b.patch.set_alpha(0)

bars_b = ax_b.bar(
    range(len(ORDEN)),
    pct_activas,
    color=COLORES,
    alpha=0.85,
    width=0.6,
)
ax_b.set_xticks(range(len(ORDEN)))
ax_b.set_xticklabels(_xlabels, fontsize=10)
ax_b.set_ylabel(
    "% semanas con ≥1 sesión de participación", fontsize=11, fontweight="bold"
)
ax_b.set_xlabel(
    "Tiempo hasta primera respuesta de participantes\n(desde apertura del facilitador)",
    fontsize=10,
    fontweight="bold",
)
ax_b.set_title(
    "Probabilidad de participación según\nrapidez de respuesta inicial",
    fontsize=12,
    fontweight="bold",
    pad=10,
)
ax_b.set_ylim(0, 105)
ax_b.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
for i, (bar, pct) in enumerate(zip(bars_b, pct_activas)):
    ax_b.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 1.5,
        f"{pct:.0f}%",
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
        color=COLORES[i],
    )
fig_b.tight_layout(pad=2.5)
out_b = FIGURES / "10f_monitoreo_inicio_semana_b.png"
fig_b.savefig(out_b, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"Figura guardada: {out_b}")
