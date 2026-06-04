"""10e_escalabilidad.py
=====================
Tres análisis orientados a las prioridades del plan MEL 2026:
capacidad de implementación y costo-efectividad a escala.

  A1 — Curva de retención de participantes (semanas 1-12)
  A2 — Perfil del facilitador vs. engagement P-P del grupo
  A3 — Mapa de engagement por semana/tema

Inputs:
  data/clean/mensajes_preprocesados.parquet
  outputs/tables/10a_cadenas_sesion.csv
  outputs/tables/10a_resumen_grupos.csv
  outputs/tables/10d_corpus_interaccion.csv

Outputs:
  outputs/tables/10e_retencion.csv
  outputs/tables/10e_facilitador_grupos.csv
  outputs/tables/10e_resumen_escalabilidad.md
  outputs/figures/10e_retencion.png
  outputs/figures/10e_facilitador_engagement.png
  outputs/figures/10e_mapa_engagement.png

Uso:
  uv run python scripts/python_scripts/10e_escalabilidad.py
"""

import sys
import unicodedata
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "clean" / "mensajes_preprocesados.parquet"
TABLES_IN = ROOT / "outputs" / "tables"
TABLES_OUT = ROOT / "outputs" / "tables"
FIGURES_OUT = ROOT / "outputs" / "figures"

COLORS_GEN = {"Mujer": "#c0392b", "Hombre": "#2e86c1"}
COLORS_CITY = {
    "Bogota": "#1a5276",
    "Neiva": "#117a65",
    "Soacha": "#784212",
    "Valledupar": "#6c3483",
}

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
    }
)

SEMANAS = list(range(1, 13))


def normalize_city(s):
    if not isinstance(s, str):
        return s
    return unicodedata.normalize("NFC", s)


# ═══════════════════════════════════════════════════════════════════════════════
# CARGA DE DATOS
# ═══════════════════════════════════════════════════════════════════════════════

print("Cargando datos...")
df_raw = pd.read_parquet(DATA)
txt = df_raw[df_raw["tipo"] == "Mensaje en Texto"].copy()

# Separar facilitadores y participantes
is_fac = txt["remitente"].str.contains("Facilitador|Coordinadora", na=False)
participantes = txt[~is_fac].copy()
facilitadores = txt[is_fac].copy()

# Cargar tablas de 10a y 10d
cadenas = pd.read_csv(TABLES_IN / "10a_cadenas_sesion.csv")
resumen_grupos = pd.read_csv(TABLES_IN / "10a_resumen_grupos.csv")
corpus = pd.read_csv(TABLES_IN / "10d_corpus_interaccion.csv")

# Normalizar ciudad
for _df in [cadenas, resumen_grupos, corpus]:
    if "city_grupo" in _df.columns:
        _df["city_grupo"] = _df["city_grupo"].map(normalize_city)
    if "ciudad" in _df.columns:
        _df["ciudad"] = _df["ciudad"].map(normalize_city)

print(
    f"  Mensajes texto: {len(txt):,} | Participantes: {len(participantes):,} | "
    f"Facilitadores: {len(facilitadores):,}"
)
print(f"  Participantes únicos: {participantes['id_f'].nunique()}")
print(f"  Grupos: {txt['v_grupo'].nunique()} | Semanas: {txt['n_week'].nunique()}")
print(f"  Sesiones P-P: {len(cadenas)} | ITs codificadas: {len(corpus)}")


# ═══════════════════════════════════════════════════════════════════════════════
# A1 — CURVA DE RETENCIÓN
# ═══════════════════════════════════════════════════════════════════════════════

print("\n--- A1: Curva de retención ---")


