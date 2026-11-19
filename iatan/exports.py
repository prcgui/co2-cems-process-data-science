"""Cópias portáteis dos registros MLflow, sem alterar a execução em andamento."""
from contextlib import closing
from io import BytesIO
import argparse
import csv
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
from tempfile import TemporaryDirectory
from urllib.parse import unquote, urlsplit
from uuid import uuid4
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo, is_zipfile


_CONTEXT = {'mlflow.user': 'equipe', 'mlflow.source.name': 'iatan'}
_SOURCE_KEYS = ('commit', 'branch', 'repoURL', 'diff', 'dirty')
_CONTEXT.update({'mlflow.source.git.' + key: '' for key in _SOURCE_KEYS})
_ANCHORS = ('mlflow_artifacts', 'mlartifacts', 'iatan', 'configs', 'notebooks',
            'pipeline', 'data', 'outputs', 'tracking')
_LOCAL = re.compile(r'^(?:file:|sqlite:|[A-Za-z]:[\\/]|/)')
_QUOTED = re.compile(r'''(["'])((?:file:|sqlite:|[A-Za-z]:[\\/]|/)[^\r\n]*?)\1''')
_INLINE = re.compile(r'''(?<![A-Za-z0-9])(?:file:///|[A-Za-z]:[\\/]|/(?:Users|home|content|tmp|var|mnt|Volumes|workspaces?)/)[^\s"'<>;,]+''')
_YAML_LOCATION = re.compile(r'(?m)^(\s*(?:artifact_path|artifact_uri|artifact_location|source)\s*:\s*)([^\r\n]+)$')


def _reference(value, root):
    """Mantém o sufixo útil de um endereço local; caminhos externos viram rótulos."""
    value = unquote(value)
    if value.lower().startswith(('file:', 'sqlite:')):
        uri = urlsplit(value)
        value = (uri.netloc + uri.path) if uri.netloc not in ('', 'localhost') else uri.path
    value = value.replace('\\', '/')
    if re.match(r'^/[A-Za-z]:/', value):
        value = value[1:]
    origin = str(Path(root).resolve()).replace('\\', '/').rstrip('/')
    if value.casefold() == origin.casefold():
        return '.'
    if value.casefold().startswith(origin.casefold() + '/'):
        return value[len(origin) + 1:]
    parts = [part for part in value.split('/') if part]
    for anchor in _ANCHORS:
        if anchor in parts:
            return '/'.join(parts[parts.index(anchor):])
    return 'external/' + (parts[-1] if parts else 'file')


def public_text(value, root):
    """Normaliza somente endereços textuais; números e fatores permanecem iguais."""
    try:
        parsed = json.loads(value)
    except (ValueError, TypeError):
        parsed = None
    if isinstance(parsed, (dict, list)):
        def visit(item):
            if isinstance(item, dict):
                return {key: _CONTEXT[key] if key in _CONTEXT else visit(val) for key, val in item.items()}
            if isinstance(item, list):
                return [visit(val) for val in item]
            return public_text(item, root) if isinstance(item, str) else item
        cleaned = visit(parsed)
        return json.dumps(cleaned, ensure_ascii=False) if cleaned != parsed else value
    if _LOCAL.match(value):
        return _reference(value, root)
    cleaned = _QUOTED.sub(lambda m: m[1] + _reference(m[2], root) + m[1], value)
    def yaml_location(match):
        location = match[2].strip()
        return match[1] + _reference(location, root) if _LOCAL.match(location) else match[0]
    cleaned = _YAML_LOCATION.sub(yaml_location, cleaned)
    cleaned = _INLINE.sub(lambda match: _reference(match[0], root), cleaned)
    origin = Path(root).resolve()
    for prefix in sorted({str(origin), origin.as_posix(), origin.as_uri()}, key=len, reverse=True):
        cleaned = cleaned.replace(prefix + '/', '').replace(prefix + '\\', '')
    return cleaned


