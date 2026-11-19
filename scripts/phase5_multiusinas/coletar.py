"""Obtém a coorte horária da EPA, preservando os campos originais usados."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import file_digest
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import csv
import gzip
import io
import json
import os
import re


ROOT = Path(__file__).resolve().parent
ENDPOINT = 'https://api.epa.gov/easey/streaming-services/emissions/apportioned/hourly'
FIELDS = [
    'State', 'Facility Name', 'Facility ID', 'Unit ID', 'Date', 'Hour',
    'Operating Time', 'Gross Load (MW)', 'CO2 Mass (short tons)',
    'CO2 Mass Measure Indicator', 'Primary Fuel Type', 'Unit Type',
]
EXCLUDED = [
    'co2Rate', 'co2RateMeasureFlg', 'hgControlInfo', 'noxControlInfo',
    'noxMassMeasureFlg', 'noxRateMeasureFlg', 'heatInputMeasureFlg',
    'pmControlInfo', 'secondaryFuelInfo', 'so2ControlInfo', 'so2MassMeasureFlg',
    'so2Rate', 'so2RateMeasureFlg', 'steamLoad', 'unit_id',
]


def identity(facility, unit):
    """Usa a mesma chave da triagem original, preservando o valor bruto na saída."""
    facility = str(int(facility.strip()))
    unit = re.sub(r'\.0$', '', unit.strip().upper())
    return facility, str(int(unit)) if unit.isdecimal() else unit


def cohort():
    with (ROOT / 'coorte_top20_2025.csv').open(newline='', encoding='utf-8') as source:
        rows = list(csv.DictReader(source))
    keys = {(row['facility_id'], row['unit_id']) for row in rows}
    assert len(keys) == len({key[0] for key in keys}) == len(rows) == 20
    assert ('6065', '2') in keys
    return keys


def collect(start, end, facilities, output_dir):
    keys = cohort()
    if facilities:
        known = {key[0] for key in keys}
        if not set(facilities) <= known:
            raise ValueError('Instalação não consta da coorte pré-especificada.')
        keys = {key for key in keys if key[0] in facilities}
    params = {
        'facilityId': '|'.join(sorted({key[0] for key in keys}, key=int)),
        'beginDate': f'{start}-01-01',
        'endDate': f'{end}-12-31',
        'operatingHoursOnly': 'false',
        'exclude': '|'.join(EXCLUDED),
    }
    if not facilities:
        params['locationName'] = '|'.join(sorted({key[1] for key in keys}))
    request = Request(ENDPOINT + '?' + urlencode(params), headers={
        'X-Api-Key': os.getenv('EPA_API_KEY', 'DEMO_KEY'),
        'Accept': 'text/csv',
    })
    suffix = '_' + '_'.join(sorted(set(facilities), key=int)) if facilities else ''
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f'epa_horario_{start}_{end}{suffix}.csv.gz'
    staging = target.with_suffix('.partial.gz')
    counts = Counter()
    received = 0
    excluded_units = 0
    retrieved_at = datetime.now(timezone.utc).isoformat()
    with urlopen(request, timeout=90) as response, gzip.open(
        staging, 'wt', newline='', encoding='utf-8', compresslevel=4
    ) as output:
        if response.headers.get_content_type() != 'text/csv':
            raise ValueError('A EPA não retornou CSV.')
        reader = csv.DictReader(io.TextIOWrapper(response, encoding='utf-8-sig', newline=''))
        if not set(FIELDS) <= set(reader.fieldnames or ()):
            raise ValueError(f'Campos esperados ausentes: {set(FIELDS) - set(reader.fieldnames or ())}')
        writer = csv.DictWriter(output, FIELDS, extrasaction='ignore')
        writer.writeheader()
        for row in reader:
            key = identity(row['Facility ID'], row['Unit ID'])
            if key not in keys:
                excluded_units += 1
                continue
            if any(row[field] is None for field in FIELDS):
                raise ValueError('Linha incompleta na resposta da EPA.')
            year = int(row['Date'][:4])
            if not start <= year <= end:
                raise ValueError(f'Ano fora da consulta: {year}.')
            counts[year, *key] += 1
            writer.writerow(row)
            received += 1
            if received % 100000 == 0:
                print(f'{received:,} registros da coorte recebidos', flush=True)
    if {key[0] for key in counts} != set(range(start, end + 1)):
        raise ValueError('A resposta não abrange todos os anos solicitados.')
    staging.replace(target)
    with target.open('rb') as file:
        digest = file_digest(file, 'sha256').hexdigest()
    receipt = {
        'retrieved_at_utc': retrieved_at,
        'source_url': request.full_url,
        'file': target.name,
        'sha256': digest,
        'rows': sum(counts.values()),
        'rows_from_other_units_discarded': excluded_units,
        'rows_by_unit_year': [
            {'year': year, 'facility_id': facility, 'unit_id': unit, 'rows': n}
            for (year, facility, unit), n in sorted(counts.items())
        ],
    }
    (output_dir / f'fonte_epa_{start}_{end}{suffix}.json').write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + '\n', encoding='utf-8'
    )
    print(f'{target.name}: {receipt["rows"]:,} registros selecionados', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    parser.add_argument('--facilities', nargs='+', default=[])
    parser.add_argument('--saida', type=Path, default=Path('outputs/phase_05_multiusinas'))
    args = parser.parse_args()
    if not 2021 <= args.start <= args.end <= 2025:
        parser.error('A janela deve estar entre 2021 e 2025.')
    collect(args.start, args.end, args.facilities, args.saida)
