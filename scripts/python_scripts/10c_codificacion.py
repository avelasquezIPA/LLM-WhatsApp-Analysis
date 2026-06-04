"""Paso 10c: Codificación a escala — un Excel por chunk
=======================================================
Genera outputs/tables/10c_chunkN.xlsx (N=1..6) para cada uno de los
6 chunks de 8 grupos representativos (semanas 1-2, 3-4, ..., 11-12).

Cada Excel tiene la misma estructura que el piloto (10b):
  - Guia_indicadores
  - Una hoja de mensajes por grupo (nombre: GRUPO_sN)
  - Una hoja de codificación (nombre: Chunk_N)

Los grupos representativos se seleccionaron en el Paso 10c:
  - Semanas impares -> grupo de mujeres más activo por ciudad
  - Semanas pares  -> grupo de hombres más activo por ciudad
  Ver outputs/tables/10c_grupos_representativos.csv

Input:
  - data/clean/mensajes_preprocesados.parquet
  - outputs/tables/10a_cadenas_sesion.csv

Output:
  - outputs/tables/10c_chunk1.xlsx … outputs/tables/10c_chunk6.xlsx
"""

from __future__ import annotations

import pandas as pd
from config_loader import PROJECT_ROOT, TABLES_DIR, cfg

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
PROJECT_NAME = cfg["project"]["name"]
ADAPTATION_KEY = f"Adaptación {PROJECT_NAME}"

COL_GROUP = cfg["data"]["columns"]["group_id"]
COL_WEEK = cfg["data"]["columns"]["week_number"]
COL_DATETIME = cfg["data"]["columns"]["datetime"]
COL_SENDER = cfg["data"]["columns"]["sender"]
COL_PARTICIPANT_ID = cfg["data"]["columns"]["participant_id"]
COL_TYPE = cfg["data"]["columns"]["message_type"]
COL_TEXT = cfg["data"]["columns"]["message_text"]
COL_THEME = cfg["data"]["columns"]["theme"]

# ---------------------------------------------------------------------------
# Guía de indicadores (construida desde config.yaml)
# ---------------------------------------------------------------------------
GUIA_INDICADORES = [
    {
        "Nivel": ind["level"],
        "N": ind["id"],
        "Indicador": ind["name"],
        "Definición (Dedios et al.)": ind["definition_dedios"].strip(),
        ADAPTATION_KEY: ind["adaptation"].strip(),
        "Código en plantilla": ind["template_code"],
    }
    for ind in cfg["coding"]["indicators"]
]

_indicator_codes = [ind["template_code"] for ind in cfg["coding"]["indicators"]]

COLS_PLANTILLA = [
    "grupo",
    "semana",
    "ciudad",
    "genero",
    "interaccion_id",
    "datetime_inicio",
    "datetime_fin",
    "n_mensajes",
    "ids_participantes",
    "resumen_tematica",
    *_indicator_codes,
    "nivel_interaccion",
    "citas_relevantes",
    "notas",
]

NIVEL_INSTRUCCION = (
    "nivel_interaccion: 'stance-only' si solo I1=1; "
    "'basica' si I2/I3/I4 ≥ 1; 'compleja' si I5/I6/I7 ≥ 1. Tomar el más alto."
)

# ---------------------------------------------------------------------------
# Chunks: grupos representativos e ITs codificadas
# ---------------------------------------------------------------------------
# Formato grupos: (v_grupo, semana, ciudad, genero)
# Formato ITs: lista de dicts con claves de COLS_PLANTILLA

