---
name: check-pii
description: Use this skill when the user wants to check a data file for potential personally identifiable information (PII) before processing it through the pipeline. Performs a dry-run analysis that reports what would be flagged or removed without modifying any data. Invoked with /check-pii or /check-pii <file_path>. IMPORTANT: This skill only reads metadata and aggregate statistics — it never outputs raw message content to avoid exposing PII in the conversation.
---

# Check PII Skill

Performs a dry-run PII audit on a data file and reports aggregate statistics.

**Privacy guarantee:** This skill only reads counts, field names, and summary statistics.
It never outputs raw message content, participant names, or identifiers into the conversation.

## Usage

```
/check-pii
/check-pii data/raw/mi_base.dta
/check-pii data/raw/mi_base.xlsx
```

If no path is given, scans all `.dta` and `.xlsx` files in `data/raw/`.

## What It Checks

### 1. Column inventory

Lists all columns in the file with their data types. Flags columns whose names
suggest PII:

| Pattern | PII risk |
|---------|---------|
| `name`, `nombre`, `apellido` | High — direct identifier |
| `phone`, `telefono`, `celular` | High — direct identifier |
| `email`, `correo` | High — direct identifier |
| `id`, `cedula`, `identificacion` | Medium — may be identifier |
| `ciudad`, `barrio`, `direccion` | Medium — location |
| `fecha_nacimiento`, `edad`, `age` | Medium — quasi-identifier |

### 2. Free-text field scan

For columns that contain free text (message content), estimates whether messages
contain patterns suggesting PII:

- Phone-number patterns (`3\d{9}`, `+57...`)
- Email patterns (`@`)
- Number sequences that could be IDs

Reports **only the count** of flagged messages, never the content.

### 3. Unique identifier check

Reports the number of unique values in potential ID columns.
A column with N unique values where N ≈ total rows is likely a direct identifier.

## Workflow

### Step 1: Identify the file

```python
# If no path given, find candidates
import glob
files = glob.glob("data/raw/*.dta") + glob.glob("data/raw/*.xlsx")
```

### Step 2: Load column metadata only

```python
import pandas as pd

# For .dta — use iterator=True to read metadata without loading all data
df_meta = pd.read_stata(path, iterator=True)
print("Columns:", df_meta.variable_labels())

# For .xlsx — read only header row
df_head = pd.read_excel(path, nrows=0)
print("Columns:", df_head.columns.tolist())
```

### Step 3: Run column-level PII scan

```python
import re

HIGH_RISK_PATTERNS = [
    r'\bname\b', r'\bnombre\b', r'\bapellido\b',
    r'\bphone\b', r'\btelefono\b', r'\bcelular\b',
    r'\bemail\b', r'\bcorreo\b',
]
MEDIUM_RISK_PATTERNS = [
    r'\bid\b', r'\bcedula\b', r'\bidentificacion\b',
    r'\bciudad\b', r'\bbarrio\b', r'\bdireccion\b',
    r'\bfecha_nacimiento\b', r'\bedad\b', r'\bage\b',
]

for col in df.columns:
    col_lower = col.lower()
    if any(re.search(p, col_lower) for p in HIGH_RISK_PATTERNS):
        print(f"  HIGH: {col}")
    elif any(re.search(p, col_lower) for p in MEDIUM_RISK_PATTERNS):
        print(f"  MEDIUM: {col}")
```

### Step 4: Scan free-text content (aggregate only)

```python
# Identify likely message-text columns
# Load only that column, count matches — never print content
text_col = cfg["data"]["columns"]["message_text"]  # from config.yaml

PHONE_RE = re.compile(r'(\+?57)?[\s-]?3\d{2}[\s-]?\d{3}[\s-]?\d{4}')
EMAIL_RE = re.compile(r'\b[\w.+-]+@[\w-]+\.\w{2,}\b')

n_phone = df[text_col].str.contains(PHONE_RE, na=False).sum()
n_email = df[text_col].str.contains(EMAIL_RE, na=False).sum()

print(f"  Phone patterns found: {n_phone} messages")
print(f"  Email patterns found: {n_email} messages")
```

### Step 5: Report (never log raw content)

Report a structured summary:

```
PII Audit Report: data/raw/mi_base.dta
==========================================
Total rows: 12,450
Total columns: 18

Column Risk Assessment:
  HIGH RISK (0 columns found)
  MEDIUM RISK (2 columns):
    - ciudad (string, 4 unique values)
    - id_f (string, 420 unique values)

Free-text content scan (column: texto_limpio):
  Phone-number patterns: 3 messages
  Email patterns: 0 messages

Recommendation:
  The file appears suitable for pipeline processing.
  Consider removing 'id_f' column if not needed for analysis,
  or ensure it is pseudonymized (not linked to real identities).
```

## Recommended Next Steps

Based on the audit results:

| Finding | Action |
|---------|--------|
| HIGH RISK columns found | Remove or hash before running pipeline |
| Phone/email patterns in text | Run Stata PII removal script first |
| ID column with real identifiers | Replace with sequential pseudonym |
| All clear | Proceed with `/run-step 2` (preprocessing) |

## Related

- `scripts/do_files/00_PII_removal.do` — Stata script that removes PII from raw data
- `data/raw/DatosEjemplos-FalsePII.dta` — Example of what the cleaned format looks like
- `config.yaml > data.values.facilitator_sender` — How senders are labeled after PII removal

## Important Notes

- This skill **never** stores or logs message content
- If the audit reveals genuine PII in a file you accidentally shared with Claude,
  clear the conversation immediately and contact support@poverty-action.org
- See IPA AI Usage Guidelines: https://ipastorage.box.com/s/mvr67ygvz1y3v8qmgjey67lk7msmyeks
