"""Backtest multianual de Iatan 2, com a ablação de atributos do Exp33."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import joblib
import mlflow
import numpy as np
import pandas as pd
from mlflow.entities.trace_location import MlflowExperimentLocation
from mlflow.data.code_dataset_source import CodeDatasetSource
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from xgboost import XGBRegressor

from .data import LOAD, OP, digest, write_json
from .phase5_data import TARGET_TONS, load_phase5_calendar
from .phase5_uncertainty import contrasts
from .processes import ProcessModel
from .tracking import portable_path, provenance, public_span


LAGS = (1, 2, 3, 6, 12, 24)
ROLLS = (3, 6, 12, 24)
HISTORY = [f'load_{stat}_last_{n}h' for n in ROLLS for stat in ('mean', 'std')]
HISTORY += [f'load_lag_{n}h' for n in LAGS]
POSTERIOR = [f'hmm_p_{n}' for n in range(5)]
HMM = POSTERIOR + ['hmm_available', 'hmm_confidence', 'hmm_entropy']
DFG = ['proc_transition_probability', 'proc_transition_surprise', 'proc_edge_known']
COLUMNS = {
    'A': ['generation_mw'],
    'B': ['generation_mw', *HISTORY],
    'C': ['generation_mw', *HISTORY, *HMM],
    'D': ['generation_mw', *HISTORY, *HMM, *DFG],
}


def features(calendar, model):
    """Atributos do Exp33. Médias incluem a hora corrente e reiniciam no ciclo."""
    frame = model.transform(calendar)
    frame['generation_mw'] = frame[LOAD]
    on = frame[OP].gt(0)
    load = frame.loc[on, LOAD].groupby(frame.loc[on, 'cycle_id'], sort=False)
    for n in ROLLS:
        frame[f'load_mean_last_{n}h'] = load.transform(lambda x: x.rolling(n, min_periods=1).mean())
        frame[f'load_std_last_{n}h'] = load.transform(
            lambda x: x.rolling(n, min_periods=2).std(ddof=0)
        ).reindex(frame.index).fillna(0.)
    for n in LAGS:
        frame[f'load_lag_{n}h'] = load.shift(n)
    return frame[['timestamp', 'cycle_id', *COLUMNS['D']]]


def scoring(observed, prediction):
    error = prediction - observed
    return dict(rmse=float(np.sqrt(np.mean(error**2))), mae=float(np.mean(np.abs(error))),
                vies=float(np.mean(error)))


def window_data(calendar, year, quarter=None):
    start = pd.Timestamp(year, 1, 1)
    if quarter is None:
        stop = pd.Timestamp(year + 1, 1, 1)
    else:
        start += pd.DateOffset(months=3 * (quarter - 1))
        stop = start + pd.DateOffset(months=3)
    through = calendar.loc[calendar.timestamp.lt(stop)]
    broken = through[OP].gt(0) & ~np.isfinite(through[LOAD])
    # A linha continua no calendário bruto. Seu salto horário quebra a sequência no HMM/DFG.
    available = through.loc[~broken].reset_index(drop=True)
    train = available.loc[available.timestamp.lt(start)]
    eligible = available[OP].gt(0) & np.isfinite(available[[LOAD, TARGET_TONS]]).all(axis=1)
    train_idx = available.index[eligible & available.timestamp.lt(start)]
    test_idx = available.index[eligible & available.timestamp.ge(start)]
    if train_idx.empty or test_idx.empty or train.timestamp.iloc[-1] >= available.timestamp.iloc[test_idx[0]]:
        period = str(year) if quarter is None else f'{year}-T{quarter}'
        raise ValueError(f'Corte temporal inválido em {period}.')
    return available, train, train_idx, test_idx, through.loc[broken, 'timestamp']


def fit_process(train, settings, folder):
    process = ProcessModel(**settings).fit(train)
    history = np.asarray(process.hmm.monitor_.history)
    if len(history) < 2 or not np.isfinite(history).all():
        raise RuntimeError('Histórico inválido de log-verossimilhança do HMM.')
    for parameter in (process.hmm.startprob_, process.hmm.transmat_, process.hmm.means_, process.hmm.covars_):
        if not np.isfinite(parameter).all():
            raise RuntimeError('Parâmetros não finitos no HMM.')
    if process.train_end != train.timestamp.max() or process.training_events.end.max() > process.train_end:
        raise RuntimeError('O log do DFG avançou além do treino.')
    increment = float(history[-1] - history[-2])
    details = dict(process.audit, incremento_final=increment,
                   convergencia_confirmada=bool(0 <= increment < process.hmm.tol
                                               and process.hmm.monitor_.iter < process.hmm.n_iter),
                   max_iter=process.hmm.n_iter)
    graph = pd.DataFrame([(a, b, n) for (a, b), n in sorted(process.edges.items())],
                         columns=['origem', 'destino', 'frequencia'])
    graph.to_csv(folder / 'dfg_treino.csv', index=False)
    process.training_events.to_csv(folder / 'log_eventos_treino.csv', index=False)
    joblib.dump(process, folder / 'representacao_treino.joblib', compress=3)
    return process, details


def log_sample(frame, index, cols, source, name, role):
    # O manifesto é um artefato da execução. Seu hash identifica o insumo sem
    # serializar o URI absoluto da máquina que executou o experimento.
    origin = CodeDatasetSource({'manifest': Path(source).name, 'sha256': digest(source)})
    dataset = mlflow.data.from_pandas(frame.loc[index, ['timestamp', *cols, TARGET_TONS]],
                                     source=origin, name=name, targets=TARGET_TONS)
    mlflow.log_input(dataset, context=role, tags={'horas_on': str(len(index))})


def fit_year(calendar, year, protocol, folder, manifest_path, quarter=None):
    available, train, train_idx, test_idx, broken = window_data(calendar, year, quarter)
    period = str(year) if quarter is None else f'{year}-T{quarter}'
    span_name = 'Janela anual' if quarter is None else 'Janela trimestral'
    period_tags = {} if quarter is None else {'janela': period, 'nivel': 'trimestre'}
    folder.mkdir()
    experiment = mlflow.active_run().info.experiment_id
    with mlflow.start_run(experiment_id=experiment, run_name=period, nested=True) as run, public_span(
        span_name, attributes={'ano': year, 'run_id': run.info.run_id, **period_tags}
    ) as year_span:
        with public_span('Ajustar escalonador, HMM e DFG'):
            process, diagnostics = fit_process(train, protocol['hmm'], folder)
        with public_span('Construir e auditar atributos causais'):
            frame = features(available, process)
            halfway = int(test_idx[len(test_idx) // 2]) + 1
            for stop in (len(train), halfway):
                pd.testing.assert_frame_equal(features(available.iloc[:stop], process), frame.iloc[:stop],
                                              rtol=1e-12, atol=1e-12)
            np.testing.assert_allclose(frame.loc[test_idx, POSTERIOR].sum(axis=1),
                                       frame.loc[test_idx, 'hmm_available'], atol=1e-12)
            if not np.isfinite(frame.loc[test_idx, HMM + DFG]).all().all():
                raise ValueError(f'Atributos de processo inválidos em {period}.')
            frame[TARGET_TONS] = available[TARGET_TONS]
        dates = frame.timestamp
        audit = dict(ano=year, treino_inicio=dates.iloc[train_idx[0]], treino_ate=train.timestamp.iloc[-1],
                     avaliacao_inicio=dates.iloc[test_idx[0]], avaliacao_fim=dates.iloc[test_idx[-1]],
                     n_treino=len(train_idx), n_avaliacao=len(test_idx), n_ciclos=int(frame.loc[test_idx, 'cycle_id'].nunique()),
                     rupturas_por_falta_de_carga=broken.astype(str).tolist(), prefixos_verificados=2,
                     posterior_normalizado=True, run_id=run.info.run_id, hmm=diagnostics, **period_tags)
        if quarter is not None:
            origin = pd.Timestamp(year, 3 * quarter - 2, 1)
            audit.update(origem_calendario=origin, fim_exclusivo_calendario=origin + pd.DateOffset(months=3))
        write_json(folder / 'auditoria.json', audit)
        mlflow.log_params({key: audit[key] for key in ('ano', 'treino_ate', 'avaliacao_inicio', 'avaliacao_fim',
                                                      'n_treino', 'n_avaliacao', 'n_ciclos')})
        mlflow.log_params({'hmm_convergiu': diagnostics['convergencia_confirmada'],
                           'hmm_iteracoes': diagnostics['iterations'], **period_tags})
        if quarter is not None:
            mlflow.log_params({key: str(audit[key]) for key in ('origem_calendario', 'fim_exclusivo_calendario')})
        log_sample(frame, train_idx, COLUMNS['D'], manifest_path, f'iatan_{period}_treino', 'training')
        log_sample(frame, test_idx, COLUMNS['D'], manifest_path, f'iatan_{period}_avaliacao', 'evaluation')
        year_span.set_attributes({'horas_treino': len(train_idx), 'horas_avaliadas': len(test_idx),
                                  'hmm_convergiu': diagnostics['convergencia_confirmada']})
        pairs = frame.loc[test_idx, ['timestamp', 'cycle_id', TARGET_TONS]].copy()
        pairs.insert(0, 'ano', year)
        if quarter is not None:
            pairs['janela'] = period
        target = pairs[TARGET_TONS].to_numpy()
        rows = []
        for scenario, cols in COLUMNS.items():
            with mlflow.start_run(experiment_id=experiment, run_name=scenario, nested=True) as child, public_span(
                'Ajustar e avaliar cenário', attributes={'ano': year, 'cenario': scenario, 'run_id': child.info.run_id,
                                                       **period_tags}
            ):
                model = make_pipeline(SimpleImputer(strategy='median', keep_empty_features=True),
                                      XGBRegressor(**protocol['xgboost']))
                model.fit(frame.loc[train_idx, cols], frame.loc[train_idx, TARGET_TONS])
                prediction = model.predict(frame.loc[test_idx, cols]).astype(float)
                if not np.isfinite(prediction).all():
                    raise RuntimeError(f'Previsões inválidas em {period}/{scenario}.')
                pairs[scenario] = prediction
                scores = scoring(target, prediction)
                mlflow.log_metrics(scores)
                mlflow.log_params({'cenario': scenario, 'n_atributos': len(cols),
                                   'n_treino': len(train_idx), 'n_avaliacao': len(test_idx), **period_tags,
                                   **protocol['xgboost']})
                mlflow.log_dict({'ordem_dos_atributos': cols}, 'atributos.json')
                path = folder / f'xgboost_{scenario}.joblib'
                joblib.dump(model, path, compress=3)
                mlflow.log_artifact(str(path), artifact_path='modelo')
                rows.append(dict(ano=year, cenario=scenario, n=len(pairs), **scores, run_id=child.info.run_id,
                                 **period_tags))
        pairs.to_csv(folder / 'previsoes_pareadas.csv', index=False)
        for filename in ('auditoria.json', 'dfg_treino.csv', 'log_eventos_treino.csv',
                         'representacao_treino.joblib', 'previsoes_pareadas.csv'):
            mlflow.log_artifact(str(folder / filename))
    return pairs, rows, audit


def run(root, output_root=None, *, cadence='annual'):
    if cadence not in ('annual', 'quarterly'):
        raise ValueError('Use cadence="annual" ou cadence="quarterly".')
    root = Path(root).resolve()
    protocol_path = root / 'configs' / 'phase5_iatan.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    quarterly = cadence == 'quarterly'
    default_output = 'phase_05_quarterly' if quarterly else 'phase_05_multiyear'
    folder = Path(output_root or root / 'outputs' / default_output).resolve() / run_name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    protocol['atributos'] = COLUMNS
    protocol['sha256_config'] = digest(protocol_path)
    if quarterly:
        protocol.update(cadencia='trimestral', cortes=(
            'Treino expansivo até a hora anterior a cada origem em janeiro, abril, julho e outubro. '
            'Avaliação no trimestre civil seguinte à origem, no relógio da fonte.'
        ), alcance=(
            'Backtest retrospectivo em Iatan 2, nos mesmos anos e horas elegíveis da rodada anual. '
            'Avaliações trimestrais disjuntas, com treinos sobrepostos.'
        ))
    write_json(results / 'protocolo.json', protocol)
    write_json(results / 'proveniencia.json', provenance(root))
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes de iniciar a Fase 5.')
    old_uri = mlflow.get_tracking_uri()
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    mlflow.set_tracking_uri(f"sqlite:///{(folder / 'mlflow.db').as_posix()}")
    try:
        experiment_name = ('Iatan 2 · Fase 5 · Origens trimestrais' if quarterly
                           else 'Iatan 2 · Fase 5 · Validação multianual')
        experiment = mlflow.create_experiment(experiment_name, artifact_location=artifacts.as_uri())
        with mlflow.start_run(experiment_id=experiment, run_name='A/B/C/D · 2023 a 2025',
                              log_system_metrics=True) as parent, public_span(
            'Fase 5 · Iatan 2', run_id=parent.info.run_id,
            trace_destination=MlflowExperimentLocation(experiment_id=experiment)
        ) as trace:
            mlflow.set_tags({'unit': protocol['unidade'], 'protocol': 'phase5_iatan_v1', 'inference': 'retrospective'})
            if quarterly:
                mlflow.set_tags({'cadence': cadence, 'protocol': 'phase5_iatan_quarterly_v1'})
            mlflow.log_artifact(str(results / 'protocolo.json'))
            mlflow.log_artifact(str(results / 'proveniencia.json'))
            with public_span('Validar séries anuais da EPA'):
                calendar, manifest = load_phase5_calendar(root)
                manifest_path = results / 'manifesto_dados.json'
                write_json(manifest_path, manifest)
                mlflow.log_artifact(str(manifest_path))
            frames, rows, audits = [], [], []
            quarters = (1, 2, 3, 4) if quarterly else (None,)
            windows = [(year, quarter) for year in protocol['anos_avaliacao'] for quarter in quarters]
            for year, quarter in windows:
                period = str(year) if quarter is None else f'{year}-T{quarter}'
                pairs, metrics, audit = fit_year(calendar, year, protocol, results / period, manifest_path, quarter)
                frames.append(pairs)
                rows.extend(metrics)
                audits.append(audit)
                print(period, 'concluído', {x['cenario']: round(x['rmse'], 4) for x in metrics}, flush=True)
            n_fits = len(rows)
            predictions = pd.concat(frames, ignore_index=True)
            if not predictions.timestamp.is_unique:
                raise RuntimeError('As janelas de avaliação devem ser disjuntas.')
            if quarterly:
                for year, group in predictions.groupby('ano', sort=False):
                    available, _, _, annual_idx, _ = window_data(calendar, year)
                    expected = available.loc[annual_idx, ['timestamp', TARGET_TONS]].reset_index(drop=True)
                    pd.testing.assert_frame_equal(group[['timestamp', TARGET_TONS]].reset_index(drop=True), expected)
            with public_span('Consolidar resultados e bootstrap pareado'):
                if quarterly:
                    for year, group in predictions.groupby('ano', sort=False):
                        for scenario in COLUMNS:
                            scores = scoring(group[TARGET_TONS].to_numpy(), group[scenario].to_numpy())
                            rows.append(dict(ano=year, cenario=scenario, n=len(group), **scores,
                                             janela=str(year), nivel='ano'))
                            mlflow.log_metrics({f'{year}_{scenario}_{name}': value for name, value in scores.items()})
                for scenario in COLUMNS:
                    scores = scoring(predictions[TARGET_TONS].to_numpy(), predictions[scenario].to_numpy())
                    rows.append(dict(ano='agrupado', cenario=scenario, n=len(predictions), **scores))
                    if quarterly:
                        rows[-1].update(janela='agrupado', nivel='agrupado')
                    mlflow.log_metrics({f'{scenario}_{name}': value for name, value in scores.items()})
                intervals = contrasts(predictions, **protocol['incerteza'])
                intervals.to_csv(results / 'contrastes.csv', index=False)
                pd.DataFrame(rows).to_csv(results / 'metricas.csv', index=False)
                predictions.to_csv(results / 'previsoes_pareadas.csv', index=False)
                audit_name = 'auditoria_trimestral.json' if quarterly else 'auditoria_anual.json'
                write_json(results / audit_name, audits)
                for name in ('contrastes.csv', 'metricas.csv', 'previsoes_pareadas.csv', audit_name):
                    mlflow.log_artifact(str(results / name))
            summary = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                           trace_id=trace.trace_id, horas_pareadas=len(predictions), ajustes=n_fits,
                           resultados=rows, convergencia={a.get('janela', a['ano']): a['hmm']['convergencia_confirmada']
                                                         for a in audits})
            if quarterly:
                summary.update(cadencia='trimestral', janelas=len(windows))
        mlflow.flush_trace_async_logging()
        client = mlflow.MlflowClient()
        if client.get_run(summary['mlflow_run_id']).info.status != 'FINISHED':
            raise RuntimeError('Execução de síntese sem término confirmado.')
        if client.get_trace(summary['trace_id']) is None:
            raise RuntimeError('O trace da Fase 5 não foi preservado.')
        write_json(results / 'resumo.json', summary)
        client.log_artifact(summary['mlflow_run_id'], str(results / 'resumo.json'))
    finally:
        mlflow.flush_trace_async_logging()
        mlflow.set_tracking_uri(old_uri)
    print('Resultados e MLflow:', portable_path(folder, root), flush=True)
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path.cwd())
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--cadence', choices=('annual', 'quarterly'), default='annual')
    args = parser.parse_args()
    run(args.root, args.output_root, cadence=args.cadence)
