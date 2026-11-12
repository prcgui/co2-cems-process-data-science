"""Compara dois comprimentos de treino do cenário A nas mesmas horas trimestrais."""

import argparse
from datetime import datetime, timezone
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
from .phase5_ablation import KEYS, read_json, reference_run
from .phase5_data import TARGET_TONS, load_phase5_calendar
from .phase5_uncertainty import contrasts
from .processes import observations
from .tracking import portable_path, provenance, public_span


REFERENCE = 'expansivo'
CANDIDATE = 'ultimos_3_anos'
STRATEGIES = (REFERENCE, CANDIDATE)
YEARS = 3


def fit_quarter(calendar, year, quarter, source, archived, folder):
    period = f'{year}-T{quarter}'
    origin = pd.Timestamp(year, 3 * quarter - 2, 1)
    start = origin - pd.DateOffset(years=YEARS)
    available, train, train_idx, test_idx, _ = phase5.window_data(calendar, year, quarter)
    frame = observations(available).assign(generation_mw=available[LOAD])
    pairs = frame.loc[test_idx, ['timestamp', 'cycle_id', TARGET_TONS]].reset_index(drop=True)
    pairs.insert(0, 'ano', year)
    pairs['janela'] = period
    expected = archived.loc[archived.janela.eq(period)].reset_index(drop=True)
    pd.testing.assert_frame_equal(pairs, expected[KEYS], check_exact=True)

    source_audit = read_json(source / period / 'auditoria.json')
    if (pd.Timestamp(source_audit['origem_calendario']) != origin
            or pd.Timestamp(source_audit['treino_ate']) != train.timestamp.max()
            or source_audit['n_treino'] != len(train_idx)):
        raise ValueError(f'Corte de treino da referência incompatível em {period}.')
    model_path = source / period / 'xgboost_A.joblib'
    baseline = joblib.load(model_path)
    columns = phase5.COLUMNS['A']
    test = frame.loc[test_idx, columns]
    np.testing.assert_array_equal(baseline.predict(test), expected['A'].to_numpy(),
                                  err_msg=f'Previsões de A da referência não reproduzidas em {period}.')
    pairs[REFERENCE] = expected['A']

    recent_idx = train_idx[frame.loc[train_idx, 'timestamp'].ge(start)]
    if recent_idx.empty:
        raise ValueError(f'Três anos anteriores à origem sem horas elegíveis em {period}.')
    model = clone(baseline)
    model.fit(frame.loc[recent_idx, columns], frame.loc[recent_idx, TARGET_TONS])
    pairs[CANDIDATE] = model.predict(test).astype(float)
    if not np.isfinite(pairs[CANDIDATE]).all():
        raise ValueError(f'Previsões não finitas no treino recente em {period}.')

    folder.mkdir()
    path = folder / 'xgboost_ultimos_3_anos.joblib'
    joblib.dump(model, path, compress=3)
    mlflow.log_artifact(str(path), artifact_path='modelo')
    audit = dict(janela=period, origem_calendario=origin.isoformat(),
                 fim_exclusivo_calendario=(origin + pd.DateOffset(months=3)).isoformat(),
                 inicio_calendario_ultimos_3_anos=start.isoformat(),
                 inicio_on_expansivo=frame.loc[train_idx[0], 'timestamp'].isoformat(),
                 inicio_on_ultimos_3_anos=frame.loc[recent_idx[0], 'timestamp'].isoformat(),
                 fim_on_treino=frame.loc[recent_idx[-1], 'timestamp'].isoformat(),
                 n_treino_expansivo=len(train_idx), n_treino_ultimos_3_anos=len(recent_idx),
                 n_avaliacao=len(pairs), referencia_sha256=digest(model_path),
                 run_janela_origem=source_audit['run_id'])
    return pairs, audit


def scores(paired, level, period):
    target = paired[TARGET_TONS].to_numpy()
    return [dict(nivel=level, janela=period, cenario=scenario, n=len(target),
                 **phase5.scoring(target, paired[scenario].to_numpy())) for scenario in STRATEGIES]