CHUNKS: list[dict] = [
    # ------------------------------------------------------------------
    # Chunk 1 — semanas 1–2
    # ------------------------------------------------------------------
    {
        "num": 1,
        "semanas": "1-2",
        "grupos": [
            ("GMB3", 1, "Bogotá", "Mujeres"),
            ("GHB1", 2, "Bogotá", "Hombres"),
            ("GMN13", 1, "Neiva", "Mujeres"),
            ("GHN18", 2, "Neiva", "Hombres"),
            ("GMS4", 1, "Soacha", "Mujeres"),
            ("GHS6", 2, "Soacha", "Hombres"),
            ("GMV10", 1, "Valledupar", "Mujeres"),
            ("GHV7", 2, "Valledupar", "Hombres"),
        ],
        "its": [
            {
                "grupo": "GMB3",
                "semana": 1,
                "ciudad": "Bogotá",
                "genero": "Mujer",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-24 12:28",
                "datetime_fin": "2024-09-24 16:28",
                "n_mensajes": 10,
                "ids_participantes": "P0971M|P0748M|P0397M|P0814M|P0659M|P0203M|P0529M|P0492M|P0417M|P0962M",
                "resumen_tematica": "Retos de la maternidad",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "basica",
                "notas": "Interacción moderada de inicio; madres comparten retos brevemente y el facilitador activa el intercambio. El consenso emerge como validación mutua ('a mí también me pasa').",
            },
            {
                "grupo": "GMB3",
                "semana": 1,
                "ciudad": "Bogotá",
                "genero": "Mujer",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-09-24 17:49",
                "datetime_fin": "2024-09-25 17:42",
                "n_mensajes": 5,
                "ids_participantes": "P0417M|P0132M|P0397M|P0659M|P0748M",
                "resumen_tematica": "Retos de crianza compartida con la pareja",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 1,
                "I6_moral": 1,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "compleja",
                "notas": "Discusión más rica sobre corresponsabilidad; emerge juicio moral explícito sobre lo que 'debería' hacer la pareja y co-construcción de normalidad ('eso es lo que pasa en la mayoría de casas').",
            },
            {
                "grupo": "GHB1",
                "semana": 2,
                "ciudad": "Bogotá",
                "genero": "Hombre",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-29 19:04",
                "datetime_fin": "2024-09-29 20:34",
                "n_mensajes": 4,
                "ids_participantes": "P0510H|N00047|P1139M|P0498H",
                "resumen_tematica": "Actividades Tiempo Apapacho con los hijos",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 1,
                "nivel_interaccion": "stance-only",
                "notas": "Padres reportan actividades individuales sin generar respuesta entre ellos. Alta I8 pero sin diálogo P-P: la adopción de práctica no genera discusión.",
            },
            {
                "grupo": "GHB1",
                "semana": 2,
                "ciudad": "Bogotá",
                "genero": "Hombre",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-10-01 19:30",
                "datetime_fin": "2024-10-01 20:45",
                "n_mensajes": 3,
                "ids_participantes": "P1039H|P0498H",
                "resumen_tematica": "Reflexión sobre tecnología vs tiempo con los hijos",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 1,
                "I7_identidad": 1,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "compleja",
                "notas": "La imagen del padre distraído con celular activa reflexión colectiva fuerte. I7 clara: 'nosotros como papás queremos mejorar'. I6 emerge como autocrítica moral compartida.",
            },
            {
                "grupo": "GMN13",
                "semana": 1,
                "ciudad": "Neiva",
                "genero": "Mujer",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-24 13:20",
                "datetime_fin": "2024-09-24 13:35",
                "n_mensajes": 12,
                "ids_participantes": "P1328M|P1320M|P0943M|P0816M",
                "resumen_tematica": "Momentos divertidos y travesuras de bebés",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "basica",
                "notas": "Intercambio cálido y lúdico; las anécdotas generan reconocimiento mutuo explícito ('jaja yo también', 'igualito mi hijo'). Tono positivo, alta densidad de respuestas P-P.",
            },
            {
                "grupo": "GMN13",
                "semana": 1,
                "ciudad": "Neiva",
                "genero": "Mujer",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-09-24 13:43",
                "datetime_fin": "2024-09-24 14:17",
                "n_mensajes": 5,
                "ids_participantes": "P0592M|P1320M|P1347M|P1328M|P1245M",
                "resumen_tematica": "Retos de la maternidad",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 1,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "basica",
                "notas": "Una participante reconoce cambio de perspectiva explícito ('nunca lo había visto así'). I4 claro y bien localizado.",
            },
            {
                "grupo": "GMN13",
                "semana": 1,
                "ciudad": "Neiva",
                "genero": "Mujer",
                "interaccion_id": "IT_03",
                "datetime_inicio": "2024-09-24 17:54",
                "datetime_fin": "2024-09-24 18:22",
                "n_mensajes": 2,
                "ids_participantes": "P1320M|P1395M",
                "resumen_tematica": "Retos de crianza con la pareja",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "stance-only",
                "notas": "Solo posturas individuales sin respuesta P-P. El tema de la pareja puede generar inhibición; cada una comparte sin engancharse con las demás.",
            },
            {
                "grupo": "GMN13",
                "semana": 1,
                "ciudad": "Neiva",
                "genero": "Mujer",
                "interaccion_id": "IT_04",
                "datetime_inicio": "2024-09-24 18:40",
                "datetime_fin": "2024-09-26 08:06",
                "n_mensajes": 3,
                "ids_participantes": "P1270M|P1325M",
                "resumen_tematica": "Reflexión de cierre: momentos únicos con los hijos",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "basica",
                "notas": "Cierre reflexivo con consenso breve. Alta participación pero mensajes cortos. El consenso es de validación emocional más que argumentativo.",
            },
            {
                "grupo": "GHN18",
                "semana": 2,
                "ciudad": "Neiva",
                "genero": "Hombre",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-29 18:28",
                "datetime_fin": "2024-09-29 20:38",
                "n_mensajes": 6,
                "ids_participantes": "P0841H|P1056H|P0873H",
                "resumen_tematica": "Tiempo Apapacho: actividades en familia",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 1,
                "nivel_interaccion": "basica",
                "notas": "Padres comparten actividades y reportan haber practicado el Tiempo Apapacho; I8 e I2 activos al mismo tiempo: adopción + validación grupal.",
            },
            {
                "grupo": "GHN18",
                "semana": 2,
                "ciudad": "Neiva",
                "genero": "Hombre",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-10-01 18:46",
                "datetime_fin": "2024-10-01 18:56",
                "n_mensajes": 2,
                "ids_participantes": "P0841H|P1056H",
                "resumen_tematica": "Cómo celebrar y reconocer los logros de los hijos",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "basica",
                "notas": "Consenso emergente sobre estrategias concretas de celebración. El intercambio es propositivo; los padres se dan ideas entre sí.",
            },
            {
                "grupo": "GMS4",
                "semana": 1,
                "ciudad": "Soacha",
                "genero": "Mujer",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-24 18:15",
                "datetime_fin": "2024-09-24 19:14",
                "n_mensajes": 8,
                "ids_participantes": "P0369M|P1217M|P0715M|P0368M|P1068M|P0892H|P1184M|P1057M",
                "resumen_tematica": "Retos individuales de la maternidad",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "stance-only",
                "notas": "Sesión 1 de grupo activo; los retos se comparten individualmente. Patrón típico de semana 1 donde el grupo aún se está conociendo.",
            },
            {
                "grupo": "GMS4",
                "semana": 1,
                "ciudad": "Soacha",
                "genero": "Mujer",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-09-24 18:44",
                "datetime_fin": "2024-09-24 20:17",
                "n_mensajes": 4,
                "ids_participantes": "P0892H|P1184M|P0710M|P1154M",
                "resumen_tematica": "Experiencia de crianza con la pareja",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 1,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "compleja",
                "notas": "Relato de crianza en pareja positivo que genera co-construcción de normalidad. Interesante que en semana 1 ya emerge I5 — la crianza compartida es tema muy presente.",
            },
            {
                "grupo": "GHS6",
                "semana": 2,
                "ciudad": "Soacha",
                "genero": "Hombre",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2024-09-29 18:33",
                "datetime_fin": "2024-09-29 18:33",
                "n_mensajes": 1,
                "ids_participantes": "P0609H",
                "resumen_tematica": "Tiempo Apapacho: juegos en casa con las hijas",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 1,
                "nivel_interaccion": "stance-only",
                "notas": "Padres comparten actividades brevemente; sin diálogo P-P. Similar a GHB1 IT_01: la adopción de práctica no necesariamente genera discusión entre hombres en semana 2.",
            },
            {
                "grupo": "GHS6",
                "semana": 2,
                "ciudad": "Soacha",
                "genero": "Hombre",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2024-10-01 15:00",
                "datetime_fin": "2024-10-03 09:41",
                "n_mensajes": 7,
                "ids_participantes": "P0609H|P0853H|P1277H|P0220H",
                "resumen_tematica": "Cómo celebrar logros de los hijos; imagen del padre con celular",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 1,
                "I7_identidad": 0,
                "I8_adopcion_practica": 1,
                "nivel_interaccion": "compleja",
                "notas": "La imagen del padre distraído con celular activa el diálogo más rico del grupo. I8 sugiere adopción inmediata. I6 emerge como autocrítica y compromiso moral.",
            },
            {
                "grupo": "GMV10",
                "semana": 1,
                "ciudad": "Valledupar",
                "genero": "Mujer",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2025-09-24 11:54",
                "datetime_fin": "2025-09-24 17:49",
                "n_mensajes": 16,
                "ids_participantes": "P0862M|N00012|P0538M|P1036M|P0884M|P1026M|P1306M|P0877M|P1323M|P0882M",
                "resumen_tematica": "Momentos divertidos de travesuras de bebés (popó, cremas, talco)",
                "I1_stance": 1,
                "I2_consenso": 1,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 1,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "compleja",
                "notas": "Mayor densidad de consenso de todo el Chunk 1. Las travesuras específicas generan reconocimiento inmediato y normalización colectiva ('todos los niños hacen eso'). I5 muy clara.",
            },
            {
                "grupo": "GMV10",
                "semana": 1,
                "ciudad": "Valledupar",
                "genero": "Mujer",
                "interaccion_id": "IT_02",
                "datetime_inicio": "2025-09-24 18:30",
                "datetime_fin": "2025-09-24 19:08",
                "n_mensajes": 3,
                "ids_participantes": "P1323M|P0862M|P1026M",
                "resumen_tematica": "Retos de crianza con la pareja o familiar cuidador",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 0,
                "nivel_interaccion": "stance-only",
                "notas": "Contraste con IT_01 del mismo grupo: el tema lúdico activa mucho más interacción que el tema de conflicto con la pareja.",
            },
            {
                "grupo": "GHV7",
                "semana": 2,
                "ciudad": "Valledupar",
                "genero": "Hombre",
                "interaccion_id": "IT_01",
                "datetime_inicio": "2025-09-29 17:48",
                "datetime_fin": "2025-09-29 17:48",
                "n_mensajes": 2,
                "ids_participantes": "P0177H|P0836H",
                "resumen_tematica": "Tiempo Apapacho: actividades con los hijos",
                "I1_stance": 1,
                "I2_consenso": 0,
                "I3_desacuerdo": 0,
                "I4_cambio_posicion": 0,
                "I5_normalidad": 0,
                "I6_moral": 0,
                "I7_identidad": 0,
                "I8_adopcion_practica": 1,
                "nivel_interaccion": "stance-only",
                "notas": "Grupo con muy baja participación (2 msgs de participantes); solo 2 hombres respondieron al facilitador. I8 presente pero sin interacción P-P.",
            },
        ],
    },
    # ------------------------------------------------------------------
    # Chunk 2 — semanas 3–4
    # ------------------------------------------------------------------
    {
        "num": 2,
        "semanas": "3-4",
        "grupos": [
            ("GMB3", 3, "Bogotá", "Mujeres"),
            ("GHB3", 4, "Bogotá", "Hombres"),
            ("GMN18", 3, "Neiva", "Mujeres"),
            ("GHN18", 4, "Neiva", "Hombres"),
            ("GMS6", 3, "Soacha", "Mujeres"),
            ("GHS5", 4, "Soacha", "Hombres"),
            ("GMV9", 3, "Valledupar", "Mujeres"),
            ("GHV9", 4, "Valledupar", "Hombres"),
        ],
        "its": [],
    },
    # ------------------------------------------------------------------
    # Chunk 3 — semanas 5–6
    # ------------------------------------------------------------------
    {
        "num": 3,
        "semanas": "5-6",
        "grupos": [
            ("GMB3", 5, "Bogotá", "Mujeres"),
            ("GHB1", 6, "Bogotá", "Hombres"),
            ("GMN13", 5, "Neiva", "Mujeres"),
            ("GHN18", 6, "Neiva", "Hombres"),
            ("GMS5", 5, "Soacha", "Mujeres"),
            ("GHS5", 6, "Soacha", "Hombres"),
            ("GMV10", 5, "Valledupar", "Mujeres"),
            ("GHV10", 6, "Valledupar", "Hombres"),
        ],
        "its": [],
    },
    # ------------------------------------------------------------------
    # Chunk 4 — semanas 7–8
    # ------------------------------------------------------------------
    {
        "num": 4,
        "semanas": "7-8",
        "grupos": [
            ("GMB3", 7, "Bogotá", "Mujeres"),
            ("GHB3", 8, "Bogotá", "Hombres"),
            ("GMN18", 7, "Neiva", "Mujeres"),
            ("GHN18", 8, "Neiva", "Hombres"),
            ("GMS5", 7, "Soacha", "Mujeres"),
            ("GHS4", 8, "Soacha", "Hombres"),
            ("GMV9", 7, "Valledupar", "Mujeres"),
            ("GHV10", 8, "Valledupar", "Hombres"),
        ],
        "its": [],
    },
    # ------------------------------------------------------------------
    # Chunk 5 — semanas 9–10
    # ------------------------------------------------------------------
    {
        "num": 5,
        "semanas": "9-10",
        "grupos": [
            ("GMB3", 9, "Bogotá", "Mujeres"),
            ("GHB1", 10, "Bogotá", "Hombres"),
            ("GMN16", 9, "Neiva", "Mujeres"),
            ("GHN18", 10, "Neiva", "Hombres"),
            ("GMS4", 9, "Soacha", "Mujeres"),
            ("GHS4", 10, "Soacha", "Hombres"),
            ("GMV10", 9, "Valledupar", "Mujeres"),
            ("GHV11", 10, "Valledupar", "Hombres"),
        ],
        "its": [],
    },
    # ------------------------------------------------------------------
    # Chunk 6 — semanas 11–12
    # ------------------------------------------------------------------
    {
        "num": 6,
        "semanas": "11-12",
        "grupos": [
            ("GMB3", 11, "Bogotá", "Mujeres"),
            ("GHB1", 12, "Bogotá", "Hombres"),
            ("GMN13", 11, "Neiva", "Mujeres"),
            ("GHN14", 12, "Neiva", "Hombres"),
            ("GMS4", 11, "Soacha", "Mujeres"),
            ("GHS5", 12, "Soacha", "Hombres"),
            ("GMV10", 11, "Valledupar", "Mujeres"),
            ("GHV10", 12, "Valledupar", "Hombres"),
        ],
        "its": [],
    },
]

