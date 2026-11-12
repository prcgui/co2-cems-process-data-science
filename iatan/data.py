"""Dados preservados e contratos. Referências: Diba et al. (2020); aula e-Science.

As decisões amostrais de 03A.05 são preservadas, não atribuídas aos artigos.
"""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

TARGET = 'CO2 Mass (short tons)'
LOAD = 'Gross Load (MW)'
OP = 'Operating Time'
B0 = ['load_current_mw', 'load_lag_1h', 'delta_load_1h',
      'abs_delta_load_1h', 'load_mean_previous_3h',
      'operating_time_lag_1h', 'hours_since_startup']
HISTORY = 'data/interim/03A05_trajectory_history'


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2,
                               allow_nan=False, default=str) + '\n', encoding='utf-8')


def verify_inputs(root):
    manifest = json.loads((root / 'configs/iatan_inputs.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = root / item['path']
        if not path.is_file():
            raise FileNotFoundError(f"Insumo ausente: {item['path']}. Restaure o pacote de dados do Drive.")
        if digest(path) != item['sha256']:
            raise ValueError(f"Insumo alterado: {item['path']}")
    return manifest


def audit_hourly(df):
    required = ['timestamp', 'facilityId_norm', 'unitId_norm', LOAD, OP, TARGET]
    if not set(required).issubset(df):
        raise ValueError('Schema horário incompleto')
    if not df.timestamp.is_unique or not df.timestamp.is_monotonic_increasing:
        raise ValueError('Timestamps duplicados ou fora de ordem')
    if not df.facilityId_norm.astype(str).eq('6065').all() or not df.unitId_norm.astype(str).eq('2').all():
        raise ValueError('Este protocolo é exclusivo de Iatan 6065/2')
    if not df[OP].between(0, 1).all():
        raise ValueError('Tempo de operação inválido')
    on = df[OP].gt(0)
    return {'rows': len(df), 'on': int(on.sum()), 'off': int((~on).sum()),
            'load_missing_on': int(df.loc[on, LOAD].isna().sum()),
            'co2_missing_on': int(df.loc[on, TARGET].isna().sum()),
            'start': str(df.timestamp.min()), 'end': str(df.timestamp.max())}


def load_splits(root):
    names = {'train_selection': 'treino_selecao', 'validation': 'validacao_outubro_2025',
             'train_final': 'treino_final', 'test': 'teste_nov_dez_2025'}
    splits = {k: pd.read_parquet(root / HISTORY / f'03A05_{v}_A_B.parquet')
              for k, v in names.items()}
    config = json.loads((root / 'configs/baseline_03A05.json').read_text(encoding='utf-8'))
    for name, df in splits.items():
        audit_hourly(df)
        if len(df) != config['expected_n'][name] or not df[OP].gt(0).all():
            raise ValueError(f'Amostra histórica diferente: {name}')
        if not np.isfinite(df[B0 + [TARGET]].to_numpy(float)).all():
            raise ValueError(f'Valores não finitos: {name}')
    a, v, f, t = (splits[k] for k in names)
    if not a.timestamp.max() < v.timestamp.min() <= v.timestamp.max() < t.timestamp.min():
        raise ValueError('Partições temporais sobrepostas')
    combined = pd.concat([a, v], ignore_index=True).sort_values('timestamp').reset_index(drop=True)
    pd.testing.assert_frame_equal(combined[['timestamp', TARGET] + B0],
                                  f[['timestamp', TARGET] + B0].reset_index(drop=True))
    if set(a.timestamp.dt.year) != set(range(2011, 2023)) | {2025}:
        raise ValueError('Anos de treinamento diferentes do protocolo congelado')
    if not v.timestamp.between('2025-10-01', '2025-10-31 23:00').all():
        raise ValueError('Validação fora de outubro')
    if not t.timestamp.between('2025-11-01', '2025-12-31 23:00').all():
        raise ValueError('Teste fora de novembro–dezembro')
    return splits


def load_calendar(root, years=tuple(range(2011, 2023)) + (2025,)):
    parts = []
    for year in years:
        df = pd.read_parquet(root / f'data/interim/03A04_multiyear/iatan_unit2_{year}.parquet')
        audit_hourly(df)
        # 2010 is an acquisition/startup partial year, preserved only for provenance.
        expected = (pd.date_range(df.timestamp.min(), df.timestamp.max(), freq='h') if year == 2010
                    else pd.date_range(f'{year}-01-01', f'{year}-12-31 23:00', freq='h'))
        if not df.timestamp.reset_index(drop=True).equals(pd.Series(expected)):
            raise ValueError(f'Calendário incompleto: {year}')
        parts.append(df)
    df = pd.concat(parts, ignore_index=True).sort_values('timestamp').reset_index(drop=True)
    audit_hourly(df)
    return df


def freeze(root):
    manifest = verify_inputs(root)
    splits = load_splits(root)
    raw = load_calendar(root, tuple(range(2010, 2026)))
    # Compare saved supervised targets and generation against original hourly measurements.
    for name, df in splits.items():
        check = df[['timestamp', TARGET, LOAD, OP]].merge(
            raw[['timestamp', TARGET, LOAD, OP]], on='timestamp', validate='one_to_one',
            suffixes=('_sample', '_raw'))
        if len(check) != len(df):
            raise ValueError(f'Horas ausentes no calendário original: {name}')
        for col in [TARGET, LOAD, OP]:
            if not np.array_equal(check[col + '_sample'], check[col + '_raw']):
                raise ValueError(f'Medição divergente: {name}/{col}')
    yearly = pd.DataFrame([dict(year=y, **audit_hourly(g))
                           for y, g in raw.groupby(raw.timestamp.dt.year)])
    out = root / 'outputs/iatan_consolidado'; out.mkdir(exist_ok=True)
    yearly.to_csv(out / 'auditoria_calendario.csv', index=False)
    result = {'passed': True, 'files_verified': len(manifest['files']),
              'samples': {k: audit_hourly(v) for k, v in splits.items()},
              'original_targets_equal': True, 'training_on_only': True,
              'test_reused': True, 'task': 'CO2_t com geração observada em t; retrospectivo'}
    write_json(out / 'base_conferida.json', result)
    return result
