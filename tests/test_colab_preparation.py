"""Preparação no Drive preserva resultados e exige escolhas cronológicas explícitas."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from iatan.colab import (PHASE_INPUTS, digest, ensure_dependencies, quarterly_reference, restore_multiyear,
                         select_phase_run, synchronize_archive)


def release(path, extra=None):
    files = {'iatan/colab.py': b'# setup\n', 'iatan/phase5.py': b'# models\n',
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


def test_zip_cannot_write_outside_root(tmp_path):
    root = tmp_path / 'execucao'
    package = tmp_path / 'release.zip'
    release(package, {'../outside.txt': b'unsafe'})
    with pytest.raises(ValueError, match='Caminho inválido'):
        synchronize_archive(root, package)
    assert not (tmp_path / 'outside.txt').exists()


def test_multiyear_restores_only_hashed_inputs_and_keeps_existing_results(tmp_path):
    root = tmp_path / 'execucao'
    data = b'preserved annual input'
    name = 'data/interim/03A04_multiyear/iatan_unit2_2025.parquet'
    (root / 'configs').mkdir(parents=True)
    (root / 'configs/iatan_inputs.json').write_text(json.dumps({'files': [
        {'path': name, 'sha256': hashlib.sha256(data).hexdigest()},
        {'path': 'data/interim/03A04_multiyear/iatan_unit2_2010.parquet',
         'sha256': hashlib.sha256(b'old baseline only').hexdigest()}]}), encoding='utf-8')
    with ZipFile(tmp_path / 'Iatan_Colab_insumos_multianuais.zip', 'w') as archive:
        archive.writestr(name, data)
        archive.writestr('iatan/old.py', b'old code must not be extracted')
        archive.writestr('outputs/old/results.csv', b'old results must not be extracted')
    assert restore_multiyear(root, tmp_path) == []
    assert (root / name).read_bytes() == data
    assert not (root / 'iatan/old.py').exists()
    assert not (root / 'outputs').exists()
    assert not (root / 'data/interim/03A04_multiyear/iatan_unit2_2010.parquet').exists()
    assert restore_multiyear(root, tmp_path) == []
    (root / name).write_bytes(b'changed input')
    with pytest.raises(ValueError, match='arquivo existente foi preservado'):
        restore_multiyear(root, tmp_path)
    assert (root / name).read_bytes() == b'changed input'


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


def test_bootstrap_fetches_missing_zip_once_and_uses_custom_delivery(tmp_path):
    """Uma raiz existente não dispensa a versão verificável; o ZIP fixa as próximas sessões."""
    source = Path(__file__).resolve().parents[1]
    notebook = json.loads((source / 'notebooks/02_com_mineracao_de_processos/06_validacao_multianual_iatan.ipynb').read_text(encoding='utf-8'))
    bootstrap = ''.join(notebook['cells'][2]['source']).split('from iatan.colab import prepare_session')[0]
    fixture = tmp_path / 'fixture.json'
    fixture.write_text(json.dumps({'bootstrap': bootstrap, 'helper': (source / 'iatan/colab.py').read_text(encoding='utf-8')}), encoding='utf-8')
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
data=io.BytesIO()
with ZipFile(data,'w') as z:
    z.comment=b'a'*40
    for name,value in {'iatan/colab.py':fixture['helper'],'iatan/phase5.py':'# models',
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
assert len(calls)==2
assert (root/'codigo_publicado.json').is_file()
exec(fixture['bootstrap'],{})
assert len(calls)==2
print('bootstrap_ok')
'''
    completed = subprocess.run([sys.executable, '-c', program, str(tmp_path)], capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert 'bootstrap_ok' in completed.stdout
