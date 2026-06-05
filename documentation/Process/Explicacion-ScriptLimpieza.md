# Explicación: Script de Limpieza de PII en Mensajes de WhatsApp

**Archivo:** `do_files/01_remove_pii.do`
**Proyecto:** Apapachar - Evaluación IPA Colombia

---

## ¿Qué hace este script?

Los grupos de WhatsApp del programa Apapachar contienen mensajes donde los
participantes se presentan con su nombre completo, mencionan nombres de sus
hijos o de otras personas. Este script detecta esos mensajes y los elimina
de la base de datos antes de cualquier análisis, para proteger la identidad
de los participantes.

El script **no modifica el texto** de los mensajes: los elimina completamente
si detecta que contienen un nombre propio.

---

## Estrategia de detección

La detección se basa en **patrones lingüísticos** típicos de las presentaciones
en WhatsApp. En lugar de buscar nombres específicos (que serían infinitos), el
script busca las frases que introducen un nombre.

La estrategia es **protectora**: prioriza no dejar pasar mensajes con PII
(sensibilidad alta) por encima de conservar todos los mensajes limpios. Esto
significa que el script puede eliminar algunos mensajes sin nombre por error
(falsos positivos), pero captura la mayoría de los casos con PII.

---

## Los 9 patrones de detección

### Patrones 1-7: presentaciones directas (alta confianza)

Estos patrones detectan las frases más comunes con las que una persona revela
su nombre en un grupo de WhatsApp.

#### Patrón 1: "Mi nombre es..."

```stata
gen byte pii_nombre_es = ustrregexm(lower(texto),
    "mi nombre es|nombre es[: ]|mi nombre[: ]")
```

Detecta frases como "Mi nombre es Diego Quintero" o "nombre es: Salomé González".
Es el patrón con mayor cobertura (captura la mayoría de presentaciones formales).

---

#### Patrón 2: "Me llamo..."

```stata
gen byte pii_me_llamo = ustrregexm(lower(texto),
    "me llamo|llamo[: ]")
```

Detecta "me llamo Jhoan Rodriguez", "llamo: Andrea".

---

#### Patrón 3: "Soy Nombre Apellido" (dos palabras en mayúscula)

```stata
gen byte pii_soy_nombre_completo = ustrregexm(texto,
    "(?i)soy\s+\p{Lu}[\p{L}]{1,}\s+\p{Lu}[\p{L}]{1,}")
```

Detecta cuando después de "soy" aparecen dos palabras que empiezan con
mayúscula. El `(?i)` hace que "soy/Soy/SOY" se detecten igual. `\p{Lu}`
es una clase Unicode que reconoce letras mayúsculas con tilde (Á, É, Ñ, etc.).

Detecta: "soy Jacobo Gutierrez", "Soy Diego Quintero".
No detecta: "soy muy feliz" (minúsculas).

---

#### Patrón 4: "Soy Nombre" (una sola palabra en mayúscula)

```stata
gen byte pii_soy_nombre_simple = ustrregexm(texto,
    "(?i)soy\s+\p{Lu}[\p{L}]{2,}")
```

Detecta "Hola soy Pepa", "Ok yo soy Antonio".

Para evitar falsos positivos, se excluyen palabras de rol conocidas:

```stata
local roles "abuela|abuelita|mamá|mama|madre|papá|papa|padre|
             cuidadora|cuidador|facilitador|única|unica|auxiliar"
replace pii_soy_nombre_simple = 0 if
    ustrregexm(lower(texto), "soy\s+(`roles')")
```

Esto asegura que "Soy Abuelita", "Soy mamá", "Soy cuidadora" no se eliminen.

---

#### Patrón 5: Nombre en negritas de WhatsApp

```stata
gen byte pii_bold_nombre = ustrregexm(texto,
    "\*\p{Lu}[\p{L}]+(\s+\p{Lu}[\p{L}]+){1,2}\*")
```

En WhatsApp, el texto entre asteriscos aparece en **negritas**. El patrón
detecta entre 2 y 3 palabras en negritas con mayúscula inicial:
`*David Jacobo Polania*`, `*Ana Rodríguez*`.

---

#### Patrón 6: Nombre al inicio del mensaje

```stata
gen byte pii_nombre_inicio = ustrregexm(texto,
    "^\p{Lu}[\p{L}]+\s+\p{Lu}[\p{L}]+\s+(tengo|vivo|soy|cuido|tenía)")
```

Detecta mensajes que empiezan directamente con el nombre sin frase
introductoria: "Salome Gonzalez tengo 31 años...".

El `^` indica inicio del mensaje. Requiere una palabra típica de presentación
(tengo, vivo, soy, cuido) después del nombre para reducir falsos positivos.

---

#### Patrón 7: "Llamo Nombre Apellido"

```stata
gen byte pii_llamo_nombre = ustrregexm(texto,
    "(?i)llamo\s+\p{Lu}[\p{L}]+\s+\p{Lu}[\p{L}]+")
```

Cubre variantes como "me llamo Jacobo Plaza Rodriguez".

---

### Patrón 8: nombres en minúsculas (nuevo)

```stata
gen byte pii_soy_minuscula = ustrregexm(lower(texto),
    "\bsoy\s+[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")
