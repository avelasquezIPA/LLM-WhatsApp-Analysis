"""10a_panel1_presentacion.py
============================
Regenera el panel 1 (Sesiones de participación por semana y ciudad)
con estilo para presentación:
  - Fuente Arial
  - Fondo transparente
  - "Sesiones de participación" en lugar de "Sesiones P-P"
  - Alta calidad (300 dpi)

Lee el CSV ya generado por 10a_cadenas_interaccion.py.

Uso:
  uv run python scripts/python_scripts/10a_panel1_presentacion.py
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

matplotlib.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)

ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

COLORES_CIUDAD = {
    "Bogota": "#1565C0",
    "Soacha": "#2E7D32",
    "Neiva": "#E65100",
    "Valledupar": "#6A1B9A",
}

df = pd.read_csv(TABLES / "10a_cadenas_sesion.csv")

por_semana = df.groupby(["n_week", "city_grupo"]).size().unstack(fill_value=0)

fig, ax = plt.subplots(figsize=(9, 5.5))
fig.patch.set_alpha(0)
ax.patch.set_alpha(0)

for ciudad in ["Bogota", "Soacha", "Neiva", "Valledupar"]:
    if ciudad in por_semana.columns:
        ax.plot(
            por_semana.index,
            por_semana[ciudad],
            marker="o",
            label=ciudad,
            color=COLORES_CIUDAD.get(ciudad),
            linewidth=2,
            markersize=5,
        )

ax.set_title(
    "Sesiones de participación por semana y ciudad",
    fontsize=13,
    fontweight="bold",
    pad=12,
)
ax.set_xlabel("Semana", fontsize=12, fontweight="bold")
ax.set_ylabel("Sesiones de participación", fontsize=12, fontweight="bold")
ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
ax.legend(fontsize=10, framealpha=0)
ax.grid(axis="y", alpha=0.25, linestyle="--")
ax.tick_params(labelsize=11)

fig.tight_layout()

out = FIGURES / "10a_panel1_sesiones_semana_presentacion.png"
fig.savefig(out, bbox_inches="tight", transparent=True, dpi=300)
plt.close()
print(f"Figura guardada: {out}")
