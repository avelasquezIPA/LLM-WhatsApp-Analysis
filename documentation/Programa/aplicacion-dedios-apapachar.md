# Aplicación del framework de Dedios et al. (2025) al Programa Apapachar

Evaluación de viabilidad y plan de implementación para aplicar el modelo de
indicadores de interacción significativa de Dedios-Sanguineti et al. (2025)
a los datos de WhatsApp del Programa Apapachar.

**Paper de referencia:**
Dedios-Sanguineti, M. C., Guarin, A., Torres-García, A., & Martínez Gómez, M.
(2025). Assessing meaningful interaction in focus group discussions conducted
over WhatsApp. *International Journal of Qualitative Methods, 24*, 1–14.
DOI: 10.1177/16094069251321599

---

## 1. ¿Qué propone el framework?

El paper propone 7 indicadores cualitativos para evaluar la **interacción
significativa** en FGDs asíncronos vía WhatsApp. Los indicadores se organizan
en tres niveles progresivos:

| Nivel | Indicadores | Qué captura |
| --- | --- | --- |
| **Stance-only** | Emergencia de posturas | Participante comparte su punto de vista sin generar respuesta |
| **Interacción básica** | Consenso, desacuerdo, cambio de posiciones | Participantes se responden, acuerdan o debaten entre sí |
| **Interacción compleja** | Construcción descriptiva de normalidad, construcción moral, identidades compartidas | Negociación de valores, normas y sentido colectivo |

La codificación produce una tabla donde cada fila es una "interacción temática"
(una cadena de mensajes sobre un mismo tema) y las columnas son los indicadores.
La complejidad de la interacción se lee de izquierda a derecha: a más columnas
activadas, más rica la interacción.

---

## 2. Por qué el contexto de Apapachar es compatible

### Modalidad idéntica

- WhatsApp asíncrono: mismo formato tecnológico que el paper
- Colombia, poblaciones vulnerables: mismo contexto sociodemográfico
- Moderadores activos con prompts diarios: estructura análoga a los FGDs del paper
- Uso de texto, audio, emojis, multimedia: mismas posibilidades comunicativas
- Participantes respondiendo en horarios irregulares (mañana temprano, mediodía,
  noche): mismo patrón documentado por Dedios et al.

### Temática con alto potencial de interacción compleja

Los temas del árbol de códigos de Apapachar (familias 3, 4, 5 y 7) son
profundamente **morales e identitarios**:

- Crianza positiva vs. crianza que conocen de su propia infancia
- Corresponsabilidad: redistribución de roles en el hogar
- Vínculo afectivo: expresiones de afecto que pueden estar normalizadas o no
- Violencia intrafamiliar: un tema con fuerte carga moral y social

