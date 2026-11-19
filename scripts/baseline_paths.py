"""Caminhos e saídas da sequência inicial de Ciência de Dados."""
from pathlib import Path
import os

DEFAULT_DRIVE_ROOT = Path("/content/drive/MyDrive/Ciência de Dados - Iatan - Process Mining e Experimentos/Iatan 2025 - entrega revisada/01 - Sem mineração de processos")


def is_project_root(path):
    path = Path(path).expanduser()
    return (path / "scripts/baseline_paths.py").is_file() and (path / "pipeline").is_dir()


def project_root():
    explicit = os.environ.get("IATAN_BASELINE_ROOT", "").strip()
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not is_project_root(root):
            raise FileNotFoundError("A raiz da sequência inicial precisa conter scripts/baseline_paths.py e pipeline/.")
        return root
    try:
        import google.colab
    except ImportError:
        override = os.environ.get("CO2_PROJECT_ROOT", "").strip()
        candidates = ([Path(override)] if override else []) + [Path.cwd(), *Path.cwd().parents]
    else:
        candidates = [DEFAULT_DRIVE_ROOT]
    for candidate in candidates:
        if is_project_root(candidate):
            return candidate.expanduser().resolve()
    raise FileNotFoundError("Abra a sequência inicial dentro da sua pasta ou defina IATAN_BASELINE_ROOT.")


def get_epa_api_key():
    value = os.environ.get("EPA_API_KEY", "").strip()
    if value:
        return value
    try:
        from google.colab import userdata
        return str(userdata.get("EPA_API_KEY") or "").strip()
    except (ImportError, KeyError):
        return ""
