"""Preparação de execução; desenho e proveniência: Aula 08, pp. 52–56.

Este módulo organiza arquivos e dependências. Não modifica o desenho dos modelos.
"""
from pathlib import Path, PurePosixPath
import hashlib
import importlib.metadata as metadata
import json
import os
import re
import subprocess
import sys
from zipfile import ZipFile


PHASE_INPUTS = {
    'phase2': ('outputs/fase2_hmm_process_mining', 'data/processed/cell30_process_features_all.parquet'),
    'phase3': ('outputs/lag_selection_predictive', 'data/processed/cell03_experimental_partitions.parquet'),
}
PHASE_ENV = {'phase2': 'IATAN_PHASE2_RUN_ID', 'phase3': 'IATAN_PHASE3_RUN_ID'}
SELECTION = 'outputs/colab_preparacao/selecao_execucoes.json'
MANAGED_TOP = {'iatan', 'configs', 'notebooks', 'scripts', 'reproducibility', 'tests', 'entregas'}


def synchronize_archive(root, source):
    """Sincroniza um ZIP publicado, mantendo dados existentes e todo outputs/ intactos."""
    root, source = Path(root).resolve(), Path(source)
    archive_sha = digest(source)
    record_path = root / 'codigo_publicado.json'
    old = json.loads(record_path.read_text(encoding='utf-8')) if record_path.is_file() else {}
    if (old.get('archive_sha256') == archive_sha and old.get('files')
            and all((root / name).is_file() and digest(root / name) == sha
                    for name, sha in old['files'].items())):
        return old
    with ZipFile(source) as archive:
        commit = archive.comment.decode('ascii').strip()
        if not re.fullmatch('[0-9a-f]{40}', commit):
            raise ValueError('O pacote de código não identifica o commit publicado. Use o ZIP do GitHub.')
        files = [item for item in archive.infolist() if not item.is_dir()]
        tops = {PurePosixPath(item.filename).parts[0] for item in files}
        prefix = len(tops) == 1 and next(iter(tops)) not in MANAGED_TOP
        pending = []
        for item in files:
            original = PurePosixPath(item.filename)
            if original.is_absolute() or '..' in original.parts or '\\' in item.filename:
                raise ValueError('Caminho inválido no pacote de código.')
            relative = PurePosixPath(*original.parts[1:]) if prefix else original
            if not relative.parts:
                continue
            name = relative.as_posix()
            top = relative.parts[0]
            managed = top in MANAGED_TOP or name in {
                'README.md', '.gitignore', '.gitattributes', 'requirements-iatan.txt',
                'requirements.txt', 'requirements-reproduction.lock',
            }
            input_file = name in {'pipeline/selected_unit.json', 'pipeline/selected_unit_hourly_raw.parquet'}
            if not managed and not input_file:
                continue
            if item.external_attr >> 16 & 0o170000 == 0o120000:
                raise ValueError('Links simbólicos não são permitidos no pacote de código.')
            target = (root / name).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Destino inválido no pacote de código.')
            data = archive.read(item)
            if input_file and target.exists() and target.read_bytes() != data:
                raise ValueError('Entrada preservada diferente do pacote: ' + name
                                 + '. Nenhum arquivo existente foi substituído.')
            pending.append((name, target, data))
        required = {'iatan/colab.py', 'iatan/phase5.py', 'configs/phase5_iatan.json', 'requirements-iatan.txt'}
        if not required.issubset({name for name, _, _ in pending}):
            raise ValueError('O pacote de código está incompleto.')
        root.mkdir(parents=True, exist_ok=True)
        for _, target, data in pending:
            if not target.exists() or target.read_bytes() != data:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    record = {'commit': commit, 'archive_sha256': archive_sha,
              'source': 'https://github.com/prcgui/co2-cems-process-data-science',
              'files': {name: hashlib.sha256(data).hexdigest() for name, _, data in pending}}
    record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return record


def digest(path):
    sha = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(chunk)
    return sha.hexdigest()


def project_version(root):
    record = Path(root) / 'codigo_publicado.json'
    if record.is_file():
        return json.loads(record.read_text(encoding='utf-8')).get('commit', 'não registrado')
    try:
        return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                       stderr=subprocess.DEVNULL, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return 'cópia local; prepare com o pacote publicado para registrar a versão'


