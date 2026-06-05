# Guía para adaptar config.yaml a un nuevo proyecto

`config.yaml` es el único archivo que necesitas modificar para usar este
pipeline con tu propio proyecto. Ningún script Python requiere cambios.

Este documento explica cada sección, qué significa, qué debes cambiar
obligatoriamente y qué puedes dejar igual.

---

## Convenciones de esta guía

| Etiqueta | Significado |
| --- | --- |
| **OBLIGATORIO** | Debes cambiar esto antes de correr cualquier paso |
| **OPCIONAL** | Solo si tu proyecto lo necesita |
| **NO CAMBIAR** | Valores técnicos — dejar como están salvo casos excepcionales |

---

## 1. `project` — Información del programa

### OBLIGATORIO

Identifica tu proyecto. Estos valores aparecen en títulos de gráficas,
nombres de columnas en los Excels de codificación y en los prompts de
Claude.

```yaml
project:
  name: "Nombre de tu programa"        # Aparece en todas las figuras
  description: >
    Descripción breve del programa,
    para quién es y qué hace.           # Contexto en prompts de Claude
  country: "Colombia"                   # País de implementación
  language: "es"                        # Código ISO del idioma (es, pt, en...)
  duration_weeks: 12                    # Semanas del programa (o null si transversal)
  target_population: "descripción"      # Población objetivo

  cities:                               # Sitios de implementación
    - "Ciudad1"
    - "Ciudad2"
```

**Cómo encontrar los valores correctos:** los nombres en `cities` deben
coincidir exactamente (mayúsculas incluidas) con los valores que aparecen
en la columna `city_group` de tu dataset.

---

## 2. `data.input` — Archivos de entrada

### OBLIGATORIO

```yaml
data:
  input:
    raw_stata_file: "data/raw/TU_ARCHIVO.dta"
```

Cambia `TU_ARCHIVO.dta` por la ruta a tu archivo de mensajes limpio
(sin PII). La ruta es relativa a la raíz del repositorio.

Las siguientes dos líneas solo son necesarias para el
**Paso 8** (buscador de citas):

```yaml
    coding_tree_file: "documentation/TU_ARBOL_DE_CODIGOS.xlsx"
    coding_tree_sheet: "NombreDeLaHoja"
    citations_excel_sheet: "NombreDeLaHoja"
```

Si no tienes árbol de códigos, puedes dejar estos campos con cualquier
valor — simplemente no corras los pasos 08 y 09.

---

## 3. `data.columns` — Nombres de columnas

### OBLIGATORIO — el más importante

Esta sección le dice al pipeline cómo se llaman las columnas en tu
dataset. Si los nombres no coinciden exactamente, los scripts fallarán.

```yaml
  columns:
    message_type: "tipo"        # ← Cambia por el nombre real en tu .dta
    message_text: "texto"
    sender: "remitente"
    city_group: "city_grupo"
    week_number: "n_week"
    group_id: "v_grupo"
    datetime: "datetime"
    theme: "tema"
    participant_id: "id_f"
    gender_group: "sex_grupo"
```

**Cómo encontrar los nombres correctos:** abre tu `.dta` en Stata y
ejecuta `describe` para ver la lista de variables. Copia los nombres
exactamente como aparecen.

**Columnas obligatorias vs. opcionales:**

| Columna | Obligatoria | Para qué sirve |
| --- | --- | --- |
| `message_text` | Sí | Texto del mensaje — base de todo el análisis |
| `sender` | Sí | Distinguir facilitadores de participantes |
| `group_id` | Sí | Identificar a qué grupo pertenece cada mensaje |
| `datetime` | Sí | Ordenar mensajes cronológicamente |
| `city_group` | Sí (long.) | Agrupar por ciudad × semana |
| `week_number` | Solo long. | Número de semana del programa |
| `message_type` | Sí | Filtrar solo mensajes de texto |
| `participant_id` | Pasos 10+ | Identificar participantes únicos |
| `gender_group` | Pasos 10+ | Análisis por género |
| `theme` | Opcional | Tema de la sesión en Excels de codificación |

