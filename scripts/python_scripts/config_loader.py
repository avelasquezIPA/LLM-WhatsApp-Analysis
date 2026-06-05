"""Cargador del archivo config.yaml del proyecto.

Uso en cualquier script del pipeline:

    from config_loader import cfg

    model_name = cfg["models"]["embedding_model"]
    col_text   = cfg["data"]["columns"]["message_text"]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Raíz del proyecto: dos niveles arriba de scripts/python_scripts/
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_CONFIG_PATH = _PROJECT_ROOT / "config.yaml"


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Carga config.yaml y retorna el diccionario completo."""
    config_path = path or _CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(
            f"config.yaml no encontrado en {config_path}\n"
            "Copia config.yaml a la raíz del proyecto y edita los valores."
        )
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


# Singleton: se carga una sola vez por proceso
cfg: dict[str, Any] = load_config()

# Atajos de uso frecuente
PROJECT_ROOT: Path = _PROJECT_ROOT
DATA_DIR: Path = PROJECT_ROOT / "data"
OUTPUTS_DIR: Path = PROJECT_ROOT / "outputs"
TABLES_DIR: Path = OUTPUTS_DIR / "tables"
FIGURES_DIR: Path = OUTPUTS_DIR / "figures"
