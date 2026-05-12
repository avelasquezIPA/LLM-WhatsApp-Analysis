/* =============================================================================
   01_remove_pii.do
   Propósito : Detectar y eliminar mensajes de WhatsApp con PII (nombres)
   Proyecto  : Apapachar - Evaluación IPA Colombia
   Creado    : 2025-12

   Notas metodológicas:
     - Los mensajes de WhatsApp contienen presentaciones personales con nombres.
     - Este script detecta patrones lingüísticos que indican la presencia de un
       nombre propio (ej. "Mi nombre es X", "Me llamo X", "Soy X Y").
     - Estrategia: alta cobertura de PII (sensibilidad), aceptando una tasa
       moderada de falsos positivos para no dejar nombres sin detectar.

   Patrones implementados (9 en total):
     1. "Mi nombre es [X]"           → alta confianza
     2. "Me llamo [X]"               → alta confianza
     3. "Soy [Nombre Apellido]"      → alta confianza (mayúsculas)
     4. "Soy [Nombre]" (una palabra) → media confianza (excluye roles)
     5. "*Nombre Apellido*" bold     → alta confianza
     6. "Nombre Apellido tengo/vivo" → alta confianza (inicio de mensaje)
     7. "Llamo Nombre Apellido"      → alta confianza
     8. "soy nombre apellido"        → nuevo: nombres en minúsculas
     9. "mi hijo/bebé/etc. + nombre" → nuevo: nombres de terceros

   Resultados en datos de ejemplo (DatosEjemplos-FalsePII.dta):
     Sensibilidad estimada : ~90% (54+ de 60 mensajes con PII detectados)
     Falsos positivos      : ~0%
     Falsos negativos      : mensajes sin frase de presentación visible
============================================================================= */

clear all
set more off

* -----------------------------------------------------------------------------
* RUTAS - ajustar según configuración del proyecto (setroot globals)
* -----------------------------------------------------------------------------
* Si usas el runner pattern del proyecto, estos globals ya están definidos.
* De lo contrario, descomenta y ajusta:
*
*   global datos_raw   "ruta/a/data/raw"
*   global datos_clean "ruta/a/data/clean"

* Nombre del archivo de entrada (sin extensión)
local archivo_entrada "DatosEjemplos-FalsePII"
local archivo_salida  "mensajes_sin_pii"

use "${datos_raw}/`archivo_entrada'.dta", clear

di as text _n "============================================"
di as text " Mensajes cargados: `=_N'"
di as text "============================================"


/* =============================================================================
   SECCIÓN 1: DETECCIÓN DE PII
   Genera flags individuales por patrón y un flag combinado `flag_pii`.
============================================================================= */

* --- 1a. "Mi nombre es [X]" y variantes ---
gen byte pii_nombre_es = ustrregexm(lower(texto), ///
    "mi nombre es|nombre es[: ]|mi nombre[: ]")

* --- 1b. "Me llamo [X]" y variantes ---
gen byte pii_me_llamo = ustrregexm(lower(texto), ///
    "me llamo|llamo[: ]")

* --- 1c. "Soy [Nombre Apellido]" — dos palabras con mayúscula inicial ---
* (?i) hace "soy/Soy/SOY" equivalentes; \p{Lu} exige mayúscula para el nombre.
gen byte pii_soy_nombre_completo = ustrregexm(texto, ///
    "(?i)soy\s+\p{Lu}[\p{L}]{1,}\s+\p{Lu}[\p{L}]{1,}")

* --- 1d. "Soy [Nombre]" — una sola palabra con mayúscula inicial ---
gen byte pii_soy_nombre_simple = ustrregexm(texto, ///
    "(?i)soy\s+\p{Lu}[\p{L}]{2,}")

* Excluir palabras de rol conocidas (no son nombres propios)
local roles "abuela|abuelita|abuelito|mamá|mama|madre|papá|papa|padre|"   ///
            "cuidadora|cuidador|facilitador|única|unica|único|unico|auxiliar"
replace pii_soy_nombre_simple = 0 if ///
    ustrregexm(lower(texto), "soy\s+(`roles')")