def ensure_dependencies(root, install=False):
    """Instala antes das importações numéricas e não reutiliza módulos incompatíveis."""
    requirements = Path(root) / 'requirements-iatan.txt'
    wanted = {}
    for line in requirements.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([^\s;]+)', line.strip())
        if match:
            wanted[match[1]] = match[2]
    imported = {'scikit-learn': 'sklearn', 'hmmlearn': 'hmmlearn', 'pyarrow': 'pyarrow',
                'joblib': 'joblib', 'matplotlib': 'matplotlib', 'statsmodels': 'statsmodels'}
    if os.environ.get('IATAN_DEPENDENCY_RESTART_REQUIRED') == '1':
        raise RuntimeError('Esta sessão ainda contém bibliotecas anteriores à atualização. '
                           'Use Ambiente de execução → Reiniciar sessão e execute a preparação novamente.')
    missing = []
    loaded_mismatch = []
    for name, version in wanted.items():
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            actual = None
        if actual != version:
            missing.append(name)
        module = sys.modules.get(imported.get(name, name.replace('-', '_')))
        loaded_version = getattr(module, '__version__', None)
        if loaded_version is not None and str(loaded_version) != version:
            loaded_mismatch.append(name)
    if not missing:
        if loaded_mismatch:
            raise RuntimeError('As versões instaladas estão corretas, mas esta sessão carregou versões '
                               'anteriores de: ' + ', '.join(loaded_mismatch)
                               + '. Reinicie a sessão antes de continuar.')
        return
    if not install:
        raise RuntimeError('Prepare as dependências com requirements-iatan.txt antes de executar: '
                           + ', '.join(missing))
    restart = any(imported.get(name, name.replace('-', '_')) in sys.modules for name in missing)
    print('Preparando as dependências; aguarde a conclusão.')
    completed = subprocess.run([sys.executable, '-m', 'pip', 'install', '--disable-pip-version-check',
                                '--quiet', '-r', str(requirements)], capture_output=True, text=True)
    if completed.returncode:
        # Não republicar a saída bruta do instalador, que pode conter caminhos e URIs locais.
        raise RuntimeError('A instalação não foi concluída. Confira a conexão e a compatibilidade '
                           'de requirements-iatan.txt com a versão Python desta sessão.')
    if restart:
        os.environ['IATAN_DEPENDENCY_RESTART_REQUIRED'] = '1'
        raise RuntimeError('Dependências atualizadas. Use Ambiente de execução → Reiniciar sessão '
                           'e execute esta célula novamente; a instalação não será repetida.')


def _manifest_files(root):
    config = Path(root) / 'configs/iatan_inputs.json'
    return json.loads(config.read_text(encoding='utf-8'))['files'] if config.is_file() else []


def restore_multiyear(root, delivery=None):
    """Reaproveita dados iguais e recupera apenas entradas ausentes pelos hashes publicados."""
    root = Path(root).resolve()
    delivery = Path(delivery or root.parent)
    # O manifesto também preserva insumos de baselines anteriores. O notebook 06
    # usa exatamente 2011–2025, conforme phase5_data; 2010 não integra esta rodada.
    wanted = {f'data/interim/03A04_multiyear/iatan_unit2_{year}.parquet'
              for year in range(2011, 2026)}
    entries = [row for row in _manifest_files(root) if row['path'] in wanted]
    missing = []
    for row in entries:
        target = root / row['path']
        if target.exists():
            if digest(target) != row['sha256']:
                raise ValueError('Insumo multianual diferente do manifesto: ' + target.name
                                 + '. O arquivo existente foi preservado.')
        else:
            missing.append(row)
    if not missing:
        return []
    sources = sorted(delivery.glob('*.zip'))
    extra = os.environ.get('IATAN_MULTIYEAR_ARCHIVE', '').strip()
    if extra:
        sources = [Path(extra).expanduser()] + sources
    pending = {Path(row['path']).name: row for row in missing}
    for source in dict.fromkeys(sources):
        if not source.is_file():
            continue
        with ZipFile(source) as archive:
            candidates = [name for name in archive.namelist() if Path(name).name in pending]
            for name in candidates:
                row = pending.get(Path(name).name)
                if row is None:
                    continue
                data = archive.read(name)
                if hashlib.sha256(data).hexdigest() != row['sha256']:
                    continue
                target = root / row['path']
                if not target.resolve().is_relative_to(root):
                    raise ValueError('Caminho inválido no manifesto de insumos.')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                del pending[Path(name).name]
        if not pending:
            break
    return [row['path'] for row in pending.values()]


def restore_2025(root, delivery=None):
    """Recupera o pacote de insumos preservado sem sobrescrever dados ou resultados."""
    root = Path(root).resolve()
    delivery = Path(delivery or root.parent)
    source = delivery / 'Iatan2025_insumos.zip'
    if not source.is_file():
        return
    expected = '32499f1af9789d9df2df4dd1748ded328232cfae6f59a6ac4e8ca769bfd12594'
    if digest(source) != expected:
        raise ValueError('Iatan2025_insumos.zip diverge do pacote preservado; nenhum arquivo foi substituído.')
    with ZipFile(source) as archive:
        manifest = json.loads(archive.read('manifesto_insumos.json'))
        pending = []
        for row in manifest['files']:
            target = (root / row['path']).resolve()
            if not target.is_relative_to(root):
                raise ValueError('Caminho inválido no pacote de insumos.')
            data = archive.read(row['path'])
            if hashlib.sha256(data).hexdigest() != row['sha256']:
                raise ValueError('Insumo inválido: ' + Path(row['path']).name)
            # Os processados podem ter sido recalculados. Não restaurar bytes antigos
            # por cima de uma execução nova; cada fase valida e registra suas entradas.
            if target.exists() and digest(target) != row['sha256']:
                continue
            pending.append((target, data))
        for target, data in pending:
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)


