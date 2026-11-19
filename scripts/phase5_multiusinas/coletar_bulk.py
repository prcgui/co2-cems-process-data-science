"""Extrai instalações do CSV estadual CAMPD por intervalos HTTP anônimos."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from hashlib import file_digest, sha256
from urllib.request import Request, urlopen
import csv
import gzip
import io
import json
import re

from coletar import FIELDS, ROOT, identity


BASE_URL = 'https://api.epa.gov/easey/bulk-files/emissions/hourly/state'


class StateCsv:
    def __init__(self, state, year):
        self.url = f'{BASE_URL}/emissions-hourly-{year}-{state.lower()}.csv'
        self.etag = None
        self.size = None
        initial = self.get(0, 8191)
        self.header_end = initial.index(b'\n') + 1
        self.header = next(csv.reader([initial[:self.header_end].decode('utf-8-sig').rstrip('\r\n')]))
        if not set(FIELDS) <= set(self.header):
            raise ValueError(f'Cabeçalho EPA inesperado: {self.url}.')
        self.facility_index = self.header.index('Facility ID')
        self.probes = {}

    def get(self, low, high):
        request = Request(self.url, headers={'Range': f'bytes={low}-{high}'})
        with urlopen(request, timeout=35) as response:
            match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
            if response.status != 206 or not match:
                raise ValueError(f'Resposta sem intervalo válido: {self.url}.')
            first, last, size = map(int, match.groups())
            etag = response.headers.get('ETag')
            if first != low or last != min(high, size - 1):
                raise ValueError('Os bytes recebidos divergem do intervalo solicitado.')
            if self.size is not None and (self.size != size or self.etag != etag):
                raise ValueError('O arquivo estadual mudou durante a extração.')
            self.etag, self.size = etag, size
            payload = response.read()
        if len(payload) != last - first + 1:
            raise ValueError('O servidor interrompeu um intervalo antes do fim.')
        return payload

    def probe(self, offset):
        if offset not in self.probes:
            sample = self.get(offset, min(offset + 8191, self.size - 1))
            _, _, following = sample.partition(b'\n')
            if not following:
                raise ValueError('Não foi possível isolar uma linha completa.')
            start = offset + len(sample) - len(following)
            values = next(csv.reader([following.splitlines()[0].decode('utf-8')]))
            self.probes[offset] = (start, int(values[self.facility_index]))
        return self.probes[offset]

    def bracket(self, target):
        low, high = self.header_end, self.size
        while high - low > 524288:
            start, facility = self.probe((low + high) // 2)
            if facility < target:
                low = start
            else:
                high = start
        return low, high

    def extract(self, facility, unit, cached):
        if cached:
            if (self.url, self.etag, self.size) != (
                cached['source_url'], cached['etag'], cached['full_source_bytes']
            ):
                raise ValueError('O arquivo estadual diverge do manifesto anterior.')
            low, high = cached['byte_start'], cached['byte_end'] + 1
        else:
            low, _ = self.bracket(int(facility))
            _, high = self.bracket(int(facility) + 1)
            sampled = [facility_id for _, facility_id in sorted(self.probes.values())]
            if sampled != sorted(sampled):
                raise ValueError(f'Arquivo estadual fora da ordem esperada: {self.url}.')
        payload = self.get(low, high - 1)
        digest = sha256(payload).hexdigest()
        if cached and digest != cached['sha256_source_range']:
            raise ValueError('O intervalo diverge do manifesto anterior.')
        selected = []
        prior = -1
        with io.TextIOWrapper(io.BytesIO(payload), encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream, self.header):
                facility_number = int(row['Facility ID'])
                if facility_number < prior:
                    raise ValueError(f'Bloco do CSV fora de ordem: {self.url}.')
                prior = facility_number
                if identity(row['Facility ID'], row['Unit ID']) == (facility, unit):
                    selected.append({field: row[field] for field in FIELDS})
        return selected, {
            'source_url': self.url,
            'etag': self.etag,
            'full_source_bytes': self.size,
            'byte_start': low,
            'byte_end': high - 1,
            'sha256_source_range': digest,
            'facility_id': facility,
            'unit_id': unit,
            'unit_ids_raw': sorted({row['Unit ID'] for row in selected}),
            'rows': len(selected),
        }


def collect_one(item):
    year, unit, cached = item
    rows, source = StateCsv(unit['state'], year).extract(unit['facility_id'], unit['unit_id'], cached)
    source['year'] = year
    print(f'{year} {unit["facility_id"]}/{unit["unit_id"]}: {len(rows):,} linhas bulk', flush=True)
    return rows, source


def collect(start, end, facilities, output_dir):
    with (ROOT / 'coorte_top20_2025.csv').open(newline='', encoding='utf-8') as file:
        units = [row for row in csv.DictReader(file) if row['facility_id'] in facilities]
    if {unit['facility_id'] for unit in units} != set(facilities):
        raise ValueError('Instalação fora da coorte pré-especificada.')
    suffix = '_'.join(sorted(set(facilities), key=int))
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = output_dir / f'fonte_bulk_{start}_{end}_{suffix}.json'
    previous = json.loads(receipt_path.read_text())['source_ranges'] if receipt_path.exists() else []
    cached = {(row['year'], row['facility_id']): row for row in previous}
    requests = [(year, unit, cached.get((year, unit['facility_id'])))
                for year in range(start, end + 1) for unit in units]
    target = output_dir / f'epa_horario_bulk_{start}_{end}_{suffix}.csv.gz'
    staging = target.with_suffix('.partial.gz')
    receipts = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    with ThreadPoolExecutor(max_workers=min(10, len(requests))) as pool, gzip.open(
        staging, 'wt', newline='', encoding='utf-8', compresslevel=4
    ) as output:
        writer = csv.DictWriter(output, FIELDS)
        writer.writeheader()
        for rows, receipt in pool.map(collect_one, requests):
            writer.writerows(rows)
            receipts.append(receipt)
    staging.replace(target)
    with target.open('rb') as data:
        digest = file_digest(data, 'sha256').hexdigest()
    manifest = {
        'retrieved_at_utc': retrieved_at,
        'file': target.name,
        'sha256': digest,
        'rows': sum(item['rows'] for item in receipts),
        'source_ranges': receipts,
    }
    receipt_path.write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8'
    )
    print(f'{target.name}: {manifest["rows"]:,} registros selecionados', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('start', type=int)
    parser.add_argument('end', type=int)
    parser.add_argument('facilities', nargs='+')
    parser.add_argument('--saida', type=Path, default=Path('outputs/phase_05_multiusinas'))
    args = parser.parse_args()
    if not 2021 <= args.start <= args.end <= 2025:
        parser.error('A janela deve estar entre 2021 e 2025.')
    collect(args.start, args.end, args.facilities, args.saida)
