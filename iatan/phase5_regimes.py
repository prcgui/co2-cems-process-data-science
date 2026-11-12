"""Estratifica as previsões pareadas do Notebook 06 por condição operacional."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import mlflow
from mlflow.entities.trace_location import MlflowExperimentLocation
import numpy as np
import pandas as pd

from .data import LOAD, OP, digest, write_json
from .phase5 import scoring
from .phase5_ablation import COLUMNS, KEYS, read_json
from .phase5_data import TARGET_TONS, load_phase5_calendar
from .phase5_uncertainty import contrasts
from .processes import observations
from .tracking import portable_path, provenance, public_span


SCENARIOS = ('A', 'E', 'F')
PAIRS = (('E', 'A'), ('F', 'A'))
GROUPS = {
    'geral': ('todas',),
    'carga': ('baixa', 'media', 'alta'),
    'variacao_20': ('estavel', 'rampa', 'sem_anterior_valido'),
    'variacao_p90': ('estavel', 'rampa', 'sem_anterior_valido'),
}


def load_reference(root, reference):
    source = reference / 'resultados'
    summary = read_json(source / 'resumo.json')
    protocol = read_json(source / 'protocolo.json')
    if (summary['status'] != 'FINISHED' or summary['cadencia'] != 'trimestral'
            or any(protocol['atributos'][scenario] != COLUMNS[scenario] for scenario in SCENARIOS)):
        raise ValueError('Indique a ablação trimestral concluída do Notebook 06.')
    calendar, manifest = load_phase5_calendar(root)
    if manifest != read_json(source / 'manifesto_dados.json'):
        raise ValueError('O calendário diverge dos dados da rodada de origem.')
    paths = ('previsoes_pareadas.csv', 'resumo.json', 'protocolo.json', 'manifesto_dados.json',
             'auditoria_trimestral.json', 'origem_trimestral.json')
    hashes = {name: digest(source / name) for name in paths}
    inputs = [*KEYS, *SCENARIOS]
    predictions = pd.read_csv(source / paths[0], usecols=inputs, parse_dates=['timestamp'],
                              float_precision='round_trip')[inputs]
    if (len(predictions) != summary['horas_pareadas'] or not predictions.timestamp.is_unique
            or not np.isfinite(predictions[list(SCENARIOS)].to_numpy()).all()):
        raise ValueError('As previsões de origem devem ter horas únicas e valores finitos.')
    origin = dict(rodada=reference.name, mlflow_run_id=summary['mlflow_run_id'],
                  trace_id=summary['trace_id'], arquivos_sha256=hashes, convergencia=summary['convergencia'])
    return calendar, manifest, predictions, protocol, origin


def classify(calendar, predictions, source_protocol):
    # Mesma ruptura das sequências do Notebook 06, conservando o relógio dos dados.
    available = observations(calendar.loc[~(calendar[OP].gt(0) & calendar[LOAD].isna())])
    eligible = available[OP].gt(0) & np.isfinite(available[[LOAD, TARGET_TONS]]).all(axis=1)
    years = source_protocol['anos_avaliacao']
    cutoff = pd.Timestamp(min(years), 1, 1)
    train = available.loc[eligible & available.timestamp.lt(cutoff)]
    sample = available.loc[eligible & available.timestamp.dt.year.isin(years)].reset_index(drop=True)
    sample['ano'] = sample.timestamp.dt.year.astype('int64')
    sample['janela'] = sample.ano.astype(str) + '-T' + sample.timestamp.dt.quarter.astype(str)
    pd.testing.assert_frame_equal(predictions[KEYS], sample[KEYS], check_exact=True)

    low, high = train[LOAD].quantile([1 / 3, 2 / 3]).to_numpy()
    ramp20 = float(source_protocol['hmm']['ramp_threshold'])
    ramp90 = train.hmm_delta.abs().quantile(.90)
    if not np.isfinite([low, high, ramp20, ramp90]).all() or not (low < high and ramp20 == 20 and ramp90 >= 0):
        raise ValueError('Limiares de estratificação inválidos para o protocolo.')
    paired = predictions.assign(generation_mw=sample[LOAD], delta_mw_h=sample.hmm_delta, geral='todas')
    paired['carga'] = np.select([paired.generation_mw.le(low), paired.generation_mw.le(high)],
                                ['baixa', 'media'], default='alta')
    for label, threshold in (('variacao_20', ramp20), ('variacao_p90', ramp90)):
        paired[label] = np.select([paired.delta_mw_h.isna(), paired.delta_mw_h.abs().gt(threshold)],
                                   ['sem_anterior_valido', 'rampa'], default='estavel')
    limits = dict(fim_exclusivo_treino=cutoff.isoformat(), n_treino=len(train),
                  n_treino_com_delta=int(train.hmm_delta.notna().sum()),
                  tercil_inferior_mw=float(low), tercil_superior_mw=float(high),
                  rampa_protocolo_mw_h=ramp20, rampa_p90_treino_mw_h=float(ramp90))
    return paired, limits


def evaluate(paired, uncertainty):
    rows = []
    intervals = []
    for dimension, groups in GROUPS.items():
        if not set(paired[dimension]).issubset(groups):
            raise ValueError(f'Rótulo operacional inesperado em {dimension}.')
        for group in groups:
            sample = paired.loc[paired[dimension].eq(group)]
            if sample.empty:
                continue
            periods = [('agrupado', sample), *((str(year), rows) for year, rows in sample.groupby('ano'))]
            for period, period_sample in periods:
                y = period_sample[TARGET_TONS].to_numpy()
                for scenario in SCENARIOS:
                    rows.append(dict(analise=dimension, grupo=group, periodo=period, cenario=scenario, n_horas=len(y),
                                     **scoring(y, period_sample[scenario].to_numpy())))
            result = contrasts(sample, **uncertainty, pairs=PAIRS)
            intervals.append(result.assign(analise=dimension, grupo=group))
    return pd.DataFrame(rows), pd.concat(intervals, ignore_index=True)


def run(root, reference, output_root=None):
    root, reference = Path(root).resolve(), Path(reference).expanduser().resolve()
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes da análise de regimes.')
    run_name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    folder = Path(output_root or root / 'outputs/phase_05_regimes').resolve() / run_name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    old_uri = mlflow.get_tracking_uri()
    mlflow.set_tracking_uri(f"sqlite:///{(folder / 'mlflow.db').as_posix()}")
    try:
        experiment = mlflow.create_experiment('Iatan 2 · Fase 5 · Faixas de carga e rampas',
                                              artifact_location=artifacts.as_uri())
        with (
            mlflow.start_run(experiment_id=experiment, run_name='A × HMM × DFG por condição operacional') as parent,
            public_span('Fase 5 · Análise por condição operacional', run_id=parent.info.run_id,
                              trace_destination=MlflowExperimentLocation(experiment_id=experiment)) as trace,
        ):
            with public_span('Conferir o calendário e as previsões de origem'):
                calendar, manifest, predictions, source_protocol, origin = load_reference(root, reference)
            with public_span('Fixar limiares e estratificar as horas pareadas'):
                paired, limits = classify(calendar, predictions, source_protocol)
            with public_span('Calcular métricas e intervalos pareados por grupo'):
                metrics, intervals = evaluate(paired, source_protocol['incerteza'])
            protocol = dict(cenarios={scenario: COLUMNS[scenario] for scenario in SCENARIOS},
                            alvo=source_protocol['alvo'], limites=limits, grupos=GROUPS,
                            carga='Tercis fixos da carga nas horas elegíveis anteriores à primeira origem.',
                            rampa='Delta de carga entre horas ON consecutivas com carga finita. Rampa se |delta| > limiar.',
                            variacao_20='Limiar de 20 MW/h já previsto na Fase 5.',
                            variacao_p90='Sensibilidade com p90 do delta absoluto no treino anterior à primeira origem.',
                            incerteza=source_protocol['incerteza'], interpretacao_ic=source_protocol['interpretacao_ic'],
                            escopo='Análise retrospectiva das mesmas previsões, sem novos ajustes.',
                            referencia='Huang et al. (2027), seção 4.3.3 e Tabela 8. https://doi.org/10.1016/j.epsr.2026.114351')
            mlflow.set_tags({'protocol': 'phase5_iatan_regimes_v1', 'inference': 'retrospective',
                             'rodada_origem': origin['rodada'], 'run_origem': origin['mlflow_run_id']})
            mlflow.log_params({'horas_pareadas': len(paired), 'ajustes_novos': 0, **limits})
            for row in metrics.loc[metrics.periodo.eq('agrupado')].itertuples():
                prefix = f'{row.analise}.{row.grupo}.{row.cenario}'
                mlflow.log_metrics({f'{prefix}.{name}': getattr(row, name) for name in ('n_horas', 'rmse', 'mae', 'vies')})
            for row in intervals.loc[intervals.periodo.eq('agrupado') & intervals.bloco_dias.eq(7)].itertuples():
                prefix = f'{row.analise}.{row.grupo}.{row.contraste}'
                mlflow.log_metrics({f'{prefix}.{name}': getattr(row, name)
                                    for name in ('delta_rmse', 'ic95_inferior', 'ic95_superior')})
            write_json(results / 'protocolo.json', protocol)
            write_json(results / 'origem_ablacao.json', origin)
            write_json(results / 'manifesto_dados.json', manifest)
            write_json(results / 'proveniencia.json', provenance(root))
            paired.to_csv(results / 'previsoes_estratificadas.csv', index=False)
            metrics.to_csv(results / 'metricas.csv', index=False)
            intervals.to_csv(results / 'contrastes.csv', index=False)
            mlflow.log_artifacts(str(results))
            report = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                          trace_id=trace.trace_id, horas_pareadas=len(paired), ajustes=0,
                          rodada_origem=origin['rodada'], mlflow_run_origem=origin['mlflow_run_id'])
        mlflow.flush_trace_async_logging()
        client = mlflow.MlflowClient()
        if client.get_run(report['mlflow_run_id']).info.status != 'FINISHED' or client.get_trace(report['trace_id']) is None:
            raise RuntimeError('A execução de regimes e o trace precisam estar disponíveis.')
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
    parser.add_argument('--reference', type=Path, required=True, help='Pasta da ablação concluída do Notebook 06.')
    parser.add_argument('--output-root', type=Path)
    args = parser.parse_args()
    run(args.root, args.reference, args.output_root)