* --- 1e. Nombre en negritas de WhatsApp (*Nombre Apellido*) ---
* Captura 2 o 3 palabras en negritas: *David Jacobo Polania*
gen byte pii_bold_nombre = ustrregexm(texto, ///
    "\*\p{Lu}[\p{L}]+(\s+\p{Lu}[\p{L}]+){1,2}\*")

* --- 1f. Nombre al inicio del mensaje sin frase de introducción ---
* Patrón: "Nombre Apellido tengo/vivo/soy/cuido..."
gen byte pii_nombre_inicio = ustrregexm(texto, ///
    "^\p{Lu}[\p{L}]+\s+\p{Lu}[\p{L}]+\s+(tengo|vivo|soy|cuido|tenía)")

* --- 1g. "Llamo Nombre Apellido" ---
gen byte pii_llamo_nombre = ustrregexm(texto, ///
    "(?i)llamo\s+\p{Lu}[\p{L}]+\s+\p{Lu}[\p{L}]+")

* ---------------------------------------------------------------------------
* NUEVOS PATRONES (mayor cobertura de PII)
* ---------------------------------------------------------------------------

* --- 1h. "soy nombre apellido" en minúsculas ---
* Detecta presentaciones donde la persona no usó mayúsculas:
* "Hola soy mariana", "soy antonia romero"
* Captura dos palabras consecutivas en minúsculas después de "soy".
gen byte pii_soy_minuscula = ustrregexm(lower(texto), ///
    "\bsoy\s+[a-záéíóúñ]{3,}\s+[a-záéíóúñ]{3,}")

* Excluir frases comunes que no son nombres:
* "soy muy feliz", "soy una mamá", "soy el facilitador", etc.
local excl_min "muy\s|una\s|un\s|el\s|la\s|bastante|también|tambien|"    ///
               "quien|mamá|mama|madre|papá|papa|padre|cuidadora|cuidador|" ///
               "abuela|abuelo|auxiliar|facilitador|mamita|toda\s|todo\s"
replace pii_soy_minuscula = 0 if ///
    ustrregexm(lower(texto), "\bsoy\s+(`excl_min')")

* --- 1i. Nombres de terceros: hijos, pareja, nietos mencionados en el texto ---
* Detecta nombres que aparecen después de palabras de relación familiar.
* Ejemplos: "mi hijo Lucas", "mi bebé pepito", "el pequeño Diego",
*           "mis niños Valerio y Antonia"
gen byte pii_tercero = ustrregexm(texto, ///
    "(?i)(mi\s+(hij[oa]s?|beb[eé]s?|ni[nñ][oa]s?|espos[oa]|sobrin[oa]|" ///
    "niet[oa]|pr[ií]ncipe|princesa|gordito|gordita|pequeñ[oa]|"           ///
    "chiquit[oa]|gordo|gorda)"                                            ///
    "|el\s+(pequeñ[oa]|beb[eé]|hijit[oa])"                               ///
    "|la\s+(pequeñ[oa]|hijita)"                                           ///
    "|niñ[oa]s?\s+[A-ZÁÉÍÓÚÑ]"                                           ///
    "|su\s+hij[oa])"                                                      ///
    "\s+\p{L}[\p{L}]{2,}")

* Excluir adjetivos comunes que siguen al trigger pero no son nombres:
* "mi hijo mayor", "mi bebé hermoso", "mi niña que aprende"
replace pii_tercero = 0 if ustrregexm(lower(texto), ///
    "(mi\s+(hij[oa]|beb[eé]|ni[nñ][oa]))\s+"                             ///
    "(mayor|menor|hermoso|hermosa|bello|bella|lindo|linda|"               ///
    "pues\s|comparte|cada\s|que\s|de\s|a\s|con\s|lo\s|la\s)")


* --- FLAG COMBINADO ---
gen byte flag_pii = max(pii_nombre_es, pii_me_llamo, pii_soy_nombre_completo, ///
                        pii_soy_nombre_simple, pii_bold_nombre,               ///
                        pii_nombre_inicio, pii_llamo_nombre,                  ///
                        pii_soy_minuscula, pii_tercero)