def copy_notebooks(root, delivery=None):
    root = Path(root)
    delivery = Path(delivery or root.parent)
    source = root / 'notebooks/02_com_mineracao_de_processos'
    destination = delivery / 'Notebooks'
    destination.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob('0[0-6]_*.ipynb')):
        target = destination / path.name
        if not target.exists() or target.read_bytes() != path.read_bytes():
            target.write_bytes(path.read_bytes())


def prepare_session(root, delivery=None, install=False, require_multiyear=False):
    root = Path(root).expanduser().resolve()
    if not ((root / 'configs/phase5_iatan.json').is_file() and (root / 'iatan/phase5.py').is_file()):
        raise FileNotFoundError('Código do projeto incompleto. Execute a preparação do notebook 00.')
    os.environ['IATAN_PROJECT_ROOT'] = str(root)
    os.chdir(root)
    ensure_dependencies(root, install=install)
    restore_2025(root, delivery)
    missing = restore_multiyear(root, delivery)
    if require_multiyear and missing:
        raise FileNotFoundError(f'Faltam {len(missing)} Parquets anuais para o notebook 06. '
                                'Coloque Iatan_Colab_insumos_multianuais.zip ao lado de Iatan_codigo_atual.zip '
                                'e execute esta célula novamente. Nenhum resultado anterior foi alterado.')
    print('Código:', project_version(root))
    print('Raiz de execução: execucao | novos resultados: execucao/outputs/')
    if missing:
        print(f'Validação multianual: faltam {len(missing)} arquivos de entrada; o fluxo de 2025 pode ser usado.')
    return root


def select_phase_run(root, phase, explicit=None):
    """Aceita escolha explícita ou uma única execução válida; nunca escolhe pela data."""
    root = Path(root)
    parent, expected = PHASE_INPUTS[phase]
    selected = (explicit or os.environ.get(PHASE_ENV[phase], '')).strip()
    saved_path = root / SELECTION
    saved = json.loads(saved_path.read_text(encoding='utf-8')) if saved_path.is_file() else {}
    if not selected:
        selected = saved.get(phase, '')
    def valid(path):
        artifact = path / expected
        if not path.is_dir() or not artifact.is_file():
            return False
        try:
            from pyarrow.parquet import read_metadata
            if read_metadata(artifact).num_rows <= 0:
                return False
            manifest = path / 'reports/cell30_process_features_manifest.json'
            if phase == 'phase2' and manifest.is_file():
                declared = json.loads(manifest.read_text(encoding='utf-8')).get('output_sha256', {}).get('all')
                if declared and digest(artifact) != declared:
                    return False
        except (OSError, ValueError):
            return False
        return True
    candidates = sorted(p for p in (root / parent).glob('iatan_6065_unit2_2025_*') if valid(p))
    if selected:
        if '/' in selected or '\\' in selected or selected not in {p.name for p in candidates}:
            raise ValueError(f'Execução {phase} informada não contém o arquivo necessário. '
                             'Escolha um dos identificadores válidos: ' + ', '.join(p.name for p in candidates))
    elif len(candidates) == 1:
        selected = candidates[0].name
    elif not candidates:
        raise FileNotFoundError(f'Não há entrada concluída de {phase}. Execute o notebook '
                                + ('03' if phase == 'phase2' else '04')
                                + ' primeiro. O bloco Exp33 do 05 pode ser executado separadamente.')
    else:
        raise ValueError(f'Há mais de uma execução válida de {phase}. Preencha '
                         + ('FASE2_EXECUCAO' if phase == 'phase2' else 'FASE3_EXECUCAO')
                         + ' com um destes identificadores: ' + ', '.join(p.name for p in candidates))
    saved[phase] = selected
    saved_path.parent.mkdir(parents=True, exist_ok=True)
    saved_path.write_text(json.dumps(saved, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.environ[PHASE_ENV[phase]] = selected
    return selected


def quarterly_reference(root, explicit=None):
    root = Path(root)
    selected = (explicit or os.environ.get('IATAN_PHASE5_QUARTERLY_REFERENCE', '')).strip()
    if selected:
        path = Path(selected).expanduser()
        path = path if path.is_absolute() else root / path
        if not (path / 'resultados/resumo.json').is_file():
            raise FileNotFoundError('A referência trimestral informada não contém resultados/resumo.json.')
        return path.resolve()
    candidates = []
    for summary in (root / 'outputs/phase_05_quarterly').glob('*/resultados/resumo.json'):
        record = json.loads(summary.read_text(encoding='utf-8'))
        if record.get('status') == 'FINISHED':
            candidates.append(summary.parents[1])
    if len(candidates) == 1:
        return candidates[0].resolve()
    if not candidates:
        raise FileNotFoundError('Execute primeiro o modo quarterly do notebook 06 para criar a referência A–D.')
    choices = ', '.join(p.relative_to(root).as_posix() for p in sorted(candidates))
    raise ValueError('Há mais de uma referência trimestral concluída. Preencha REFERENCIA_TRIMESTRAL: ' + choices)
