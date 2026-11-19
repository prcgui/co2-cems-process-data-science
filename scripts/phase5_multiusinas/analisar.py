"""Compara uma unidade por usina em 2021–2025, conforme o protocolo salvo."""

import argparse
from collections import Counter, defaultdict
from datetime import date
from hashlib import file_digest
from math import isfinite
from pathlib import Path
from statistics import median, quantiles
import csv
import gzip
import json

from coletar import identity


ROOT = Path(__file__).resolve().parent
YEARS = tuple(range(2021, 2026))
TONNES_PER_SHORT_TON = 0.90718474


def file_record(path):
    with path.open('rb') as stream:
        return {'file': path.name, 'sha256': file_digest(stream, 'sha256').hexdigest()}


def number(text):
    if not text.strip():
        return None
    value = float(text)
    return value if isfinite(value) else None


def divide(num, denom):
    return num / denom if denom else None


def timestamp(row, period):
    day = date.fromisoformat(row['Date'])
    hour = int(row['Hour'])
    if day.year not in period or not 0 <= hour <= 23:
        raise ValueError(f'Data ou hora fora do protocolo: {day} {hour}.')
    return day.year, day.toordinal() * 24 + hour


def read_files(paths, selection):
    entries = defaultdict(dict)
    duplicates = Counter()
    types = defaultdict(set)
    fuels = defaultdict(set)
    hashes = []
    for path in paths:
        hashes.append(file_record(path))
        with gzip.open(path, 'rt', newline='', encoding='utf-8') as stream:
            for row in csv.DictReader(stream):
                pair = identity(row['Facility ID'], row['Unit ID'])
                if pair not in selection or row['State'] != selection[pair]['state']:
                    raise ValueError(f'Unidade ou estado fora da coorte: {pair}.')
                year, hour_key = timestamp(row, YEARS)
                key = year, *pair
                if row['Unit Type'].strip():
                    types[key].add(row['Unit Type'].strip())
                if row['Primary Fuel Type'].strip():
                    fuels[key].add(row['Primary Fuel Type'].strip())
                records = entries[key]
                if hour_key in records:
                    duplicates[key] += 1
                    records[hour_key] = None
                    continue
                records[hour_key] = (
                    number(row['Operating Time']),
                    number(row['Gross Load (MW)']),
                    number(row['CO2 Mass (short tons)']),
                    row['CO2 Mass Measure Indicator'].strip().casefold() == 'measured',
                )
    return entries, duplicates, types, fuels, hashes


def describe_year(records, year):
    expected = (date(year + 1, 1, 1) - date(year, 1, 1)).days * 24
    usable = []
    hours_invalid_optime = 0
    hours_duplicates = 0
    off_with_nonzero_load_or_mass = 0
    for hour, record in sorted(records.items()):
        if record is None:
            hours_duplicates += 1
            continue
        op, load, mass, measured = record
        if op is None or not 0 <= op <= 1:
            hours_invalid_optime += 1
            continue
        if op == 0 and (load not in (0, None) or mass not in (0, None)):
            off_with_nonzero_load_or_mass += 1
        usable.append((hour, op, load, mass, measured))

    on = [row for row in usable if row[1] > 0]
    load_rows = [row for row in on if row[2] is not None and row[2] >= 0]
    mass_rows = [row for row in on if row[3] is not None and row[3] >= 0]
    loads = [row[2] for row in load_rows]
    quantile = quantiles(loads, n=20, method='inclusive') if len(loads) >= 2 else []
    observed_mwh = sum(row[1] * row[2] for row in load_rows) if load_rows else None
    observed_co2 = sum(row[3] for row in mass_rows) * TONNES_PER_SHORT_TON if mass_rows else None
    full = len(usable) == expected
    mass_total = (observed_co2 or 0.0) if full and len(on) == len(mass_rows) else None
    mwh_total = (observed_mwh or 0.0) if full and len(on) == len(load_rows) else None
    intensity = mass_total / mwh_total if mass_total is not None and mwh_total and mwh_total > 0 else None
    startups = sum(now[0] == prev[0] + 1 and prev[1] == 0 < now[1]
                   for prev, now in zip(usable, usable[1:]))
    shutdowns = sum(now[0] == prev[0] + 1 and prev[1] > 0 and now[1] == 0
                     for prev, now in zip(usable, usable[1:]))

    return {
        'horas_esperadas': expected,
        'horas_presentes': len(records),
        'horas_faltantes': expected - len(records),
        'cobertura_horaria': len(records) / expected,
        'horas_duplicadas': hours_duplicates,
        'horas_optime_invalido': hours_invalid_optime,
        'horas_off_com_carga_ou_co2_nao_zero': off_with_nonzero_load_or_mass,
        'horas_on': len(on),
        'horas_equivalentes_on': sum(row[1] for row in on),
        'cobertura_carga_on': divide(len(load_rows), len(on)),
        'cobertura_co2_on': divide(len(mass_rows), len(on)),
        'fracao_co2_medido_on_valido': divide(sum(row[4] for row in mass_rows), len(mass_rows)),
        'carga_on_p05_mw': quantile[0] if quantile else (loads[0] if loads else None),
        'carga_on_mediana_mw': median(loads) if loads else None,
        'carga_on_p95_mw': quantile[-1] if quantile else (loads[0] if loads else None),
        'partidas_observadas': startups,
        'paradas_observadas': shutdowns,
        'co2_on_observado_t': observed_co2,
        'geracao_bruta_on_observada_mwh': observed_mwh,
        'co2_anual_t': mass_total,
        'geracao_bruta_anual_mwh': mwh_total,
        'intensidade_anual_t_co2_mwh_bruto': intensity,
    }


