"""Teste cronológico do candidato operacional definido antes de abrir 2026."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from uuid import uuid4

import joblib
import mlflow
from mlflow.entities.trace_location import MlflowExperimentLocation
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from xgboost import XGBRegressor

from . import phase5
from .data import LOAD, OP, TARGET, digest, write_json
from .phase5_ablation import KEYS, read_json
from .phase5_data import SHORT_TON_TO_TONNE, TARGET_TONS, load_phase5_calendar
from .phase5_operational_ablation import COLUMNS, OPERATIONAL_COLUMNS, operational_features
from .phase5_uncertainty import _block_draws, _contrast_rows
from .processes import observations
from .tracking import portable_path, provenance, public_span, source_matches


CANDIDATES = ('R', 'RH', 'RD')
UNIT = 'EPA 6065/2'
START = '2026-01-01'
STOPS = ('2026-04-01', '2026-07-01')
RAW_COLUMNS = ('Facility ID', 'Unit ID', 'Date', 'Hour', OP, LOAD, TARGET)
CODE = ('iatan/phase5_operational_holdout.py', 'iatan/phase5_operational_ablation.py',
        'iatan/phase5.py', 'iatan/phase5_ablation.py', 'iatan/phase5_data.py',
        'iatan/phase5_uncertainty.py', 'iatan/processes.py', 'iatan/data.py',
        'configs/phase5_iatan.json', 'configs/iatan_inputs.json')
SELECTION = ('Menor RMSE retrospectivo agrupado entre candidatos com limite superior do IC95% '
             'pareado de 7 dias abaixo de zero contra A. Sem esse sinal, menor RMSE entre os '
             'candidatos como hipótese. Empates na ordem R, RH, RD.')
CONFIRMATION = ('No teste inédito, limite superior do IC95% agrupado de ΔRMSE candidata − A '
                'abaixo de zero com blocos de 7 dias. Sensibilidades de 1 e 3 dias, MAE, '
                'viés e contrastes trimestrais são descritivos.')


def source_metadata(manifest_path):
    data = read_json(manifest_path)
    if (data['unidade'] != UNIT or data['inicio'] != START or data['fim_exclusivo'] not in STOPS
            or not data['arquivos']):
        raise ValueError('A origem deve ser Iatan 2, em 2026-T1 ou 2026-T1 a T2 completos.')
    return data


def choose_candidate(retrospective):
    results = retrospective / 'resultados'
    summary = read_json(results / 'resumo.json')
    if (summary['status'] != 'FINISHED' or summary['horas_pareadas'] != 14966
            or summary['janelas'] != 12):
        raise ValueError('A seleção exige a ablação operacional concluída nas 14.966 horas.')
    metrics = pd.read_csv(results / 'metricas.csv')
    intervals = pd.read_csv(results / 'contrastes.csv')
    rmse = metrics.loc[metrics.nivel.eq('agrupado')].set_index('cenario').rmse
    primary = intervals.loc[intervals.periodo.eq('agrupado') & intervals.bloco_dias.eq(7)
                            & intervals.referencia.eq('A')].set_index('candidata')
    rows = {scenario: {'rmse': float(rmse.loc[scenario]),
                       'ic95_superior_vs_A_7d': float(primary.loc[scenario, 'ic95_superior'])}
            for scenario in CANDIDATES}
    if not np.isfinite([value for row in rows.values() for value in row.values()]).all():
        raise ValueError('A seleção exige métricas e intervalos retrospectivos finitos.')
    supported = [scenario for scenario in CANDIDATES if rows[scenario]['ic95_superior_vs_A_7d'] < 0]
    candidate = min(supported or CANDIDATES, key=lambda scenario: rows[scenario]['rmse'])
    hashes = {name: digest(results / name) for name in (
        'resumo.json', 'protocolo.json', 'proveniencia.json', 'metricas.csv', 'contrastes.csv',
    )}
    return candidate, {'mlflow_run_id': summary['mlflow_run_id'], 'sha256': hashes,
                       'rmse_A': float(rmse.loc['A']), 'candidatos': rows,
                       'sinal_retrospectivo': bool(supported)}


def freeze_protocol(root, retrospective, manifest_path, output):
    """Seleciona com a rodada antiga e lê apenas os metadados do novo insumo."""
    root, retrospective = Path(root).resolve(), Path(retrospective).resolve()
    manifest_path, output = Path(manifest_path).resolve(), Path(output).resolve()
    metadata = source_metadata(manifest_path)
    candidate, selection = choose_candidate(retrospective)
    settings = read_json(root / 'configs/phase5_iatan.json')
    retrospective_results = retrospective / 'resultados'
    retro_protocol = read_json(retrospective_results / 'protocolo.json')
    retro_provenance = read_json(retrospective_results / 'proveniencia.json')
    code_hashes = {name: digest(root / name) for name in CODE}
    packages = provenance(root)['packages']
    if (retro_protocol['atributos'] != COLUMNS
            or any(retro_protocol[key] != settings[key] for key in ('xgboost', 'hmm', 'incerteza'))
            or any(not source_matches(root, name, retro_provenance['source_hashes'].get(name))
                   for name in code_hashes if name != CODE[0])
            or retro_provenance['packages'] != packages):
        raise ValueError('A rodada retrospectiva usa atributos, código ou ambiente diferentes.')
    frozen = {
        'protocolo': 'iatan_operational_holdout_v1', 'unidade': UNIT,
        'congelado_utc': datetime.now(timezone.utc).isoformat(),
        'inicio': metadata['inicio'], 'fim_exclusivo': metadata['fim_exclusivo'],
        'alvo': settings['alvo'], 'candidata': candidate,
        'atributos': {scenario: COLUMNS[scenario] for scenario in ('A', candidate)},
        'selecao': SELECTION, 'resultado_retrospectivo': selection,
        'confirmacao': CONFIRMATION, 'incerteza': settings['incerteza'],
        'bootstrap': 'Blocos pareados de calendário estratificados por trimestre avaliado.',
        'treino': 'Expansivo desde 2011 até a hora anterior a cada origem trimestral.',
        'xgboost': settings['xgboost'], 'hmm': settings['hmm'],
        'sha256_manifesto_inedito': digest(manifest_path),
        'sha256_codigo_e_config': code_hashes, 'pacotes': packages,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(frozen, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print('Protocolo congelado:', portable_path(output, root), digest(output), 'candidata:', candidate, flush=True)
    return output


def read_holdout(manifest_path, metadata):
    parts = []
    for item in metadata['arquivos']:
        path = (manifest_path.parent / item['arquivo']).resolve()
        if not path.is_relative_to(manifest_path.parent) or digest(path) != item['sha256']:
            raise ValueError('O arquivo horário diverge do manifesto congelado.')
        parts.append(pd.read_csv(path, usecols=list(RAW_COLUMNS), dtype={'Unit ID': str},
                                 float_precision='round_trip'))
    raw = pd.concat(parts, ignore_index=True)
    if not raw['Facility ID'].eq(6065).all() or not raw['Unit ID'].eq('2').all():
        raise ValueError('Os registros devem pertencer exclusivamente a Iatan 2.')
    dates = pd.to_datetime(raw.Date, format='mixed', errors='raise')
    if (dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all()
            or not raw.Hour.between(0, 23).all() or not raw.Hour.eq(raw.Hour.round()).all()
            or not raw[OP].between(0, 1).all()):
        raise ValueError('Data, hora ou tempo de operação fora do contrato horário da EPA.')
    stamp = dates + pd.to_timedelta(raw.Hour, unit='h')
    data = raw.assign(timestamp=stamp).sort_values('timestamp').reset_index(drop=True)
    expected = pd.date_range(metadata['inicio'], metadata['fim_exclusivo'], freq='h', inclusive='left')
    if not data.timestamp.equals(pd.Series(expected)):
        raise ValueError('O calendário do teste deve ter todas as horas, sem duplicidades ou lacunas.')
    values = data[[LOAD, TARGET]].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(values).any() or (values < 0).any():
        raise ValueError('Carga ou CO₂ inválidos no teste.')
    return data[['timestamp', LOAD, OP]].assign(**{TARGET_TONS: data[TARGET] * SHORT_TON_TO_TONNE})


def fit_origin(calendar, operating, origin, frozen, folder, manifest):
    year, quarter = origin.year, origin.quarter
    period = f'{year}-T{quarter}'
    candidate = frozen['candidata']
    columns = COLUMNS[candidate]
    available, train, train_idx, test_idx, missing = phase5.window_data(calendar, year, quarter)
    raw = available[['timestamp', LOAD, OP]]
    folder.mkdir()
    diagnostics = None
    if candidate == 'R':
        transform = observations
    else:
        with public_span('Ajustar representação operacional somente no treino'):
            process, diagnostics = phase5.fit_process(train[['timestamp', LOAD, OP]], frozen['hmm'], folder)
        transform = process.transform
    frame = transform(raw).assign(generation_mw=raw[LOAD])
    frame[OPERATIONAL_COLUMNS] = operating.loc[frame.timestamp, OPERATIONAL_COLUMNS].to_numpy()
    midpoint = available.timestamp.iloc[test_idx[len(test_idx) // 2]]
    for end in (origin, midpoint):
        prefix = calendar.loc[calendar.timestamp.lt(end), ['timestamp', LOAD, OP]]
        pd.testing.assert_frame_equal(operational_features(prefix), operating.loc[operating.index < end])
        if diagnostics is not None:
            eligible_prefix = raw.loc[raw.timestamp.lt(end)]
            process_columns = phase5.HMM if candidate == 'RH' else phase5.DFG
            pd.testing.assert_frame_equal(transform(eligible_prefix)[process_columns],
                                          frame.loc[frame.timestamp.lt(end), process_columns],
                                          rtol=1e-12, atol=1e-12)
    frame[TARGET_TONS] = available[TARGET_TONS]
    pairs = frame.loc[test_idx, ['timestamp', 'cycle_id', TARGET_TONS]].reset_index(drop=True)
    pairs.insert(0, 'ano', year)
    pairs['janela'] = period
    pairs = pairs[KEYS]
    for scenario in ('A', candidate):
        inputs = COLUMNS[scenario]
        model = make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True),
                              XGBRegressor(**frozen['xgboost']))
        with public_span('Ajustar e estimar cenário', attributes={'cenario': scenario}):
            model.fit(frame.loc[train_idx, inputs], frame.loc[train_idx, TARGET_TONS])
            pairs[scenario] = model.predict(frame.loc[test_idx, inputs]).astype(float)
            if not np.isfinite(pairs[scenario]).all():
                raise RuntimeError(f'Previsões não finitas em {period}/{scenario}.')
            joblib.dump(model, folder / f'xgboost_{scenario}.joblib', compress=3)
    phase5.log_sample(frame, train_idx, columns, manifest, f'iatan_{period}_treino', 'training')
    phase5.log_sample(frame, test_idx, columns, manifest, f'iatan_{period}_teste', 'evaluation')
    audit = dict(janela=period, origem=origin.isoformat(), treino_ate=train.timestamp.max().isoformat(),
                 avaliacao_inicio=pairs.timestamp.min().isoformat(), avaliacao_fim=pairs.timestamp.max().isoformat(),
                 n_treino=len(train_idx), n_avaliacao=len(test_idx), prefixos_verificados=2,
                 rupturas_por_falta_de_carga=missing.astype(str).tolist(), hmm=diagnostics)
    write_json(folder / 'auditoria.json', audit)
    pairs.to_csv(folder / 'previsoes_pareadas.csv', index=False)
    mlflow.log_artifacts(str(folder))
    return pairs, audit


def holdout_contrasts(predictions, candidate, uncertainty):
    """Reusa o bootstrap da Fase 5 sem reamostrar trimestres fora do teste."""
    scenarios, pairs = ('A', candidate), ((candidate, 'A'),)
    losses = predictions[list(scenarios)].sub(predictions[TARGET_TONS], axis=0).pow(2)
    groups = losses.assign(timestamp=predictions.timestamp).groupby(predictions.janela)
    rows = []
    for days in uncertainty['block_days']:
        replicates = uncertainty['replicates']
        quarters = {period: _block_draws(int(period[:4]), data, scenarios, days, replicates,
                                        uncertainty['seed'], int(period[-1]))
                    for period, data in groups}
        pooled = {key: sum(draw[key] for draw in quarters.values())
                  for key in next(iter(quarters.values()))}
        for period, draw in {**quarters, 'agrupado': pooled}.items():
            rows.extend(_contrast_rows(period, draw, scenarios, pairs, days, replicates))
    return pd.DataFrame(rows)


def score_period(pairs, candidate, period):
    rows = [dict(janela=period, nivel='agrupado' if period == 'agrupado' else 'trimestre',
                 cenario=scenario, n=len(pairs),
                 **phase5.scoring(pairs[TARGET_TONS].to_numpy(), pairs[scenario].to_numpy()))
            for scenario in ('A', candidate)]
    for row in rows:
        mlflow.log_metrics({f'{row["cenario"]}.{key}': row[key] for key in ('rmse', 'mae', 'vies')})
    return rows


def run(root, protocol_path, manifest_path, output_root=None):
    root, protocol_path, manifest_path = (Path(value).resolve() for value in (root, protocol_path, manifest_path))
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes do teste inédito.')
    frozen = read_json(protocol_path)
    metadata = source_metadata(manifest_path)
    candidate = frozen['candidata']
    environment = provenance(root)
    if (frozen['protocolo'] != 'iatan_operational_holdout_v1' or frozen['unidade'] != UNIT
            or candidate not in CANDIDATES or frozen['confirmacao'] != CONFIRMATION
            or frozen['selecao'] != SELECTION or frozen['atributos'] != {s: COLUMNS[s] for s in ('A', candidate)}
            or set(frozen['sha256_codigo_e_config']) != set(CODE)
            or any(not source_matches(root, name, frozen['sha256_codigo_e_config'][name]) for name in CODE)
            or frozen['pacotes'] != environment['packages']
            or frozen['sha256_manifesto_inedito'] != digest(manifest_path)
            or any(frozen[key] != metadata[key] for key in ('inicio', 'fim_exclusivo'))):
        raise ValueError('O código, o ambiente ou os insumos divergem do protocolo congelado.')
    settings = read_json(root / 'configs/phase5_iatan.json')
    if any(frozen[key] != settings[key] for key in ('xgboost', 'hmm', 'incerteza')):
        raise ValueError('Os parâmetros diferem do protocolo de origem.')

    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    folder = Path(output_root or root / 'outputs/phase_05_operational_holdout').resolve() / run_name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    previous = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f'sqlite:///{(folder / "mlflow.db").as_posix()}')
    try:
        experiment = mlflow.create_experiment('Iatan 2 · Fase 5 · Teste temporal inédito',
                                              artifact_location=artifacts.as_uri())
        with (
            mlflow.start_run(experiment_id=experiment, run_name=f'2026 · A × {candidate}') as parent,
            public_span('Avaliar protocolo congelado', run_id=parent.info.run_id,
                              trace_destination=MlflowExperimentLocation(experiment_id=experiment)) as trace,
        ):
            mlflow.set_tags({'protocol': frozen['protocolo'], 'unidade': UNIT,
                             'run_origem': frozen['resultado_retrospectivo']['mlflow_run_id']})
            mlflow.log_params({'protocolo_sha256': digest(protocol_path), 'candidata': candidate,
                               'inicio': frozen['inicio'], 'fim_exclusivo': frozen['fim_exclusivo']})
            shutil.copyfile(protocol_path, results / 'protocolo_congelado.json')
            mlflow.log_artifact(str(results / 'protocolo_congelado.json'))
            with public_span('Conferir e abrir o calendário inédito'):
                historical, history_manifest = load_phase5_calendar(root)
                calendar = pd.concat([historical, read_holdout(manifest_path, metadata)], ignore_index=True)
                operating = operational_features(calendar[['timestamp', LOAD, OP]])
                manifest = results / 'manifesto_dados.json'
                write_json(manifest, {'historico': history_manifest, 'inedito': metadata})
            frames, rows, audits = [], [], []
            for origin in pd.date_range(frozen['inicio'], frozen['fim_exclusivo'], freq='QS', inclusive='left'):
                period = f'{origin.year}-T{origin.quarter}'
                with (mlflow.start_run(experiment_id=experiment, run_name=period, nested=True) as window,
                      public_span('Avaliar janela trimestral', attributes={'janela': period})):
                    pairs, audit = fit_origin(calendar, operating, origin, frozen, results / period, manifest)
                    mlflow.log_params({key: audit[key] for key in ('treino_ate', 'n_treino', 'n_avaliacao')})
                    audit['run_id'] = window.info.run_id
                    frames.append(pairs)
                    audits.append(audit)
                    rows.extend(score_period(pairs, candidate, period))
            with public_span('Consolidar contraste pareado e aplicar critério congelado'):
                predictions = pd.concat(frames, ignore_index=True)
                expected = calendar.loc[calendar.timestamp.ge(pd.Timestamp(frozen['inicio']))
                                        & calendar[OP].gt(0) & np.isfinite(calendar[[LOAD, TARGET_TONS]]).all(axis=1)]
                pd.testing.assert_frame_equal(predictions[['timestamp', TARGET_TONS]],
                                              expected[['timestamp', TARGET_TONS]].reset_index(drop=True))
                rows.extend(score_period(predictions, candidate, 'agrupado'))
                contrasts = holdout_contrasts(predictions, candidate, frozen['incerteza'])
                primary = contrasts.loc[contrasts.periodo.eq('agrupado') & contrasts.bloco_dias.eq(7)].iloc[0]
                convergence_ok = all(audit['hmm'] is None or audit['hmm']['convergencia_confirmada'] for audit in audits)
                confirmed = bool(primary.ic95_superior < 0)
                mlflow.log_metrics({key: primary[key] for key in ('delta_rmse', 'ic95_inferior', 'ic95_superior')})
                mlflow.log_params({'hmm_convergencia_confirmada': convergence_ok, 'melhora_confirmada': confirmed})
                predictions.to_csv(results / 'previsoes_pareadas.csv', index=False)
                pd.DataFrame(rows).to_csv(results / 'metricas.csv', index=False)
                contrasts.to_csv(results / 'contrastes.csv', index=False)
                write_json(results / 'auditoria_trimestral.json', audits)
                write_json(results / 'proveniencia.json', environment)
                for path in results.iterdir():
                    if path.is_file() and path.name != 'protocolo_congelado.json':
                        mlflow.log_artifact(str(path))
                summary = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                               trace_id=trace.trace_id, candidata=candidate, horas_pareadas=len(predictions),
                               ajustes=2 * len(audits), janelas=len(audits), melhora_confirmada=confirmed,
                               convergencia=convergence_ok, contraste_principal=primary.to_dict(),
                               protocolo_sha256=digest(protocol_path))
        mlflow.flush_trace_async_logging()
        client = mlflow.MlflowClient()
        if client.get_run(summary['mlflow_run_id']).info.status != 'FINISHED' or client.get_trace(summary['trace_id']) is None:
            raise RuntimeError('A execução inédita e o trace precisam estar disponíveis.')
        write_json(results / 'resumo.json', summary)
        client.log_artifact(summary['mlflow_run_id'], str(results / 'resumo.json'))
    finally:
        mlflow.flush_trace_async_logging()
        mlflow.set_tracking_uri(previous)
    print('Resultados e MLflow:', portable_path(folder, root), flush=True)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    freeze = commands.add_parser('congelar')
    execute = commands.add_parser('executar')
    for subparser in (freeze, execute):
        subparser.add_argument('--root', type=Path, default=Path.cwd())
        subparser.add_argument('--data-manifest', type=Path, required=True)
        subparser.add_argument('--protocol', type=Path, required=True)
    freeze.add_argument('--operational-run', type=Path, required=True)
    execute.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    if args.command == 'congelar':
        freeze_protocol(args.root, args.operational_run, args.data_manifest, args.protocol)
    else:
        run(args.root, args.protocol, args.data_manifest, args.output_root)
