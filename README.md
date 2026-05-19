# Análisis LLM de Grupos de WhatsApp - Programa Apapáchar

Repositorio de IPA Colombia para el análisis de mensajes de WhatsApp de la
intervención del **Programa Apapáchar**, usando Large Language Models (LLMs)
para summarización temática y análisis de contenido.

> [!WARNING]
> NUNCA SUBAS DATOS A GITHUB.
>
> NUNCA USES HERRAMIENTAS DE IA CON DATOS QUE CONTENGAN
> INFORMACION PERSONALMENTE IDENTIFICABLE (PII) SIN HABERLA REMOVIDO ANTES.

---

## El Programa Apapáchar

Apapáchar es un programa de crianza **gratuito e híbrido** (80% digital / 20%
presencial) co-desarrollado por Fundación Apapacho, ICBF, Equimundo, CINDE e
IPA Colombia. Está dirigido a cuidadores de niñas y niños de 0 a 5 años en
familias vulnerables, con énfasis especial en involucrar a padres y cuidadores
hombres.

**Objetivo central:** prevenir la violencia intrafamiliar contra la niñez y
promover una crianza amorosa, sensible y corresponsable.

La intervención dura 12 semanas organizadas en 4 niveles. El canal principal
de comunicación son grupos de WhatsApp donde facilitadores y beneficiarios
intercambian mensajes, reflexiones y actividades semanales.

Para la documentación completa del programa ver
[`documentation/PROYECTO.md`](documentation/PROYECTO.md).

---

## Propósito de este repositorio

Este repositorio contiene el pipeline de análisis de los mensajes de WhatsApp
generados durante la intervención. El objetivo es extraer aprendizajes
cualitativos a escala: temas recurrentes, evolución del programa semana a
semana, nivel de participación y engagement, y hallazgos relevantes para la
investigación.

El pipeline combina **Stata** (limpieza y preprocesamiento) con **Python +
Claude API** (embeddings, clustering temático y summarización).

---

## Paso 1: Limpieza y remoción de PII

Antes de cualquier análisis, los mensajes pasan por un proceso de limpieza que
**elimina todos los mensajes con nombres propios** u otra información
personalmente identificable.

El script `do_files/01_remove_pii.do` implementa 9 patrones de detección en
Stata cubriendo los casos más comunes en mensajes de WhatsApp en español:

| Patrón | Ejemplo |
| --- | --- |
| "Mi nombre es..." | `"Mi nombre es Diego Quintero"` |
| "Me llamo..." | `"me llamo Salomé González"` |
| "Soy Nombre Apellido" | `"soy Jacobo Gutierrez"` |
| "Soy Nombre" (una palabra) | `"Hola soy Pepa"` |
| Negritas WhatsApp | `"soy *David Jacobo Polania*"` |
| Nombre al inicio del mensaje | `"Salome Gonzalez tengo 31 años..."` |
| "Llamo Nombre Apellido" | `"llamo Andrea Trujillo"` |
| Nombres en minúsculas | `"soy mariana"`, `"soy antonia romero"` |
| Nombres de terceros | `"mi hijo Lucas"`, `"mi bebé pepito"` |

**Rendimiento estimado sobre datos de ejemplo:**

- Sensibilidad (PII detectado): ~90%
- Falsos positivos: ~0%

Una vez removidos los mensajes con PII, los datos se clasifican como
**Internal** según las políticas de IPA, lo lo que permite su procesamiento con
herramientas de IA como Claude.

Para la explicación detallada del script ver
[`documentation/Explicacion-ScriptLimpieza.md`](documentation/Explicacion-ScriptLimpieza.md).

---

## Paso 2: Pipeline LLM (summarización y embeddings)

El pipeline de análisis está informado por Ferreira et al. (2025), que evalúa
exactamente este escenario: mensajes de WhatsApp informales, en idioma
no-inglés, con datos ruidosos, usando LLMs para generar resúmenes útiles.

> Ferreira et al. (2025). *A comprehensive qualitative analysis of patient
> dialogue summarization using large language models applied to noisy,
> informal, non-English real-world data.* Scientific Reports, 15, 31660.

