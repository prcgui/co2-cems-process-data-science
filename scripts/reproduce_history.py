"""Execute 03A.04 and 03A.05 sequentially and compare immutable references.

The annual input files must already exist at their documented paths. Each notebook
validates their identity and calendar before model fitting. This runner does not
silently download or replace inputs, change hyperparameters, or repair metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import nbformat
import numpy as np
import pandas as pd
from jupyter_client import KernelManager
from nbclient import NotebookClient

NOTEBOOKS = [
    '03A.04_volume_dados_generalizacao_temporal_iatan.ipynb',
    '03A.05_trajetoria_operacional_historico_ampliado.ipynb',
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def environment() -> dict:
    return {
        'python': platform.python_version(),
        'implementation': platform.python_implementation(),
        'platform': platform.platform(),
        'machine': platform.machine(),
        'logical_cpus': os.cpu_count(),
        'cpu_affinity': sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
        'thread_environment': {
            name: os.environ.get(name)
            for name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                         'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS']
        },
        'packages': dict(sorted((d.metadata['Name'], d.version)
                                for d in importlib.metadata.distributions())),
        'scope': 'Environment used for this reproduction, not a reconstruction of the original Colab environment.',
    }


def input_manifest(root: Path) -> list[dict]:
    paths = [root/'pipeline/selected_unit.json']
    paths += [root/'data/interim/03A04_multiyear'/f'iatan_unit2_{year}.parquet'
              for year in range(2010, 2026)]
    entries = []
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f'Required preserved input is missing: {path.relative_to(root)}')
        entry = {'path': path.relative_to(root).as_posix(),
                 'size_bytes': path.stat().st_size, 'sha256': digest(path)}
        if path.suffix == '.parquet':
            df = pd.read_parquet(path)
            entry.update(rows=len(df), columns=df.columns.tolist())
        entries.append(entry)
    return entries


def compare_references(root: Path, atol=1e-6, rtol=1e-8) -> dict:
    checks = []
    for reference in sorted((root/'reproducibility/baselines').glob('*.csv')):
        current = root/'outputs/tables'/reference.name
        a, b = pd.read_csv(reference), pd.read_csv(current)
        check = {'file': reference.name, 'reference_sha256': digest(reference),
                 'generated_sha256': digest(current), 'passed': True,
                 'max_absolute_numeric_difference': 0.0, 'issues': []}
        if list(a.columns) != list(b.columns) or a.shape != b.shape:
            check.update(passed=False)
            check['issues'].append('Different table shape or column names')
        else:
            for col in a:
                if pd.api.types.is_numeric_dtype(a[col]) and pd.api.types.is_numeric_dtype(b[col]):
                    av, bv = a[col].to_numpy(dtype=float), b[col].to_numpy(dtype=float)
                    if np.any(np.isfinite(av) & np.isfinite(bv)):
                        delta = float(np.nanmax(np.abs(av-bv)))
                        check['max_absolute_numeric_difference'] = max(delta, check['max_absolute_numeric_difference'])
                    if not np.allclose(av, bv, atol=atol, rtol=rtol, equal_nan=True):
                        check['passed'] = False
                        check['issues'].append(f'Numeric difference outside tolerance: {col}')
                elif not a[col].fillna('<NA>').astype(str).equals(b[col].fillna('<NA>').astype(str)):
                    check['passed'] = False
                    check['issues'].append(f'Categorical difference: {col}')
        checks.append(check)
    if not checks:
        raise RuntimeError('No immutable reference tables were found.')
    return {'absolute_tolerance': atol, 'relative_tolerance': rtol,
            'all_passed': all(c['passed'] for c in checks), 'checks': checks,
            'reference_commits': {
                '03A.04': '0fa317271ec2cd08d66e0d9e2723c01008667412',
                '03A.05': '8f23aa9488cdab980d2dcd875e720c15242f4845'}}


def run_notebook(root: Path, filename: str, runtime: Path, timeout: int) -> dict:
    path = root/'notebooks'/filename
    nb = nbformat.read(path, as_version=4)
    # Session metadata inherited from Colab is unrelated to the experiment.
    # Keep scientific code and outputs, but do not republish user/session IDs.
    nb.metadata.pop('colab', None)
    nb.metadata.pop('reproduction', None)
    for cell in nb.cells:
        for key in ['executionInfo', 'colab', 'outputId', 'execution']:
            cell.metadata.pop(key, None)
    code_source = '\n\n'.join(c.source for c in nb.cells if c.cell_type == 'code')
    source_digest = hashlib.sha256(code_source.encode()).hexdigest()
    for cell in nb.cells:
        if cell.cell_type == 'code':
            cell.outputs = []
            cell.execution_count = None
    print(f'EXECUTING {filename}', flush=True)
    started = time.perf_counter()
    km = KernelManager(kernel_name='python3')
    km.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
    env = dict(os.environ)
    env['CO2_PROJECT_ROOT'] = str(root)
    env['IPYTHONDIR'] = str(runtime/'ipython')
    env['JUPYTER_RUNTIME_DIR'] = str(runtime/'jupyter')
    env['MPLCONFIGDIR'] = str(runtime/'matplotlib')

    def show_cell(cell, cell_index, **_):
        if cell.cell_type == 'code':
            title = next((s.strip('# =') for s in cell.source.splitlines()
                          if 'CÉLULA' in s), f'cell {cell_index}')
            print(f'  {title}', flush=True)

    client = NotebookClient(nb, km=km, timeout=timeout, allow_errors=False,
                            resources={'metadata': {'path': str(root)}},
                            on_cell_start=show_cell, record_timing=True)
    try:
        client.execute(env=env)
    except Exception:
        failed = root/'outputs/reproducibility'/f'{path.stem}.failed.ipynb'
        nbformat.write(nb, failed)
        raise
    finally:
        if km.has_kernel:
            km.shutdown_kernel(now=True)
    # Only a complete execution replaces the versioned notebook.
    nb.metadata['reproduction'] = {
        'executed_at_utc': datetime.now(timezone.utc).isoformat(),
        'python_version': platform.python_version(),
        'code_source_sha256': source_digest,
        'command': 'python scripts/reproduce_history.py',
    }
    nbformat.write(nb, path)
    result = {'notebook': path.relative_to(root).as_posix(),
              'code_source_sha256': source_digest, 'executed_notebook_sha256': digest(path),
              'elapsed_seconds': round(time.perf_counter()-started, 3),
              'executed_code_cells': sum(c.cell_type == 'code' for c in nb.cells),
              'completed': True}
    print(f'COMPLETED {filename}: {result["elapsed_seconds"]} s', flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--timeout', type=int, default=1800, help='Timeout per notebook cell in seconds.')
    args = parser.parse_args()
    root = args.root.resolve()
    out = root/'outputs/reproducibility'
    out.mkdir(parents=True, exist_ok=True)
    write_json(out/'environment.json', environment())
    write_json(out/'input_manifest.json', input_manifest(root))
    summary = {'started_at_utc': datetime.now(timezone.utc).isoformat(),
               'runner_sha256': digest(Path(__file__).resolve()),
               'scope': ['03A.04', '03A.05'], 'runs': [], 'completed': False}
    write_json(out/'execution_summary.json', summary)
    with tempfile.TemporaryDirectory(prefix='co2-reproduction-') as tmp:
        for name in NOTEBOOKS:
            result = run_notebook(root, name, Path(tmp), args.timeout)
            summary['runs'].append(result)
            write_json(out/'execution_summary.json', summary)
    # Confirm that fitting and report generation did not modify source annual files.
    before = json.loads((out/'input_manifest.json').read_text())
    if input_manifest(root) != before:
        raise RuntimeError('A preserved input changed during execution.')
    comparison = compare_references(root)
    write_json(out/'reference_comparison.json', comparison)
    generated = []
    for folder in ['outputs/tables', 'outputs/models', 'outputs/reports', 'outputs/figures',
                   'data/interim/03A04_multiyear', 'data/interim/03A05_trajectory_history']:
        for path in sorted((root/folder).glob('*')):
            if path.is_file() and (path.name.startswith('03A04') or path.name.startswith('03A05')):
                generated.append({'path': path.relative_to(root).as_posix(),
                                  'size_bytes': path.stat().st_size, 'sha256': digest(path)})
    write_json(out/'output_manifest.json', generated)
    summary.update(completed=True, finished_at_utc=datetime.now(timezone.utc).isoformat(),
                   reference_comparison_passed=comparison['all_passed'], inputs_unchanged=True)
    write_json(out/'execution_summary.json', summary)
    print(json.dumps({'completed': True, 'reference_comparison_passed': comparison['all_passed'],
                      'tables_checked': len(comparison['checks'])}), flush=True)
    if not comparison['all_passed']:
        raise SystemExit('Execution completed, but differences require review. See reference_comparison.json.')


if __name__ == '__main__':
    main()
