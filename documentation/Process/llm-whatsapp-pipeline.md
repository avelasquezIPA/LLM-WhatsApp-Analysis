# Pipeline LLM para Análisis de Mensajes de WhatsApp - Programa Apapachar

## Referencia base

Este pipeline está informado por el paper:

> Ferreira et al. (2025). *A comprehensive qualitative analysis of patient dialogue summarization
> using large language models applied to noisy, informal, non-English real-world data.*
> Scientific Reports, 15, 31660. https://doi.org/10.1038/s41598-025-13560-9

El paper evalúa exactamente este escenario: mensajes de WhatsApp informales, en un idioma
no-inglés (portugués), con datos ruidosos (abreviaciones, errores ortográficos, mensajes
muy cortos), usando LLMs para generar resúmenes útiles. Sus hallazgos principales son
directamente aplicables al contexto de Apapachar.

---

## Visión general del pipeline

```
Mensajes WhatsApp anonimizados (.csv / .xlsx)
            |
     [PASO 1] Análisis de calidad
            |
     [PASO 2] Limpieza y preprocesamiento
            |
     [PASO 3] Chunking (agrupación de mensajes)
            |
     [PASO 4] Embeddings (representación vectorial)
            |
         --------
        |        |
  [PASO 5a]  [PASO 5b]
 Clustering   Búsqueda
 temático     semántica (RAG)
        |
     Análisis de similitud semántica [PASO 7]
```

---

## PASO 1: Análisis de calidad de los mensajes

Antes de procesar, el paper recomienda evaluar tres dimensiones de calidad. Esto es
importante porque mensajes de mala calidad afectan directamente la calidad de los embeddings y el análisis.

### 1.1 Tamaño

Clasificar los mensajes en cortos, medianos y largos.

```python
# En Python (pandas)
df['n_palabras'] = df['mensaje'].str.split().str.len()
df['n_caracteres'] = df['mensaje'].str.len()

promedio = df['n_palabras'].mean()
df['tipo_mensaje'] = 'mediano'
df.loc[df['n_palabras'] <= promedio - 5, 'tipo_mensaje'] = 'corto'
df.loc[df['n_palabras'] >= promedio + 10, 'tipo_mensaje'] = 'largo'
```

El paper encontró que ~56% de los mensajes son cortos y ~23% son largos. Espera una
distribución similar en los mensajes de Apapachar.

### 1.2 Corrección ortográfica (informalidad)

El paper halló que solo el 44% de las palabras de pacientes estaban en el diccionario
estándar. Esto es normal en WhatsApp: "pq" (porque), "tmb" (también), "xq" (porque).
Los LLMs modernos manejan esto bien en español.

### 1.3 Legibilidad

Opcional: Flesch-Kincaid para comparar complejidad de mensajes de facilitadores vs.
beneficiarios. Anticipa que los facilitadores escriben más formalmente.

**Herramienta para este paso:** Python + pandas (solo lectura y estadísticas descriptivas).
Claude puede hacer este análisis directamente si le pegas una muestra del dataset.

---

## PASO 2: Limpieza y preprocesamiento

Antes de cualquier procesamiento con LLM:

```python
import pandas as pd
import re

def limpiar_mensaje(texto):
    texto = re.sub(r'\s+', ' ', texto)       # espacios múltiples
    texto = re.sub(r'\n+', ' ', texto)       # saltos de línea
    texto = texto.strip()
    return texto

df['mensaje_limpio'] = df['mensaje'].apply(limpiar_mensaje)

# Filtrar mensajes vacíos o de sistema
df = df[df['mensaje_limpio'].str.len() > 0]
df = df[~df['mensaje_limpio'].str.contains('Mensaje eliminado|audio omitido')]
```

**Nota del paper:** Los autores también eliminaron mensajes plantilla (mensajes automáticos
estandarizados), lo que redujo el dataset de 207,040 a 202,326 mensajes.

---

## PASO 3: Chunking (agrupación de mensajes)