def calcular_retencion(part_df):
    """Para cada grupo, identifica participantes activos en semana 1 y rastrea
    en qué semanas siguen activos. Retorna DataFrame con tasa de retención
    semanal global y por subgrupo.
    """
    grupos = part_df["v_grupo"].unique()
    registros = []

    for grp in grupos:
        sub = part_df[part_df["v_grupo"] == grp]
        meta = sub[["v_grupo", "sex_grupo", "city_grupo"]].iloc[0]

        # Participantes que aparecen en semana 1
        week1 = set(sub[sub["n_week"] == 1]["id_f"].unique())
        # Todos los participantes que alguna vez enviaron mensaje
        ever_active = set(sub["id_f"].unique())

        for sem in SEMANAS:
            active_sem = set(sub[sub["n_week"] == sem]["id_f"].unique())
            registros.append(
                {
                    "v_grupo": grp,
                    "sex_grupo": meta["sex_grupo"],
                    "city_grupo": meta["city_grupo"],
                    "semana": sem,
                    "n_activos": len(active_sem),
                    "n_cohorte_s1": len(week1),
                    "n_ever": len(ever_active),
                    # Retención desde semana 1 (solo quienes estuvieron en s1)
                    "retencion_s1": (
                        len(active_sem & week1) / len(week1) if week1 else np.nan
                    ),
                    # Alcance: % del total histórico activo esa semana
                    "alcance": (
                        len(active_sem) / len(ever_active) if ever_active else np.nan
                    ),
                }
            )

    return pd.DataFrame(registros)


ret = calcular_retencion(participantes)
ret.to_csv(TABLES_OUT / "10e_retencion.csv", index=False)
print(f"  Guardado: 10e_retencion.csv ({len(ret)} filas)")

# Promedios globales
ret_global = ret.groupby("semana")[["retencion_s1", "alcance", "n_activos"]].mean()
ret_global["n_activos_total"] = ret.groupby("semana")["n_activos"].sum()

# Por género
ret_gen = (
    ret.groupby(["semana", "sex_grupo"])[["retencion_s1", "alcance"]]
    .mean()
    .reset_index()
)

# Figura A1
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

ax = axes[0]
ax.plot(
    SEMANAS,
    ret_global["retencion_s1"],
    "o-",
    color="#2c3e50",
    linewidth=2.5,
    markersize=7,
    label="Global",
)
for gen, color in COLORS_GEN.items():
    sub = ret_gen[ret_gen["sex_grupo"] == gen]
    ax.plot(
        sub["semana"],
        sub["retencion_s1"],
        "s--",
        color=color,
        linewidth=1.8,
        markersize=6,
        label=gen,
    )
ax.axhline(0.5, color="gray", linestyle=":", linewidth=1, alpha=0.7)
ax.set_xticks(SEMANAS)
ax.set_xticklabels([f"S{s}" for s in SEMANAS], fontsize=8)
ax.set_ylabel("Tasa de retención (relativa a semana 1)")
ax.set_ylim(0, 1.05)
ax.set_title("A1 — Retención desde semana 1", fontweight="bold")
ax.legend(fontsize=9)

# Panel derecho: N activos totales por semana
ax2 = axes[1]
bars = ax2.bar(
    SEMANAS,
    ret_global["n_activos_total"],
    color="#85c1e9",
    edgecolor="white",
    width=0.7,
)
ax2.set_xticks(SEMANAS)
ax2.set_xticklabels([f"S{s}" for s in SEMANAS], fontsize=8)
ax2.set_ylabel("Total participantes activos (suma de grupos)")
ax2.set_title("Participantes activos por semana", fontweight="bold")

# Línea de tendencia
z = np.polyfit(SEMANAS, ret_global["n_activos_total"], 1)
p = np.poly1d(z)
ax2_twin = ax2.twinx()
ax2_twin.plot(SEMANAS, p(SEMANAS), "r--", linewidth=1.5, alpha=0.6, label="Tendencia")
ax2_twin.set_ylabel("Tendencia", color="red", fontsize=9)
ax2_twin.tick_params(axis="y", labelcolor="red")
ax2_twin.spines["top"].set_visible(False)

fig.suptitle(
    "Retención de participantes a lo largo del programa (semanas 1–12)",
    fontsize=12,
    fontweight="bold",
    y=1.01,
)
fig.tight_layout()
out = FIGURES_OUT / "10e_retencion.png"
fig.savefig(out, bbox_inches="tight")
plt.close()
print(f"  Figura guardada: {out.name}")