Si tu dataset no tiene alguna columna opcional, deja el nombre de campo
actual — el script la ignorará si no existe en los datos.

---

## 4. `data.chunking` — Longitudinal vs. transversal

### OBLIGATORIO — define el tipo de análisis

Esta es la decisión más importante después de los nombres de columnas.

**Para datos longitudinales** (el programa tiene semanas, rondas o momentos
en el tiempo):

```yaml
  chunking:
    groupby:
      - "city_grupo"    # ← nombre de tu columna city_group
      - "n_week"        # ← nombre de tu columna week_number
```

Cada unidad de análisis será: un grupo × una semana.

**Para datos transversales** (una sola toma, sin estructura temporal):

```yaml
  chunking:
    groupby:
      - "v_grupo"       # ← nombre de tu columna group_id
```

Cada unidad de análisis será: un grupo completo.

> Con datos transversales, los pasos 06 (evolución semántica semana a
> semana), 10e (retención) y 10f (latencia) se omiten automáticamente.

---

## 5. `data.values` — Valores de filtro

### OBLIGATORIO

Indican qué valores concretos tiene tu dataset para distinguir el tipo
de mensaje y el rol del remitente.

```yaml
  values:
    text_message_type: "Mensaje en Texto"  # Valor en la columna message_type
    participant_sender: "Participante"     # Valor en la columna sender
    facilitator_sender: "Facilitador"      # Valor en la columna sender
    missing_gender: "Sin género"           # Valor de relleno (puede dejarse igual)
```

**Cómo encontrar los valores correctos:** en Stata, ejecuta
`tab remitente` (o el nombre de tu columna) para ver los valores únicos.
Copia el texto exactamente como aparece, incluyendo mayúsculas y tildes.

---

## 6. `models` — Modelos de inteligencia artificial

### NO CAMBIAR (salvo que quieras probar otro modelo de embeddings)

```yaml
models:
  embedding_model: "paraphrase-multilingual-mpnet-base-v2"
  claude_model: "claude-sonnet-4-6"
```

El modelo de embeddings se descarga automáticamente la primera vez
(~400 MB). Es multilingüe y funciona bien en español, portugués,
inglés y otros idiomas.

Si tu programa está en un idioma diferente, este modelo sigue siendo
una buena opción. Para inglés exclusivamente, puedes usar
`all-mpnet-base-v2` (más preciso para inglés).

---

## 7. `vectordb` — Base de datos vectorial

### NO CAMBIAR (salvo que tengas múltiples proyectos en el mismo directorio)

```yaml
vectordb:
  collection_chunks: "llm_wa_chunks"
  collection_messages: "llm_wa_mensajes"
  ...
```

Si corres dos proyectos distintos desde el mismo directorio, cambia
los nombres de las colecciones para que no se sobreescriban entre sí.
Por ejemplo: `"proyecto_a_chunks"` y `"proyecto_b_chunks"`.

---

## 8. `prompts` — Instrucciones para Claude

### OPCIONAL — solo afecta el Paso 5b (búsqueda semántica interactiva)

```yaml
prompts:
  rag_answer: |
    Eres un asistente de investigación del {project_name},
    {project_description}
    ...
```

Los marcadores entre llaves (`{project_name}`, `{pregunta}`,
`{contexto}`) son reemplazados automáticamente en tiempo de ejecución.
No los elimines.

Puedes ajustar el tono o las instrucciones, pero el prompt base ya
funciona bien para la mayoría de proyectos.

---

## 9. `analysis` — Parámetros técnicos de los algoritmos

### NO CAMBIAR para la mayoría de proyectos

Los valores por defecto están calibrados para funcionar bien con datos
típicos de programas sociales.

Las únicas excepciones donde puede valer la pena ajustar:

```yaml
  interaction:
    session_gap_minutes: 60      # Ventana para detectar sesiones P-P
                                 # Aumentar si los grupos son menos activos
  clustering:
    kmeans_range: [2, 10]        # Rango de clusters a explorar
                                 # Ampliar si esperas más temas distintos

  citation_search:
    relevant_families:           # [ADAPTAR si usas el Paso 08]
      - "Nombre exacto de familia 1"
      - "Nombre exacto de familia 2"
```

