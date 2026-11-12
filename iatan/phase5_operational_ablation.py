"""Ablação trimestral de rampa e religamento na estimação de CO₂ em Iatan 2."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import mlflow
from mlflow.entities.trace_location import MlflowExperimentLocation
import numpy as np
import pandas as pd

from . import phase5
from .data import LOAD, OP, write_json
from .phase5_ablation import consolidate, fit_window, read_json, reference_run
from .phase5_data import load_phase5_calendar
from .tracking import portable_path, provenance, public_span


OPERATIONAL_COLUMNS = ['rampa_assinada_mw', 'horas_desde_religamento']
COLUMNS = {
    'A': phase5.COLUMNS['A'],
    'R': [*phase5.COLUMNS['A'], *OPERATIONAL_COLUMNS],
    'RH': [*phase5.COLUMNS['A'], *OPERATIONAL_COLUMNS, *phase5.HMM],
    'RD': [*phase5.COLUMNS['A'], *OPERATIONAL_COLUMNS, *phase5.DFG],
}
PAIRS = (('R', 'A'), ('RH', 'A'), ('RD', 'A'), ('RH', 'R'), ('RD', 'R'))


def operational_features(calendar):
    """Rampa e idade ON causais, indexadas pela hora do calendário bruto."""
    time = calendar['timestamp']
    index = pd.DatetimeIndex(time, name='timestamp')
    if index.hasnans or not index.is_unique or not index.is_monotonic_increasing:
        raise ValueError('O calendário operacional deve ter horas únicas, válidas e em ordem.')

    op = calendar[OP]
    on = op.gt(0).fillna(False)
    consecutive = time.diff().eq(pd.Timedelta(hours=1))
    continuous_on = consecutive & on & on.shift(fill_value=False)
    load = calendar[LOAD].astype(float)
    ramp = load.where(np.isfinite(load)).diff().where(continuous_on)

    restart = time.where(consecutive & on & op.shift().eq(0).fillna(False))
    segments = (~continuous_on).cumsum()
    # Uma lacuna ou começo de série em ON não estabelece um religamento.
    start = restart.groupby(segments, sort=False).ffill()
    elapsed = (time - start).dt.total_seconds().div(3600)
    return pd.DataFrame(dict(rampa_assinada_mw=ramp.to_numpy(),
                             horas_desde_religamento=elapsed.to_numpy()), index=index)


def audit_prefixes(calendar, features, windows):
    for year, quarter in windows:
        origin = pd.Timestamp(year, 3 * quarter - 2, 1)
        for cut in (origin, origin + pd.DateOffset(months=1)):
            stop = calendar.timestamp.searchsorted(cut)
            pd.testing.assert_frame_equal(operational_features(calendar.iloc[:stop]), features.iloc[:stop],
                                          check_exact=True)


def run(root, reference, output_root=None):
    """Avalia R, RH e RD nas horas arquivadas da rodada trimestral A–D."""
    root, reference = Path(root).resolve(), Path(reference).expanduser().resolve()
    if mlflow.active_run() is not None:
        raise RuntimeError('Encerre a execução ativa do MLflow antes da ablação operacional.')
    environment = provenance(root)
    source, summary, protocol, expected, source_audit = reference_run(root, reference, environment)
    calendar, manifest = load_phase5_calendar(root)
    if manifest != read_json(source / 'manifesto_dados.json'):
        raise ValueError('Os dados anuais divergem do manifesto da rodada trimestral.')
    windows = [(year, quarter) for year in protocol['anos_avaliacao'] for quarter in range(1, 5)]
    if len(windows) != summary['janelas']:
        raise ValueError('O protocolo e a referência divergem na quantidade de janelas.')

    protocol.update(atributos=COLUMNS, contrastes=[f'{candidate}-{base}' for candidate, base in PAIRS],
                    contraste_principal='R-A', contraste_hmm='RH-R', contraste_dfg='RD-R',
                    rampa_regra='Carga atual menos a anterior quando ambas são válidas e ON em horas consecutivas.',
                    religamento_regra='Horas desde OFF → ON observado em horas consecutivas, com zero na primeira ON.',
                    faltantes_regra='Rampa sem par válido e idade sem religamento conhecido permanecem ausentes.',
                    elegibilidade='Mesmas horas ON elegíveis da referência trimestral.',
                    hmm_regra='Reaplicar a representação HMM/DFG da referência ajustada no treino de cada janela.')
    protocol['referencias']['rampa'] = 'Gu, Sward e Zhang (2023), Eq. 2. https://doi.org/10.1039/D3VA00191A'
    del protocol['contraste_pacote_completo']
    name = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    folder = Path(output_root or root / 'outputs/phase_05_operational_ablation').resolve() / name
    results = folder / 'resultados'
    results.mkdir(parents=True)
    files = {'protocolo.json': protocol, 'proveniencia.json': environment,
             'manifesto_dados.json': manifest, 'origem_trimestral.json': source_audit}
    for filename, value in files.items():
        write_json(results / filename, value)

    old_uri = mlflow.get_tracking_uri()
    artifacts = folder / 'mlflow_artifacts'
    artifacts.mkdir()
    mlflow.set_tracking_uri(f"sqlite:///{(folder / 'mlflow.db').as_posix()}")
    try:
        experiment = mlflow.create_experiment('Iatan 2 · Fase 5 · Rampa e religamento',
                                              artifact_location=artifacts.as_uri())
        with (
            mlflow.start_run(experiment_id=experiment, run_name='A/R/RH/RD · 2023 a 2025') as parent,
            public_span('Fase 5 · Ablação operacional', run_id=parent.info.run_id,
                              trace_destination=MlflowExperimentLocation(experiment_id=experiment)) as trace,
        ):
            mlflow.set_tags({'unit': protocol['unidade'], 'protocol': 'phase5_iatan_operational_ablation_v1',
                             'inference': 'retrospective', 'rodada_origem': reference.name,
                             'run_origem': summary['mlflow_run_id']})
            for filename in files:
                mlflow.log_artifact(str(results / filename))
            with public_span('Construir rampa e religamento e conferir prefixos temporais'):
                operational = operational_features(calendar)
                audit_prefixes(calendar, operational, windows)
                mlflow.log_param('prefixos_operacionais_verificados', 2 * len(windows))
            frames, rows, audits = [], [], []
            for year, quarter in windows:
                period = f'{year}-T{quarter}'
                pairs, metrics, audit = fit_window(calendar, operational, year, quarter, source, expected, protocol,
                                                   results / period, results / 'manifesto_dados.json', scenarios=COLUMNS)
                frames.append(pairs)
                rows.extend(metrics)
                audits.append(audit)
                print(period, 'concluído', {x['cenario']: round(x['rmse'], 4) for x in metrics}, flush=True)
            predictions = pd.concat(frames, ignore_index=True)
            with public_span('Consolidar resultados e bootstrap pareado'):
                consolidate(results, predictions, expected, rows, audits, protocol, scenarios=COLUMNS, pairs=PAIRS)
            report = dict(status='FINISHED', mlflow_run_id=parent.info.run_id, experimento=experiment,
                          trace_id=trace.trace_id, horas_pareadas=len(predictions), ajustes=3 * len(windows),
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
