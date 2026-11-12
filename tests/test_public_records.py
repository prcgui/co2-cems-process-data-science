"""Registros públicos preservam identidade científica sem diretórios pessoais."""
import json

import iatan
import mlflow
import pandas as pd
from mlflow.entities.trace_location import MlflowExperimentLocation
from iatan.data import digest
from iatan.phase5 import log_sample
from iatan.phase5_data import TARGET_TONS
from iatan.tracking import portable_path, public_span, source_matches


def test_paths_are_portable(tmp_path):
    root = tmp_path / 'project'
    assert portable_path(root / 'outputs/metricas.csv', root) == 'outputs/metricas.csv'
    assert portable_path(tmp_path / 'other/metricas.csv', root) == 'external/metricas.csv'


def test_source_compatibility_is_exact_and_does_not_hide_changes(tmp_path):
    source = tmp_path / 'iatan/model.py'
    source.parent.mkdir()
    source.write_text('value = 1\n', encoding='utf-8')
    old_hash = '0' * 64
    current_hash = digest(source)
    configs = tmp_path / 'configs'
    configs.mkdir()
    (configs / 'source_compatibility.json').write_text(json.dumps({'files': {
        'iatan/model.py': {'previous_sha256': [old_hash], 'current_sha256': current_hash},
    }}), encoding='utf-8')
    assert source_matches(tmp_path, 'iatan/model.py', current_hash)
    assert source_matches(tmp_path, 'iatan/model.py', old_hash)
    assert not source_matches(tmp_path, 'iatan/model.py', 'f' * 64)
    source.write_text('value = 2\n', encoding='utf-8')
    assert not source_matches(tmp_path, 'iatan/model.py', old_hash)


def test_mlflow_run_and_dataset_do_not_copy_local_identity(tmp_path):
    old_uri = mlflow.get_tracking_uri()
    manifest = tmp_path / 'manifesto_dados.json'
    manifest.write_text('[]\n', encoding='utf-8')
    data = pd.DataFrame({'timestamp': pd.date_range('2025-01-01', periods=2, freq='h'),
                         'generation_mw': [100., 120.], TARGET_TONS: [70., 84.]})
    mlflow.set_tracking_uri('sqlite:///' + (tmp_path / 'tracking.db').as_posix())
    try:
        experiment = mlflow.create_experiment('public-records')
        with mlflow.start_run(experiment_id=experiment) as run, public_span(
            'Registro público', trace_destination=MlflowExperimentLocation(experiment_id=experiment),
        ) as span:
            log_sample(data, data.index, ['generation_mw'], manifest, 'iatan_teste', 'evaluation')
            run_id = run.info.run_id
            trace_id = span.trace_id
        saved = mlflow.get_run(run_id)
        assert saved.data.tags['mlflow.user'] == 'equipe'
        assert saved.data.tags['mlflow.source.name'] == 'iatan'
        assert saved.data.tags['mlflow.source.git.commit'] == ''
        origin = saved.inputs.dataset_inputs[0].dataset.source
        assert str(tmp_path) not in origin
        assert json.loads(origin)['tags'] == {'manifest': manifest.name, 'sha256': digest(manifest)}
        mlflow.flush_trace_async_logging()
        metadata = mlflow.get_trace(trace_id).info.trace_metadata
        assert metadata['mlflow.user'] == 'equipe'
        assert metadata['mlflow.source.name'] == 'iatan'
        assert metadata['mlflow.source.git.commit'] == ''
        assert metadata['mlflow.source.git.repoURL'] == ''
    finally:
        mlflow.set_tracking_uri(old_uri)