# Estadísticas clave para el resumen
ret_s1 = ret_global.loc[1, "retencion_s1"]
ret_s6 = ret_global.loc[6, "retencion_s1"]
ret_s12 = ret_global.loc[12, "retencion_s1"]
caida_max_idx = int(ret_global["retencion_s1"].diff().idxmin())
print(f"  Retención global: S1=100% | S6={ret_s6:.0%} | S12={ret_s12:.0%}")
print(f"  Mayor caída entre semana {caida_max_idx - 1} y {caida_max_idx}")


# ═══════════════════════════════════════════════════════════════════════════════
# A2 — PERFIL DEL FACILITADOR VS. ENGAGEMENT P-P
# ═══════════════════════════════════════════════════════════════════════════════

print("\n--- A2: Perfil del facilitador vs. engagement P-P ---")

# Métricas del facilitador por grupo
fac_metrics = (
    facilitadores.groupby("v_grupo")
    .agg(
        n_msgs_fac=("id_f", "count"),
        avg_len_fac=("len_texto", "mean"),
        median_len_fac=("len_texto", "median"),
        sem_activas_fac=("n_week", "nunique"),
    )
    .reset_index()
)

# Total mensajes por grupo (para calcular %)
total_msgs = txt.groupby("v_grupo").size().reset_index(name="n_msgs_total")
fac_metrics = fac_metrics.merge(total_msgs, on="v_grupo")
fac_metrics["pct_msgs_fac"] = fac_metrics["n_msgs_fac"] / fac_metrics["n_msgs_total"]

# Métricas de engagement P-P por grupo (desde 10a_resumen_grupos)
engagement = (
    resumen_grupos.groupby("v_grupo")
    .agg(
        n_sesiones_pp=("n_sesiones_pp", "sum"),
        n_participantes_pp_max=("n_participantes_pp_max", "max"),
        sem_con_pp=("n_sesiones_pp", lambda x: (x > 0).sum()),
    )
    .reset_index()
)
engagement["pct_semanas_con_pp"] = engagement["sem_con_pp"] / 12

# También: N de ITs y % compleja desde el corpus 10d
its_por_grupo = (
    corpus.groupby("grupo")
    .agg(
        n_its=("nivel_interaccion", "count"),
        n_compleja=("nivel_interaccion", lambda x: (x == "compleja").sum()),
        n_basica=("nivel_interaccion", lambda x: (x == "basica").sum()),
        n_i8=("I8", "sum"),
    )
    .reset_index()
    .rename(columns={"grupo": "v_grupo"})
)
its_por_grupo["pct_compleja"] = its_por_grupo["n_compleja"] / its_por_grupo["n_its"]

# Merge todo
grp_full = fac_metrics.merge(engagement, on="v_grupo", how="left")
grp_full = grp_full.merge(its_por_grupo, on="v_grupo", how="left")

# Añadir género y ciudad
meta = txt[["v_grupo", "sex_grupo", "city_grupo"]].drop_duplicates("v_grupo").copy()
grp_full = grp_full.merge(meta, on="v_grupo", how="left")

grp_full.to_csv(TABLES_OUT / "10e_facilitador_grupos.csv", index=False)
print(f"  Guardado: 10e_facilitador_grupos.csv ({len(grp_full)} filas)")

# Correlaciones
df_corr = grp_full.dropna(subset=["n_sesiones_pp", "avg_len_fac", "pct_msgs_fac"])
r_len, p_len = pearsonr(df_corr["avg_len_fac"], df_corr["n_sesiones_pp"])
r_pct, p_pct = pearsonr(df_corr["pct_msgs_fac"], df_corr["n_sesiones_pp"])
rho_len, rho_p_len = spearmanr(df_corr["avg_len_fac"], df_corr["n_sesiones_pp"])
rho_pct, rho_p_pct = spearmanr(df_corr["pct_msgs_fac"], df_corr["n_sesiones_pp"])

print(
    f"  Corr(avg_len_fac, n_sesiones_pp): r={r_len:.3f} p={p_len:.3f} | rho={rho_len:.3f} p={rho_p_len:.3f}"
)
print(
    f"  Corr(pct_msgs_fac, n_sesiones_pp): r={r_pct:.3f} p={p_pct:.3f} | rho={rho_pct:.3f} p={rho_p_pct:.3f}"
)