Esta es la decisión más importante del pipeline. Los LLMs tienen una ventana de contexto
limitada, no pueden leer todos los mensajes a la vez.

### Estrategia recomendada para Apapachar: Chunking por sesión

Dado que el Programa Apapachar tiene sesiones estructuradas (semanas del programa),
la agrupación natural es por sesión o por semana.

```python
# Opción A: Agrupar por ciudad + semana del programa
df['fecha'] = pd.to_datetime(df['fecha'])
df['semana'] = df['fecha'].dt.isocalendar().week

chunks = df.groupby(['ciudad', 'semana'])['mensaje_limpio'].apply(
    lambda msgs: '\n'.join([f"[{i+1}] {m}" for i, m in enumerate(msgs)])
).reset_index()
chunks.columns = ['ciudad', 'semana', 'texto_chunk']
```

### Límite de tokens por chunk

El paper usó los últimos **5,000 tokens** de cada diálogo como estrategia de truncación,
priorizando los mensajes más recientes. Para Claude, el límite es mucho más generoso
(200,000 tokens), pero se recomienda mantener los chunks manejables.

**Regla práctica:** Aproximadamente 1 token = 0.75 palabras en español.

| Tamaño del chunk | Tokens aproximados | Recomendado para |
|---|---|---|
| 100 mensajes | ~2,000 tokens | Sesiones cortas |
| 500 mensajes | ~10,000 tokens | Sesiones largas |
| 2,000 mensajes | ~40,000 tokens | Grupos completos |

### Estrategia alternativa: Chunking con overlap

Si no tienes estructura de sesiones clara, usa ventanas con solapamiento:

```python
def crear_chunks_con_overlap(mensajes, tamaño=100, overlap=15):
    chunks = []
    i = 0
    while i < len(mensajes):
        chunk = mensajes[i:i + tamaño]
        chunks.append(chunk)
        i += (tamaño - overlap)
    return chunks
```

El overlap de 10-20% evita que una conversación que cruza el límite del chunk se pierda.

---

## PASO 4: Embeddings

Un embedding convierte texto en un vector numérico que captura su significado semántico.
Textos con significado similar tienen vectores similares (alta similitud coseno).

```
"Hoy aprendimos sobre límites con amor"  →  [0.23, -0.41, 0.87, ...]
"La sesión de crianza positiva fue útil" →  [0.21, -0.38, 0.85, ...]  <- similar
"El precio del transporte subió"         →  [-0.67, 0.12, -0.34, ...] <- diferente
```

### Modelo recomendado: sentence-transformers (gratuito, local)

```python
from sentence_transformers import SentenceTransformer

# Modelo multilingüe que funciona bien en español
modelo = SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')

# Generar embeddings para todos los chunks
embeddings = modelo.encode(chunks['texto_chunk'].tolist(), show_progress_bar=True)
# resultado: matriz de shape (n_chunks, 768)
```

**Por qué este modelo:**

- Gratuito, corre localmente (sin enviar datos a servidores externos)
- Entrenado en 50+ idiomas incluyendo español
- Buen balance entre calidad y velocidad
- ~400MB de descarga única

**Instalación:**

```bash
uv add sentence-transformers
```

### Almacenamiento de vectores: ChromaDB (gratuito, local)

```python
import chromadb

cliente = chromadb.PersistentClient(path="./data/vectorstore")
coleccion = cliente.get_or_create_collection("apapachar_mensajes")

# Guardar chunks con sus embeddings
coleccion.add(
    documents=chunks['texto_chunk'].tolist(),
    embeddings=embeddings.tolist(),
    metadatas=[
        {'ciudad': r['ciudad'], 'semana': str(r['semana'])}
        for _, r in chunks.iterrows()
    ],
    ids=[f"chunk_{i}" for i in range(len(chunks))]
)
```

ChromaDB guarda los vectores en disco y persisten entre sesiones de Python.

---

## PASO 5a: Clustering temático

Agrupa automáticamente los chunks por temas similares sin supervisión.