# ---------------------------------------------------------------------------
# Funciones de escritura (idénticas a 10b)
# ---------------------------------------------------------------------------


def get_tema(df: pd.DataFrame, v_grupo: str, semana: int) -> str:
    """Obtiene el tema de una sesión desde el DataFrame de mensajes."""
    sub = df[(df[COL_GROUP] == v_grupo) & (df[COL_WEEK] == semana)]
    if COL_THEME in sub.columns and not sub.empty:
        vals = sub[COL_THEME].dropna()
        return vals.iloc[0] if not vals.empty else ""
    return ""


def cargar_mensajes(df: pd.DataFrame, v_grupo: str, semana: int) -> pd.DataFrame:
    """Extrae y formatea los mensajes de un grupo-semana."""
    sub = df[(df[COL_GROUP] == v_grupo) & (df[COL_WEEK] == semana)].copy()
    sub = sub.sort_values(COL_DATETIME).reset_index(drop=True)
    sub["hora"] = pd.to_datetime(sub[COL_DATETIME]).dt.strftime("%Y-%m-%d %H:%M")
    cols = ["hora", COL_SENDER, COL_PARTICIPANT_ID, COL_TYPE, COL_TEXT]
    return sub[cols].rename(
        columns={
            "hora": "Fecha/hora",
            COL_SENDER: "Remitente",
            COL_PARTICIPANT_ID: "ID participante",
            COL_TYPE: "Tipo",
            COL_TEXT: "Mensaje",
        }
    )