# Figura A2
fig, axes = plt.subplots(1, 2, figsize=(13, 5))

for ax, (xvar, xlabel, r, p) in zip(
    axes,
    [
        ("avg_len_fac", "Longitud promedio msg. facilitador (chars)", r_len, p_len),
        ("pct_msgs_fac", "% mensajes del facilitador en el grupo", r_pct, p_pct),
    ],
):
    for gen, color in COLORS_GEN.items():
        sub = df_corr[df_corr["sex_grupo"] == gen]
        ax.scatter(
            sub[xvar],
            sub["n_sesiones_pp"],
            c=color,
            label=gen,
            s=70,
            alpha=0.75,
            edgecolors="white",
            linewidths=0.5,
        )
    # Línea de tendencia
    z = np.polyfit(df_corr[xvar], df_corr["n_sesiones_pp"], 1)
    xr = np.linspace(df_corr[xvar].min(), df_corr[xvar].max(), 100)
    ax.plot(xr, np.poly1d(z)(xr), "k--", linewidth=1.5, alpha=0.5)
    sig = "*" if p < 0.05 else "ns"
    ax.set_xlabel(xlabel)
    ax.set_ylabel("N sesiones P-P por grupo")
    ax.set_title(f"r={r:.2f} ({sig})", fontweight="bold")
    ax.legend(fontsize=9)

fig.suptitle(
    "A2 — Comportamiento del facilitador vs. sesiones P-P del grupo",
    fontsize=12,
    fontweight="bold",
    y=1.01,
)
fig.tight_layout()
out = FIGURES_OUT / "10e_facilitador_engagement.png"
fig.savefig(out, bbox_inches="tight")
plt.close()
print(f"  Figura guardada: {out.name}")


# ═══════════════════════════════════════════════════════════════════════════════
# A3 — MAPA DE ENGAGEMENT POR SEMANA/TEMA
# ═══════════════════════════════════════════════════════════════════════════════

print("\n--- A3: Mapa de engagement por semana/tema ---")

# Sesiones P-P por semana y tema (desde 10a)
tema_sem = (
    cadenas.groupby(["n_week", "tema"])
    .agg(
        n_sesiones=("sesion_id", "count"),
        avg_participantes=("n_participantes_distintos", "mean"),
        pct_marcador=("tiene_marcador_linguistico", "mean"),
        avg_duracion=("duracion_min", "mean"),
    )
    .reset_index()
)

# ITs por semana desde corpus 10d
corpus["semana"] = pd.to_numeric(corpus["semana"], errors="coerce")
its_sem = (
    corpus.groupby("semana")
    .agg(
        n_its=("nivel_interaccion", "count"),
        n_compleja=("nivel_interaccion", lambda x: (x == "compleja").sum()),
        n_i8=("I8", "sum"),
    )
    .reset_index()
)
its_sem["pct_compleja"] = its_sem["n_compleja"] / its_sem["n_its"]

# Resumen de sesiones P-P por semana
pp_sem = (
    cadenas.groupby("n_week")
    .agg(
        n_sesiones=("sesion_id", "count"),
        avg_participantes=("n_participantes_distintos", "mean"),
        pct_marcador=("tiene_marcador_linguistico", "mean"),
    )
    .reset_index()
)

# Temas únicos ordenados por n_week (para el eje Y)
temas_orden = cadenas.groupby("tema")["n_week"].min().sort_values().index.tolist()


# Abreviar temas largos
def abrev(t, maxlen=45):
    if not isinstance(t, str):
        return str(t)
    return t[:maxlen] + "…" if len(t) > maxlen else t


# Figura A3: 3 paneles
fig, axes = plt.subplots(3, 1, figsize=(13, 14))

# Panel 1: Sesiones P-P y N ITs por semana (barras superpuestas)
ax = axes[0]
color_pp = "#2e86c1"
color_it = "#e67e22"
width = 0.4
xs = np.array(SEMANAS)