def write_table(path, rows):
    with path.open('w', newline='', encoding='utf-8') as output:
        writer = csv.DictWriter(output, list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({name: round(value, 9) if isinstance(value, float) else value
                             for name, value in row.items()})


def summary_by_year(rows):
    intensity_col = 'intensidade_anual_t_co2_mwh_bruto'
    summaries = []
    for year in YEARS:
        cohort_rows = [row for row in rows if row['ano'] == year]
        iatan = next(row for row in cohort_rows if row['facility_id'] == '6065')
        comparable = [row[intensity_col] for row in cohort_rows if row[intensity_col] is not None]
        others = [row[intensity_col] for row in cohort_rows
                  if row['facility_id'] != '6065' and row[intensity_col] is not None]
        summaries.append({
            'ano': year,
            'unidades_na_coorte': len(cohort_rows),
            'unidades_calendario_completo': sum(
                row['cobertura_horaria'] == 1 and not row['horas_duplicadas'] and not row['horas_optime_invalido']
                for row in cohort_rows
            ),
            'unidades_intensidade_calculavel': len(comparable),
            'iatan_horas_on': iatan['horas_on'],
            'iatan_co2_t': iatan['co2_anual_t'],
            'iatan_intensidade_t_co2_mwh_bruto': iatan[intensity_col],
            'iatan_posicao_intensidade_crescente': (1 + sum(value < iatan[intensity_col] for value in comparable)
                                                   if iatan[intensity_col] is not None else None),
            'outras_unidades_intensidade_min': min(others) if others else None,
            'outras_unidades_intensidade_mediana': median(others) if others else None,
            'outras_unidades_intensidade_max': max(others) if others else None,
        })
    return summaries


def main(paths, output):
    with (ROOT / 'coorte_top20_2025.csv').open(newline='', encoding='utf-8') as stream:
        selection = {(row['facility_id'], row['unit_id']): row for row in csv.DictReader(stream)}
    records, duplicates, types, fuels, hashes = read_files(paths, selection)
    if {key[0] for key in records} != set(YEARS):
        raise ValueError('Insuficiência de dados: forneça arquivos EPA para os cinco anos.')
    rows = []
    for year in YEARS:
        for pair, unit in selection.items():
            key = year, *pair
            obs = records.get(key, {})
            stats = describe_year(obs, year)
            rows.append({
                'ano': year,
                **unit,
                'tipo_unidade_reportado_no_ano': '; '.join(sorted(types[key])),
                'combustivel_primario_reportado_no_ano': '; '.join(sorted(fuels[key])),
                'linhas_duplicadas_excedentes': duplicates[key],
                **stats,
            })
    summaries = summary_by_year(rows)
    output.mkdir(parents=True, exist_ok=True)
    detail = output / 'comparacao_unidade_ano_2021_2025.csv'
    summary = output / 'iatan_vs_coorte_2021_2025.csv'
    write_table(detail, rows)
    write_table(summary, summaries)
    manifest = {
        'protocol': file_record(ROOT / 'protocolo_multiusinas.json'),
        'cohort': file_record(ROOT / 'coorte_top20_2025.csv'),
        'inputs': hashes,
        'outputs': [file_record(detail), file_record(summary)],
        'unidades': len(selection),
        'linhas_unidade_ano': len(rows),
        'registros_horarios': sum(row['horas_presentes'] + row['linhas_duplicadas_excedentes'] for row in rows),
        'horas_faltantes': sum(row['horas_faltantes'] for row in rows),
        'linhas_duplicadas_excedentes': sum(row['linhas_duplicadas_excedentes'] for row in rows),
        'unidades_ano_sem_registros': sum(row['horas_presentes'] == 0 for row in rows),
        'unidades_ano_intensidade_calculavel': sum(row['intensidade_anual_t_co2_mwh_bruto'] is not None for row in rows),
    }
    (output / 'manifesto_analise_multiusinas.json').write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inputs', type=Path, nargs='+')
    parser.add_argument('--saida', type=Path, default=Path('outputs/phase_05_multiusinas'))
    args = parser.parse_args()
    main(args.inputs, args.saida)
