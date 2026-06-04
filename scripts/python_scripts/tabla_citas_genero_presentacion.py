"""tabla_citas_genero_presentacion.py
=====================================
Genera una imagen de tabla con los top 5 códigos de similitud
por género (Hombres / Mujeres) para pegar en presentación.

  - Fuente Arial
  - Fondo transparente
  - Colores IPA: verde oscuro (mujeres) y cyan (hombres)

Uso:
  uv run python scripts/python_scripts/tabla_citas_genero_presentacion.py
"""

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd

matplotlib.rcParams["font.family"] = "Arial"

ROOT = Path(__file__).resolve().parents[2]
FIGURES = ROOT / "outputs" / "figures"

# ── Datos ──────────────────────────────────────────────────────────────────────
xl = pd.ExcelFile(
    ROOT / "outputs" / "tables" / "08b_citas_por_codigo_participantes_v2.xlsx"
)
df = pd.read_excel(xl, sheet_name="Citas_Mensajes_Part")

# Descripciones resumidas manualmente para que quepan en la tabla
DESC_CORTA = {
    "[7.10]": "Fortalecimiento del vínculo cuidador-niño",
    "[7.13]": "Redistribución de tareas en el hogar",
    "[7.11]": "Mayor entendimiento del comportamiento infantil",
    "[7.15]": "Cambios en corresponsabilidad en la crianza",
    "[7.2]": "Fortalecimiento de la autoeficacia parental",
    "[7.5]": "Adopción de prácticas de desarrollo infantil",
    "[7.6]": "Adopción de prácticas de crianza no violenta",
}

tops = {}
for gen in ["Hombre", "Mujer"]:
    sub = df[df["genero"] == gen]
    tops[gen] = (
        sub.groupby(["codigo", "descripcion_codigo"])["similitud"]
        .agg(sim_media="mean", n_citas="count")
        .reset_index()
        .sort_values("sim_media", ascending=False)
        .head(3)
        .reset_index(drop=True)
    )

# ── Figura ─────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 3.0))
fig.patch.set_alpha(0)

configs = [
    ("Hombre", axes[0]),
    ("Mujer", axes[1]),
]

for gen, ax in configs:
    ax.axis("off")
    ax.patch.set_alpha(0)

    data = tops[gen]
    table_data = [
        [
            row["codigo"],
            DESC_CORTA.get(row["codigo"].strip(), row["descripcion_codigo"][:40]),
            f"{row['sim_media']:.3f}",
        ]
        for _, row in data.iterrows()
    ]
    col_labels = ["Código", "Descripción", "Similitud"]
    col_widths = [0.14, 0.58, 0.14]

    tbl = ax.table(
        cellText=table_data,
        colLabels=col_labels,
        colWidths=col_widths,
        loc="center",
        cellLoc="left",
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)

    # Cabecera: negro sobre blanco
    for col in range(3):
        cell = tbl[0, col]
        cell.set_facecolor("white")
        cell.set_text_props(weight="bold", color="black", fontsize=10)
        cell.set_edgecolor("black")
        cell.set_linewidth(0.8)

    # Filas: blanco y negro
    for row in range(1, 4):
        for col in range(3):
            cell = tbl[row, col]
            cell.set_facecolor("white")
            cell.set_edgecolor("#888888")
            cell.set_linewidth(0.4)
            if col == 0:
                cell.set_text_props(weight="bold", color="black", fontsize=10)
            else:
                cell.set_text_props(color="black", fontsize=10)

    # Título del panel
    ax.set_title(
        f"{'Cuidadores hombres' if gen == 'Hombre' else 'Cuidadoras mujeres'} — Top 3 códigos",
        fontsize=11,
        fontweight="bold",
        color="black",
        pad=10,
    )

fig.suptitle(
    "Afinidad semántica con códigos cualitativos por género",
    fontsize=12,
    fontweight="bold",
    color="black",
    y=1.02,
)
fig.tight_layout(pad=1.5)

out = FIGURES / "09_tabla_top5_codigos_genero.png"
fig.savefig(out, bbox_inches="tight", transparent=True, dpi=150)
plt.close()
print(f"Tabla guardada: {out}")