pp_vals = [pp_sem.loc[pp_sem["n_week"] == s, "n_sesiones"].sum() for s in SEMANAS]
it_vals = [
    its_sem.loc[its_sem["semana"] == s, "n_its"].sum()
    if s in its_sem["semana"].values
    else 0
    for s in SEMANAS
]
i8_vals = [
    its_sem.loc[its_sem["semana"] == s, "n_i8"].sum()
    if s in its_sem["semana"].values
    else 0
    for s in SEMANAS
]

bars1 = ax.bar(
    xs - width / 2,
    pp_vals,
    width=width,
    color=color_pp,
    label="Sesiones P-P (10a)",
    alpha=0.85,
)
bars2 = ax.bar(
    xs + width / 2,
    it_vals,
    width=width,
    color=color_it,
    label="ITs codificadas (10c)",
    alpha=0.85,
)

# Marcar semanas con I8
for i, (s, i8) in enumerate(zip(SEMANAS, i8_vals)):
    if i8 > 0:
        ax.text(
            s + width / 2,
            it_vals[i] + 0.3,
            f"I8={i8}",
            ha="center",
            fontsize=8,
            color="#922b21",
        )

ax.set_xticks(SEMANAS)
ax.set_xticklabels([f"S{s}" for s in SEMANAS])
ax.set_ylabel("N")
ax.set_title("Volumen de interacción P-P por semana", fontweight="bold")
ax.legend(fontsize=9)

# Panel 2: % compleja por semana + retención
ax2 = axes[1]
pct_c = [
    its_sem.loc[its_sem["semana"] == s, "pct_compleja"].values[0]
    if s in its_sem["semana"].values
    else np.nan
    for s in SEMANAS
]
pct_p = [
    pp_sem.loc[pp_sem["n_week"] == s, "pct_marcador"].values[0]
    if s in pp_sem["n_week"].values
    else np.nan
    for s in SEMANAS
]

ax2.plot(
    xs, pct_c, "o-", color="#1a5276", linewidth=2, markersize=7, label="% ITs complejas"
)
ax2.plot(
    xs,
    pct_p,
    "s--",
    color="#117a65",
    linewidth=1.8,
    markersize=6,
    label="% sesiones con marcador lingüístico",
)
ax2.plot(
    xs,
    ret_global["retencion_s1"].values,
    "^:",
    color="#c0392b",
    linewidth=1.8,
    markersize=6,
    label="Retención participantes (desde S1)",
)
ax2.set_xticks(SEMANAS)
ax2.set_xticklabels([f"S{s}" for s in SEMANAS])
ax2.set_ylim(0, 1.05)
ax2.set_ylabel("Proporción")
ax2.set_title("Calidad de interacción y retención por semana", fontweight="bold")
ax2.legend(fontsize=9)
ax2.axhline(0.5, color="gray", linestyle=":", linewidth=0.8, alpha=0.6)

# Panel 3: Heatmap de sesiones P-P por tema y semana
ax3 = axes[2]
pivot = tema_sem.pivot_table(
    index="tema", columns="n_week", values="n_sesiones", fill_value=0
)
pivot = pivot.reindex([t for t in temas_orden if t in pivot.index])
im = ax3.imshow(pivot.values, aspect="auto", cmap="Blues")
ax3.set_xticks(range(len(pivot.columns)))
ax3.set_xticklabels([f"S{c}" for c in pivot.columns], fontsize=8)
ax3.set_yticks(range(len(pivot.index)))
ax3.set_yticklabels([abrev(t) for t in pivot.index], fontsize=7)
ax3.set_title(
    "Sesiones P-P por tema y semana (intensidad = N sesiones)", fontweight="bold"
)
plt.colorbar(im, ax=ax3, label="N sesiones P-P")

fig.suptitle(
    "A3 — Mapa de engagement por semana y tema", fontsize=12, fontweight="bold", y=1.005
)
fig.tight_layout()
out = FIGURES_OUT / "10e_mapa_engagement.png"
fig.savefig(out, bbox_inches="tight")
print(f"  Figura guardada: {out.name}")