```python
from sklearn.cluster import KMeans
import numpy as np

# Definir número de clusters (empieza con 8-12 para Apapachar)
n_clusters = 10
kmeans = KMeans(n_clusters=n_clusters, random_state=42)
etiquetas = kmeans.fit_predict(embeddings)

chunks['cluster'] = etiquetas
```

### Visualización con UMAP

```python
import umap
import matplotlib.pyplot as plt

# Reducir de 768 dimensiones a 2 para visualizar
reductor = umap.UMAP(n_components=2, random_state=42)
coords_2d = reductor.fit_transform(embeddings)

plt.figure(figsize=(12, 8))
scatter = plt.scatter(coords_2d[:, 0], coords_2d[:, 1],
                      c=etiquetas, cmap='tab10', alpha=0.7)
plt.colorbar(scatter, label='Cluster')
plt.title('Clusters temáticos de mensajes Apapachar')
plt.savefig('outputs/figures/clusters_mensajes.png', dpi=150)
```

### Etiquetar clusters con Claude

Una vez que tienes los clusters, envía una muestra de cada uno a Claude para que
identifique el tema:

```
Prompt: "Aquí hay 10 mensajes del mismo grupo temático de un programa de crianza en
Colombia. ¿Cuál es el tema principal que los une? Responde en máximo 5 palabras.

[mensajes del cluster]"
```

---

## PASO 5b: Búsqueda semántica (base para RAG)

```python
def buscar_chunks_relevantes(pregunta, n_resultados=5):
    embedding_pregunta = modelo.encode([pregunta])
    resultados = coleccion.query(
        query_embeddings=embedding_pregunta.tolist(),
        n_results=n_resultados
    )
    return resultados['documents'][0]  # lista de chunks más similares
```

---

## Stack tecnológico completo

| Componente | Herramienta | Costo | Instalación |
|---|---|---|---|
| Manejo de datos | `pandas` | Gratuito | `uv add pandas` |
| Embeddings | `sentence-transformers` | Gratuito | `uv add sentence-transformers` |
| Vector store | `chromadb` | Gratuito | `uv add chromadb` |
| Clustering | `scikit-learn` | Gratuito | `uv add scikit-learn` |
| Visualización | `umap-learn` + `matplotlib` | Gratuito | `uv add umap-learn matplotlib` |
| RAG / Codificación | Claude API (Anthropic) | Plan Enterprise | `uv add anthropic` |

### Agregar todas las dependencias de una vez

```bash
uv add pandas sentence-transformers chromadb scikit-learn umap-learn matplotlib anthropic
```

---

## Orden de ejecución recomendado

```
1. Cargar y explorar el dataset de mensajes (pandas)
2. Análisis de calidad (tamaño, informalidad)        <- PASO 1
3. Limpieza básica del texto                         <- PASO 2
4. Definir estrategia de chunking y agrupar          <- PASO 3
5. Generar embeddings con sentence-transformers      <- PASO 4
6. Guardar vectores en ChromaDB                      <- PASO 4
7. Clustering temático (KMeans + UMAP)               <- PASO 5a
8. Análisis de similitud semántica entre chunks      <- PASO 7
9. Búsqueda semántica (RAG) con Claude               <- PASO 5b
```

---

## Nota sobre privacidad y clasificación de datos

El dataset de mensajes de Apapachar, una vez anonimizado (sin nombres completos,
documentos, celulares), se clasifica como **Internal** según las políticas de IPA.
Esto permite su procesamiento con herramientas de IA como Claude.

El paper de referencia adoptó una postura más conservadora (modelos locales, sin enviar
datos a APIs externas) porque trabajaba con datos de salud de pacientes en Brasil.
Para el contexto de Apapachar con datos ya anonimizados, el uso de Claude API es
apropiado bajo la clasificación Internal de IPA.

Si tienes dudas sobre clasificación de datos, consulta las IPA AI Usage Guidelines
en Box (`IPA_IT_Resources/Policies/AI - Claude`) o escribe a support@poverty-action.org.