def run(root, reference, output_root=None):
    root, reference = Path(root).resolve(), Path(reference).expanduser().resolve()
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes da comparação de treino.')
    environment = provenance(root)
    source, summary, source_protocol, archived, source_audit = reference_run(root, reference, environment)
    calendar, manifest = load_phase5_calendar(root)
    if manifest != read_json(source / 'manifesto_dados.json'):
        raise ValueError('O calendário diverge dos dados da rodada de origem.')
    windows = [(year, quarter) for year in source_protocol['anos_avaliacao'] for quarter in range(1, 5)]
    if len(windows) != summary['janelas']:
        raise ValueError('A quantidade de janelas diverge da referência trimestral.')

    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    folder = Path(output_root or root / 'outputs/phase_05_training_window').resolve() / run_name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    protocol = dict(cenario='A', atributos=phase5.COLUMNS['A'], alvo=source_protocol['alvo'],
                    xgboost=source_protocol['xgboost'], incerteza=source_protocol['incerteza'],
                    estrategias={REFERENCE: 'Modelo expansivo arquivado de cada origem trimestral.',
                                 CANDIDATE: 'Mesmo pipeline ajustado nos três anos de calendário anteriores à origem.'},
                    recorte_treino_recente='[origem − três anos, origem), somente horas ON elegíveis.',
                    alcance='Comparação retrospectiva de Iatan 2 nas mesmas origens, horas e alvos.')
    old_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{(folder / 'mlflow.db').as_posix()}")
    try:
        experiment = mlflow.create_experiment('Iatan 2 · Fase 5 · Comprimento do treino',
                                              artifact_location=artifacts.as_uri())
        with (
            mlflow.start_run(experiment_id=experiment, run_name='Cenário A · Expansivo × últimos três anos') as parent,
            public_span('Fase 5 · Comparar comprimentos de treino', run_id=parent.info.run_id,
                              trace_destination=MlflowExperimentLocation(experiment_id=experiment)) as trace,
        ):
            mlflow.set_tags({'inference': 'retrospective', 'run_origem': source_audit['mlflow_run_id'],
                             'protocol': 'phase5_iatan_training_window_v1'})
            mlflow.log_params({'anos_treino_recente': YEARS, 'janelas': len(windows), 'cenario': 'A',
                               **source_protocol['xgboost']})
            frames, rows, audits = [], [], []
            for year, quarter in windows:
                period = f'{year}-T{quarter}'
                with (mlflow.start_run(experiment_id=experiment, run_name=period, nested=True) as child,
                      public_span('Ajustar treino recente e conferir A', attributes={'janela': period})):
                    paired, audit = fit_quarter(calendar, year, quarter, source, archived, results / period)
                    audit['run_id'] = child.info.run_id
                    mlflow.log_params(audit)
                    window_scores = scores(paired, 'trimestre', period)
                    for row in window_scores:
                        mlflow.log_metrics({f'{row["cenario"]}.{key}': row[key] for key in ('rmse', 'mae', 'vies')})
                    frames.append(paired)
                    rows.extend(window_scores)
                    audits.append(audit)
            with public_span('Consolidar previsões, métricas e contrastes pareados'):
                paired = pd.concat(frames, ignore_index=True)
                pd.testing.assert_frame_equal(paired[KEYS + [REFERENCE]],
                                              archived[KEYS + ['A']].rename(columns={'A': REFERENCE}), check_exact=True)
                for year, sample in paired.groupby('ano'):
                    rows.extend(scores(sample, 'ano', str(year)))
                rows.extend(scores(paired, 'agrupado', 'agrupado'))
                intervals = contrasts(paired, **protocol['incerteza'], pairs=((CANDIDATE, REFERENCE),), by_quarter=True)
                for row in rows:
                    if row['nivel'] != 'trimestre':
                        mlflow.log_metrics({f'{row["janela"]}.{row["cenario"]}.{key}': row[key]
                                            for key in ('rmse', 'mae', 'vies')})
                for row in intervals.loc[intervals.periodo.eq('agrupado')].itertuples():
                    mlflow.log_metrics({f'contraste.{key}.{row.bloco_dias}d': getattr(row, key)
                                        for key in ('delta_rmse', 'ic95_inferior', 'ic95_superior')})
                for name, content in {'protocolo.json': protocol, 'proveniencia.json': environment,
                                      'origem_trimestral.json': source_audit, 'manifesto_dados.json': manifest,
                                      'auditoria_trimestral.json': audits}.items():
                    write_json(results / name, content)
                paired.to_csv(results / 'previsoes_pareadas.csv', index=False)
                pd.DataFrame(rows).to_csv(results / 'metricas.csv', index=False)
                intervals.to_csv(results / 'contrastes.csv', index=False)
                for path in results.iterdir():
                    if path.is_file():
                        mlflow.log_artifact(str(path))
            report = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                          trace_id=trace.trace_id, horas_pareadas=len(paired), ajustes=len(windows),
                          janelas=len(windows), rodada_origem=reference.name,
                          mlflow_run_origem=source_audit['mlflow_run_id'])
        mlflow.flush_trace_async_logging()
        client = mlflow.MlflowClient()
        if client.get_run(report['mlflow_run_id']).info.status != 'FINISHED' or client.get_trace(report['trace_id']) is None:
            raise RuntimeError('A execução de comparação e o trace precisam estar disponíveis.')
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
