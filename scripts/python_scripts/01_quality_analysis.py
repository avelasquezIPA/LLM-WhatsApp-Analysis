"""Paso 1: Análisis de calidad de mensajes de WhatsApp - Programa Apapachar
=========================================================================
Evalúa tamaño, informalidad y distribución de los mensajes de texto
antes de procesarlos con el pipeline LLM.

Estrategia de chunking: city_grupo + n_week

Outputs:
  - outputs/tables/01_quality_summary.csv
  - outputs/tables/01_chunks_summary.csv
  - outputs/figures/01_distribucion_longitud.png
  - outputs/figures/01_distribucion_longitud_participantes.png
  - outputs/figures/01_mensajes_por_semana.png
  - outputs/figures/01_mensajes_por_semana_participantes.png
  - outputs/figures/01_flesch_kincaid.png
"""

from __future__ import annotations

import re

import matplotlib.pyplot as plt
import pandas as pd
import textstat
from config_loader import FIGURES_DIR, PROJECT_ROOT, TABLES_DIR, cfg
from scipy import stats as scipy_stats

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
DATA_PATH = PROJECT_ROOT / cfg["data"]["input"]["raw_stata_file"]
OUT_TABLES = TABLES_DIR
OUT_FIGURES = FIGURES_DIR

COL_TYPE = cfg["data"]["columns"]["message_type"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_CITY = cfg["data"]["columns"]["city_group"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_GROUP = cfg["data"]["columns"]["group_id"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_NWORDS = cfg["data"]["columns"]["word_count"]
COL_NCHARS = cfg["data"]["columns"]["char_count"]
COL_LENGTH = cfg["data"]["columns"]["length_type"]
COL_FK_TEXT = cfg["data"]["columns"]["flesch_text"]
COL_FK = cfg["data"]["columns"]["flesch_score"]
COL_INFORM = cfg["data"]["columns"]["informality_rate"]
COL_INF_LING = cfg["data"]["columns"]["linguistic_informality_rate"]

TEXT_TYPE = cfg["data"]["values"]["text_message_type"]
PARTICIPANT = cfg["data"]["values"]["participant_sender"]
FACILITATOR = cfg["data"]["values"]["facilitator_sender"]

SHORT_OFFSET = cfg["analysis"]["message_length"]["short_offset"]
LONG_OFFSET = cfg["analysis"]["message_length"]["long_offset"]
LANG_CODE = cfg["project"]["language"]
TOKENS_RATIO = cfg["analysis"]["words_to_tokens_ratio"]
COLORS_CITY = list(cfg["visualization"]["colors"]["cities"].values())

OUT_TABLES.mkdir(parents=True, exist_ok=True)
OUT_FIGURES.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Carga y filtro
# ---------------------------------------------------------------------------
print("Cargando datos...")
df = pd.read_stata(DATA_PATH)

print(f"  Total filas: {len(df)}")
print(f"  Tipos de mensaje:\n{df[COL_TYPE].value_counts().to_string()}\n")

# Solo mensajes de texto con contenido
txt = df[df[COL_TYPE] == TEXT_TYPE].copy()
txt = txt[txt[COL_TEXT].notna() & (txt[COL_TEXT].str.strip() != "")]
print(f"  Mensajes de texto para análisis: {len(txt)}")

# ---------------------------------------------------------------------------
# 2. Métricas de tamaño
# ---------------------------------------------------------------------------
txt[COL_NWORDS] = txt[COL_TEXT].str.split().str.len()
txt[COL_NCHARS] = txt[COL_TEXT].str.len()

promedio = txt[COL_NWORDS].mean()
txt[COL_LENGTH] = "mediano"
txt.loc[txt[COL_NWORDS] <= promedio - SHORT_OFFSET, COL_LENGTH] = "corto"
txt.loc[txt[COL_NWORDS] >= promedio + LONG_OFFSET, COL_LENGTH] = "largo"

print("=== Distribución de longitud ===")
dist = txt[COL_LENGTH].value_counts()
dist_pct = txt[COL_LENGTH].value_counts(normalize=True).mul(100).round(1)
print(pd.DataFrame({"n": dist, "%": dist_pct}).to_string())

# ---------------------------------------------------------------------------
# 3. Estadísticas por remitente
# ---------------------------------------------------------------------------
print("\n=== Palabras por remitente ===")
stats_rem = txt.groupby(COL_SENDER, observed=True)[COL_NWORDS].describe().round(1)
print(stats_rem.to_string())

# ---------------------------------------------------------------------------
# 4. Legibilidad Flesch-Kincaid (español)
# ---------------------------------------------------------------------------
textstat.set_lang(LANG_CODE)


def limpiar_para_fk(texto: str) -> str:
    """Elimina URLs y emojis/caracteres no textuales antes de calcular FK."""
    t = re.sub(r"http\S+|www\.\S+", "", str(texto))
    t = re.sub(r"[^\w\s\.,;:!?áéíóúüñÁÉÍÓÚÜÑ]", "", t)
    return t.strip()


# Aplicar a todos los mensajes (no solo los largos)
txt[COL_FK_TEXT] = txt[COL_TEXT].apply(limpiar_para_fk)
txt_fk = txt[txt[COL_FK_TEXT].str.len() > 0].copy()
print(
    f"\nCalculando Flesch-Kincaid ({len(txt_fk)} mensajes tras limpiar URLs y emojis)..."
)
txt_fk[COL_FK] = txt_fk[COL_FK_TEXT].apply(textstat.flesch_reading_ease)

# Escala Flesch: 90-100 muy fácil, 60-70 estándar, 0-30 muy difícil
print("\n=== Flesch Reading Ease por remitente (todos los mensajes) ===")
fk_rem = txt_fk.groupby(COL_SENDER, observed=True)[COL_FK].describe().round(1)
print(fk_rem.to_string())

print("\n=== Flesch por ciudad ===")
fk_city = txt_fk.groupby(COL_CITY, observed=True)[COL_FK].describe().round(1)
print(fk_city.to_string())

n_outliers = (txt_fk[COL_FK] < 0).sum()
print(
    f"\n  Nota: {n_outliers} mensajes con FK < 0 (mashing de teclado, 'JAJAJA' etc.) "
    f"representan el {n_outliers / len(txt_fk) * 100:.1f}% del total."
)

# ---------------------------------------------------------------------------
# 5. Análisis de informalidad (tasa de palabras no estándar)
# ---------------------------------------------------------------------------
# Aproximación: palabras con dígitos, repetición de letras, < 3 chars que no
# son artículos/preposiciones comunes, o con signos de puntuación embebidos
STOPWORDS_CORTAS = {
    "a",
    "al",
    "de",
    "el",
    "en",
    "es",
    "la",
    "le",
    "lo",
    "me",
    "mi",
    "no",
    "o",
    "os",
    "se",
    "si",
    "su",
    "te",
    "tu",
    "un",
    "yo",
    "y",
    "e",
    "ni",
    "con",
    "que",
    "por",
    "los",
    "las",
    "una",
    "del",
    "hay",
    "son",
    "muy",
    "fue",
    "ser",
    "nos",
    "ya",
}


def tasa_informalidad(texto: str) -> float:
    # Excluir URLs antes de calcular (igual que en FK)
    t = re.sub(r"http\S+|www\.\S+", "", str(texto))
    # Excluir mensajes que son solo emojis (sin ningún carácter alfabético)
    if not re.search(r"[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]", t):
        return 0.0
    palabras = t.lower().split()
    if not palabras:
        return 0.0
    informales = sum(
        1
        for p in palabras
        if (
            (len(p) < 3 and p not in STOPWORDS_CORTAS)
            or re.search(r"\d", p)
            or re.search(r"(.)\1{2,}", p)  # letras repetidas 3+ veces
            or re.search(r"[^a-záéíóúüñ\-']", p)  # caracteres no estándar
        )
    )
    return informales / len(palabras)


print("\nCalculando tasa de informalidad (puede tomar unos segundos)...")
txt[COL_INFORM] = txt[COL_TEXT].apply(tasa_informalidad)

print("=== Informalidad por remitente ===")
inf_rem = txt.groupby(COL_SENDER, observed=True)[COL_INFORM].describe().round(3)
print(inf_rem.to_string())

# ---------------------------------------------------------------------------
# 5b. Informalidad lingüística (solo lenguaje, sin formato)
# ---------------------------------------------------------------------------
# Mide: abreviaciones de WhatsApp, marcadores de risa y alargamiento vocálico.
# Se extraen solo tokens alfabéticos (se eliminan números, emojis, URLs)
# para que el formato estructurado de los facilitadores no interfiera.
ABREVIACIONES = {
    # Pronombres/conjunciones abreviados
    "q",
    "k",  # que
    "xq",
    "pq",
    "pk",
    "porq",  # porque
    "tb",
    "tbn",
    "tmb",
    "tmbn",  # también
    "d",  # de (ambiguo, pero frecuente en abrev.)
    "bn",
    "bn",  # bien
    # Saludos / despedidas
    "bsos",
    "bss",
    "bs",  # besos
    "slds",
    "sludes",  # saludos
    "gcias",
    "gcias",  # gracias
    # Instrucciones / peticiones
    "xfa",
    "xfav",
    "pf",
    "plis",
    "pls",  # por favor
    "msj",  # mensaje
    "info",  # información
    # Coloquiales frecuentes en Colombia
    "pa",  # para
    "na",  # nada
    "xa",  # para
    "x",  # por
    "weno",  # bueno
    "profe",  # profesor/a (semi-formal)
    "finde",  # fin de semana
    "dnd",  # donde
    "kmo",
    "cmo",  # cómo
    "ntp",  # no te preocupes
    "omg",  # oh my god
    "ok",
    "okok",
    "oki",  # ok
    "jeje",
    "jeje",  # risa (se incluye aquí y en patrón)
}

_RE_RISA = re.compile(r"^j[aeiou]{2,}j[aeiou]*$|^h[aeiou]{3,}$", re.IGNORECASE)
_RE_ALARGAMIENTO = re.compile(r"([aeiouáéíóú])\1{2,}", re.IGNORECASE)
_RE_SOLO_ALFA = re.compile(r"^[a-záéíóúüñ]+$", re.IGNORECASE)


def tasa_informalidad_linguistica(texto: str) -> float:
    """Proporción de tokens lingüísticamente informales sobre total alfabético.

    Excluye URLs y tokens no alfabéticos (números, emojis, símbolos) antes
    de evaluar. Cuenta como informal: abreviaciones de WhatsApp, marcadores
    de risa (jaja/jeje) y alargamiento vocálico (siiii, nooo).
    """
    t = re.sub(r"http\S+|www\.\S+", "", str(texto))
    tokens = t.lower().split()
    # Solo tokens puramente alfabéticos
    alfa = [p for p in tokens if _RE_SOLO_ALFA.match(p)]
    if not alfa:
        return 0.0
    informales = sum(
        1
        for p in alfa
        if p in ABREVIACIONES or _RE_RISA.match(p) or _RE_ALARGAMIENTO.search(p)
    )
    return informales / len(alfa)


print("\nCalculando informalidad lingüística...")
txt[COL_INF_LING] = txt[COL_TEXT].apply(tasa_informalidad_linguistica)

print("=== Informalidad lingüística por remitente ===")
inf_ling = txt.groupby(COL_SENDER, observed=True)[COL_INF_LING].describe().round(3)
print(inf_ling.to_string())

# Pct de mensajes con al menos alguna señal informal
pct_con_inf = (
    txt.groupby(COL_SENDER, observed=True)[COL_INF_LING]
    .apply(lambda x: (x > 0).mean() * 100)
    .round(1)
)
print("\n% de mensajes con al menos un token informal por remitente:")
print(pct_con_inf.to_string())

# ---------------------------------------------------------------------------
# 5. Resumen por ciudad + semana (chunks para el pipeline)
# ---------------------------------------------------------------------------
chunks = (
    txt.groupby([COL_CITY, COL_WEEK], observed=True)
    .agg(
        n_mensajes=(COL_TEXT, "count"),
        n_palabras_total=(COL_NWORDS, "sum"),
        n_palabras_promedio=(COL_NWORDS, "mean"),
        pct_cortos=(COL_LENGTH, lambda x: (x == "corto").mean() * 100),
        pct_largos=(COL_LENGTH, lambda x: (x == "largo").mean() * 100),
        tasa_informalidad_promedio=(COL_INFORM, "mean"),
    )
    .round(2)
    .reset_index()
)

chunks["tokens_aprox"] = (
    (chunks["n_palabras_total"] / TOKENS_RATIO).round(0).astype(int)
)

print("\n=== Chunks city_grupo + n_week (primeros 12) ===")
print(chunks.head(12).to_string(index=False))

print(f"\n  Total chunks: {len(chunks)}")
print(
    f"  Tokens por chunk - min: {chunks['tokens_aprox'].min()}, "
    f"max: {chunks['tokens_aprox'].max()}, "
    f"mediana: {chunks['tokens_aprox'].median():.0f}"
)

# ---------------------------------------------------------------------------
# 6. Guardar tablas
# ---------------------------------------------------------------------------
summary = {
    "total_mensajes_raw": len(df),
    "total_mensajes_texto": len(txt),
    "pct_texto": round(len(txt) / len(df) * 100, 1),
    "promedio_palabras": round(promedio, 1),
    "pct_cortos": round(dist_pct.get("corto", 0), 1),
    "pct_medianos": round(dist_pct.get("mediano", 0), 1),
    "pct_largos": round(dist_pct.get("largo", 0), 1),
    "n_chunks": len(chunks),
    "ciudades": df[COL_CITY].nunique(),
    "semanas": df[COL_WEEK].nunique(),
    "grupos": df[COL_GROUP].nunique(),
    "fecha_inicio": str(df[COL_DATETIME].min().date()),
    "fecha_fin": str(df[COL_DATETIME].max().date()),
}
pd.Series(summary).to_csv(OUT_TABLES / "01_quality_summary.csv", header=["valor"])
chunks.to_csv(OUT_TABLES / "01_chunks_summary.csv", index=False)
print("\nTablas guardadas en outputs/tables/")

# ---------------------------------------------------------------------------
# 7. Figuras
# ---------------------------------------------------------------------------

# Figura 1: Distribución de longitud (palabras)
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("Distribución de longitud de mensajes - Apapachar", fontsize=13)

axes[0].hist(
    txt[COL_NWORDS].clip(upper=100), bins=40, color="#1976D2", edgecolor="white"
)
axes[0].set_xlabel("Número de palabras")
axes[0].set_ylabel("Frecuencia")
axes[0].set_title("Histograma (truncado en 100 palabras)")
axes[0].axvline(
    promedio, color="#D32F2F", linestyle="--", label=f"Media: {promedio:.1f}"
)
axes[0].legend()

tipo_order = ["corto", "mediano", "largo"]
colores = ["#90CAF9", "#1976D2", "#0D47A1"]
axes[1].bar(tipo_order, [dist.get(t, 0) for t in tipo_order], color=colores)
axes[1].set_xlabel("Tipo de mensaje")
axes[1].set_ylabel("Frecuencia")
axes[1].set_title("Corto / Mediano / Largo")
for i, t in enumerate(tipo_order):
    axes[1].text(i, dist.get(t, 0) + 50, f"{dist_pct.get(t, 0):.1f}%", ha="center")

plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_distribucion_longitud.png", dpi=150)
plt.close()

# Figura 2: Mensajes por semana y ciudad
pivot = chunks.pivot(index=COL_WEEK, columns=COL_CITY, values="n_mensajes").fillna(0)
pivot.plot(kind="bar", figsize=(12, 5), colormap="tab10", edgecolor="white")
plt.title("Mensajes de texto por semana y ciudad - Apapachar")
plt.xlabel("Semana del programa")
plt.ylabel("Número de mensajes")
plt.xticks(rotation=0)
plt.legend(title="Ciudad")
plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_mensajes_por_semana.png", dpi=150)
plt.close()

# Figura 3: Flesch-Kincaid por remitente y ciudad (todos los mensajes, sin URLs/emojis)
# Clippeamos outliers extremos (<0) solo para la visualización
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle(
    "Legibilidad Flesch-Kincaid - Todos los mensajes (sin URLs ni emojis) - Apapachar",
    fontsize=12,
)

grupos_rem = [
    txt_fk[txt_fk[COL_SENDER] == r][COL_FK].clip(lower=0).dropna()
    for r in [FACILITATOR, PARTICIPANT]
]
bp = axes[0].boxplot(
    grupos_rem, tick_labels=[FACILITATOR, PARTICIPANT], patch_artist=True
)
bp["boxes"][0].set_facecolor("#1976D2")
bp["boxes"][1].set_facecolor("#388E3C")
axes[0].set_ylabel("Flesch Reading Ease")
axes[0].set_title("Por remitente")
axes[0].axhline(
    60, color="gray", linestyle="--", linewidth=0.8, label="Umbral estándar (60)"
)
axes[0].axhline(
    90, color="lightgray", linestyle=":", linewidth=0.8, label="Muy fácil (90)"
)
axes[0].legend(fontsize=8)
axes[0].set_ylim(-10, 150)

ciudades = txt_fk[COL_CITY].cat.categories.tolist()
grupos_city = [
    txt_fk[txt_fk[COL_CITY] == c][COL_FK].clip(lower=0).dropna() for c in ciudades
]
bp2 = axes[1].boxplot(grupos_city, tick_labels=ciudades, patch_artist=True)
for box, color in zip(bp2["boxes"], COLORS_CITY):
    box.set_facecolor(color)
axes[1].set_ylabel("Flesch Reading Ease")
axes[1].set_title("Por ciudad")
axes[1].axhline(60, color="gray", linestyle="--", linewidth=0.8)
axes[1].set_ylim(-10, 150)

plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_flesch_kincaid.png", dpi=150)
plt.close()

# Figura 3b: FK por ciudad - solo participantes
txt_fk_part = txt_fk[txt_fk[COL_SENDER] == PARTICIPANT]
ciudades_part = txt_fk_part[COL_CITY].cat.categories.tolist()
grupos_city_part = [
    txt_fk_part[txt_fk_part[COL_CITY] == c][COL_FK].clip(lower=0).dropna()
    for c in ciudades_part
]
f_stat, p_anova = scipy_stats.f_oneway(*grupos_city_part)

fig, ax = plt.subplots(figsize=(9, 5))
bp3 = ax.boxplot(grupos_city_part, tick_labels=ciudades_part, patch_artist=True)
for box, color in zip(bp3["boxes"], COLORS_CITY):
    box.set_facecolor(color)
ax.set_ylabel("Flesch Reading Ease")
ax.set_title(
    f"Legibilidad FK por ciudad - Solo participantes (sin facilitadores)\n"
    f"ANOVA: F={f_stat:.3f}, p={p_anova:.3f}"
)
ax.axhline(
    60, color="gray", linestyle="--", linewidth=0.8, label="Umbral estándar (60)"
)
ax.axhline(90, color="lightgray", linestyle=":", linewidth=0.8, label="Muy fácil (90)")
ax.set_ylim(-10, 150)
ax.legend(fontsize=8)
plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_flesch_kincaid_participantes_ciudad.png", dpi=150)
plt.close()

print("Figuras guardadas en outputs/figures/")

# ---------------------------------------------------------------------------
# 8. Figuras solo participantes (sin facilitadores)
# ---------------------------------------------------------------------------
txt_part = txt[txt[COL_SENDER] == PARTICIPANT].copy()

chunks_part = (
    txt_part.groupby([COL_CITY, COL_WEEK], observed=True)
    .agg(
        n_mensajes=(COL_TEXT, "count"),
        n_palabras_total=(COL_NWORDS, "sum"),
    )
    .reset_index()
)

promedio_part = txt_part[COL_NWORDS].mean()
dist_part = txt_part[COL_LENGTH].value_counts()
dist_part_pct = txt_part[COL_LENGTH].value_counts(normalize=True).mul(100).round(1)

# Figura 1 participantes: distribución de longitud
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle(
    "Distribución de longitud de mensajes - Solo participantes (sin facilitadores)",
    fontsize=13,
)

axes[0].hist(
    txt_part[COL_NWORDS].clip(upper=100), bins=40, color="#388E3C", edgecolor="white"
)
axes[0].set_xlabel("Número de palabras")
axes[0].set_ylabel("Frecuencia")
axes[0].set_title("Histograma (truncado en 100 palabras)")
axes[0].axvline(
    promedio_part,
    color="#D32F2F",
    linestyle="--",
    label=f"Media: {promedio_part:.1f}",
)
axes[0].legend()

tipo_order = ["corto", "mediano", "largo"]
colores_part = ["#A5D6A7", "#388E3C", "#1B5E20"]
axes[1].bar(
    tipo_order,
    [dist_part.get(t, 0) for t in tipo_order],
    color=colores_part,
)
axes[1].set_xlabel("Tipo de mensaje")
axes[1].set_ylabel("Frecuencia")
axes[1].set_title("Corto / Mediano / Largo")
for i, t in enumerate(tipo_order):
    axes[1].text(
        i, dist_part.get(t, 0) + 10, f"{dist_part_pct.get(t, 0):.1f}%", ha="center"
    )

plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_distribucion_longitud_participantes.png", dpi=150)
plt.close()

# Figura 2 participantes: mensajes por semana y ciudad
pivot_part = chunks_part.pivot(
    index=COL_WEEK, columns=COL_CITY, values="n_mensajes"
).fillna(0)
pivot_part.plot(kind="bar", figsize=(12, 5), colormap="tab10", edgecolor="white")
plt.title("Mensajes por semana y ciudad - Solo participantes (sin facilitadores)")
plt.xlabel("Semana del programa")
plt.ylabel("Número de mensajes")
plt.xticks(rotation=0)
plt.legend(title="Ciudad")
plt.tight_layout()
plt.savefig(OUT_FIGURES / "01_mensajes_por_semana_participantes.png", dpi=150)
plt.close()

print("Figuras de participantes guardadas en outputs/figures/")
print("\nPaso 1 completado.")
