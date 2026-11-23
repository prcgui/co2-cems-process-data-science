"""Preparação no Drive preserva resultados e exige escolhas cronológicas explícitas."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import types
from urllib.error import URLError
from zipfile import ZipFile, ZipInfo

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from iatan.colab import (PHASE_INPUTS, digest, ensure_dependencies, quarterly_reference, restore_2025, restore_multiyear,
                         select_phase_run, synchronize_archive)


def release(path, extra=None):
    files = {'iatan/colab.py': b'# setup\n', 'iatan/exports.py': b'# portable results\n', 'iatan/phase5.py': b'# models\n',
             'configs/phase5_iatan.json': b'{}\n', 'requirements-iatan.txt': b'numpy==2.3.5\n'}
    files.update(extra or {})
    with ZipFile(path, 'w') as archive:
        archive.comment = b'a' * 40
        for name, data in files.items():
            archive.writestr('release/' + name, data)
    return files


def test_sync_is_idempotent_and_preserves_outputs_and_data(tmp_path):
    root = tmp_path / 'execucao'
    old_result = root / 'outputs/rodada/resultados.csv'
    old_data = root / 'data/interim/observacoes.parquet'
    for path, value in [(old_result, b'preserved result'), (old_data, b'preserved data')]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    package = tmp_path / 'Iatan_codigo_atual.zip'
    files = release(package, {'outputs/rodada/resultados.csv': b'wrong', 'data/interim/observacoes.parquet': b'wrong'})
    first = synchronize_archive(root, package)
    assert first['commit'] == 'a' * 40
    assert old_result.read_bytes() == b'preserved result'
    assert old_data.read_bytes() == b'preserved data'
    source = root / 'iatan/phase5.py'
    stamp = source.stat().st_mtime_ns
    assert synchronize_archive(root, package) == first
    assert source.stat().st_mtime_ns == stamp
    source.write_bytes(b'outdated code')
    synchronize_archive(root, package)
    assert source.read_bytes() == files['iatan/phase5.py']
    assert (root / 'iatan/exports.py').read_bytes() == files['iatan/exports.py']


def test_conflicting_pipeline_is_never_overwritten(tmp_path):
    root = tmp_path / 'execucao'
    old = root / 'pipeline/selected_unit.json'
    old.parent.mkdir(parents=True)
    old.write_bytes(b'other preserved selection')
    package = tmp_path / 'release.zip'
    release(package, {'pipeline/selected_unit.json': b'published selection'})
    with pytest.raises(ValueError, match='Entrada preservada diferente'):
        synchronize_archive(root, package)
    assert old.read_bytes() == b'other preserved selection'
    assert not (root / 'iatan/phase5.py').exists()


def test_package_without_current_exporter_is_rejected_before_writing(tmp_path):
    root = tmp_path / 'execucao'
    result = root / 'outputs/rodada/resultados.csv'
    result.parent.mkdir(parents=True)
    result.write_bytes(b'preserved result')
    package = tmp_path / 'release.zip'
    with ZipFile(package, 'w') as archive:
        archive.comment = b'a' * 40
        for name in ('iatan/colab.py', 'iatan/phase5.py', 'configs/phase5_iatan.json', 'requirements-iatan.txt'):
            archive.writestr('release/' + name, b'{}')
    with pytest.raises(ValueError, match='incompleto'):
        synchronize_archive(root, package)
    assert result.read_bytes() == b'preserved result'
    assert not (root / 'iatan').exists()


@pytest.mark.parametrize('inputs_first', [True, False])
def test_json_formatting_does_not_block_sync_or_change_preserved_bytes(tmp_path, monkeypatch, inputs_first):
    import iatan.colab as setup
    unit = {'facility_id': 6065, 'unit_id': '2', 'year': 2025}
    published = json.dumps(unit, separators=(',', ':')).encode()
    preserved = (json.dumps(unit, indent=4) + '\n').encode()
    raw = b'preserved raw observations'
    code = tmp_path / 'Iatan_codigo_atual.zip'
    release(code, {'pipeline/selected_unit.json': published,
                   'pipeline/selected_unit_hourly_raw.parquet': raw})
    inputs = tmp_path / 'Iatan2025_insumos.zip'
    observations = {'pipeline/selected_unit.json': preserved,
                    'pipeline/selected_unit_hourly_raw.parquet': raw}
    manifest = {'files': [{'path': name, 'sha256': hashlib.sha256(value).hexdigest()}
                          for name, value in observations.items()]}
    with ZipFile(inputs, 'w') as archive:
        archive.writestr('manifesto_insumos.json', json.dumps(manifest))
        for name, value in observations.items():
            archive.writestr(name, value)
    monkeypatch.setattr(setup, 'INPUTS_2025_SHA256', digest(inputs))
    root = tmp_path / 'execucao'
    result = root / 'outputs/old/resultados.csv'
    result.parent.mkdir(parents=True)
    result.write_bytes(b'previous results')
    if inputs_first:
        restore_2025(root, tmp_path)
        record = synchronize_archive(root, code)
        expected_bytes = preserved
    else:
        record = synchronize_archive(root, code)
        restore_2025(root, tmp_path)
        expected_bytes = published
    for _ in range(2):
        assert synchronize_archive(root, code) == record
        restore_2025(root, tmp_path)
    actual = root / 'pipeline/selected_unit.json'
    assert actual.read_bytes() == expected_bytes
    assert (root / 'pipeline/selected_unit_hourly_raw.parquet').read_bytes() == raw
    assert result.read_bytes() == b'previous results'
    assert record['files']['pipeline/selected_unit.json'] == digest(actual)
    if inputs_first:
        comparison = record['preserved_inputs']['pipeline/selected_unit.json']
        assert comparison['actual_sha256'] == digest(actual)
        assert comparison['published_sha256'] == hashlib.sha256(published).hexdigest()
    verification = json.loads((root / 'outputs/colab_preparacao/insumos2025_conferidos.json').read_text(encoding='utf-8'))
    entry = next(row for row in verification['files'] if row['path'] == 'pipeline/selected_unit.json')
    assert entry['actual_sha256'] == digest(actual)
    assert entry['published_sha256'] == hashlib.sha256(preserved).hexdigest()
    actual.write_text('{"facility_id": 9999, "unit_id":"2", "year":2025}', encoding='utf-8')
    with pytest.raises(ValueError, match='Entrada preservada diferente'):
        synchronize_archive(root, code)
    with pytest.raises(ValueError, match='Entrada preservada diferente'):
        restore_2025(root, tmp_path)


def test_zip_cannot_write_outside_root(tmp_path):
    root = tmp_path / 'execucao'
    package = tmp_path / 'release.zip'
    release(package, {'../outside.txt': b'unsafe'})
    with pytest.raises(ValueError, match='Caminho inválido'):
        synchronize_archive(root, package)
    assert not (tmp_path / 'outside.txt').exists()


def annual_inputs(root):
    observations = {f'data/interim/03A04_multiyear/iatan_unit2_{year}.parquet':
                    f'preserved annual input {year}'.encode() for year in range(2011, 2026)}
    manifest = {'files': [{'path': name, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                          for name, data in observations.items()]}
    (root / 'configs').mkdir(parents=True, exist_ok=True)
    (root / 'configs/iatan_inputs.json').write_text(json.dumps(manifest), encoding='utf-8')
    return observations


def annual_archive(observations, extra=None):
    stream = io.BytesIO()
    with ZipFile(stream, 'w') as archive:
        for name, data in {**observations, **(extra or {})}.items():
            archive.writestr(ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)), data)
    return stream.getvalue()


def annual_download(root, payload):
    record = {'url': 'https://github.com/prcgui/co2-cems-process-data-science/releases/download/'
                     'inputs-v1/Iatan_Colab_insumos_multianuais.zip',
              'sha256': hashlib.sha256(payload).hexdigest(), 'bytes': len(payload),
              'filename': 'Iatan_Colab_insumos_multianuais.zip'}
    (root / 'configs/iatan_downloads.json').write_text(
        json.dumps({'multiyear': record}), encoding='utf-8')
    return record


def preserved_result(root):
    result = root / 'outputs/previous/resultados.csv'
    result.parent.mkdir(parents=True)
    result.write_bytes(b'previous result must not change')
    return result, result.stat().st_mtime_ns


def assert_result_unchanged(result, stamp):
    assert result.read_bytes() == b'previous result must not change'
    assert result.stat().st_mtime_ns == stamp


def test_multiyear_restores_only_hashed_inputs_and_keeps_existing_results(tmp_path):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    name = 'data/interim/03A04_multiyear/iatan_unit2_2025.parquet'
    manifest_path = root / 'configs/iatan_inputs.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['files'].append({'path': 'data/interim/03A04_multiyear/iatan_unit2_2010.parquet',
                              'sha256': hashlib.sha256(b'old baseline only').hexdigest()})
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with ZipFile(tmp_path / 'Iatan_Colab_insumos_multianuais.zip', 'w') as archive:
        for relative, data in observations.items():
            archive.writestr(relative, data)
        archive.writestr('data/interim/03A04_multiyear/iatan_unit2_2010.parquet', b'old baseline only')
        archive.writestr('iatan/old.py', b'old code must not be extracted')
        archive.writestr('outputs/old/results.csv', b'old results must not be extracted')
    assert restore_multiyear(root, tmp_path) == []
    assert all((root / relative).read_bytes() == data for relative, data in observations.items())
    assert not (root / 'iatan/old.py').exists()
    assert not (root / 'outputs').exists()
    assert not (root / 'data/interim/03A04_multiyear/iatan_unit2_2010.parquet').exists()
    assert restore_multiyear(root, tmp_path) == []
    (root / name).write_bytes(b'changed input')
    with pytest.raises(ValueError, match='arquivo existente foi preservado'):
        restore_multiyear(root, tmp_path)
    assert (root / name).read_bytes() == b'changed input'


def test_multiyear_without_download_reports_all_missing_years(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    def unexpected_download(*args, **kwargs):
        pytest.fail('Offline preparation must not access the network')
    monkeypatch.setattr('urllib.request.urlopen', unexpected_download)
    missing = restore_multiyear(root, tmp_path, download=False)
    assert set(missing) == set(observations)
    assert not (root / 'data').exists()


def test_multiyear_download_fills_empty_drive_and_replays_without_network(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    payload = annual_archive(observations)
    record = annual_download(root, payload)
    result, stamp = preserved_result(root)
    calls = []
    def request(url, *, timeout):
        calls.append((getattr(url, 'full_url', str(url)), timeout))
        return io.BytesIO(payload)
    monkeypatch.setattr('urllib.request.urlopen', request)
    assert restore_multiyear(root, tmp_path, download=True) == []
    assert calls == [(record['url'], 60)]
    package = tmp_path / record['filename']
    assert package.read_bytes() == payload
    assert all((root / name).read_bytes() == data for name, data in observations.items())
    assert_result_unchanged(result, stamp)
    stamps = {name: (root / name).stat().st_mtime_ns for name in observations}
    assert restore_multiyear(root, tmp_path, download=True) == []
    assert len(calls) == 1
    assert {name: (root / name).stat().st_mtime_ns for name in observations} == stamps
    # The validated archive also restores a later missing file without another download.
    missing_name = next(iter(observations))
    (root / missing_name).unlink()
    assert restore_multiyear(root, tmp_path, download=True) == []
    assert len(calls) == 1
    assert_result_unchanged(result, stamp)


def test_multiyear_download_keeps_partial_cache_and_existing_outputs(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    payload = annual_archive(observations)
    annual_download(root, payload)
    existing = list(observations)[:3]
    for name in existing:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(observations[name])
    stamps = {name: (root / name).stat().st_mtime_ns for name in existing}
    result, stamp = preserved_result(root)
    calls = []
    def request(url, *, timeout):
        calls.append(url)
        return io.BytesIO(payload)
    monkeypatch.setattr('urllib.request.urlopen', request)
    assert restore_multiyear(root, tmp_path, download=True) == []
    assert len(calls) == 1
    assert all((root / name).read_bytes() == data for name, data in observations.items())
    assert {name: (root / name).stat().st_mtime_ns for name in existing} == stamps
    assert_result_unchanged(result, stamp)


def test_multiyear_complete_cache_needs_neither_network_nor_download_config(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    for name, data in observations.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    def unexpected_download(*args, **kwargs):
        pytest.fail('Complete inputs must be reused offline')
    monkeypatch.setattr('urllib.request.urlopen', unexpected_download)
    assert restore_multiyear(root, tmp_path, download=True) == []


def test_multiyear_truncated_local_archive_is_preserved_and_download_recovers(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    payload = annual_archive(observations)
    record = annual_download(root, payload)
    old_package = tmp_path / record['filename']
    interrupted = payload[:len(payload) // 2]
    old_package.write_bytes(interrupted)
    old_stamp = old_package.stat().st_mtime_ns
    result, stamp = preserved_result(root)
    calls = []
    def request(url, *, timeout):
        calls.append((getattr(url, 'full_url', str(url)), timeout))
        return io.BytesIO(payload)
    monkeypatch.setattr('urllib.request.urlopen', request)
    assert restore_multiyear(root, tmp_path, download=True) == []
    assert calls == [(record['url'], 60)]
    assert old_package.read_bytes() == interrupted
    assert old_package.stat().st_mtime_ns == old_stamp
    recovered_package = tmp_path / (old_package.stem + '_' + record['sha256'][:12] + '.zip')
    assert recovered_package.read_bytes() == payload
    assert all((root / name).read_bytes() == data for name, data in observations.items())
    assert_result_unchanged(result, stamp)


def test_multiyear_existing_divergent_input_is_not_overwritten_or_downloaded(tmp_path, monkeypatch):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    annual_download(root, annual_archive(observations))
    name = next(iter(observations))
    path = root / name
    path.parent.mkdir(parents=True)
    path.write_bytes(b'different existing observations')
    result, stamp = preserved_result(root)
    def unexpected_download(*args, **kwargs):
        pytest.fail('A divergent existing input must fail before network access')
    monkeypatch.setattr('urllib.request.urlopen', unexpected_download)
    with pytest.raises(ValueError):
        restore_multiyear(root, tmp_path, download=True)
    assert path.read_bytes() == b'different existing observations'
    assert not (tmp_path / 'Iatan_Colab_insumos_multianuais.zip').exists()
    assert_result_unchanged(result, stamp)


@pytest.mark.parametrize('failure', ['network', 'truncated', 'annual_hash'])
def test_multiyear_failed_download_preserves_inputs_and_outputs(tmp_path, monkeypatch, failure):
    root = tmp_path / 'execucao'
    observations = annual_inputs(root)
    payload = annual_archive(observations)
    if failure == 'annual_hash':
        last_name = list(observations)[-1]
        payload = annual_archive({**observations, last_name: b'wrong annual bytes'})
    annual_download(root, payload)
    result, stamp = preserved_result(root)
    def request(url, *, timeout):
        if failure == 'network':
            raise URLError('connection interrupted')
        return io.BytesIO(payload[:len(payload) // 2] if failure == 'truncated' else payload)
    monkeypatch.setattr('urllib.request.urlopen', request)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        restore_multiyear(root, tmp_path, download=True)
    assert all(not (root / name).exists() for name in observations)
    assert not (tmp_path / 'Iatan_Colab_insumos_multianuais.zip').exists()
    assert_result_unchanged(result, stamp)


@pytest.mark.parametrize('failure', ['missing', 'incomplete', 'duplicate', 'invalid_hash'])
def test_multiyear_rejects_invalid_annual_manifest(tmp_path, failure):
    root = tmp_path / 'execucao'
    annual_inputs(root)
    path = root / 'configs/iatan_inputs.json'
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if failure == 'missing':
        path.unlink()
    else:
        if failure == 'incomplete':
            manifest['files'].pop()
        elif failure == 'duplicate':
            manifest['files'].append(manifest['files'][0].copy())
        else:
            manifest['files'][0]['sha256'] = 'not-a-sha256'
        path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        restore_multiyear(root, tmp_path, download=False)
    assert not (root / 'data').exists()


def phase_run(root, phase, suffix):
    parent, expected = PHASE_INPUTS[phase]
    folder = root / parent / ('iatan_6065_unit2_2025_' + suffix)
    artifact = folder / expected
    artifact.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({'timestamp': [1], 'value': [2.]}), artifact)
    if phase == 'phase2':
        manifest = folder / 'reports/cell30_process_features_manifest.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'output_sha256': {'all': digest(artifact)}}), encoding='utf-8')
    return folder


def test_phase_selection_accepts_single_valid_run_and_rejects_ambiguity(tmp_path, monkeypatch):
    monkeypatch.delenv('IATAN_PHASE2_RUN_ID', raising=False)
    first = phase_run(tmp_path, 'phase2', 'first')
    second = phase_run(tmp_path, 'phase2', 'second')
    with pytest.raises(ValueError, match='mais de uma execução válida'):
        select_phase_run(tmp_path, 'phase2')
    assert select_phase_run(tmp_path, 'phase2', first.name) == first.name
    monkeypatch.delenv('IATAN_PHASE3_RUN_ID', raising=False)
    only = phase_run(tmp_path, 'phase3', 'only')
    assert select_phase_run(tmp_path, 'phase3') == only.name
    (first / 'data/processed/cell30_process_features_all.parquet').write_bytes(b'damaged')
    with pytest.raises(ValueError, match='não contém o arquivo necessário'):
        select_phase_run(tmp_path, 'phase2', first.name)


def test_quarterly_selection_never_chooses_latest_implicitly(tmp_path, monkeypatch):
    monkeypatch.delenv('IATAN_PHASE5_QUARTERLY_REFERENCE', raising=False)
    for name in ['first', 'second']:
        summary = tmp_path / 'outputs/phase_05_quarterly' / name / 'resultados/resumo.json'
        summary.parent.mkdir(parents=True)
        summary.write_text('{"status":"FINISHED"}', encoding='utf-8')
    with pytest.raises(ValueError, match='mais de uma referência'):
        quarterly_reference(tmp_path)
    choice = 'outputs/phase_05_quarterly/first'
    assert quarterly_reference(tmp_path, choice) == (tmp_path / choice).resolve()


def test_dependency_restart_cannot_be_bypassed_by_rerunning_cell(tmp_path, monkeypatch):
    import iatan.colab as setup
    monkeypatch.delenv('IATAN_DEPENDENCY_RESTART_REQUIRED', raising=False)
    (tmp_path / 'requirements-iatan.txt').write_text('numpy==2.3.5\n', encoding='utf-8')
    state = {'installed': '2.2.0', 'pip_calls': 0}
    monkeypatch.setattr(setup.metadata, 'version', lambda name: state['installed'])
    monkeypatch.setitem(sys.modules, 'numpy', types.SimpleNamespace(__version__='2.2.0'))
    def install(*args, **kwargs):
        state.update(installed='2.3.5', pip_calls=state['pip_calls'] + 1)
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(setup.subprocess, 'run', install)
    with pytest.raises(RuntimeError, match='Reiniciar sessão'):
        ensure_dependencies(tmp_path, install=True)
    with pytest.raises(RuntimeError, match='Reiniciar sessão'):
        ensure_dependencies(tmp_path, install=True)
    assert state['pip_calls'] == 1
    monkeypatch.delenv('IATAN_DEPENDENCY_RESTART_REQUIRED')
    with pytest.raises(RuntimeError, match='carregou versões anteriores'):
        ensure_dependencies(tmp_path, install=True)


@pytest.mark.parametrize(('notebook_name', 'cell_index', 'cache_version'), [
    ('06_validacao_multianual_iatan.ipynb', 2, None),
    ('06_validacao_multianual_iatan.ipynb', 2, 2),
    ('00_PREPARAR_IATAN_2025.ipynb', 1, 3),
])
def test_bootstrap_fetches_missing_zip_once_and_uses_custom_delivery(tmp_path, notebook_name, cell_index, cache_version):
    """Uma raiz existente não dispensa a versão verificável; o ZIP fixa as próximas sessões."""
    source = Path(__file__).resolve().parents[1]
    notebook = json.loads((source / 'notebooks/02_com_mineracao_de_processos' / notebook_name).read_text(encoding='utf-8'))
    bootstrap = ''.join(notebook['cells'][cell_index]['source']).split('from iatan.colab import prepare_session')[0]
    fixture = tmp_path / 'fixture.json'
    fixture.write_text(json.dumps({'bootstrap': bootstrap,
                                  'helper': (source / 'iatan/colab.py').read_text(encoding='utf-8'),
                                  'cache_version': cache_version}), encoding='utf-8')
    program = '''
from pathlib import Path
from zipfile import ZipFile
import io,json,os,sys,types,urllib.request
folder=Path(sys.argv[1])
fixture=json.loads((folder/'fixture.json').read_text(encoding='utf-8'))
root=folder/'custom'/'execucao'
(root/'iatan').mkdir(parents=True)
(root/'iatan/colab.py').write_text('# stale helper',encoding='utf-8')
os.environ['IATAN_PROJECT_ROOT']=str(root)
os.environ.pop('IATAN_DELIVERY_ROOT',None)
google=types.ModuleType('google')
colab=types.ModuleType('google.colab')
colab.drive=types.SimpleNamespace(mount=lambda path:None)
google.colab=colab
sys.modules['google']=google
sys.modules['google.colab']=colab
if fixture['cache_version'] is not None:
    with ZipFile(root.parent/'Iatan_codigo_atual.zip','w') as z:
        z.comment=b'b'*40
        z.writestr('release/iatan/colab.py','PREPARATION_VERSION = ' + str(fixture['cache_version']))
data=io.BytesIO()
with ZipFile(data,'w') as z:
    z.comment=b'a'*40
    for name,value in {'iatan/colab.py':fixture['helper'],'iatan/exports.py':'# portable results','iatan/phase5.py':'# models',
                       'iatan/carbon_tracking.py':'# tracking',
                       'notebooks/02_com_mineracao_de_processos/07_mudancas_intensidade_carbonica.ipynb':'notebook07',
                       'notebooks/02_com_mineracao_de_processos/08_avaliacao_correcao_carbonica.ipynb':'notebook08',
                       'reproducibility/iatan/06_anual_2025/previsoes_pareadas.csv.gz':'reference',
                       'configs/phase5_iatan.json':'{}','requirements-iatan.txt':'numpy==2.3.5'}.items():
        z.writestr('release/'+name,value)
calls=[]
def request(url,**kwargs):
    calls.append(url.full_url if hasattr(url,'full_url') else str(url))
    return io.BytesIO(json.dumps({'sha':'a'*40}).encode() if len(calls)==1 else data.getvalue())
urllib.request.urlopen=request
namespace={}
exec(fixture['bootstrap'],namespace)
assert namespace['_delivery']==root.parent
assert (root.parent/'Iatan_codigo_atual.zip').is_file()
assert (root.parent/'Iatan_codigo_atual.zip').read_bytes()==data.getvalue()
assert len(calls)==2
assert (root/'codigo_publicado.json').is_file()
exec(fixture['bootstrap'],{})
assert len(calls)==2
from iatan.colab import copy_notebooks
copy_notebooks(root,root.parent)
for n in [7,8]:
    notebook=next((root.parent/'Notebooks').glob(f'0{n}_*.ipynb'))
    assert notebook.read_text()==f'notebook0{n}'
assert (root/'reproducibility/iatan/06_anual_2025/previsoes_pareadas.csv.gz').read_text()=='reference'
print('bootstrap_ok')
'''
    completed = subprocess.run([sys.executable, '-c', program, str(tmp_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert 'bootstrap_ok' in completed.stdout
