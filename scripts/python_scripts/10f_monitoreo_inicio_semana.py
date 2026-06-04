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

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from scipy.stats import kruskal, mannwhitneyu

matplotlib.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
    }
)

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

# ── Cargar datos ───────────────────────────────────────────────────────────────
df = pd.read_parquet(ROOT / "data" / "clean" / "mensajes_preprocesados.parquet")
df["datetime"] = pd.to_datetime(df["datetime"])
df = df[df["tipo"] == "Mensaje en Texto"].copy()

df_10a = pd.read_csv(TABLES / "10a_resumen_grupos.csv")

# ── Calcular latencia de primera respuesta por grupo-semana ────────────────────
registros = []
for (grupo, semana), gdf in df.groupby(["v_grupo", "n_week"]):
    fac = gdf[gdf["remitente"] == "Facilitador"].sort_values("datetime")
    part = gdf[gdf["remitente"] == "Participante"].sort_values("datetime")

    if len(fac) == 0:
        continue

    t_apertura = fac["datetime"].iloc[0]

    # Solo mensajes de participantes DESPUES de la apertura del facilitador
    part_despues = part[part["datetime"] > t_apertura]

    if len(part_despues) == 0:
        horas = np.nan
    else:
        t_primera = part_despues["datetime"].iloc[0]
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
    elif h <= 2:
        return "≤ 2 h"
    elif h <= 12:
        return "2–12 h"
    elif h <= 48:
        return "12–48 h"
    else:
        return "> 48 h"


df_merged["categoria"] = df_merged["horas_primera_resp"].apply(categorizar)

ORDEN = ["≤ 2 h", "2–12 h", "12–48 h", "> 48 h", "Sin respuesta\nesa semana"]
COLORES = ["#1B5E20", "#66BB6A", "#FFA726", "#EF6C00", "#B71C1C"]

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

# Mann-Whitney: "≤ 2 h" vs "Sin respuesta"
a = df_merged[df_merged["categoria"] == "≤ 2 h"]["n_sesiones_pp"].values
b = df_merged[df_merged["categoria"] == "Sin respuesta\nesa semana"][
    "n_sesiones_pp"
].values
if len(a) > 0 and len(b) > 0:
    stat_mw, p_mw = mannwhitneyu(a, b, alternative="greater")
    print(f"Mann-Whitney ≤2h vs Sin respuesta: p = {p_mw:.4f}")

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
ax.set_xticklabels(
    ["≤ 2 h", "2–12 h", "12–48 h", "> 48 h", "Sin\nrespuesta"],
    fontsize=10,
)
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
ns2 = ns  # mismos N

bars2 = ax2.bar(
    range(len(ORDEN)),
    pct_activas,
    color=COLORES,
    alpha=0.85,
    width=0.6,
)

ax2.set_xticks(range(len(ORDEN)))
ax2.set_xticklabels(
    ["≤ 2 h", "2–12 h", "12–48 h", "> 48 h", "Sin\nrespuesta"],
    fontsize=10,
)
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
ax_a.set_xticklabels(
    ["≤ 2 h", "2–12 h", "12–48 h", "> 48 h", "Sin\nrespuesta"],
    fontsize=10,
)
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
ax_b.set_xticklabels(
    ["≤ 2 h", "2–12 h", "12–48 h", "> 48 h", "Sin\nrespuesta"],
    fontsize=10,
)
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