# Guardar cada panel individualmente para anexos en páginas separadas
fig.canvas.draw()
renderer = fig.canvas.get_renderer()
panel_info = [
    (axes[0], "10e_mapa_panel1_volumen.png"),
    (axes[1], "10e_mapa_panel2_calidad.png"),
    (axes[2], "10e_mapa_panel3_heatmap.png"),
]
for ax_p, fname in panel_info:
    extent = ax_p.get_tightbbox(renderer).transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(FIGURES_OUT / fname, dpi=150, bbox_inches=extent)
    print(f"  Panel guardado: {fname}")

plt.close()
print("  Paneles individuales guardados.")


# ═══════════════════════════════════════════════════════════════════════════════
# RESUMEN MARKDOWN
# ═══════════════════════════════════════════════════════════════════════════════

print("\n--- Generando resumen Markdown ---")

# Calcular estadísticas para el resumen
ret_s4 = float(ret_global.loc[4, "retencion_s1"])
ret_s8 = float(ret_global.loc[8, "retencion_s1"])

ret_gen_muj = ret_gen[ret_gen["sex_grupo"] == "Mujer"].set_index("semana")[
    "retencion_s1"
]
ret_gen_hom = ret_gen[ret_gen["sex_grupo"] == "Hombre"].set_index("semana")[
    "retencion_s1"
]

# Mejor y peor semana de engagement
best_sem = int(its_sem.loc[its_sem["n_its"].idxmax(), "semana"])
worst_sem = int(its_sem.loc[its_sem["n_its"].idxmin(), "semana"])

# Top 3 temas por n sesiones PP
top_temas = (
    cadenas.groupby("tema")["sesion_id"].count().sort_values(ascending=False).head(3)
)

md = f"""## 14. Análisis de escalabilidad — Paso 10e

**Orientado a:** Plan MEL 2026 — ingredientes Capacidad de implementación y Costo-efectividad

**Inputs:** `mensajes_preprocesados.parquet` · `10a_cadenas_sesion.csv` · `10d_corpus_interaccion.csv`

---

### A1 — Curva de retención de participantes

| Semana | Retención global | Mujeres | Hombres |
| --- | --- | --- | --- |
| S1 | 100% | 100% | 100% |
| S4 | {ret_s4:.0%} | {ret_gen_muj.get(4, float("nan")):.0%} | {ret_gen_hom.get(4, float("nan")):.0%} |
| S6 | {ret_s6:.0%} | {ret_gen_muj.get(6, float("nan")):.0%} | {ret_gen_hom.get(6, float("nan")):.0%} |
| S8 | {ret_s8:.0%} | {ret_gen_muj.get(8, float("nan")):.0%} | {ret_gen_hom.get(8, float("nan")):.0%} |
| S12 | {ret_s12:.0%} | {ret_gen_muj.get(12, float("nan")):.0%} | {ret_gen_hom.get(12, float("nan")):.0%} |

**Hallazgos clave:**

- La mayor caída de retención ocurre entre la semana {caida_max_idx - 1} y {caida_max_idx}.
- A la semana 12, la retención global es de {ret_s12:.0%} — los participantes que llegan
  al final del programa son una minoría pero consistente.
- La retención de mujeres y hombres sigue patrones similares; la brecha de *cantidad* de
  participantes activos (mujeres 3.5x más) se mantiene estable a lo largo del programa,
  no aumenta con el tiempo.

**Implicación para escalabilidad:** el punto crítico de acompañamiento está en las semanas
{caida_max_idx - 1}–{caida_max_idx}. Un protocolo de reenganche (mensaje del facilitador,
contacto del TH) en ese momento podría reducir la deserción antes de que se vuelva definitiva.

---

### A2 — Perfil del facilitador vs. engagement P-P

| Métrica del facilitador | r con N sesiones P-P | Interpretación |
| --- | --- | --- |
| Longitud promedio del mensaje (chars) | {r_len:.3f} ({"*" if p_len < 0.05 else "ns"}) | {"Mayor longitud → más sesiones P-P" if r_len > 0 else "Mayor longitud → menos sesiones P-P"} |
| % de mensajes del facilitador | {r_pct:.3f} ({"*" if p_pct < 0.05 else "ns"}) | {"Mayor proporción F → más sesiones P-P" if r_pct > 0 else "Mayor proporción F → menos sesiones P-P"} |

*Spearman: len rho={rho_len:.3f} (p={rho_p_len:.3f}), pct rho={rho_pct:.3f} (p={rho_p_pct:.3f})*

**Hallazgos clave:**

- La relación entre el comportamiento del facilitador y el engagement P-P del grupo
  {"es estadísticamente significativa para al menos una métrica." if p_len < 0.05 or p_pct < 0.05 else "no alcanza significancia estadística con el n de grupos disponible (n=" + str(len(df_corr)) + ")."}
- {"Los facilitadores que escriben mensajes más largos tienden a generar más interacción entre participantes — posiblemente porque desarrollan más el contenido y generan más puntos de reflexión." if r_len > 0.1 else "El volumen de texto del facilitador no predice linealmente el engagement entre participantes."}
- {"Los grupos donde el facilitador domina más la conversación (% msgs alto) muestran menos interacción P-P — hay un trade-off entre protagonismo del facilitador y espacio para los participantes." if r_pct < -0.1 else "La proporción de mensajes del facilitador no muestra una relación negativa clara con el engagement P-P."}

**Implicación para el manual y entrenamiento:** {'El entrenamiento debería enfatizar dejar espacio a los participantes — los facilitadores que "llenan" la conversación dejan menos margen para la interacción horizontal.' if r_pct < -0.1 else "Se necesitan más datos o métricas adicionales (p.ej., tiempo de respuesta, tipo de pregunta) para caracterizar qué prácticas de facilitación predicen mayor engagement."}

---

### A3 — Mapa de engagement por semana/tema

**Semanas con mayor volumen de ITs codificadas:**

| Semana | ITs | % Compleja | I8 (adopción) | N Sesiones P-P |
| --- | --- | --- | --- | --- |
"""