def _quote(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def _rewrite_text(connection, rewrite):
    tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    for (table,) in tables:
        columns = connection.execute('PRAGMA table_info(' + _quote(table) + ')').fetchall()
        names = [column[1] for column in columns]
        definition = connection.execute('SELECT sql FROM sqlite_master WHERE name=?', (table,)).fetchone()[0]
        keys = [column[1] for column in sorted(columns, key=lambda col: col[5]) if column[5]] if 'WITHOUT ROWID' in definition.upper() else ['rowid']
        selected = keys + names
        rows = connection.execute('SELECT ' + ','.join(_quote(name) for name in selected) + ' FROM ' + _quote(table)).fetchall()
        for row in rows:
            values = dict(zip(names, row[len(keys):]))
            changes = {name: rewrite(table, name, value, values) for name, value in values.items() if isinstance(value, str)}
            changes = {name: value for name, value in changes.items() if value != values[name]}
            if changes:
                statement = ('UPDATE ' + _quote(table) + ' SET ' + ','.join(_quote(name) + '=?' for name in changes)
                             + ' WHERE ' + ' AND '.join(_quote(name) + ' IS ?' for name in keys))
                connection.execute(statement, (*changes.values(), *row[:len(keys)]))


def _copy_database(source, target, rewrite):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target:
        raise ValueError('O banco ativo e a cópia de distribuição devem ser arquivos diferentes.')
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name('.' + target.name + '.' + uuid4().hex + '.tmp')
    try:
        with TemporaryDirectory(prefix='iatan-db-export-') as temporary:
            private = Path(temporary) / 'mlflow.db'
            with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original:
                with closing(sqlite3.connect(private)) as copied:
                    original.backup(copied)
                    copied.execute('PRAGMA secure_delete=ON')
                    _rewrite_text(copied, rewrite)
                    copied.commit()
                    copied.execute('PRAGMA journal_mode=DELETE')
                    copied.execute('VACUUM')
                    if copied.execute('PRAGMA integrity_check').fetchone() != ('ok',):
                        raise RuntimeError('A cópia do registro MLflow não passou na checagem de integridade.')
            # O diretório de distribuição recebe somente bytes já normalizados.
            partial.write_bytes(private.read_bytes())
            partial.replace(target)
    finally:
        if partial.exists():
            partial.unlink()
    return target


def export_mlflow_database(source, target, root):
    """Copia inclusive WAL, torna os TEXT portáteis e elimina páginas antigas.

    O banco de origem permanece intacto. IDs, métricas, parâmetros, conjuntos de
    dados e spans são copiados; apenas identidade inferida e endereços mudam.
    Os endereços de artefatos são relativos à raiz de distribuição informada.
    """
    source, target = Path(source).resolve(), Path(target).resolve()
    if target.is_file():
        with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as original, closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as previous:
            for connection in (original, previous):
                if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runs'").fetchone():
                    break
            else:
                columns = {row[1] for row in original.execute('PRAGMA table_info(runs)')}
                key = 'run_uuid' if 'run_uuid' in columns else 'run_id'
                old_ids = {row[0] for row in previous.execute('SELECT ' + _quote(key) + ' FROM runs')}
                current_ids = {row[0] for row in original.execute('SELECT ' + _quote(key) + ' FROM runs')}
                if not old_ids.issubset(current_ids):
                    raise ValueError('A origem não contém os registros anteriores. Restaure a cópia existente antes de continuar.')
    def rewrite(table, column, value, row):
        if column == 'value' and row.get('key') in _CONTEXT:
            return _CONTEXT[row['key']]
        if column == 'user_id':
            return 'equipe'
        return public_text(value, root)
    return _copy_database(source, target, rewrite)


def restore_mlflow_database(source, target, root):
    """Cria uma cópia local para a UI; nunca acrescenta caminhos à distribuição."""
    root = Path(root).resolve()
    columns = {('experiments', 'artifact_location'), ('runs', 'artifact_uri'),
               ('logged_models', 'artifact_location'), ('model_versions', 'source')}
    def rewrite(table, column, value, row):
        location = ((table, column) in columns or
                    (table == 'trace_tags' and column == 'value' and row.get('key') == 'mlflow.artifactLocation'))
        if not location or urlsplit(value).scheme or not value:
            return value
        path = (root / value).resolve()
        if not path.is_relative_to(root):
            raise ValueError('O registro de artefatos aponta para fora da distribuição.')
        return path.as_uri()
    return _copy_database(source, target, rewrite)


def _public_bytes(name, raw, root, temporary, source_path=None):
    if raw.startswith(b'SQLite format 3\x00'):
        source = temporary / (uuid4().hex + '.db')
        target = temporary / (uuid4().hex + '.db')
        if source_path is None:
            source.write_bytes(raw)
        else:
            source = source_path
        export_mlflow_database(source, target, root)
        return target.read_bytes()
    if is_zipfile(BytesIO(raw)):
        with ZipFile(BytesIO(raw)) as old:
            entries = []
            changed = False
            members = {item.filename: item for item in old.infolist() if not item.is_dir()}
            for filename in members:
                if PurePosixPath(filename).is_absolute() or '..' in PurePosixPath(filename).parts or '\\' in filename or re.match(r'^[A-Za-z]:', filename):
                    raise ValueError('Caminho inválido no pacote de registros.')
            nested = temporary / uuid4().hex
            nested.mkdir()
            databases = {name for name in members if old.read(name).startswith(b'SQLite format 3\x00')}
            sidecars = {name + suffix for name in databases for suffix in ('-wal', '-shm', '-journal') if name + suffix in members}
            for filename in databases | sidecars:
                relative = Path(filename)
                if relative.is_absolute() or '..' in relative.parts or '\\' in filename:
                    raise ValueError('Caminho inválido no pacote de registros.')
                target = (nested / relative).resolve()
                if not target.is_relative_to(nested.resolve()):
                    raise ValueError('Caminho inválido no pacote de registros.')
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(old.read(filename))
            for item in old.infolist():
                if item.is_dir():
                    continue
                if item.filename in sidecars or '__pycache__' in Path(item.filename).parts or item.filename.endswith(('.pyc', '.pyo')):
                    changed = True
                    continue
                data = old.read(item)
                new = _public_bytes(item.filename, data, root, temporary,
                                    source_path=nested / item.filename if item.filename in databases else None)
                entries.append((item.filename, new))
                changed |= new != data
            if not changed:
                return raw
        output = BytesIO()
        with ZipFile(output, 'w', ZIP_DEFLATED) as new:
            for filename, data in entries:
                new.writestr(ZipInfo(filename), data, compress_type=ZIP_DEFLATED)
        return output.getvalue()
    if name.endswith(('.json', '.yaml', '.yml', '.csv', '.txt', '.md', '.html', '.xml')) or Path(name).name == 'MLmodel':
        try:
            text = raw.decode('utf-8')
        except UnicodeDecodeError:
            return raw
        if name.endswith('.csv'):
            rows = list(csv.reader(text.splitlines(keepends=True)))
            cleaned_rows = [[public_text(value, root) for value in row] for row in rows]
            if cleaned_rows == rows:
                return raw
            from io import StringIO
            output = StringIO(newline='')
            csv.writer(output, lineterminator='\r\n' if '\r\n' in text else '\n').writerows(cleaned_rows)
            return output.getvalue().encode('utf-8')
        cleaned = public_text(text, root)
        return cleaned.encode('utf-8') if cleaned != text else raw
    return raw


def export_results_archive(root, destination, extra_files=()):
    """Empacota resultados com bancos portáteis; pesos e valores não são recalculados."""
    root, destination = Path(root).resolve(), Path(destination).resolve()
    paths = [(path.relative_to(root).as_posix(), path) for path in sorted(root.rglob('*')) if path.is_file()]
    paths += [(Path(path).name, Path(path)) for path in extra_files]
    destination.parent.mkdir(parents=True, exist_ok=True)
    names = set()
    partial = destination.with_name('.' + destination.name + '.' + uuid4().hex + '.tmp')
    try:
        with TemporaryDirectory(prefix='iatan-export-') as temporary, ZipFile(partial, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
            for name, path in paths:
                if path.resolve() == destination or any(part in {'.git', '__pycache__'} for part in Path(name).parts) or name.endswith(('.pyc', '.pyo', '-wal', '-shm', '-journal')):
                    continue
                if name in names:
                    raise ValueError('O pacote contém nomes de arquivo repetidos.')
                names.add(name)
                raw = _public_bytes(name, path.read_bytes(), root, Path(temporary), source_path=path)
                archive.writestr(ZipInfo(name), raw, compress_type=ZIP_DEFLATED)
        partial.replace(destination)
    finally:
        if partial.exists():
            partial.unlink()
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('source', type=Path)
    restore.add_argument('--output', type=Path, required=True)
    restore.add_argument('--root', type=Path, default=Path.cwd())
    package = commands.add_parser('package')
    package.add_argument('root', type=Path)
    package.add_argument('destination', type=Path)
    arguments = parser.parse_args()
    if arguments.command == 'restore':
        restore_mlflow_database(arguments.source, arguments.output, arguments.root)
    else:
        export_results_archive(arguments.root, arguments.destination)
