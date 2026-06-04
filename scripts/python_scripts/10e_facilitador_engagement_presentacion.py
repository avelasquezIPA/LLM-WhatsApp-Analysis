"""10e_facilitador_engagement_presentacion.py
=============================================
Regenera únicamente la figura A2 (facilitador vs. engagement P-P)
con estilo para presentación:
  - Mujeres → verde oscuro  (#1B5E20)
  - Hombres → azul cyan     (#00BCD4)
  - Fondo transparente
  - Fuente Arial

Lee el CSV ya generado por 10e_escalabilidad.py; no requiere
procesar los datos crudos de nuevo.

Uso:
  uv run python scripts/python_scripts/10e_facilitador_engagement_presentacion.py
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr

matplotlib.rcParams.update(
    {
        "font.family": "Arial",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 150,
    }
)

# ── Rutas ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
TABLES = ROOT / "outputs" / "tables"
FIGURES = ROOT / "outputs" / "figures"

# ── Colores para presentación ──────────────────────────────────────────────────
COLORES = {
    "Mujer": "#1B5E20",  # verde oscuro
    "Hombre": "#00BCD4",  # azul cyan
}

# ── Cargar datos ───────────────────────────────────────────────────────────────
df = pd.read_csv(TABLES / "10e_facilitador_grupos.csv")
df = df.dropna(subset=["n_sesiones_pp", "avg_len_fac", "pct_msgs_fac"])

r_len, p_len = pearsonr(df["avg_len_fac"], df["n_sesiones_pp"])
r_pct, p_pct = pearsonr(df["pct_msgs_fac"], df["n_sesiones_pp"])

# ── Figura ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.patch.set_alpha(0)  # fondo del lienzo transparente

paneles = [
    (
        "avg_len_fac",
        "Longitud promedio del mensaje del facilitador (chars)",
        r_len,
        p_len,
        "10e_facilitador_engagement_izquierda.png",
    ),
    (
        "pct_msgs_fac",
        "% de mensajes del facilitador en el grupo",
        r_pct,
        p_pct,
        "10e_facilitador_engagement_derecha.png",
    ),
]

for xvar, xlabel, r, p, fname in paneles:
    fig, ax = plt.subplots(figsize=(6.5, 5))
    fig.patch.set_alpha(0)
    ax.patch.set_alpha(0)

    for gen, color in COLORES.items():
        sub = df[df["sex_grupo"] == gen]
        ax.scatter(
            sub[xvar],
            sub["n_sesiones_pp"],
            c=color,
            label=gen,
            s=90,
            alpha=0.85,
            edgecolors="white",
            linewidths=0.6,
            zorder=3,
        )

    # Línea de tendencia
    z = np.polyfit(df[xvar], df["n_sesiones_pp"], 1)
    xr = np.linspace(df[xvar].min(), df[xvar].max(), 100)
    ax.plot(xr, np.poly1d(z)(xr), "--", color="#555555", linewidth=1.5, alpha=0.55)

    sig = "*" if p < 0.05 else "ns"
    ax.set_xlabel(xlabel, fontsize=11, fontweight="bold")
    ax.set_ylabel("Sesiones de participación", fontsize=11, fontweight="bold")
    ax.set_title(f"r = {r:.2f}  ({sig})", fontweight="bold", fontsize=12)
    ax.legend(fontsize=10, framealpha=0)
    ax.tick_params(labelsize=10)

    fig.tight_layout()
    out = FIGURES / fname
    fig.savefig(out, bbox_inches="tight", transparent=True, dpi=150)
    plt.close()
    print(f"Figura guardada: {out}")