```

Este patrón nuevo detecta presentaciones donde la persona **no usó mayúsculas**:

- "Hola soy mariana"
- "soy antonia romero"

Busca dos palabras consecutivas de 3+ caracteres después de "soy". Trabaja
sobre `lower(texto)` para capturar cualquier capitalización.

Para evitar falsos positivos como "soy muy feliz" o "soy una mamá", se
excluyen palabras comunes que no son nombres:

```stata
local excl_min "muy\s|una\s|un\s|el\s|la\s|bastante|también|tambien|
                quien|mamá|mama|madre|papá|papa|cuidadora|cuidador|
                abuela|abuelo|auxiliar|facilitador|mamita|toda\s|todo\s"
replace pii_soy_minuscula = 0 if
    ustrregexm(lower(texto), "\bsoy\s+(`excl_min')")
```

---

### Patrón 9: nombres de terceros (nuevo)

```stata
gen byte pii_tercero = ustrregexm(texto,
    "(?i)(mi\s+(hij[oa]s?|beb[eé]s?|ni[nñ][oa]s?|espos[oa]|sobrin[oa]|
    niet[oa]|pr[ií]ncipe|princesa|gordito|gordita|pequeñ[oa]|chiquit[oa])
    |el\s+(pequeñ[oa]|beb[eé]|hijit[oa])
    |la\s+(pequeñ[oa]|hijita)
    |niñ[oa]s?\s+[A-ZÁÉÍÓÚÑ]
    |su\s+hij[oa])
    \s+\p{L}[\p{L}]{2,}")
```

Este patrón nuevo detecta cuando en el texto se menciona el **nombre de un
hijo, pareja u otro familiar**, aunque el autor no haya dado su propio nombre:

- "mi hijo Lucas" → "Lucas" es PII
- "mi bebé pepito Landázuri" → nombre del bebé
- "mis niños Valerio y Antonia" → nombres de los hijos
- "el pequeño Diego" → nombre del niño

El patrón usa palabras de relación como disparador y luego busca un nombre
de 3+ caracteres a continuación.

Para reducir falsos positivos ("mi hijo mayor", "mi bebé hermoso"), se excluyen
adjetivos comunes:

```stata
replace pii_tercero = 0 if ustrregexm(lower(texto),
    "(mi\s+(hij[oa]|beb[eé]|ni[nñ][oa]))\s+
    (mayor|menor|hermoso|hermosa|bello|bella|lindo|linda|
    pues\s|comparte|cada\s|que\s|de\s|a\s|con\s|lo\s|la\s)")
```

---

## Flag combinado

Una vez generados los 9 patrones, se combina en un único indicador:

```stata
gen byte flag_pii = max(pii_nombre_es, pii_me_llamo, pii_soy_nombre_completo,
                        pii_soy_nombre_simple, pii_bold_nombre,
                        pii_nombre_inicio, pii_llamo_nombre,
                        pii_soy_minuscula, pii_tercero)
```

Un mensaje queda marcado como `flag_pii = 1` si **al menos uno** de los
patrones lo detecta.

---

## Rendimiento estimado

Medido sobre los datos de ejemplo (`DatosEjemplos-FalsePII.dta`, 143 mensajes):

| Métrica | Valor |
| --- | --- |
| Mensajes con PII (ground truth) | 60 |
| Mensajes sin PII (ground truth) | 83 |
| Sensibilidad (PII detectado) | ~90% |
| Falsos positivos | ~0% |

### Falsos negativos que permanecen

Los únicos mensajes con PII que el script no captura son:

1. **Mensajes sin ninguna frase de presentación visible**: algunos mensajes
   marcados como PII en los datos de ejemplo parecen haber tenido el nombre
   ya removido o no siguen ningún patrón lingüístico identificable.

2. **Plantillas del facilitador** ("Por ejemplo, este es el mío: Tengo X años..."):
   mensajes enviados por el facilitador como ejemplo al grupo. No se incluyen
   como objetivo de detección.

---

## Sección de validación (Sección 3)

Si la base de datos tiene una variable `Modificado` con valores `"Si"`/`"No"`,
el script calcula y muestra automáticamente:

- Tabla de confusión
- Sensibilidad y especificidad
- Lista de falsos negativos y falsos positivos para revisión manual

Si esa variable no existe (caso de los datos reales), esta sección se salta
sin errores ni advertencias.

---

## Cómo correr el script

### Prerrequisitos

- Stata 17 o superior (usa `ustrregexm` para Unicode)
- Globals `${datos_raw}` y `${datos_clean}` definidos (via setroot del proyecto)

### Ajustar los nombres de archivo

Al inicio del script, cambiar los locales según el archivo real:

```stata
local archivo_entrada "nombre_del_archivo_real"
local archivo_salida  "mensajes_sin_pii"
```

### Ejecución

```bash
just stata-script 01_remove_pii
```

O directamente en Stata:

```stata
do "do_files/01_remove_pii.do"
```

### Output

Guarda la base limpia en `${datos_clean}/mensajes_sin_pii.dta` sin las
variables auxiliares de detección.

---

## Posibles mejoras futuras

- Ampliar la lista de exclusiones en los Patrones 4 y 8 si aparecen nuevos
  falsos positivos con los datos reales.
- Agregar detección de números de teléfono o direcciones si se identifican
  en los datos.
- Considerar una versión que anonimice (reemplace el nombre por `[NOMBRE]`)
  en lugar de eliminar el mensaje completo, para conservar más datos útiles.