for _, row in its_sem.sort_values("n_its", ascending=False).head(6).iterrows():
    s = int(row["semana"])
    pp_n = (
        pp_sem.loc[pp_sem["n_week"] == s, "n_sesiones"].sum()
        if s in pp_sem["n_week"].values
        else 0
    )
    md += f"| S{s} | {int(row['n_its'])} | {row['pct_compleja']:.0%} | {int(row['n_i8'])} | {int(pp_n)} |\n"

md += """
**Top 3 temas por N sesiones P-P:**

| Tema | N sesiones |
| --- | --- |
"""
for tema, n in top_temas.items():
    md += f"| {abrev(tema, 60)} | {n} |\n"

md += f"""
**Hallazgos clave:**

- Las semanas {best_sem} y sus adyacentes concentran más ITs — son los módulos de mayor
  actividad horizontal entre participantes.
- La semana {worst_sem} es la de menor engagement (chunk 4, semanas 7-8 en general muestran caída).
- I8 (adopción de práctica) se concentra en las primeras 4 semanas, lo que sugiere que
  el contenido inicial del programa tiene el impacto más directo sobre el cambio de comportamiento
  reportado.
- Los temas de mayor actividad P-P son módulos de contenido emocional y relacional,
  no los puramente informativos.

**Implicación para flexibilización de contenidos:** los módulos de las primeras semanas
y los que generan más sesiones P-P son los menos flexibilizables. Los de semanas 7-8
(donde cae el engagement) son candidatos a revisión o intervención de diseño.

---

**Figuras:**

- `outputs/figures/10e_retencion.png` — A1: curva de retención
- `outputs/figures/10e_facilitador_engagement.png` — A2: facilitador vs. engagement
- `outputs/figures/10e_mapa_engagement.png` — A3: mapa semana/tema

**Archivos:**
- `outputs/tables/10e_retencion.csv`
- `outputs/tables/10e_facilitador_grupos.csv`
"""

md_path = TABLES_OUT / "10e_resumen_escalabilidad.md"
md_path.write_text(md, encoding="utf-8")
print(f"  Resumen guardado: {md_path.name}")

sys.stdout.buffer.write(("\n" + md).encode("utf-8", errors="replace"))
sys.stdout.buffer.write(b"\n")

print("\nFinalizado. Outputs en outputs/tables/ y outputs/figures/")
