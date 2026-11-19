"""Incerteza descritiva do delta pareado de RMSE na validação anual.

O notebook 03A.05B orienta a adaptação para blocos de calendário não
sobrepostos. Künsch (1989), DOI 10.1214/aos/1176347265, fundamenta a
reamostragem em blocos sob dependência temporal. Os intervalos são
condicionais às previsões dos modelos já ajustados.
"""

from numbers import Integral

import numpy as np
import pandas as pd


PAIRS = (("D", "C"), ("D", "A"), ("B", "A"), ("C", "B"))
TARGET = "co2_metric_tons"


def _block_draws(year, errors, scenarios, days, replicates, seed, quarter=None):
    start = pd.Timestamp(year=year, month=1 if quarter is None else 3 * quarter - 2, day=1)
    end = start + pd.DateOffset(months=12 if quarter is None else 3)
    block_length = pd.Timedelta(days=days)
    n_blocks = ((end - start).days + days - 1) // days
    blocks = ((errors["timestamp"] - start) // block_length).to_numpy(dtype=int)
    counts = np.bincount(blocks, minlength=n_blocks)
    sums = np.column_stack([
        np.bincount(blocks, weights=errors[scenario], minlength=n_blocks)
        for scenario in scenarios
    ])
    seed_parts = [seed, days, year] if quarter is None else [seed, days, year, quarter]
    rng = np.random.default_rng(np.random.SeedSequence(seed_parts))
    draws = rng.integers(0, n_blocks, size=(replicates, n_blocks), dtype=np.int32)
    return {
        "hours": counts.sum(),
        "sse": sums.sum(axis=0),
        "bootstrap_hours": counts[draws].sum(axis=1),
        "bootstrap_sse": np.column_stack([
            sums[:, col][draws].sum(axis=1) for col in range(len(scenarios))
        ]),
        "blocks": n_blocks,
        "blocks_with_on": np.count_nonzero(counts),
    }


def _contrast_rows(period, stats, scenarios, pairs, days, replicates):
    rmse = np.sqrt(stats["sse"] / stats["hours"])
    hours = stats["bootstrap_hours"]
    valid = hours > 0
    bootstrap_rmse = np.sqrt(stats["bootstrap_sse"][valid] / hours[valid, None])
    n_valid = int(valid.sum())
    for candidate, reference in pairs:
        c, r = scenarios.index(candidate), scenarios.index(reference)
        deltas = bootstrap_rmse[:, c] - bootstrap_rmse[:, r]
        lower, upper = np.quantile(deltas, [.025, .975]) if n_valid else (np.nan, np.nan)
        yield {
            "periodo": period,
            "contraste": f"{candidate}-{reference}",
            "candidata": candidate,
            "referencia": reference,
            "bloco_dias": days,
            "n_horas_on": int(stats["hours"]),
            "n_blocos": int(stats["blocks"]),
            "n_blocos_com_on": int(stats["blocks_with_on"]),
            "delta_rmse": float(rmse[c] - rmse[r]),
            "ic95_inferior": float(lower),
            "ic95_superior": float(upper),
            "replicas_validas": n_valid,
            "replicas_sem_on": replicates - n_valid,
        }


def contrasts(predictions: pd.DataFrame, block_days=(7, 1, 3), replicates=10000, seed=42,
              *, pairs=PAIRS, by_quarter=False) -> pd.DataFrame:
    """Calcula RMSE(candidata) − RMSE(referência) em t CO₂/h e IC percentil.

    Espera uma linha por hora ON elegível, com os cenários avaliados
    sobre o mesmo alvo. As datas usam o calendário horário da fonte, sem fuso.
    A âncora de cada ano é 1 de janeiro às 00h. Blocos vazios e o último
    bloco parcial integram a amostragem. As janelas trimestrais opcionais
    usam âncoras nos respectivos inícios. O agregado soma perdas e contagens
    de réplicas reamostradas separadamente em cada ano.
    """
    block_days = tuple(block_days)
    if (not block_days or any(not isinstance(d, Integral) or d < 1 for d in block_days)
            or len(set(block_days)) != len(block_days)):
        raise ValueError("Informe tamanhos distintos de bloco em dias inteiros positivos.")
    if not isinstance(replicates, Integral) or replicates < 1 or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("Informe número positivo de réplicas e semente inteira não negativa.")

    scenarios = tuple(sorted({scenario for pair in pairs for scenario in pair}))
    columns = ("timestamp", "ano", TARGET, *scenarios)
    if predictions.empty or not set(columns).issubset(predictions):
        raise ValueError("As previsões devem ter timestamp, ano, alvo e os cenários dos contrastes.")
    frame = predictions.loc[:, list(columns)].sort_values("timestamp").reset_index(drop=True)
    timestamps = frame["timestamp"]
    if (not pd.api.types.is_datetime64_any_dtype(timestamps)
            or timestamps.dt.tz is not None or timestamps.isna().any()
            or not timestamps.is_unique or not timestamps.eq(timestamps.dt.floor("h")).all()):
        raise ValueError("Os timestamps devem ser horários, únicos e sem fuso.")
    years = frame["ano"]
    if (not pd.api.types.is_integer_dtype(years) or years.isna().any()
            or not years.eq(timestamps.dt.year).all()):
        raise ValueError("A coluna ano deve corresponder ao ano dos timestamps.")
    values = frame.loc[:, [TARGET, *scenarios]].to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("O alvo e as previsões pareadas devem ser finitos.")
    errors = pd.DataFrame((values[:, 1:] - values[:, [0]]) ** 2, columns=scenarios)
    if not np.isfinite(errors.to_numpy()).all():
        raise ValueError("Os erros quadráticos devem ser finitos.")
    groups = tuple(errors.assign(timestamp=timestamps, ano=years).groupby("ano", sort=True))

    rows = []
    for days in block_days:
        days = int(days)
        annual = {
            str(year): _block_draws(int(year), group, scenarios, days, replicates, seed)
            for year, group in groups
        }
        pooled = {key: sum(stats[key] for stats in annual.values())
                  for key in next(iter(annual.values()))}
        for period, stats in {**annual, "agrupado": pooled}.items():
            rows.extend(_contrast_rows(period, stats, scenarios, pairs, days, replicates))
        if by_quarter:
            for year, group in groups:
                for quarter, window in group.groupby(group.timestamp.dt.quarter, sort=True):
                    stats = _block_draws(int(year), window, scenarios, days, replicates, seed, int(quarter))
                    rows.extend(_contrast_rows(f'{year}-T{quarter}', stats, scenarios, pairs, days, replicates))
    return pd.DataFrame(rows)
