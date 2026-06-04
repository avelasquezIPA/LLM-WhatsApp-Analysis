"""09a_citas_presentacion.py
===========================
Versión de presentación de la figura 09a: solo los dos paneles de la derecha
(citas por ciudad y género + similitud media por familia y género).
Elimina el panel izquierdo de barras simples por género.

Arial, fondo transparente, 300 dpi.

Uso:
  uv run python scripts/python_scripts/09a_citas_presentacion.py
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
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
IN_PATH = ROOT / "outputs" / "tables" / "08b_citas_por_codigo_participantes.xlsx"
FIGURES = ROOT / "outputs" / "figures"

COLORES = {
    "Hombre": "#1976D2",
    "Mujer": "#E91E8C",
    "Sin género": "#9E9E9E",
}

FAMILIAS_CORTAS = {
    "3. ENFOQUE PARA ESCALAR": "3. Escalar",
    "4. VIABILIDAD DE LA IMPLEMENTACIÓN": "4. Viabilidad",
    "5. ACTITUD DE LOS PARTICIPANTES FRENTE AL PROGRAMA": "5. Actitud part.",
    "7. RESULTADOS INICIALES E INTERMEDIOS": "7. Resultados",
}

# ── Cargar datos ───────────────────────────────────────────────────────────────
df = pd.read_excel(IN_PATH, sheet_name="Citas_Mensajes_Part")
df["genero"] = df["genero"].fillna("Sin género").replace("", "Sin género")
df["familia_corta"] = df["familia"].map(
    lambda x: next((v for k, v in FAMILIAS_CORTAS.items() if k[:10] in x), x[:25])
)

# ── Figura: dos paneles ────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
fig.patch.set_alpha(0)

# ── Panel izquierdo: citas por ciudad y género (apilado) ──────────────────────
ax = axes[0]
ax.patch.set_alpha(0)

pivot_ciudad = df.groupby(["ciudad", "genero"]).size().unstack(fill_value=0)
ciudades_orden = ["Bogota", "Soacha", "Neiva", "Valledupar"]
pivot_ciudad = pivot_ciudad.reindex(ciudades_orden)

bottom = np.zeros(len(pivot_ciudad))
for genero in ["Hombre", "Mujer", "Sin género"]:
    if genero in pivot_ciudad.columns:
        vals = pivot_ciudad[genero].values
        bars = ax.bar(
            pivot_ciudad.index,
            vals,
            bottom=bottom,
            label=genero,
            color=COLORES[genero],
            edgecolor="white",
        )
        for bar, val, bot in zip(bars, vals, bottom):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bot + val / 2,
                    str(val),
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                )
        bottom += vals

totales = pivot_ciudad.sum(axis=1)
for i, (ciudad, total) in enumerate(totales.items()):
    ax.text(
        i,
        total + 1.5,
        str(total),
        ha="center",
        va="bottom",
        fontsize=10,
        fontweight="bold",
    )

ax.set_title("Citas por ciudad y género", fontsize=12, fontweight="bold", pad=10)
ax.set_ylabel("N citas", fontsize=11, fontweight="bold")
ax.set_ylim(0, totales.max() * 1.18)
ax.legend(fontsize=9, loc="upper right", framealpha=0)

# ── Panel derecho: similitud media por familia y género ───────────────────────
ax2 = axes[1]
ax2.patch.set_alpha(0)

pivot_sim = (
    df.groupby(["familia_corta", "genero"])["similitud"]
    .mean()
    .unstack(fill_value=np.nan)
)
familias_orden = ["3. Escalar", "4. Viabilidad", "5. Actitud part.", "7. Resultados"]
pivot_sim = pivot_sim.reindex(familias_orden)

x = np.arange(len(pivot_sim))
width = 0.28
generos_plot = [g for g in ["Hombre", "Mujer", "Sin género"] if g in pivot_sim.columns]
offsets = np.linspace(
    -(len(generos_plot) - 1) * width / 2,
    (len(generos_plot) - 1) * width / 2,
    len(generos_plot),
)

for genero, offset in zip(generos_plot, offsets):
    vals = pivot_sim[genero].values
    bars = ax2.bar(
        x + offset,
        vals,
        width=width,
        label=genero,
        color=COLORES[genero],
        edgecolor="white",
        alpha=0.9,
    )
    for bar, val in zip(bars, vals):
        if not np.isnan(val):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )

ax2.set_title(
    "Similitud media por familia de código y género",
    fontsize=12,
    fontweight="bold",
    pad=10,
)
ax2.set_ylabel("Similitud coseno media", fontsize=11, fontweight="bold")
ax2.set_xticks(x)
ax2.set_xticklabels(familias_orden, fontsize=9, rotation=15, ha="right")
ax2.set_ylim(0, pivot_sim.max().max() * 1.18)
ax2.axhline(
    df["similitud"].mean(),
    color="gray",
    linestyle="--",
    linewidth=0.8,
    label=f"Media global ({df['similitud'].mean():.2f})",
)
ax2.legend(fontsize=8, framealpha=0)

fig.tight_layout(pad=2.5)

out = FIGURES / "09a_citas_genero_ciudad_presentacion.png"
fig.savefig(out, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"Figura guardada: {out}")
