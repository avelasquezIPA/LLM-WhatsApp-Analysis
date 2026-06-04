"""Paso 9: Análisis de citas por género y ciudad - Programa Apapachar
====================================================================
Genera visualizaciones sobre las citas encontradas en el script 08b,
desglosadas por género del participante, ciudad y familia de código.

Input:
  - outputs/tables/08b_citas_por_codigo_participantes.xlsx

Output:
  - outputs/figures/09a_citas_genero_ciudad.png
  - outputs/figures/09b_citas_similitud_codigos.png
  - outputs/tables/09_resumen_citas.csv
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
IN_PATH = ROOT / "outputs" / "tables" / "08b_citas_por_codigo_participantes.xlsx"
OUT_FIGURES = ROOT / "outputs" / "figures"
OUT_TABLES = ROOT / "outputs" / "tables"

COLORES = {
    "Hombre": "#1976D2",
    "Mujer": "#E91E8C",
    "Sin género": "#9E9E9E",
}

CIUDADES_COLORES = {
    "Bogota": "#1565C0",
    "Soacha": "#2E7D32",
    "Neiva": "#E65100",
    "Valledupar": "#6A1B9A",
}

FAMILIAS_CORTAS = {
    "3. ENFOQUE PARA ESCALAR": "3. Escalar",
    "4. VIABILIDAD DE LA IMPLEMENTACIÓN": "4. Viabilidad",
    "5. ACTITUD DE LOS PARTICIPANTES FRENTE AL PROGRAMA": "5. Actitud part.",
    "7. RESULTADOS INICIALES E INTERMEDIOS": "7. Resultados",
}

# ---------------------------------------------------------------------------
# 1. Cargar datos
# ---------------------------------------------------------------------------
print("Cargando datos...")
df = pd.read_excel(IN_PATH, sheet_name="Citas_Mensajes_Part")
df["genero"] = df["genero"].fillna("Sin género").replace("", "Sin género")

# Etiqueta corta de familia
df["familia_corta"] = df["familia"].map(
    lambda x: next((v for k, v in FAMILIAS_CORTAS.items() if k[:10] in x), x[:25])
)

print(f"  Total citas: {len(df)}")
print(f"  Género: {df['genero'].value_counts().to_dict()}")
print(f"  Ciudades: {df['ciudad'].value_counts().to_dict()}")

# ---------------------------------------------------------------------------
# 2. Resumen para CSV
# ---------------------------------------------------------------------------
resumen = (
    df.groupby(["familia_corta", "genero"])
    .agg(n_citas=("mensaje", "count"), sim_media=("similitud", "mean"))
    .round(3)
    .reset_index()
)
resumen.to_csv(OUT_TABLES / "09_resumen_citas.csv", index=False)
print("  Resumen guardado.")

# ---------------------------------------------------------------------------
# 3. Figura A: Overview género + ciudad + familia
# ---------------------------------------------------------------------------
print("\nGenerando figura A...")

fig, axes = plt.subplots(1, 3, figsize=(16, 6))
fig.suptitle(
    "Distribución de citas por género, ciudad y familia de código\n"
    "Programa Apapachar - Solo participantes",
    fontsize=13,
    y=1.01,
)

# Panel 1: N citas por género
ax = axes[0]
gen_counts = df["genero"].value_counts()
colores_gen = [COLORES.get(g, "#9E9E9E") for g in gen_counts.index]
bars = ax.bar(
    gen_counts.index, gen_counts.values, color=colores_gen, edgecolor="white", width=0.5
)
for bar, val in zip(bars, gen_counts.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 2,
        str(val),
        ha="center",
        va="bottom",
        fontsize=11,
        fontweight="bold",
    )
ax.set_title("Citas por género", fontsize=11)
ax.set_ylabel("N citas")
ax.set_ylim(0, gen_counts.max() * 1.15)
ax.yaxis.set_major_locator(mticker.MultipleLocator(20))

# Panel 2: N citas por ciudad, apilado por género
ax = axes[1]
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

ax.set_title("Citas por ciudad y género", fontsize=11)
ax.set_ylabel("N citas")
ax.set_ylim(0, totales.max() * 1.15)
ax.legend(fontsize=9, loc="upper right")

# Panel 3: Similitud media por familia y género
ax = axes[2]
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
    bars = ax.bar(
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
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.005,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=7.5,
            )

ax.set_title("Similitud media por familia y género", fontsize=11)
ax.set_ylabel("Similitud coseno media")
ax.set_xticks(x)
ax.set_xticklabels(familias_orden, fontsize=9, rotation=15, ha="right")
ax.set_ylim(0, pivot_sim.max().max() * 1.18)
ax.axhline(
    df["similitud"].mean(),
    color="gray",
    linestyle="--",
    linewidth=0.8,
    label=f"Media global ({df['similitud'].mean():.2f})",
)
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(OUT_FIGURES / "09a_citas_genero_ciudad.png", dpi=150, bbox_inches="tight")
plt.close()
print("  Figura A guardada.")

# ---------------------------------------------------------------------------
# 4. Figura B: Top códigos por similitud, desglosado por género
# ---------------------------------------------------------------------------
print("\nGenerando figura B...")

# Top 15 códigos por similitud media global
top_codigos = (
    df.groupby(["codigo", "descripcion_codigo"])["similitud"]
    .mean()
    .sort_values(ascending=False)
    .head(15)
    .reset_index()
)
top_codigos["etiqueta"] = (
    top_codigos["codigo"] + " " + top_codigos["descripcion_codigo"].str[:45]
)

# Similitud por género para esos códigos
df_top = df[df["codigo"].isin(top_codigos["codigo"])].copy()
pivot_top = (
    df_top.groupby(["codigo", "genero"])["similitud"]
    .mean()
    .unstack(fill_value=np.nan)
    .reindex(top_codigos["codigo"])
)
pivot_top.index = top_codigos["etiqueta"].values

fig, ax = plt.subplots(figsize=(14, 8))

y = np.arange(len(pivot_top))
height = 0.28
generos_plot = [g for g in ["Hombre", "Mujer", "Sin género"] if g in pivot_top.columns]
offsets = np.linspace(
    -(len(generos_plot) - 1) * height / 2,
    (len(generos_plot) - 1) * height / 2,
    len(generos_plot),
)

for genero, offset in zip(generos_plot, offsets):
    vals = pivot_top[genero].values
    bars = ax.barh(
        y + offset,
        vals,
        height=height,
        label=genero,
        color=COLORES[genero],
        edgecolor="white",
        alpha=0.9,
    )
    for bar, val in zip(bars, vals):
        if not np.isnan(val) and val > 0:
            ax.text(
                val + 0.003,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                va="center",
                fontsize=7.5,
            )

ax.set_yticks(y)
ax.set_yticklabels(pivot_top.index, fontsize=9)
ax.set_xlabel("Similitud coseno media")
ax.set_title(
    "Top 15 códigos por relevancia semántica\nSimilitud media por género - Solo participantes",
    fontsize=12,
)
ax.axvline(
    df["similitud"].mean(),
    color="gray",
    linestyle="--",
    linewidth=0.8,
    label=f"Media global ({df['similitud'].mean():.2f})",
)
ax.legend(fontsize=9, loc="lower right")
ax.set_xlim(0, pivot_top.max().max() * 1.12)
ax.invert_yaxis()

plt.tight_layout()
plt.savefig(
    OUT_FIGURES / "09b_citas_similitud_codigos.png", dpi=150, bbox_inches="tight"
)
plt.close()
print("  Figura B guardada.")

# ---------------------------------------------------------------------------
# 5. Resumen en consola
# ---------------------------------------------------------------------------
print("\n=== Resumen de citas por género ===")
print(
    df.groupby("genero")
    .agg(
        n_citas=("mensaje", "count"),
        sim_media=("similitud", "mean"),
        sim_max=("similitud", "max"),
    )
    .round(3)
    .to_string()
)

print("\n=== Similitud media por ciudad y género ===")
print(
    df.groupby(["ciudad", "genero"])["similitud"].mean().round(3).unstack().to_string()
)

print("\n=== Top 5 códigos por similitud (Mujeres) ===")
top_m = (
    df[df["genero"] == "Mujer"]
    .groupby(["codigo", "descripcion_codigo"])["similitud"]
    .mean()
    .nlargest(5)
)
for (cod, desc), sim in top_m.items():
    print(f"  {cod} | sim={sim:.3f} | {desc[:60]}")

print("\n=== Top 5 códigos por similitud (Hombres) ===")
top_h = (
    df[df["genero"] == "Hombre"]
    .groupby(["codigo", "descripcion_codigo"])["similitud"]
    .mean()
    .nlargest(5)
)
for (cod, desc), sim in top_h.items():
    print(f"  {cod} | sim={sim:.3f} | {desc[:60]}")

print("\nScript 09 completado.")