def marcar_sesiones_pp(
    msgs: pd.DataFrame,
    sesiones: pd.DataFrame,
    v_grupo: str,
    semana: int,
) -> pd.DataFrame:
    """Añade columna indicando si el mensaje cae en una sesión P-P."""
    subs = sesiones[(sesiones[COL_GROUP] == v_grupo) & (sesiones[COL_WEEK] == semana)][
        ["datetime_inicio", "datetime_fin", "sesion_id"]
    ].copy()

    if subs.empty:
        msgs["Sesion_PP"] = ""
        return msgs

    subs["datetime_inicio"] = pd.to_datetime(subs["datetime_inicio"])
    subs["datetime_fin"] = pd.to_datetime(subs["datetime_fin"])
    msgs_dt = pd.to_datetime(msgs["Fecha/hora"])

    sesion_col = []
    for dt in msgs_dt:
        matched = subs[(subs["datetime_inicio"] <= dt) & (subs["datetime_fin"] >= dt)]
        sesion_col.append(
            f"PP-{int(matched.iloc[0]['sesion_id'])}" if not matched.empty else ""
        )

    msgs["Sesion_PP"] = sesion_col
    return msgs


def write_sheet_mensajes(
    writer: pd.ExcelWriter,
    msgs: pd.DataFrame,
    sheet_name: str,
    info: tuple,
) -> None:
    """Escribe la hoja de mensajes con formato y color-coding P-P."""
    from openpyxl.styles import PatternFill

    v_grupo, semana, ciudad, genero, tema = info

    header = pd.DataFrame(
        [
            {
                "Fecha/hora": f"GRUPO: {v_grupo}",
                "Remitente": f"SEMANA: {semana}",
                "ID participante": f"CIUDAD: {ciudad}",
                "Tipo": f"GÉNERO: {genero}",
                "Mensaje": f"TEMA: {tema}",
                "Sesion_PP": "Sesion P-P (de 10a)",
            }
        ]
    )
    separador = pd.DataFrame([{col: "---" for col in msgs.columns}])
    completo = pd.concat([header, separador, msgs], ignore_index=True)
    completo.to_excel(writer, sheet_name=sheet_name, index=False)

    ws = writer.sheets[sheet_name]
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 80
    ws.column_dimensions["F"].width = 14

    fill_p = PatternFill(start_color="DDEEFF", end_color="DDEEFF", fill_type="solid")
    fill_pp = PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid")

    for row_idx, row in enumerate(ws.iter_rows(min_row=4), start=4):
        if row[1].value == "Participante":
            color = fill_pp if row[5].value else fill_p
            for cell in row:
                cell.fill = color


