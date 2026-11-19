"""Proveniência explícita: aula e-Science (pp. 53–56), MLflow Tracking API.

Manual logging is deliberate: feature lists and time boundaries are scientific factors.
"""
from pathlib import Path
import contextlib
import importlib.metadata
import json
import os
import platform
import shutil
import subprocess
from tempfile import gettempdir, mkdtemp
from threading import RLock
import mlflow
from . import PUBLIC_CONTEXT
from .data import digest, write_json
from .exports import export_mlflow_database, restore_mlflow_database


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
def portable_tracking(folder):
    """Mantém o banco ativo privado e publica somente seu snapshot portátil.

    Uma pasta já existente pode ser reaberta por uma cópia de trabalho; registros
    anteriores e artefatos não são modificados pela restauração para leitura.
    """
    folder = Path(folder).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    working = Path(mkdtemp(prefix='iatan-mlflow-')).resolve()
    database = working / 'mlflow.db'
    published = folder / 'mlflow.db'
    previous_uri = mlflow.get_tracking_uri()
    exported = False
    if published.is_file():
        restore_mlflow_database(published, database, folder)
    uri = 'sqlite:///' + database.as_posix()
    mlflow.set_tracking_uri(uri)
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    store = mlflow.MlflowClient(tracking_uri=uri)._tracking_client.store
    engine = store.engine
    lock = RLock()
    def mark_completed(session, flush_context):
        if session.get_bind() is engine and any(
            getattr(type(item), '__tablename__', None) == 'runs'
            and getattr(item, 'status', None) in {'FINISHED', 'FAILED', 'KILLED'}
            for item in session.dirty
        ):
            session.info['_iatan_snapshot_ready'] = True
    def snapshot(session=None):
        if session is None or (session.get_bind() is engine and session.info.pop('_iatan_snapshot_ready', False)):
            with lock:
                export_mlflow_database(database, published, folder)
    # Preserva cada execução/subexecução concluída sem copiar a base por métrica.
    # Uma interrupção abrupta conserva o histórico já consolidado nesses limites.
    event.listen(Session, 'after_flush', mark_completed)
    event.listen(Session, 'after_commit', snapshot)
    try:
        yield
    finally:
        try:
            mlflow.flush_trace_async_logging()
            if database.is_file():
                snapshot()
            exported = True
        finally:
            try:
                event.remove(Session, 'after_commit', snapshot)
                event.remove(Session, 'after_flush', mark_completed)
                engine = getattr(store, 'engine', None)
                if engine is not None:
                    engine.dispose()
            finally:
                mlflow.set_tracking_uri(previous_uri)
                # Em caso de falha de exportação, a cópia privada é preservada.
                if exported:
                    assert working.is_relative_to(Path(gettempdir()).resolve()) and working.name.startswith('iatan-mlflow-')
                    shutil.rmtree(working)


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
