"""Paso 10a: Detección de cadenas de interacción participante-participante (P-P)
=============================================================================
Identifica sesiones de actividad dentro de cada grupo WhatsApp donde
participantes se responden entre sí (no solo al facilitador), como proxy
de interacción horizontal entre pares.

Metodología basada en Dedios-Sanguineti et al. (2025):
  - La unidad de análisis es v_grupo + n_week (no ciudad-semana), ya que
    los participantes solo interactúan dentro de su propio grupo.
  - Cadena estricta: secuencia de mensajes P consecutivos (≥2 participantes
    distintos) sin ningún mensaje de facilitador en medio.
  - Cadena por sesión: ventana de actividad (gap < UMBRAL_MINUTOS entre
    mensajes consecutivos) con ≥2 participantes distintos activos, aunque
    el facilitador intervenga entre ellos.
  - Marcadores lingüísticos: palabras o frases que indican respuesta
    explícita a otro participante.

Consideración clave: el 76% de los mensajes son de facilitadores. La
interacción horizontal P-P es la minoría y requiere detección cuidadosa.

Input:
  - data/clean/mensajes_preprocesados.parquet

Output:
  - outputs/tables/10a_cadenas_sesion.csv    (una fila por sesión P-P)
  - outputs/tables/10a_cadenas_estrictas.csv (una fila por cadena estricta)
  - outputs/tables/10a_resumen_grupos.csv    (una fila por v_grupo-semana)
  - outputs/figures/10a_distribucion_cadenas.png
"""

from __future__ import annotations

import re

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd
from config_loader import FIGURES_DIR, PROJECT_ROOT, TABLES_DIR, cfg

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
MENSAJES_PATH = PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
OUT_TABLES = TABLES_DIR
OUT_FIGURES = FIGURES_DIR

UMBRAL_MINUTOS = cfg["analysis"]["interaction"]["session_gap_minutes"]
MIN_PARTICIPANTES = cfg["analysis"]["interaction"]["min_participants_per_session"]