def write_sheet_coding(
    writer: pd.ExcelWriter,
    its_data: list[dict],
    sheet_name: str,
) -> None:
    """Escribe la hoja de codificación con ITs pre-llenadas + filas vacías."""
    from openpyxl.styles import Font, PatternFill

    pre = (
        pd.DataFrame(its_data).reindex(columns=COLS_PLANTILLA)
        if its_data
        else pd.DataFrame(columns=COLS_PLANTILLA)
    )
    empty = pd.DataFrame(index=range(20), columns=COLS_PLANTILLA)
    plantilla = pd.concat([pre, empty], ignore_index=True)
    plantilla.to_excel(writer, sheet_name=sheet_name, index=False)

    ws = writer.sheets[sheet_name]
    anchos = {
        "A": 10,
        "B": 8,
        "C": 12,
        "D": 10,
        "E": 14,
        "F": 18,
        "G": 18,
        "H": 10,
        "I": 25,
        "J": 40,
        "K": 8,
        "L": 8,
        "M": 8,
        "N": 8,
        "O": 8,
        "P": 8,
        "Q": 8,
        "R": 8,
        "S": 16,
        "T": 50,
        "U": 40,
    }
    for col_letter, width in anchos.items():
        ws.column_dimensions[col_letter].width = width

    ws["A1"].font = Font(bold=True)

    nivel_fills = {
        "compleja": PatternFill(
            start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"
        ),
        "basica": PatternFill(
            start_color="DDEEFF", end_color="DDEEFF", fill_type="solid"
        ),
        "stance-only": PatternFill(
            start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
        ),
    }
    idx_nivel = COLS_PLANTILLA.index("nivel_interaccion")
    for row_idx, row in enumerate(
        ws.iter_rows(min_row=2, max_row=len(pre) + 1), start=2
    ):
        nivel = str(row[idx_nivel].value).lower() if row[idx_nivel].value else ""
        fill = nivel_fills.get(nivel)
        if fill:
            for cell in row:
                cell.fill = fill

    nota_row = len(plantilla) + 3
    ws.cell(row=nota_row, column=1, value=NIVEL_INSTRUCCION)
    ws.cell(row=nota_row, column=1).font = Font(italic=True, color="666666")