Para `relevant_families`: los nombres deben coincidir exactamente con
los valores en la columna `"familia"` de tu Excel de árbol de códigos.

---

## 10. `coding` — Framework de codificación DEDIOS

Esta sección configura los pasos 10b y 10c (análisis de interacción
participante-participante).

### 10a. `coding.chunk_ranges` — Rangos de semanas por chunk

#### ADAPTAR si tu programa tiene una duración diferente

```yaml
  chunk_ranges:
    1: [1, 2]     # Chunk 1 cubre semanas 1 y 2
    2: [3, 4]
    ...
```

Cambia el número de chunks y los rangos según las semanas de tu
programa. Para un programa de 8 semanas con chunks de 2 semanas:

```yaml
  chunk_ranges:
    1: [1, 2]
    2: [3, 4]
    3: [5, 6]
    4: [7, 8]
```

### 10b. `coding.pilot_groups` — Grupos del piloto de codificación

#### ADAPTAR antes de correr el Paso 10b

```yaml
  pilot_groups:
    - grupo: "GRU01"       # Valor real de group_id en tu dataset
      semana: 3            # Semana del programa
      ciudad: "Ciudad1"    # Valor real de city_group en tu dataset
      genero: "Mujeres"    # Descripción libre del grupo
```

Escoge 2 o 3 grupos representativos y variados de tu dataset para el
piloto. Los valores de `grupo` y `ciudad` deben coincidir exactamente
con los que aparecen en tus datos.

### 10c. `coding.indicators` — Indicadores del framework

**ADAPTAR la columna `adaptation` de cada indicador**

Los indicadores I1–I7 son del framework original de Dedios-Sanguineti
et al. (2025) y su `definition_dedios` no debe modificarse. Lo que sí
debes adaptar es la columna `adaptation`: cómo se manifiesta ese
indicador específicamente en el contexto de tu programa.

```yaml
    - id: "I2"
      level: "Interacción básica"
      name: "Consenso"
      definition_dedios: >
        Dos o más participantes expresan acuerdo explícito...  # No cambiar
      adaptation: >
        Descripción de cómo se ve el consenso en TU programa.
        Qué marcadores lingüísticos son relevantes en tu contexto.
      template_code: "I2_consenso"   # No cambiar
```

El indicador **I8** es un indicador adicional propuesto específicamente
para intervenciones donde los participantes reportan adoptar prácticas
en casa. Si tu programa no tiene este componente, puedes eliminar la
entrada de I8 o dejarla — simplemente no aparecerá en los datos si
nunca se codifica.

---

## 11. `visualization.colors` — Colores por ciudad

**ADAPTAR** para que coincida con tus sitios de implementación

```yaml
  colors:
    cities:
      Ciudad1: "#1976D2"    # Azul
      Ciudad2: "#388E3C"    # Verde
      Ciudad3: "#F57C00"    # Naranja
      Ciudad4: "#7B1FA2"    # Morado
```

Las claves (`Ciudad1`, `Ciudad2`) deben coincidir exactamente con
los valores en `project.cities`. Puedes usar cualquier color en formato
hexadecimal. Si tienes más de 4 ciudades, agrega las líneas necesarias.

---

## Resumen: mínimo indispensable para empezar

Si quieres correr el pipeline rápidamente, estos son los campos que
**debes** cambiar antes de cualquier cosa:

| Campo | Sección | Qué poner |
| --- | --- | --- |
| `project.name` | project | Nombre de tu programa |
| `project.cities` | project | Lista de ciudades/sitios |
| `data.input.raw_stata_file` | data.input | Ruta a tu `.dta` limpio |
| `data.columns.*` | data.columns | Nombres de columnas de tu dataset |
| `data.values.*` | data.values | Valores de filtro en tus datos |
| `data.chunking.groupby` | data.chunking | `[city_group, week_number]` o `[group_id]` |
| `visualization.colors.cities` | visualization | Un color por ciudad |

Todo lo demás puede dejarse como está para el primer run.
