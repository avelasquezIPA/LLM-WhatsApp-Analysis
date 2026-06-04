"""10e_retencion_presentacion.py
================================
Curva de retención semanal por género para presentación.

Destaca:
  - Caída pronunciada en S1–S2 (ventana crítica, 70% del abandono)
  - Retención final del 15%
  - Brecha de género (mujeres 18% vs hombres 13%)

Lee el CSV ya generado por 10e_escalabilidad.py.

Uso:
  uv run python scripts/python_scripts/10e_retencion_presentacion.py
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

matplotlib.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

df = pd.read_csv(TABLES / "10e_retencion.csv")

SEMANAS = list(range(1, 13))

# Promedios globales y por género
ret_global = df.groupby("semana")["retencion_s1"].mean().reindex(SEMANAS)
ret_gen = (
    df.groupby(["semana", "sex_grupo"])["retencion_s1"]
    .mean()
    .unstack()
    .reindex(SEMANAS)
)

# ── Figura ─────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5.5))
fig.patch.set_alpha(0)
ax.patch.set_alpha(0)

# Zona sombreada S1–S2: ventana crítica
ax.axvspan(0.6, 2.4, alpha=0.07, color="#E65100", zorder=0)
ax.text(
    1.5,
    1.09,
    "Ventana crítica\nde intervención",
    ha="center",
    va="top",
    fontsize=9,
    color="#E65100",
    fontweight="bold",
)

# Líneas
ax.plot(
    SEMANAS,
    ret_global,
    "o-",
    color="#2c3e50",
    linewidth=2.5,
    markersize=6,
    label="Total",
    zorder=3,
)
if "Mujer" in ret_gen.columns:
    ax.plot(
        SEMANAS,
        ret_gen["Mujer"],
        "s--",
        color="#c0392b",
        linewidth=1.8,
        markersize=5,
        label="Mujeres",
        zorder=3,
    )
if "Hombre" in ret_gen.columns:
    ax.plot(
        SEMANAS,
        ret_gen["Hombre"],
        "^--",
        color="#2e86c1",
        linewidth=1.8,
        markersize=5,
        label="Hombres",
        zorder=3,
    )

# Línea de referencia: 15%
ax.axhline(0.15, color="#7f8c8d", linestyle=":", linewidth=1.2, alpha=0.8)
ax.text(
    12.15,
    0.155,
    "15%\nretención final",
    va="bottom",
    ha="left",
    fontsize=9,
    color="#7f8c8d",
)

# Anotación: 70% del abandono en S1–S2
val_s2 = ret_global.loc[2] if 2 in ret_global.index else 0.35
ax.annotate(
    "70% del abandono\nocurre en S1–S2",
    xy=(2, val_s2),
    xytext=(4.2, 0.62),
    arrowprops=dict(arrowstyle="->", color="#E65100", lw=1.5),
    fontsize=9.5,
    color="#E65100",
    fontweight="bold",
)

# Etiquetas de % al final (S12)
for col, color in [("Mujer", "#c0392b"), ("Hombre", "#2e86c1")]:
    if col in ret_gen.columns:
        val = ret_gen.loc[12, col]
        if pd.notna(val):
            ax.text(
                12.15,
                val,
                f"{val:.0%}",
                va="center",
                ha="left",
                fontsize=9,
                color=color,
            )

ax.set_xticks(SEMANAS)
ax.set_xticklabels([f"S{s}" for s in SEMANAS], fontsize=10)
ax.set_ylabel("Tasa de retención (relativa a S1)", fontsize=11, fontweight="bold")
ax.set_ylim(0, 1.15)
ax.set_xlim(0.5, 13.2)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.0%}"))
ax.set_title(
    "Retención de cuidadores a lo largo del programa",
    fontsize=13,
    fontweight="bold",
    pad=12,
)
ax.legend(fontsize=10, framealpha=0, loc="upper right")
ax.grid(axis="y", alpha=0.2, linestyle="--")

fig.tight_layout()

out = FIGURES / "10e_retencion_presentacion.png"
fig.savefig(out, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"Figura guardada: {out}")