label var flag_pii                "1 = mensaje contiene potencial PII (nombre)"
label var pii_nombre_es           "Patrón: 'mi nombre es...'"
label var pii_me_llamo            "Patrón: 'me llamo...'"
label var pii_soy_nombre_completo "Patrón: 'soy Nombre Apellido' (mayúsculas)"
label var pii_soy_nombre_simple   "Patrón: 'soy Nombre' (una palabra, mayúscula)"
label var pii_bold_nombre         "Patrón: '*Nombre Apellido*' (negritas WhatsApp)"
label var pii_nombre_inicio       "Patrón: 'Nombre Apellido tengo/vivo...'"
label var pii_llamo_nombre        "Patrón: 'llamo Nombre Apellido'"
label var pii_soy_minuscula       "Patrón: 'soy nombre apellido' (minúsculas)"
label var pii_tercero             "Patrón: 'mi hijo/bebé/etc. + nombre'"

label define lbl_pii 0 "No PII" 1 "PII detectado"
label values flag_pii lbl_pii


/* =============================================================================
   SECCIÓN 2: REPORTE DE DETECCIÓN
============================================================================= */

di as text _n "============================================"
di as text " Resumen de detección de PII"
di as text "============================================"

di as text _n "  Mensajes flaggeados por patrón:"
foreach var of varlist pii_* {
    qui count if `var' == 1
    di as text "    `var': `r(N)'"
}

di as text _n "  Total mensajes con flag_pii = 1:"
count if flag_pii == 1
di as text "  Total mensajes con flag_pii = 0:"
count if flag_pii == 0


/* =============================================================================
   SECCIÓN 3: VALIDACIÓN (solo si existe la variable `Modificado`)
   Compara el flag generado contra el ground truth.
   Esta sección se salta automáticamente si la variable no existe.
============================================================================= */

capture confirm variable Modificado
if !_rc {

    di as text _n "============================================"
    di as text " Validación contra variable Modificado"
    di as text "============================================"

    gen byte mod_si = (Modificado == "Si")

    di as text _n "  Tabla de confusión (flag_pii vs Modificado):"
    tab flag_pii mod_si, row col nofreq

    qui count if mod_si == 1
    local total_si = r(N)
    qui count if mod_si == 1 & flag_pii == 1
    local vp = r(N)
    di as text _n "  Sensibilidad (recall) : " ///
        %4.1f (`vp'/`total_si'*100) "% (" `vp' "/" `total_si' " mensajes PII detectados)"

    qui count if mod_si == 0
    local total_no = r(N)
    qui count if mod_si == 0 & flag_pii == 0
    local vn = r(N)
    di as text "  Especificidad         : " ///
        %4.1f (`vn'/`total_no'*100) "% (" `vn' "/" `total_no' " mensajes limpios conservados)"

    qui count if mod_si == 1 & flag_pii == 0
    if r(N) > 0 {
        di as text _n "  --- FALSOS NEGATIVOS (PII no detectado) ---"
        list texto if mod_si == 1 & flag_pii == 0, clean noobs
    }

    qui count if mod_si == 0 & flag_pii == 1
    if r(N) > 0 {
        di as text _n "  --- FALSOS POSITIVOS (mensajes limpios eliminados) ---"
        list texto if mod_si == 0 & flag_pii == 1, clean noobs
    }

    drop mod_si

}


/* =============================================================================
   SECCIÓN 4: ELIMINACIÓN DE MENSAJES CON PII
============================================================================= */

di as text _n "============================================"
di as text " Eliminando mensajes con PII"
di as text "============================================"

qui count
local n_antes = r(N)

drop if flag_pii == 1

qui count
local n_despues = r(N)
local n_eliminados = `n_antes' - `n_despues'

di as text "  Mensajes antes     : `n_antes'"
di as text "  Mensajes eliminados: `n_eliminados'"
di as text "  Mensajes restantes : `n_despues'"

* Limpiar variables auxiliares
drop pii_nombre_es pii_me_llamo pii_soy_nombre_completo pii_soy_nombre_simple ///
     pii_bold_nombre pii_nombre_inicio pii_llamo_nombre                        ///
     pii_soy_minuscula pii_tercero flag_pii


/* =============================================================================
   SECCIÓN 5: GUARDAR
============================================================================= */

compress
save "${datos_clean}/`archivo_salida'.dta", replace

di as text _n "Guardado: ${datos_clean}/`archivo_salida'.dta"
di as text "============================================" _n