Estos temas deberían generar exactamente el tipo de interacción compleja
que el paper documenta: construcción de normalidad ("en mi familia siempre fue
así"), negociación moral ("ahora entiendo que pegarle a un niño no está bien"),
e identidades compartidas ("nosotras como madres sabemos que...").

### Ventaja temporal única

El paper solo observa 1 semana de FGD. Apapachar tiene **12 semanas**. Esto
permite hacer algo que el paper no pudo: analizar si la **complejidad de la
interacción evoluciona** con el avance del programa. La hipótesis es que las
semanas iniciales tendrán más stance-only (presentaciones, normas del grupo)
y las semanas finales más interacción compleja (reflexión, cambios percibidos,
negociación de identidades).

---

## 3. Consideraciones críticas antes de aplicar

### 3.1 El propósito es diferente

El paper estudia un FGD de investigación cuyo **objetivo es generar datos** sobre
opiniones. Apapachar es una **intervención de cambio conductual** cuyo objetivo
es modificar prácticas de crianza. Esto tiene consecuencias directas:

- Muchos mensajes de participantes son respuestas a actividades estructuradas
  del programa, no debate espontáneo entre pares
- El facilitador dirige activamente el contenido, lo que puede canalizar la
  interacción hacia temas específicos antes de que se desarrolle orgánicamente
- Los participantes pueden estar respondiendo "lo correcto" en lugar de expresar
  tensión genuina

**Implicación:** La prevalencia de interacción stance-only será mayor en Apapachar
que en los FGDs del paper. Esto no invalida el análisis; al contrario, documenta
el tipo de interacción que genera un programa de intervención vs. un FGD de
investigación abierta, lo cual es una contribución metodológica en sí misma.

### 3.2 El ratio facilitador/participante sesga el análisis

En Apapachar, el **76% de los mensajes son de facilitadores** (11,312 de 14,894).
En el paper, los moderadores facilitan pero no dominan el contenido temático.

Esto genera dos problemas específicos:

1. **Ruido en la identificación de stances:** los facilitadores también expresan
   posturas ("la crianza positiva fortalece el vínculo"), lo cual puede confundirse
   con stances de participantes.
2. **Supresión de interacción horizontal:** cuando el facilitador responde cada
   mensaje individualmente (agradeciendo, validando, re-encuadrando), puede
   interrumpir el hilo de interacción entre participantes antes de que se desarrolle.

**Implicación:** El análisis de interacción debe realizarse **únicamente sobre
mensajes de participantes** y detectar específicamente cuándo un participante
responde a **otro participante** (no al facilitador). Esto requiere identificar
cadenas de respuesta P-P (participante a participante) separadas de cadenas P-F
(participante a facilitador) o F-P (facilitador a participante).

### 3.3 La escala es radicalmente mayor

El paper codificó 12 FGDs de 1 semana con un coder manual (206 filas de
interacción identificadas). Apapachar tiene:

- 3,582 mensajes de participantes
- 48 grupos-semana (4 ciudades × 12 semanas)
- 12 semanas de duración

La codificación manual completa del corpus no es viable. Se requiere
codificación asistida por LLM con validación humana sobre una muestra.

### 3.4 WhatsApp de programa vs. WhatsApp de investigación

En los FGDs del paper, todos los mensajes tienen como propósito responder a las
preguntas de investigación. En Apapachar, los mensajes incluyen:

- Respuestas a actividades (rellenar formularios, compartir reflexiones)
- Saludos, agradecimientos, confirmaciones de asistencia
- Mensajes logísticos ("¿a qué hora es la sesión?")
- Contenido emocional de apoyo mutuo que no es debate temático

Solo el subconjunto de mensajes con contenido temático sustantivo es relevante
para aplicar los indicadores de Dedios et al. El pipeline ya filtra por
mensajes con ≥5 palabras (script 08b), pero se necesita una capa adicional
de filtrado temático.

---

## 4. Lo que el repositorio ya tiene

Antes de diseñar el nuevo script, conviene mapear qué está disponible:

| Recurso | Script | Relevancia |
| --- | --- | --- |
| Mensajes preprocesados con remitente, ciudad, semana | `01_quality_analysis.py` | Base de datos para filtrar solo participantes |
| Embeddings de mensajes individuales de participantes | `08b_citation_finder_participantes.py` | 2,318 mensajes ≥5 palabras indexados en ChromaDB |
| Similitud semántica por semana | `06b_similarity_map_participantes.py` | Identifica semanas con mayor cambio temático (candidatas para análisis profundo) |
| Citas encontradas por código cualitativo | `08b_citation_finder_participantes.py` | Mensajes más relevantes por código del árbol |
| Género de participantes inferido de id_f | `08b_citation_finder_participantes.py` | Permite análisis de interacción por género |
| Variable `tema` por semana | datos limpios | Permite segmentar por contenido temático del programa |

---

## 5. Plan de implementación paso a paso

### Paso A: Identificar cadenas de interacción P-P

**Script nuevo: `10a_cadenas_interaccion.py`**

El prerrequisito del framework es identificar cuándo un participante responde
a otro participante (no al facilitador). En WhatsApp esto se detecta por:

1. **Proximidad temporal:** dos mensajes de participantes distintos separados
   por menos de N minutos (sin mensaje de facilitador en medio)
2. **Mención explícita:** el mensaje cita el nombre o el contenido de otro
   participante
3. **Marcadores lingüísticos de respuesta:** "como dice [nombre]...",
   "estoy de acuerdo con...", "yo también", "pero en mi caso..."

**Output esperado:**

- `10a_cadenas_interaccion.csv`: cada fila es una cadena P-P con ciudad,
  semana, tema, participantes involucrados, n_mensajes en la cadena
- Estadísticas básicas: n cadenas por ciudad-semana, longitud promedio,
  % de mensajes de participantes que forman parte de cadenas P-P

**Lo que esto revelaría:** ¿Cuánto de la interacción de participantes es entre
ellos vs. solo hacia el facilitador? Si la mayoría es P-F, el programa funciona
como curso más que como grupo de pares.

### Paso B: Codificación piloto manual en una muestra

Antes de automatizar, codificar manualmente 2–3 city-weeks usando los 7
indicadores del paper para:

1. Calibrar qué tipos de mensajes activan cada indicador en el contexto de crianza
2. Detectar indicadores que no aparecen o requieren adaptación
3. Identificar indicadores nuevos específicos de Apapachar
   (e.g., "adopción de práctica": participante reporta haber aplicado algo del
   programa en casa, lo cual es el equivalente de "shifting of positions" en
   intervención)

**Recomendación de muestra:**

- Neiva semana 8 (alta similitud, alta actividad)
- Valledupar semana 11 (baja similitud → mayor cambio temático)
- Soacha semana 3 (semana de contenido activo temprano)

### Paso C: Codificación LLM-asistida

**Script nuevo: `10b_codificacion_interaccion.py`**

Usar Claude para clasificar cada mensaje de participante (o cada cadena P-P
identificada en el Paso A) contra los 7 indicadores. El prompt incluiría:

- Definición de cada indicador (tomada literalmente del paper, Tabla 2)
- Adaptaciones específicas para contexto de crianza:
    - "stance" = postura sobre una práctica de crianza, corresponsabilidad
      o experiencia familiar
    - "shifting of positions" incluye reportar haber cambiado una práctica
      en casa como resultado de la discusión
- El mensaje o cadena a clasificar
- Contexto: ciudad, semana, tema

**Output:** tabla con un indicador por columna (0/1) para cada mensaje o
cadena, análogo a la Tabla 3 del paper pero a escala.

### Paso D: Agregación y análisis

**Script nuevo: `10c_analisis_interaccion.py`**

Con la tabla de codificación del Paso C:

1. **Clasificar cada city-week** en el nivel de interacción predominante
   (stance-only / básica / compleja) según los indicadores presentes
2. **Evolución temporal:** ¿aumenta la complejidad semana a semana?
3. **Comparación entre ciudades:** ¿algunas ciudades generan más interacción
   compleja? ¿Correlaciona con tamaño del grupo o perfil demográfico?
4. **Análisis de género:** ¿hombres y mujeres producen tipos distintos de
   interacción? ¿Los hombres aportan más "shifting of positions" hacia la
   corresponsabilidad (hipótesis basada en sección 11 de LLM-ResultsSummary)?
5. **Correlación con similitud semántica:** ¿los city-weeks con baja similitud
   inter-semana (mayor cambio temático, de `07b`) también tienen mayor
   interacción compleja?

### Paso E: Validación humana

Sobre una muestra aleatoria de 10–15% de las clasificaciones del LLM,
hacer codificación humana independiente y calcular acuerdo (kappa de Cohen).
El paper usó 3 codificadores para el piloto; con LLM se puede hacer a escala
pero sin reemplazar la validación humana.

---

## 6. Hipótesis de investigación que esto permitiría testear

1. **Hipótesis de evolución:** La complejidad de la interacción entre
   participantes aumenta a lo largo de las 12 semanas del programa, con las
   semanas finales produciendo más interacción compleja (moral sense-making,
   identidades compartidas).

2. **Hipótesis de género:** Los hombres producen más mensajes de "shifting of
   positions" (particularmente hacia corresponsabilidad) que las mujeres, que
   tienden más a "consensus" en torno a prácticas concretas de crianza.

3. **Hipótesis de homogeneidad regional:** La complejidad de interacción varía
   entre ciudades, con Valledupar y Neiva (mayor similitud semántica con los
   códigos) produciendo más interacción compleja que Bogotá y Soacha.

4. **Hipótesis de programa vs. FGD de investigación:** La prevalencia de
   interacción stance-only será significativamente mayor en Apapachar que en
   los FGDs del paper de referencia, documentando la diferencia entre
   intervención programática y FGD de investigación abierta.

---

## 7. Contribución metodológica potencial

Una aplicación rigurosa de este framework a los datos de Apapachar generaría
dos tipos de contribuciones:

**Para la literatura de métodos:**

- Primera aplicación del framework de Dedios et al. a una intervención de
  cambio conductual (no FGD de investigación)
- Primera aplicación a escala usando codificación LLM-asistida con validación
  humana
- Extensión del framework con un nuevo indicador propuesto: "adopción de
  práctica reportada" (específico de intervenciones)

**Para la evaluación de Apapachar:**

- Evidencia cualitativa de que el programa generó interacción significativa
  entre participantes (no solo transmisión de información unidireccional)
- Documentación de qué tipos de interacción (básica vs. compleja) emergieron
  y en qué momentos del programa
- Insumo para el diseño de futuras iteraciones del programa: ¿qué semanas
  o temas generaron más reflexión colectiva?

---

## 8. Próximos pasos inmediatos

1. Leer el paper completo y discutir qué indicadores requieren adaptación
   para el contexto de crianza
2. Hacer la codificación piloto manual del Paso B en 2–3 city-weeks
3. Diseñar el prompt para el Paso C basado en los resultados del piloto
4. Implementar `10a_cadenas_interaccion.py` (detección de cadenas P-P)
   como primer script técnico

El Paso A (cadenas P-P) es el más crítico y el que más diferencia este
análisis del trabajo ya hecho: si resulta que casi no hay cadenas P-P en los
datos, la aplicación del framework quedaría limitada al análisis de posturas
individuales, lo cual tiene valor pero es cualitativamente distinto a lo que
el paper propone.