def write_sheet_guia(writer: pd.ExcelWriter) -> None:
    """Escribe la hoja guía de indicadores."""
    from openpyxl.styles import Alignment, Font, PatternFill

    guia_df = pd.DataFrame(GUIA_INDICADORES)[
        [
            "Nivel",
            "N",
            "Indicador",
            "Definición (Dedios et al.)",
            ADAPTATION_KEY,
            "Código en plantilla",
        ]
    ]
    guia_df.to_excel(writer, sheet_name="Guia_indicadores", index=False)

    ws = writer.sheets["Guia_indicadores"]
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 5
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 55
    ws.column_dimensions["E"].width = 65
    ws.column_dimensions["F"].width = 22

    fills = {
        "Stance-only": PatternFill(
            start_color="FFF2CC", end_color="FFF2CC", fill_type="solid"
        ),
        "Interacción básica": PatternFill(
            start_color="DDEEFF", end_color="DDEEFF", fill_type="solid"
        ),
        "Interacción compleja": PatternFill(
            start_color="E2EFDA", end_color="E2EFDA", fill_type="solid"
        ),
        f"Específico {PROJECT_NAME}": PatternFill(
            start_color="FCE4D6", end_color="FCE4D6", fill_type="solid"
        ),
    }

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        nivel = row[0].value
        fill = fills.get(nivel)
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            if fill:
                cell.fill = fill

    for cell in ws[1]:
        cell.font = Font(bold=True)

    ws.row_dimensions[1].height = 18
    for i in range(2, 10):
        ws.row_dimensions[i].height = 80


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("Cargando datos...")
    df = pd.read_parquet(
        PROJECT_ROOT / cfg["data"]["intermediate"]["preprocessed_messages"]
    )
    sesiones = pd.read_csv(TABLES_DIR / "10a_cadenas_sesion.csv")

    for chunk in CHUNKS:
        n = chunk["num"]
        out_path = TABLES_DIR / f"10c_chunk{n}.xlsx"
        print(
            f"\nGenerando chunk {n} (semanas {chunk['semanas']}) -> {out_path.name}..."
        )

        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            write_sheet_guia(writer)

            for v_grupo, semana, ciudad, genero in chunk["grupos"]:
                tema = get_tema(df, v_grupo, semana)
                info = (v_grupo, semana, ciudad, genero, tema)
                sheet_name = f"{v_grupo}_s{semana}"
                print(f"  {sheet_name}...")
                msgs = cargar_mensajes(df, v_grupo, semana)
                msgs = marcar_sesiones_pp(msgs, sesiones, v_grupo, semana)
                write_sheet_mensajes(writer, msgs, sheet_name, info)

            write_sheet_coding(writer, chunk["its"], f"Chunk_{n}")

        n_its = len(chunk["its"])
        print(f"  -> {n_its} ITs codificadas")

    print("\nListo.")


if __name__ == "__main__":
    main()
