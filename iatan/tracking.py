"""Proveniência explícita: aula e-Science (pp. 53–56), MLflow Tracking API.

Manual logging is deliberate: feature lists and time boundaries are scientific factors.
"""
from pathlib import Path
import contextlib
import importlib.metadata
import json
import os
import platform
import subprocess
import mlflow
from . import PUBLIC_CONTEXT
from .data import digest, write_json


def configure(root):
    folder = (root / 'tracking').resolve(); folder.mkdir(exist_ok=True)
    uri = os.environ.get('MLFLOW_TRACKING_URI', 'sqlite:///' + (folder / 'mlflow.db').as_posix())
    mlflow.set_tracking_uri(uri)
    name = 'Iatan2 - Ciencia de Dados - Process Mining'
    if mlflow.get_experiment_by_name(name) is None:
        mlflow.create_experiment(name, artifact_location=(folder / 'artifacts').as_uri())
    mlflow.set_experiment(name)


def provenance(root):
    try:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                         text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = 'unavailable'
    packages = {}
    for name in ['numpy', 'pandas', 'pyarrow', 'scikit-learn', 'xgboost', 'hmmlearn', 'pm4py', 'mlflow']:
        try: packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError: packages[name] = 'not_installed'
    paths = list((root / 'iatan').glob('*.py')) + list((root / 'configs').glob('*.json'))
    result = {'python': platform.python_version(),
              'packages': packages, 'git_head': commit,
              'source_hashes': {p.relative_to(root).as_posix(): digest(p) for p in sorted(paths)}}
    compatibility = root / 'configs/source_compatibility.json'
    if compatibility.is_file():
        result['source_compatibility'] = {
            'manifest_sha256': digest(compatibility),
            'scope': 'Audited changes to public records; actual source hashes remain recorded. '
                     'A compatible source revision is not a bit-identical historical execution.',
        }
    return result


def portable_path(path, root):
    """Nome público de um arquivo, sem publicar diretórios da máquina."""
    path, root = Path(path).resolve(), Path(root).resolve()
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return 'external/' + path.name


def source_matches(root, name, previous_sha256):
    """Valida a fonte atual ou uma migração de privacidade explicitamente auditada.

    O manifesto não substitui o hash atual na proveniência. Alterações posteriores
    em qualquer fonte invalidam a migração; previsões de referência continuam
    sujeitas à comparação exata nos fluxos que as reutilizam.
    """
    current = digest(Path(root) / name)
    if current == previous_sha256:
        return True
    manifest = Path(root) / 'configs/source_compatibility.json'
    if not manifest.is_file():
        return False
    entry = json.loads(manifest.read_text(encoding='utf-8')).get('files', {}).get(name, {})
    return (entry.get('current_sha256') == current
            and previous_sha256 in entry.get('previous_sha256', []))


@contextlib.contextmanager
def public_span(*args, **kwargs):
    """Registra spans sem inferir a identidade ou a cópia Git da máquina."""
    with mlflow.tracing.context(metadata=PUBLIC_CONTEXT), mlflow.start_span(*args, **kwargs) as span:
        yield span


@contextlib.contextmanager
def tracked(root, name, out, params=None, nested=False):
    with mlflow.start_run(run_name=name, nested=nested) as run:
        mlflow.set_tags({'unit': '6065/2', 'scope': 'Iatan pilot',
                         'inference': 'retrospective_exploratory', 'automl': 'not_enabled'})
        if params: mlflow.log_params(params)
        write_json(out / 'provenance.json', provenance(root))
        write_json(out / 'tracking.json', {'run_id': run.info.run_id,
                                          'experiment_id': run.info.experiment_id})
        try:
            yield run
        finally:
            # Also retain the provenance and partial artifacts of failed runs.
            mlflow.log_artifacts(str(out))


def log_metrics(metrics, prefix=''):
    mlflow.log_metrics({prefix + k: float(v) for k, v in metrics.items()
                        if isinstance(v, (int, float))})