COL_TYPE = cfg["data"]["columns"]["message_type"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_GROUP = cfg["data"]["columns"]["group_id"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_CITY = cfg["data"]["columns"]["city_group"]
COL_THEME = cfg["data"]["columns"]["theme"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_PARTICIPANT_ID = cfg["data"]["columns"]["participant_id"]
TEXT_TYPE = cfg["data"]["values"]["text_message_type"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]
FACILITATOR = cfg["data"]["values"]["facilitator_sender"]

CIUDADES_COLORES = cfg["visualization"]["colors"]["cities"]
CITIES = cfg["project"]["cities"]

# Marcadores lingüísticos de respuesta explícita entre participantes
PATRONES_RESPUESTA = [
    r"\byo tambi[eé]n\b",
    r"\bestoy de acuerdo\b",
    r"\bde acuerdo\b",
    r"\bcomparto\b",
    r"\btienes? raz[oó]n\b",
    r"\bcomo (dijo|dice|mencion[oó]|comenta|dijiste)\b",
    r"\bigual que\b",
    r"\btambi[eé]n (me pasa|me pas[oó]|pienso|creo|considero)\b",
    r"\ben mi caso tambi[eé]n\b",
    r"\ba m[ií] tambi[eé]n\b",
    r"\bcon raz[oó]n\b",
    r"\bexacto\b",
    r"\bexactamente\b",
    r"\bas[ií] mismo\b",
    r"\bnosotras?\b",  # identidad compartida grupal
    r"\bcomo (grupo|todas?|todos?)\b",
]
RE_RESPUESTA = re.compile("|".join(PATRONES_RESPUESTA), re.IGNORECASE)

# ---------------------------------------------------------------------------
# 1. Cargar y preparar datos
# ---------------------------------------------------------------------------
print("Cargando datos...")
df = pd.read_parquet(MENSAJES_PATH)
txt = df[df[COL_TYPE] == TEXT_TYPE].copy()
txt = txt.sort_values([COL_GROUP, COL_WEEK, COL_DATETIME]).reset_index(drop=True)

# Extraer género del grupo desde el nombre del grupo (GH = hombres, GM = mujeres)
txt["genero_grupo"] = txt[COL_GROUP].str[:2].map({"GH": "Hombres", "GM": "Mujeres"})

grupos_activos = txt[COL_GROUP].unique()
print(f"  Mensajes de texto: {len(txt)}")
print(f"  Grupos activos: {len(grupos_activos)}")
print(
    f"  Participantes únicos: {txt[txt[COL_SENDER] == PARTICIPANT][COL_PARTICIPANT_ID].nunique()}"
)
print(f"  Semanas: {txt[COL_WEEK].min()} - {txt[COL_WEEK].max()}")

# ---------------------------------------------------------------------------
# 2. Detectar sesiones de actividad (gap < UMBRAL entre mensajes consecutivos)
# ---------------------------------------------------------------------------
print(f"\nDetectando sesiones (umbral gap: {UMBRAL_MINUTOS} min)...")

registros_sesion = []
registros_estricta = []

for (v_grupo, n_week), grupo in txt.groupby([COL_GROUP, COL_WEEK], observed=True):
    grupo = grupo.sort_values(COL_DATETIME).reset_index(drop=True)
    if len(grupo) == 0:
        continue

    ciudad = grupo[COL_CITY].iloc[0]
    genero_grupo = grupo["genero_grupo"].iloc[0]
    tema = grupo[COL_THEME].iloc[0] if COL_THEME in grupo.columns else ""

    # --- 2a. Sesiones por ventana temporal ---
    grupo["gap_min"] = grupo[COL_DATETIME].diff().dt.total_seconds().div(60).fillna(0)
    grupo["sesion_id"] = (grupo["gap_min"] > UMBRAL_MINUTOS).cumsum()

    for sesion_id, sesion in grupo.groupby("sesion_id"):
        participantes_sesion = sesion[sesion[COL_SENDER] == PARTICIPANT]
        ids_distintos = participantes_sesion[COL_PARTICIPANT_ID].nunique()

        if ids_distintos < MIN_PARTICIPANTES:
            continue

        n_msgs_total = len(sesion)
        n_msgs_p = len(participantes_sesion)
        duracion = (
            sesion[COL_DATETIME].max() - sesion[COL_DATETIME].min()
        ).total_seconds() / 60

        # Revisar marcadores lingüísticos en mensajes de participantes
        tiene_marcador = (
            participantes_sesion[COL_TEXT]
            .apply(lambda t: bool(RE_RESPUESTA.search(str(t))))
            .any()
        )

        registros_sesion.append(
            {
                "v_grupo": v_grupo,
                "city_grupo": ciudad,
                "genero_grupo": genero_grupo,
                "n_week": n_week,
                "tema": str(tema),
                "sesion_id": int(sesion_id),
                "datetime_inicio": sesion[COL_DATETIME].min(),
                "datetime_fin": sesion[COL_DATETIME].max(),
                "duracion_min": round(duracion, 1),
                "n_msgs_total": n_msgs_total,
                "n_msgs_participantes": n_msgs_p,
                "n_participantes_distintos": ids_distintos,
                "pct_msgs_p": round(n_msgs_p / n_msgs_total * 100, 1),
                "tiene_marcador_linguistico": tiene_marcador,
            }
        )

    # --- 2b. Cadenas estrictas (sin facilitador en medio) ---
    cadena_actual = []
    for _, row in grupo.iterrows():
        if row[COL_SENDER] == FACILITATOR:
            # Cerrar cadena actual si tiene ≥ MIN_PARTICIPANTES distintos
            ids_en_cadena = {m[COL_PARTICIPANT_ID] for m in cadena_actual}
            if len(ids_en_cadena) >= MIN_PARTICIPANTES:
                msgs_df = pd.DataFrame(cadena_actual)
                tiene_marcador = (
                    msgs_df[COL_TEXT]
                    .apply(lambda t: bool(RE_RESPUESTA.search(str(t))))
                    .any()
                )
                duracion = (
                    msgs_df[COL_DATETIME].max() - msgs_df[COL_DATETIME].min()
                ).total_seconds() / 60
                registros_estricta.append(
                    {
                        "v_grupo": v_grupo,
                        "city_grupo": ciudad,
                        "genero_grupo": genero_grupo,
                        "n_week": n_week,
                        "tema": str(tema),
                        "datetime_inicio": msgs_df[COL_DATETIME].min(),
                        "datetime_fin": msgs_df[COL_DATETIME].max(),
                        "duracion_min": round(duracion, 1),
                        "n_msgs": len(msgs_df),
                        "n_participantes_distintos": len(ids_en_cadena),
                        "ids_participantes": "|".join(sorted(ids_en_cadena)),
                        "tiene_marcador_linguistico": tiene_marcador,
                    }
                )
            cadena_actual = []
        else:
            cadena_actual.append(row.to_dict())

    # Procesar cadena final si quedó abierta
    ids_en_cadena = {m[COL_PARTICIPANT_ID] for m in cadena_actual}
    if len(ids_en_cadena) >= MIN_PARTICIPANTES:
        msgs_df = pd.DataFrame(cadena_actual)
        tiene_marcador = (
            msgs_df[COL_TEXT].apply(lambda t: bool(RE_RESPUESTA.search(str(t)))).any()
        )
        duracion = (
            msgs_df[COL_DATETIME].max() - msgs_df[COL_DATETIME].min()
        ).total_seconds() / 60
        registros_estricta.append(
            {
                "v_grupo": v_grupo,
                "city_grupo": ciudad,
                "genero_grupo": genero_grupo,
                "n_week": n_week,
                "tema": str(tema),
                "datetime_inicio": msgs_df[COL_DATETIME].min(),
                "datetime_fin": msgs_df[COL_DATETIME].max(),
                "duracion_min": round(duracion, 1),
                "n_msgs": len(msgs_df),
                "n_participantes_distintos": len(ids_en_cadena),
                "ids_participantes": "|".join(sorted(ids_en_cadena)),
                "tiene_marcador_linguistico": tiene_marcador,
            }
        )

df_sesiones = pd.DataFrame(registros_sesion)
df_estrictas = pd.DataFrame(registros_estricta)

print(f"  Sesiones P-P detectadas (ventana {UMBRAL_MINUTOS} min): {len(df_sesiones)}")
print(f"  Cadenas P-P estrictas (sin facilitador): {len(df_estrictas)}")

# ---------------------------------------------------------------------------
# 3. Resumen por grupo-semana
# ---------------------------------------------------------------------------
print("\nGenerando resumen por grupo-semana...")

# Base: todos los v_grupo x n_week con mensajes
base = (
    txt.groupby([COL_GROUP, COL_WEEK], observed=True)
    .agg(
        city_grupo=(COL_CITY, "first"),
        genero_grupo=("genero_grupo", "first"),
        tema=(COL_THEME, "first"),
        n_msgs_total=(COL_TEXT, "count"),
        n_msgs_facilitador=(COL_SENDER, lambda x: (x == FACILITATOR).sum()),
        n_msgs_participante=(COL_SENDER, lambda x: (x == PARTICIPANT).sum()),
        n_participantes_distintos=(
            COL_PARTICIPANT_ID,
            lambda x: x[txt.loc[x.index, COL_SENDER] == PARTICIPANT].nunique(),
        ),
    )
    .reset_index()
)
base.rename(columns={COL_GROUP: "v_grupo", COL_WEEK: "n_week"}, inplace=True)
base["pct_msgs_participante"] = (
    base["n_msgs_participante"] / base["n_msgs_total"] * 100
).round(1)

# Agregar conteos de cadenas
if len(df_sesiones) > 0:
    cadenas_por_gw = (
        df_sesiones.groupby(["v_grupo", "n_week"])
        .agg(
            n_sesiones_pp=("sesion_id", "count"),
            n_sesiones_con_marcador=("tiene_marcador_linguistico", "sum"),
            n_participantes_pp_max=("n_participantes_distintos", "max"),
            duracion_sesion_media=("duracion_min", "mean"),
            n_msgs_pp_total=("n_msgs_participantes", "sum"),
        )
        .round(1)
        .reset_index()
    )
    base = base.merge(cadenas_por_gw, on=["v_grupo", "n_week"], how="left")
else:
    base["n_sesiones_pp"] = 0
    base["n_sesiones_con_marcador"] = 0

if len(df_estrictas) > 0:
    estrictas_por_gw = (
        df_estrictas.groupby(["v_grupo", "n_week"])
        .agg(n_cadenas_estrictas=("n_msgs", "count"))
        .reset_index()
    )
    base = base.merge(estrictas_por_gw, on=["v_grupo", "n_week"], how="left")
else:
    base["n_cadenas_estrictas"] = 0

cols_numericas = [
    "n_sesiones_pp",
    "n_sesiones_con_marcador",
    "n_participantes_pp_max",
    "duracion_sesion_media",
    "n_msgs_pp_total",
    "n_cadenas_estrictas",
]
for col in cols_numericas:
    if col in base.columns:
        base[col] = base[col].fillna(0)
base["n_sesiones_pp"] = base["n_sesiones_pp"].astype(int)
base["n_cadenas_estrictas"] = base["n_cadenas_estrictas"].astype(int)
base = base[base["n_msgs_total"] > 0].copy()

# ---------------------------------------------------------------------------
# 4. Estadísticas generales en consola
# ---------------------------------------------------------------------------
print("\n=== Estadísticas globales ===")
total_gw = len(base)
gw_con_pp = (base["n_sesiones_pp"] > 0).sum()
print(f"  Grupo-semanas totales con mensajes: {total_gw}")
print(
    f"  Grupo-semanas con al menos 1 sesión P-P: {gw_con_pp} ({gw_con_pp / total_gw * 100:.1f}%)"
)

if len(df_sesiones) > 0:
    print(f"\n  Sesiones P-P (ventana {UMBRAL_MINUTOS} min):")
    print(f"    Total: {len(df_sesiones)}")
    print(
        f"    Con marcador lingüístico: {df_sesiones['tiene_marcador_linguistico'].sum()} "
        f"({df_sesiones['tiene_marcador_linguistico'].mean() * 100:.1f}%)"
    )
    print(
        f"    Participantes distintos por sesión (media): "
        f"{df_sesiones['n_participantes_distintos'].mean():.1f}"
    )
    print(f"    Duración media sesión: {df_sesiones['duracion_min'].mean():.0f} min")
    print(
        f"    N mensajes P por sesión (media): {df_sesiones['n_msgs_participantes'].mean():.1f}"
    )

if len(df_estrictas) > 0:
    print("\n  Cadenas estrictas (sin facilitador):")
    print(f"    Total: {len(df_estrictas)}")
    print(
        f"    Con marcador lingüístico: {df_estrictas['tiene_marcador_linguistico'].sum()} "
        f"({df_estrictas['tiene_marcador_linguistico'].mean() * 100:.1f}%)"
    )
    print(f"    N mensajes por cadena (media): {df_estrictas['n_msgs'].mean():.1f}")

print("\n=== Sesiones P-P por ciudad ===")
if len(df_sesiones) > 0:
    by_city = (
        df_sesiones.groupby("city_grupo")
        .agg(
            n_sesiones=("sesion_id", "count"),
            n_con_marcador=("tiene_marcador_linguistico", "sum"),
            part_distintos_media=("n_participantes_distintos", "mean"),
        )
        .round(2)
    )
    print(by_city.to_string())

print("\n=== Sesiones P-P por género de grupo ===")
if len(df_sesiones) > 0:
    by_gen = (
        df_sesiones.groupby("genero_grupo")
        .agg(
            n_sesiones=("sesion_id", "count"),
            n_con_marcador=("tiene_marcador_linguistico", "sum"),
            part_distintos_media=("n_participantes_distintos", "mean"),
        )
        .round(2)
    )
    print(by_gen.to_string())

print("\n=== Evolución temporal: sesiones P-P por semana ===")
if len(df_sesiones) > 0:
    by_week = df_sesiones.groupby("n_week").agg(
        n_sesiones=("sesion_id", "count"),
        n_con_marcador=("tiene_marcador_linguistico", "sum"),
    )
    print(by_week.to_string())

# Top grupo-semanas con más interacción P-P
print("\n=== Top 10 grupo-semanas por sesiones P-P ===")
top = base.nlargest(10, "n_sesiones_pp")[
    [
        "v_grupo",
        "n_week",
        "city_grupo",
        "genero_grupo",
        "tema",
        "n_msgs_participante",
        "n_sesiones_pp",
        "n_cadenas_estrictas",
        "n_sesiones_con_marcador",
    ]
]
print(top.to_string(index=False))

# ---------------------------------------------------------------------------
# 5. Guardar tablas
# ---------------------------------------------------------------------------
print("\nGuardando tablas...")
if len(df_sesiones) > 0:
    df_sesiones.to_csv(OUT_TABLES / "10a_cadenas_sesion.csv", index=False)
    print(f"  10a_cadenas_sesion.csv: {len(df_sesiones)} filas")
if len(df_estrictas) > 0:
    df_estrictas.to_csv(OUT_TABLES / "10a_cadenas_estrictas.csv", index=False)
    print(f"  10a_cadenas_estrictas.csv: {len(df_estrictas)} filas")
base.to_csv(OUT_TABLES / "10a_resumen_grupos.csv", index=False)
print(f"  10a_resumen_grupos.csv: {len(base)} filas")

# ---------------------------------------------------------------------------
# 6. Figuras
# ---------------------------------------------------------------------------
print("\nGenerando figuras...")

fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle(
    f"Interacción participante-participante (P-P) — Umbral sesión: {UMBRAL_MINUTOS} min\n"
    "Basado en Dedios-Sanguineti et al. (2025)",
    fontsize=12,
    y=1.01,
)

COLORES_CIUDAD = CIUDADES_COLORES

# Panel 1: Sesiones P-P por semana (línea)
ax = axes[0, 0]
if len(df_sesiones) > 0:
    por_semana = (
        df_sesiones.groupby(["n_week", "city_grupo"]).size().unstack(fill_value=0)
    )
    for ciudad in CITIES:
        if ciudad in por_semana.columns:
            ax.plot(
                por_semana.index,
                por_semana[ciudad],
                marker="o",
                label=ciudad,
                color=COLORES_CIUDAD.get(ciudad),
                linewidth=1.5,
                markersize=4,
            )
ax.set_title("Sesiones P-P por semana y ciudad", fontsize=10)
ax.set_xlabel("Semana")
ax.set_ylabel("N sesiones P-P")
ax.xaxis.set_major_locator(mticker.MultipleLocator(1))
ax.legend(fontsize=8)
ax.grid(axis="y", alpha=0.3)

# Panel 2: Distribución de participantes distintos por sesión
ax = axes[0, 1]
if len(df_sesiones) > 0:
    max_part = df_sesiones["n_participantes_distintos"].max()
    counts = df_sesiones["n_participantes_distintos"].value_counts().sort_index()
    ax.bar(counts.index, counts.values, color="#1976D2", edgecolor="white")
    for x, y in zip(counts.index, counts.values):
        ax.text(x, y + 0.5, str(y), ha="center", fontsize=9, fontweight="bold")
ax.set_title("Participantes distintos por sesión P-P", fontsize=10)
ax.set_xlabel("N participantes distintos")
ax.set_ylabel("N sesiones")
ax.set_xticks(range(2, int(max_part) + 1 if len(df_sesiones) > 0 else 3))

# Panel 3: Heatmap grupos x semanas (n sesiones P-P)
ax = axes[1, 0]
if len(df_sesiones) > 0:
    pivot = base.pivot_table(
        index="v_grupo",
        columns="n_week",
        values="n_sesiones_pp",
        fill_value=0,
    )
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, fontsize=7)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=7)
    ax.set_title("Heatmap: sesiones P-P por grupo y semana", fontsize=10)
    ax.set_xlabel("Semana")
    ax.set_ylabel("Grupo")
    plt.colorbar(im, ax=ax, label="N sesiones")

# Panel 4: % mensajes P en sesiones P-P vs. total, por ciudad
ax = axes[1, 1]
if len(df_sesiones) > 0:
    # Total mensajes P por ciudad
    total_p_ciudad = (
        txt[txt[COL_SENDER] == PARTICIPANT].groupby(COL_CITY, observed=True).size()
    )
    # Mensajes P que cayeron en sesiones P-P
    pp_p_ciudad = df_sesiones.groupby("city_grupo")["n_msgs_participantes"].sum()
    pct = (pp_p_ciudad / total_p_ciudad * 100).fillna(0).round(1)

    ciudades = pct.index.tolist()
    colores = [COLORES_CIUDAD.get(c, "#9E9E9E") for c in ciudades]
    bars = ax.bar(ciudades, pct.values, color=colores, edgecolor="white")
    for bar, val in zip(bars, pct.values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.3,
            f"{val:.1f}%",
            ha="center",
            fontsize=9,
            fontweight="bold",
        )
ax.set_title("% mensajes de participantes en sesiones P-P", fontsize=10)
ax.set_ylabel("% del total de mensajes de participantes")
ax.set_ylim(0, 100)
ax.axhline(50, color="gray", linestyle="--", linewidth=0.8, label="50%")
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig(OUT_FIGURES / "10a_distribucion_cadenas.png", dpi=150, bbox_inches="tight")
print("  10a_distribucion_cadenas.png guardado.")

# Guardar cada panel individualmente (recortando el bbox de cada eje)
panel_info = [
    (axes[0, 0], "10a_panel1_sesiones_semana.png"),
    (axes[0, 1], "10a_panel2_participantes_sesion.png"),
    (axes[1, 0], "10a_panel3_heatmap_grupos.png"),
    (axes[1, 1], "10a_panel4_pct_mensajes_pp.png"),
]
fig.canvas.draw()  # forzar renderizado para obtener coordenadas
for ax_panel, fname in panel_info:
    extent = ax_panel.get_tightbbox(fig.canvas.get_renderer())
    extent = extent.transformed(fig.dpi_scale_trans.inverted())
    fig.savefig(OUT_FIGURES / fname, dpi=150, bbox_inches=extent)
    print(f"  {fname} guardado.")

plt.close()
print("  Paneles individuales guardados.")

print("\nScript 10a completado.")