El pipeline tiene 6 pasos:

```text
Mensajes anonimizados (.dta)
        |
 [1] Análisis de calidad (tamaño, informalidad)
        |
 [2] Limpieza y preprocesamiento
        |
 [3] Chunking (agrupación por semana/ciudad)
        |
 [4] Embeddings (sentence-transformers, multilingüe)
        |
     --------
    |        |
 [5a]      [5b]
Clustering  Búsqueda
temático    semántica (RAG)
    |        |
     --------
        |
 [6] Summarización con Claude API
        |
 Resúmenes estructurados por grupo/sesión
```text

### Herramientas por paso

| Paso | Herramienta |
| --- | --- |
| Limpieza y preprocesamiento | Stata (`01_remove_pii.do`) |
| Análisis de calidad | Python + pandas |
| Chunking | Python + pandas |
| Embeddings | `sentence-transformers` (gratuito, local) |
| Vector store | `chromadb` (gratuito, local) |
| Clustering | `scikit-learn` (KMeans) + `umap-learn` |
| Summarización / RAG | Claude API (Anthropic) |

Los pasos de embeddings, clustering y summarización **no pueden hacerse en
Stata** ya que requieren librerías de machine learning inexistentes en ese
entorno.

Para la documentación completa del pipeline ver
[`documentation/llm-whatsapp-pipeline.md`](documentation/llm-whatsapp-pipeline.md).

---

## Estructura del repositorio

```text
├── README.md
├── data/
│   ├── raw/                        # Datos originales (NO subir a GitHub)
│   ├── clean/                      # Datos limpios (sin PII)
│   └── final/                      # Datasets listos para análisis
├── do_files/
│   └── 01_remove_pii.do            # Detección y remoción de PII
├── documentation/
│   ├── PROYECTO.md                 # Descripción completa del Programa Apapáchar
│   ├── llm-whatsapp-pipeline.md    # Diseño del pipeline LLM
│   ├── Explicacion-ScriptLimpieza.md # Documentación del script de PII
│   └── s41598-025-13560-9.md       # Paper de referencia (Ferreira et al., 2025)
├── src/                            # Scripts Python del pipeline LLM
└── outputs/
    ├── figures/
    └── tables/
```text

---

## Configuración del entorno

### Prerrequisitos

- Stata 17+ (para el script de limpieza de PII)
- Python 3.12+ con `uv` (para el pipeline LLM)

### Setup

```bash
# Instalar dependencias Python
uv add pandas sentence-transformers chromadb scikit-learn umap-learn matplotlib anthropic

# Configurar API key de Claude en .env
ANTHROPIC_API_KEY=tu_api_key_aqui

# Configurar ruta de Stata en .env
STATA_CMD='C:\Program Files\Stata18\StataSE-64.exe'
STATA_EDITION='se'
```text

### Correr el script de limpieza de PII

```bash
just stata-script 01_remove_pii
```text

---

## Privacidad y clasificación de datos

- Los datos **crudos** (con nombres de participantes) son **Confidential** y
  nunca deben subirse a GitHub ni procesarse con IA.
- Los datos **anonimizados** (después de correr `01_remove_pii.do`) se
  clasifican como **Internal** y pueden procesarse con Claude API.
- Ante dudas sobre clasificación de datos, consulta las
  [IPA AI Usage Guidelines](https://ipastorage.box.com/s/mvr67ygvz1y3v8qmgjey67lk7msmyeks)
  o escribe a support@poverty-action.org.

---

## Referencias

- Ferreira, A. A. et al. (2025). A comprehensive qualitative analysis of
  patient dialogue summarization using large language models applied to noisy,
  informal, non-English real-world data. *Scientific Reports*, 15, 31660.
  https://doi.org/10.1038/s41598-025-13560-9
- Cuartas, J. et al. (2022). The Apapacho Violence Prevention Parenting
  Program: Conceptual Foundations and Pathways to Scale. *Int J Environ Res
  Public Health*, 19(14), 8582.
