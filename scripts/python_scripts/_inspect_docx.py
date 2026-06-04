"""Inspects the default font from document XML settings."""

import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
path = ROOT / "documentation" / "Programa" / "A+P_Informe cierre de año 2025.docx"

# Read raw XML from the docx zip
with zipfile.ZipFile(path) as z:
    # Document defaults
    with z.open("word/settings.xml") as f:
        settings = f.read().decode("utf-8")
    # Styles for default font
    with z.open("word/styles.xml") as f:
        styles_xml = f.read().decode("utf-8")
    # Theme fonts
    try:
        with z.open("word/theme/theme1.xml") as f:
            theme_xml = f.read().decode("utf-8")
        fonts_in_theme = re.findall(r'typeface="([^"]+)"', theme_xml)
        print("Theme fonts:", set(fonts_in_theme))
    except Exception as e:
        print(f"Theme: {e}")

# Find docDefaults in styles.xml
defaults = re.search(r"<w:docDefaults>(.*?)</w:docDefaults>", styles_xml, re.DOTALL)
if defaults:
    print("\ndocDefaults XML:")
    print(defaults.group(0)[:800])

# Look for w:rFonts in Normal style
normal = re.search(
    r'<w:style[^>]*w:styleId="Normal"[^>]*>(.*?)</w:style>', styles_xml, re.DOTALL
)
if normal:
    print("\nNormal style (first 500 chars):")
    print(normal.group(0)[:500])
