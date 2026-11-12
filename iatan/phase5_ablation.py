"""Compara lags, HMM e DFG com a referência trimestral de geração."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

import joblib
import mlflow
from mlflow.entities.trace_location import MlflowExperimentLocation
import numpy as np
import pandas as pd
from sklearn.base import clone

from . import phase5
from .data import LOAD, digest, write_json
from .phase5_data import TARGET_TONS, load_phase5_calendar
from .phase5_uncertainty import contrasts
from .tracking import portable_path, provenance, public_span, source_matches


LAGS = (2, 20, 23, 24, 26, 29, 41, 52)
LAG_COLUMNS = [f'generation_lag_{hours:03d}h' for hours in LAGS]
COLUMNS = {
    'A': phase5.COLUMNS['A'],
    'L': ['generation_mw', *LAG_COLUMNS],
    'LH': ['generation_mw', *LAG_COLUMNS, *phase5.HMM],
    'LD': ['generation_mw', *LAG_COLUMNS, *phase5.DFG],
    'H': ['generation_mw', *phase5.HMM, *phase5.DFG],
    'F': ['generation_mw', *phase5.DFG],
    'E': ['generation_mw', *phase5.HMM],
}
PAIRS = tuple((scenario, 'A') for scenario in COLUMNS if scenario != 'A') + (
    ('LH', 'L'), ('LD', 'L'), ('H', 'E'), ('H', 'F'),
)
KEYS = ['ano', 'timestamp', 'cycle_id', TARGET_TONS, 'janela']
COMMON_FILES = ('configs/phase5_iatan.json', 'configs/iatan_inputs.json', 'iatan/data.py',
                'iatan/phase5.py', 'iatan/phase5_data.py', 'iatan/processes.py')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def reference_run(root, reference, environment):
    source = reference / 'resultados'
    summary = read_json(source / 'resumo.json')
    if summary['status'] != 'FINISHED' or summary.get('cadencia') != 'trimestral':
        raise ValueError('Selecione uma rodada trimestral A–D concluída.')
    previous = read_json(source / 'proveniencia.json')
    for name in COMMON_FILES:
        if not source_matches(root, name, previous['source_hashes'].get(name)):
            raise ValueError(f'O código ou a configuração da referência diverge em {name}.')
    for name in ('numpy', 'pandas', 'pyarrow', 'scikit-learn', 'xgboost', 'hmmlearn'):
        if environment['packages'][name] != previous['packages'].get(name):
            raise ValueError(f'Use a mesma versão de {name} da rodada trimestral.')
    protocol = read_json(source / 'protocolo.json')
    if (protocol['sha256_config'] != digest(root / 'configs/phase5_iatan.json')
            or protocol['atributos'] != phase5.COLUMNS):
        raise ValueError('O protocolo da rodada trimestral não corresponde à referência A–D.')
    predictions = pd.read_csv(source / 'previsoes_pareadas.csv', parse_dates=['timestamp'],
                              float_precision='round_trip')
    if not predictions.timestamp.is_unique or len(predictions) != summary['horas_pareadas']:
        raise ValueError('As previsões da referência precisam conter uma linha por hora elegível.')
    audit = dict(rodada=reference.name, mlflow_run_id=summary['mlflow_run_id'], trace_id=summary['trace_id'],
                 arquivos_sha256={name: digest(source / name) for name in (
                     'resumo.json', 'protocolo.json', 'proveniencia.json', 'manifesto_dados.json', 'previsoes_pareadas.csv',
                 )}, ambiente=previous)
    return source, summary, protocol, predictions, audit


def fit_window(calendar, extra_features, year, quarter, reference, source_predictions, protocol, folder,
               manifest_path, *, scenarios=COLUMNS):
    period = f'{year}-T{quarter}'
    saved = reference / period
    source_audit = read_json(saved / 'auditoria.json')
    available, train, train_idx, test_idx, _ = phase5.window_data(calendar, year, quarter)
    folder.mkdir()
    experiment = mlflow.active_run().info.experiment_id
    with mlflow.start_run(experiment_id=experiment, run_name=period, nested=True) as window, public_span(
        'Janela trimestral', attributes={'janela': period, 'run_id': window.info.run_id}
    ):
        with public_span('Reaplicar representação e verificar referência'):
            process_file = saved / 'representacao_treino.joblib'
            process = joblib.load(process_file)
            if (process.train_end != train.timestamp.max()
                    or process.train_end != pd.Timestamp(source_audit['treino_ate'])
                    or process.training_events.end.max() > process.train_end
                    or len(train_idx) != source_audit['n_treino']):
                raise ValueError(f'Corte de treino incompatível com a referência em {period}.')
            frame = phase5.features(available, process)
            # Atributos adicionais usam o calendário antes do filtro de horas ON.
            frame[extra_features.columns] = extra_features.loc[available.timestamp].to_numpy()
            frame[TARGET_TONS] = available[TARGET_TONS]
            pairs = frame.loc[test_idx, ['timestamp', 'cycle_id', TARGET_TONS]].reset_index(drop=True)
            pairs.insert(0, 'ano', year)
            pairs['janela'] = period
            expected = source_predictions.loc[source_predictions.janela.eq(period)].reset_index(drop=True)
            pd.testing.assert_frame_equal(pairs, expected[KEYS], check_exact=True)
            hashes = {'representacao_treino.joblib': digest(process_file)}
            for scenario in ('A', 'C', 'D'):
                model_file = saved / f'xgboost_{scenario}.joblib'
                model = joblib.load(model_file)
                hashes[model_file.name] = digest(model_file)
                reproduced = model.predict(frame.loc[test_idx, phase5.COLUMNS[scenario]])
                np.testing.assert_array_equal(reproduced, expected[scenario].to_numpy(),
                                              err_msg=f'Previsões da referência {period}/{scenario} não reproduzidas.')
                if scenario == 'A':
                    baseline = model
            pairs['A'] = expected['A']
        target = pairs[TARGET_TONS].to_numpy()
        audit = dict(ano=year, janela=period, nivel='trimestre', treino_ate=source_audit['treino_ate'],
                     origem_calendario=source_audit['origem_calendario'],
                     fim_exclusivo_calendario=source_audit['fim_exclusivo_calendario'],
                     n_treino=len(train_idx), n_avaliacao=len(test_idx), hmm=source_audit['hmm'],
                     previsoes_origem_reproduzidas=['A', 'C', 'D'], arquivos_origem_sha256=hashes,
                     run_janela_origem=source_audit['run_id'], run_id=window.info.run_id)
        mlflow.log_params({key: audit[key] for key in (
            'treino_ate', 'origem_calendario', 'fim_exclusivo_calendario', 'n_treino', 'n_avaliacao', 'run_janela_origem',
        )})
        mlflow.log_param('hmm_convergiu', audit['hmm']['convergencia_confirmada'])
        rows = []
        for scenario, columns in scenarios.items():
            reused = scenario == 'A'
            span_name = 'Registrar referência A' if reused else f'Ajustar e avaliar cenário {scenario}'
            with mlflow.start_run(experiment_id=experiment, run_name=scenario, nested=True) as run, public_span(
                span_name, attributes={'janela': period, 'cenario': scenario, 'run_id': run.info.run_id}
            ):
                if not reused:
                    model = clone(baseline)
                    model.fit(frame.loc[train_idx, columns], frame.loc[train_idx, TARGET_TONS])
                    prediction = model.predict(frame.loc[test_idx, columns]).astype(float)
                    if not np.isfinite(prediction).all():
                        raise ValueError(f'Previsões inválidas em {period}/{scenario}.')
                    pairs[scenario] = prediction
                    model_file = folder / f'xgboost_{scenario}.joblib'
                    joblib.dump(model, model_file, compress=3)
                    mlflow.log_artifact(str(model_file), artifact_path='modelo')
                    for role, index in (('training', train_idx), ('evaluation', test_idx)):
                        phase5.log_sample(frame, index, columns, manifest_path, f'iatan_{period}_{scenario}_{role}', role)
                scores = phase5.scoring(target, pairs[scenario].to_numpy())
                mlflow.log_metrics(scores)
                mlflow.log_params(dict(cenario=scenario, janela=period, ajuste_reutilizado=reused,
                                       n_atributos=len(columns), **protocol['xgboost']))
                mlflow.log_dict({'ordem_dos_atributos': columns}, 'atributos.json')
                rows.append(dict(ano=year, janela=period, nivel='trimestre', cenario=scenario,
                                 n=len(pairs), run_id=run.info.run_id, **scores))
        pairs.to_csv(folder / 'previsoes_pareadas.csv', index=False)
        write_json(folder / 'auditoria.json', audit)
        mlflow.log_artifact(str(folder / 'previsoes_pareadas.csv'))
        mlflow.log_artifact(str(folder / 'auditoria.json'))
    return pairs, rows, audit


def consolidate(results, predictions, expected, rows, audits, protocol, *, scenarios=COLUMNS, pairs=PAIRS):
    pd.testing.assert_frame_equal(predictions[KEYS + ['A']], expected[KEYS + ['A']], check_exact=True)
    groups = [(year, 'ano', group) for year, group in predictions.groupby('ano', sort=True)]
    groups.append(('agrupado', 'agrupado', predictions))
    for period, level, group in groups:
        for scenario in scenarios:
            scores = phase5.scoring(group[TARGET_TONS].to_numpy(), group[scenario].to_numpy())
            rows.append(dict(ano=period, janela=str(period), nivel=level, cenario=scenario, n=len(group), **scores))
            prefix = '' if level == 'agrupado' else f'{period}_'
            mlflow.log_metrics({f'{prefix}{scenario}_{metric}': value for metric, value in scores.items()})
    intervals = contrasts(predictions, **protocol['incerteza'], pairs=pairs, by_quarter=True)
    for row in intervals.loc[intervals.periodo.eq('agrupado')].itertuples():
        mlflow.log_metrics({f'{row.contraste}_{name}_{row.bloco_dias}d': getattr(row, name)
                            for name in ('delta_rmse', 'ic95_inferior', 'ic95_superior')})
    intervals.to_csv(results / 'contrastes.csv', index=False)
    pd.DataFrame(rows).to_csv(results / 'metricas.csv', index=False)
    predictions.to_csv(results / 'previsoes_pareadas.csv', index=False)
    write_json(results / 'auditoria_trimestral.json', audits)
    for filename in ('contrastes.csv', 'metricas.csv', 'previsoes_pareadas.csv', 'auditoria_trimestral.json'):
        mlflow.log_artifact(str(results / filename))


def run(root, reference, output_root=None):
    """Compara seis combinações de atributos com A da rodada trimestral concluída."""
    root, reference = Path(root).resolve(), Path(reference).expanduser().resolve()
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes de iniciar a ablação.')
    environment = provenance(root)
    source, summary, protocol, expected, source_audit = reference_run(root, reference, environment)
    calendar, manifest = load_phase5_calendar(root)
    if manifest != read_json(source / 'manifesto_dados.json'):
        raise ValueError('Os dados anuais divergem do manifesto da rodada trimestral.')
    generation = calendar.set_index('timestamp')[LOAD]
    lags = pd.DataFrame({name: generation.shift(hours) for hours, name in zip(LAGS, LAG_COLUMNS, strict=True)})
    windows = [(year, quarter) for year in protocol['anos_avaliacao'] for quarter in range(1, 5)]
    if len(windows) != summary['janelas']:
        raise ValueError('O protocolo e a referência divergem na quantidade de janelas.')
    protocol.update(atributos=COLUMNS, lags_horas=LAGS,
                    lags_regra='Defasagens da Fase 3 no calendário horário completo, antes do filtro de horas ON.',
                    contrastes=[f'{candidate}-{reference}' for candidate, reference in PAIRS],
                    contraste_principal='Cada combinação comparada com A',
                    elegibilidade='Mesmas horas ON elegíveis da referência trimestral.',
                    hmm_regra='Reaplicar a representação HMM/DFG da referência em cada janela.')
    del protocol['contraste_pacote_completo']
    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    folder = Path(output_root or root / 'outputs/phase_05_process_ablation').resolve() / run_name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    files = {'protocolo.json': protocol, 'proveniencia.json': environment,
             'manifesto_dados.json': manifest, 'origem_trimestral.json': source_audit}
    for name, value in files.items():
        write_json(results / name, value)
    old_uri = mlflow.get_tracking_uri()
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    mlflow.set_tracking_uri(f"sqlite:///{(folder / 'mlflow.db').as_posix()}")
    try:
        experiment = mlflow.create_experiment('Iatan 2 · Fase 5 · Lags, HMM e DFG', artifact_location=artifacts.as_uri())
        with mlflow.start_run(experiment_id=experiment, run_name='Sete cenários · 2023 a 2025',
                              log_system_metrics=True) as parent, public_span(
            'Fase 5 · Ablação de lags, HMM e DFG', run_id=parent.info.run_id,
            trace_destination=MlflowExperimentLocation(experiment_id=experiment)
        ) as trace:
            mlflow.set_tags({'unit': protocol['unidade'], 'protocol': 'phase5_iatan_process_ablation_v1',
                             'inference': 'retrospective', 'rodada_origem': reference.name,
                             'run_origem': summary['mlflow_run_id']})
            for name in files:
                mlflow.log_artifact(str(results / name))
            frames, rows, audits = [], [], []
            for year, quarter in windows:
                period = f'{year}-T{quarter}'
                pairs, metrics, audit = fit_window(calendar, lags, year, quarter, source, expected, protocol,
                                                   results / period, results / 'manifesto_dados.json')
                frames.append(pairs)
                rows.extend(metrics)
                audits.append(audit)
                print(period, 'concluído', {x['cenario']: round(x['rmse'], 4) for x in metrics}, flush=True)
            predictions = pd.concat(frames, ignore_index=True)
            with public_span('Consolidar resultados e bootstrap pareado'):
                consolidate(results, predictions, expected, rows, audits, protocol)
            report = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                          trace_id=trace.trace_id, horas_pareadas=len(predictions), ajustes=(len(COLUMNS) - 1) * len(windows),
                          resultados=rows, cadencia='trimestral', janelas=len(windows), rodada_origem=reference.name,
                          convergencia={a['janela']: a['hmm']['convergencia_confirmada'] for a in audits})
        mlflow.flush_trace_async_logging()
        client = mlflow.MlflowClient()
        if client.get_run(report['mlflow_run_id']).info.status != 'FINISHED' or client.get_trace(report['trace_id']) is None:
            raise RuntimeError('A execução de síntese e o trace precisam estar disponíveis.')
        write_json(results / 'resumo.json', report)
        client.log_artifact(report['mlflow_run_id'], str(results / 'resumo.json'))
    finally:
        mlflow.flush_trace_async_logging()
        mlflow.set_tracking_uri(old_uri)
    print('Resultados e MLflow:', portable_path(folder, root), flush=True)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--reference', type=Path, required=True, help='Pasta da rodada trimestral A–D concluída.')
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    run(args.root, args.reference, args.output_root)
