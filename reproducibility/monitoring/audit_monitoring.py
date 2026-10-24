#!/usr/bin/env python3
"""Read-only audit of reported hourly CO2 and monitoring-plan histories.

Input Parquet/CSV files and plan archives are never modified. Only audit outputs
are written. No model sample is changed and no remote mutation is performed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

VERSION = "1.0.0"
BASE = Path(__file__).resolve().parent
REPO = BASE.parents[1]
CATEGORIES = ("measured_only", "mixed_measured_substitute", "substitute_only",
              "calculated", "missing", "other")
LABELS = {
    "measured": "measured_only",
    "measured and substitute": "mixed_measured_substitute",
    "substitute": "substitute_only",
    "calculated": "calculated",
}
PLAN_GROUPS = {
    "method": "monitoringMethodData",
    "formula": "monitoringFormulaData",
    "system": "monitoringSystemData",
    "component": "componentData",
    "span": "monitoringSpanData",
}
FIELDS = {
    "method": ["parameterCode", "monitoringMethodCode", "substituteDataCode", "bypassApproachCode"],
    "formula": ["parameterCode", "formulaId", "formulaCode", "formulaText"],
    "system": ["monitoringSystemId", "systemTypeCode", "systemDesignationCode", "fuelCode"],
    "component": ["componentId", "componentTypeCode", "sampleAcquisitionMethodCode",
                  "basisCode", "manufacturer", "modelVersion", "serialNumber"],
    "span": ["componentTypeCode", "spanScaleCode", "spanMethodCode", "mpcValue", "mpfValue",
             "spanValue", "fullScaleRange", "spanUnitsOfMeasureCode",
             "flowSpanValue", "flowFullScaleRange"],
    "system_component": ["componentId"],
    "analyzer_range": ["analyzerRangeCode", "dualRangeIndicator"],
}
INTERVAL_FIELDS = ["beginDate", "beginHour", "endDate", "endHour"]
COMMON_KEY_FIELDS = sorted(set(sum(FIELDS.values(), [])) | {"begin", "end"})
DOC_URL = "https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf"
API_BASE = "https://api.epa.gov/easey"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_key(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def get(record, name, default=None):
    wanted = norm_key(name)
    for k, v in record.items():
        if norm_key(k) == wanted:
            return v
    return default


def norm_id(x):
    if x is None or pd.isna(x):
        return None
    s = str(x).strip().upper()
    if re.fullmatch(r"\d+(?:\.0+)?", s):
        return str(int(float(s)))
    return s


def canon(x):
    if x is None or (not isinstance(x, (list, dict)) and pd.isna(x)):
        return ""
    if isinstance(x, pd.Timestamp):
        return x.isoformat()
    s = str(x).strip()
    if re.fullmatch(r"-?\d+\.0+", s):
        return str(int(float(s)))
    return s


def timestamp_from_date_hour(date, hour, *, is_end=False):
    """EndHour is the last effective hour, so comparisons use <= end."""
    if date is None or not str(date).strip():
        if is_end:
            return None, ""
        raise ValueError("missing beginDate")
    d = pd.to_datetime(str(date), errors="raise")
    if d.tzinfo is not None:
        # Plan date/hour fields are local reporting dates, not UTC instants.
        d = d.tz_localize(None)
    d = d.normalize()
    note = ""
    if hour is None or str(hour).strip() == "":
        hour = 23 if is_end else 0
        note = "endHour_assumed_23" if is_end else "beginHour_assumed_0"
    n = float(hour)
    if not n.is_integer() or n < 0 or n > 23:
        raise ValueError("hour outside 0..23")
    return d + pd.Timedelta(hours=int(n)), note


def interval(record):
    try:
        start, note1 = timestamp_from_date_hour(get(record, "beginDate"), get(record, "beginHour"))
        end, note2 = timestamp_from_date_hour(get(record, "endDate"), get(record, "endHour"), is_end=True)
        if end is not None and end < start:
            raise ValueError("end before begin")
        return start, end, "valid", ";".join(x for x in (note1, note2) if x)
    except (ValueError, TypeError, OverflowError):
        return None, None, "invalid", "invalid_or_missing_interval"


def xml_record(element):
    result = {}
    for child in element:
        tag = child.tag.split("}")[-1]
        if len(child) == 0:
            result[tag] = child.text
        else:
            value = xml_record(child)
            result.setdefault(tag, []).append(value)
    return result


def list_value(record, key):
    v = get(record, key, [])
    return v if isinstance(v, list) else ([] if v is None else [v])


def plan_documents(path):
    """Yield complete JSON plans or individual XML members without extraction."""
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                if name.lower().endswith(".xml"):
                    yield name, xml_record(ET.fromstring(z.read(name))), "xml"
    elif path.suffix.lower() == ".xml":
        yield path.name, xml_record(ET.parse(path).getroot()), "xml"
    else:
        doc = json.loads(path.read_text(encoding="utf-8"))
        plans = doc if isinstance(doc, list) else doc.get("items", [doc])
        for i, plan in enumerate(plans):
            yield f"{path.name}#{i}", plan, "json"


def flatten_plan(path, facility, unit):
    rows, metadata = [], []
    source = path.stem
    for member, plan, fmt in plan_documents(path):
        oris = norm_id(get(plan, "orisCode", get(plan, "facilityId")))
        if oris != norm_id(facility):
            continue
        locations = list_value(plan, "monitoringLocationData")
        for loc in locations:
            if norm_id(get(loc, "unitId")) != norm_id(unit) or get(loc, "stackPipeId"):
                continue
            # Legacy EPA XML nests the unit's plan sections under UnitData,
            # whereas the current JSON schema places them on the location.
            sections = dict(loc)
            unit_data = list_value(loc, "unitData")
            if len(unit_data) > 1:
                raise ValueError(f"Ambiguous UnitData blocks in {path.name}: {member}")
            if unit_data:
                sections.update(unit_data[0])
            meta = {
                "source": source, "path": "sources/" + path.name, "member": member,
                "format": fmt, "sha256": sha256(path),
                "facility_id": str(facility), "unit_id": str(unit),
                "plan_id": get(plan, "id"), "location_id": get(loc, "id"),
                "reported_update_date": get(plan, "updateDate"),
                "begin_report_period_id": get(plan, "beginReportPeriodId"),
                "end_report_period_id": get(plan, "endReportPeriodId"),
            }
            metadata.append(meta)
            components = {
                canon(get(c, "componentId")): c for c in list_value(sections, "componentData")
            }

            def add(kind, item, parent=None):
                row = {"source": source, "source_member": member, "kind": kind,
                       "facility_id": str(facility), "unit_id": str(unit)}
                row.update({key: get(item, key) for key in FIELDS[kind]})
                row.update({key: get(item, key) for key in INTERVAL_FIELDS})
                if kind != "component":
                    row["begin"], row["end"], row["interval_status"], row["interval_note"] = interval(item)
                if parent:
                    row.update(parent)
                rows.append(row)

            for kind, group in PLAN_GROUPS.items():
                for item in list_value(sections, group):
                    add(kind, item)
                    if kind == "system":
                        parent = {k: get(item, k) for k in FIELDS["system"]}
                        for assoc in list_value(item, "monitoringSystemComponentData"):
                            c = components.get(canon(get(assoc, "componentId")), {})
                            detail = {k: get(c, k) for k in FIELDS["component"]}
                            add("system_component", assoc, {**parent, **detail})
                    elif kind == "component":
                        for ar in list_value(item, "analyzerRangeData"):
                            add("analyzer_range", ar, {
                                "componentId": get(item, "componentId"),
                                "componentTypeCode": get(item, "componentTypeCode"),
                            })
    if not metadata:
        raise ValueError(f"No direct Unit {unit}, Facility {facility} in plan {path.name}")
    if not any(r["kind"] == "method" and r.get("parameterCode") in ("CO2", "CO2M") for r in rows):
        raise ValueError(f"No CO2 monitoring-method section parsed in {path.name}")
    return rows, metadata


def indicator_category(value):
    if value is None or pd.isna(value) or not str(value).strip():
        return "missing"
    return LABELS.get(str(value).strip().casefold(), "other")


def pct(n, denominator):
    return 100.0 * int(n) / int(denominator) if denominator else None


def sum_mass(values):
    return float(values.sum(min_count=1)) if values.notna().any() else None


def summarize(frame, period):
    op = frame["_op"]
    on, off = op.gt(0), op.eq(0)
    mass, load, cat = frame["_co2"], frame["_load"], frame["_category"]
    result = {
        "period": period, "n_rows": len(frame), "n_on": int(on.sum()), "n_off": int(off.sum()),
        "n_operating_time_missing": int(op.isna().sum()),
        "n_operating_time_outside_0_1": int(((op < 0) | (op > 1)).sum()),
        "n_co2_missing_on": int((on & mass.isna()).sum()),
        "n_co2_negative_on": int((on & mass.lt(0)).sum()),
        "n_load_missing_on": int((on & load.isna()).sum()),
        "n_load_zero_on": int((on & load.eq(0)).sum()),
        "n_co2_positive_off": int((off & mass.gt(0)).sum()),
        "n_indicator_missing_off": int((off & cat.eq("missing")).sum()),
        "co2_mass_sum_on_short_tons": sum_mass(mass[on]),
    }
    for category in CATEGORIES:
        selected = on & cat.eq(category)
        result[f"n_{category}_on"] = int(selected.sum())
        result[f"pct_{category}_of_on"] = pct(selected.sum(), on.sum())
        result[f"co2_mass_in_{category}_on_hours_short_tons"] = sum_mass(mass[selected])
    any_sub = on & cat.isin(["mixed_measured_substitute", "substitute_only"])
    result["n_any_substitute_on"] = int(any_sub.sum())
    result["pct_any_substitute_of_on"] = pct(any_sub.sum(), on.sum())
    legacy = frame["_indicator"].fillna("").astype(str).str.strip().str.lower().str.contains("measured", regex=False)
    result["n_legacy_contains_measured_on"] = int((on & legacy).sum())
    result["pct_legacy_contains_measured_of_on"] = pct((on & legacy).sum(), on.sum())
    return result


def mask_for_intervals(times, records):
    mask = np.zeros(len(times), dtype=bool)
    for record in records:
        if record.get("interval_status") != "valid":
            continue
        selected = times.ge(record["begin"])
        if record["end"] is not None and not pd.isna(record["end"]):
            selected &= times.le(record["end"])
        mask |= selected.fillna(False).to_numpy()
    return mask


def coverage_summary(source, methods, year, hourly):
    calendar = pd.Series(pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00:00", freq="h"))
    co2 = [r for r in methods if r.get("parameterCode") in ["CO2", "CO2M"]]
    cem = [r for r in co2 if r.get("parameterCode") == "CO2" and r.get("monitoringMethodCode") == "CEM"]
    covered = mask_for_intervals(calendar, co2)
    cem_covered = mask_for_intervals(calendar, cem)
    signatures = {}
    for record in co2:
        key = (canon(record.get("parameterCode")), canon(record.get("monitoringMethodCode")))
        signatures.setdefault(key, []).append(record)
    number_active = np.zeros(len(calendar), dtype=int)
    for recs in signatures.values():
        number_active += mask_for_intervals(calendar, recs)
    on = hourly["_op"].gt(0).to_numpy()
    hourly_cem = mask_for_intervals(hourly["_timestamp"], cem)
    return {
        "source": source, "year": year, "expected_calendar_hours": len(calendar),
        "co2_cem_declared_hours": int(cem_covered.sum()),
        "pct_calendar_with_co2_cem": pct(cem_covered.sum(), len(calendar)),
        "co2_method_declared_hours": int(covered.sum()),
        "hours_without_co2_method": int((~covered).sum()),
        "hours_with_multiple_co2_method_signatures": int((number_active > 1).sum()),
        "n_on": int(on.sum()), "n_on_with_declared_cem": int((on & hourly_cem).sum()),
        "n_on_without_declared_cem": int((on & ~hourly_cem).sum()),
        "invalid_co2_intervals": sum(r["interval_status"] != "valid" for r in co2),
    }


def component_coverage_summary(source, records, year, hourly):
    """Describe association continuity; no claim of calibration or accuracy."""
    calendar = pd.Series(pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00:00", freq="h"))
    relevant = [r for r in records if r["kind"] == "system_component" and r.get("systemTypeCode") in ("CO2", "FLOW")]
    groups = {}
    for record in relevant:
        key = (canon(record.get("monitoringSystemId")), record.get("systemTypeCode"), record.get("componentTypeCode"))
        groups.setdefault(key, []).append(record)
    output = []
    for (system_id, system_type, component_type), associations in sorted(groups.items()):
        by_component = {}
        for record in associations:
            by_component.setdefault(canon(record.get("componentId")), []).append(record)
        active = np.zeros(len(calendar), dtype=int)
        for same_component in by_component.values():
            active += mask_for_intervals(calendar, same_component)
        hourly_covered = mask_for_intervals(hourly["_timestamp"], associations)
        on = hourly["_op"].gt(0).to_numpy()
        observed_ids = [cid for cid, recs in by_component.items() if mask_for_intervals(calendar, recs).any()]
        output.append({
            "source": source, "year": year, "monitoringSystemId": system_id,
            "systemTypeCode": system_type, "componentTypeCode": component_type,
            "expected_calendar_hours": len(calendar),
            "hours_with_declared_component": int((active > 0).sum()),
            "hours_without_declared_component": int((active == 0).sum()),
            "hours_with_multiple_component_ids": int((active > 1).sum()),
            "component_ids_active_in_year": ";".join(sorted(observed_ids)),
            "n_on_without_declared_component": int((on & ~hourly_covered).sum()),
            "invalid_association_intervals": sum(r["interval_status"] != "valid" for r in associations),
        })
    return output


def contiguous_ranges(times, **extra):
    ordered = pd.DatetimeIndex(times).dropna().unique().sort_values()
    if len(ordered) == 0:
        return []
    groups = pd.Series(ordered).diff().ne(pd.Timedelta(hours=1)).cumsum()
    return [{**extra, "begin": x.min().isoformat(), "end": x.max().isoformat(), "n_hours": len(x)}
            for _, x in pd.Series(ordered).groupby(groups)]


def load_year(path, year, facility, unit):
    before = sha256(path)
    df = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
    required = ["Facility ID", "Unit ID", "Date", "Hour", "Operating Time",
                "Gross Load (MW)", "CO2 Mass (short tons)"]
    absent = sorted(set(required) - set(df.columns))
    if absent:
        raise ValueError(f"{path.name}: required columns missing: {absent}")
    target = df["Facility ID"].map(norm_id).eq(norm_id(facility)) & df["Unit ID"].map(norm_id).eq(norm_id(unit))
    if not target.all():
        raise ValueError(f"{path.name}: contains records outside the target unit; no rows silently removed")
    dates = pd.to_datetime(df["Date"], errors="coerce").dt.normalize()
    hours = pd.to_numeric(df["Hour"], errors="coerce")
    valid_hour = hours.notna() & hours.between(0, 23) & hours.mod(1).eq(0)
    ts = dates + pd.to_timedelta(hours.where(valid_hour), unit="h")
    df["_timestamp"] = ts
    df["_op"] = pd.to_numeric(df["Operating Time"], errors="coerce")
    df["_co2"] = pd.to_numeric(df["CO2 Mass (short tons)"], errors="coerce")
    df["_load"] = pd.to_numeric(df["Gross Load (MW)"], errors="coerce")
    has_indicator = "CO2 Mass Measure Indicator" in df
    df["_indicator"] = df["CO2 Mass Measure Indicator"] if has_indicator else None
    df["_category"] = df["_indicator"].map(indicator_category)
    in_year = ts.dt.year.eq(year)
    # This is an audit grouping, not a modification of any experimental sample.
    frame = df.loc[in_year].copy()
    expected = pd.date_range(f"{year}-01-01", f"{year}-12-31 23:00:00", freq="h")
    present = pd.DatetimeIndex(frame["_timestamp"]).unique()
    missing = expected.difference(present)
    stored_ts_mismatch = None
    if "timestamp" in df:
        stored = pd.to_datetime(df["timestamp"], errors="coerce")
        stored_ts_mismatch = int((~(stored.eq(ts) | (stored.isna() & ts.isna()))).sum())
    summary = summarize(frame, str(year))
    summary.update({
        "year": year, "file_name": path.name, "input_rows": len(df),
        "expected_calendar_hours": len(expected), "reported_unique_hours": len(present),
        "calendar_gap_hours": len(missing), "pct_calendar_coverage": pct(len(present), len(expected)),
        "duplicate_extra_rows": int(frame["_timestamp"].duplicated().sum()),
        "rows_in_duplicate_timestamps": int(frame["_timestamp"].duplicated(keep=False).sum()),
        "invalid_timestamp_rows": int(ts.isna().sum()),
        "timestamp_outside_file_year_rows": int((ts.notna() & ~in_year).sum()),
        "stored_timestamp_disagreement_rows": stored_ts_mismatch,
        "indicator_column_present": has_indicator,
    })
    manifest = {"file_name": path.name, "logical_repository_path": "data/interim/03A04_multiyear/" + path.name, "sha256_before": before, "size_bytes": path.stat().st_size,
                "year": year, "rows": len(df), "sha256_after": sha256(path)}
    if before != manifest["sha256_after"]:
        raise RuntimeError(f"Input changed while reading: {path.name}")
    return frame, summary, contiguous_ranges(missing, year=year, kind="missing_calendar_records"), manifest


def raw_label_counts(frame, year):
    work = frame.copy()
    work["_raw_label"] = work["_indicator"].fillna("<missing>").astype(str)
    records = []
    for (label, cat), group in work.groupby(["_raw_label", "_category"], dropna=False):
        on = group["_op"].gt(0)
        records.append({
            "year": year, "raw_indicator": label, "audit_category": cat,
            "n_all": len(group), "n_on": int(on.sum()), "n_off": int(group["_op"].eq(0).sum()),
            "co2_mass_in_on_hours_short_tons": sum_mass(group.loc[on, "_co2"]),
        })
    return records


def compare_selection_2025(selection_path, annual_path):
    """Link the selection-stage source with the annual extraction by exact data."""
    fields = ["Facility ID", "Unit ID", "Date", "Hour", "Operating Time",
              "Gross Load (MW)", "CO2 Mass (short tons)", "CO2 Mass Measure Indicator"]
    def read(path):
        before = sha256(path)
        frame = pd.read_parquet(path) if path.suffix.lower() == ".parquet" else pd.read_csv(path)
        missing = sorted(set(fields) - set(frame))
        if missing:
            raise ValueError(f"{path.name}: comparison fields missing: {missing}")
        selected = frame[fields].copy()
        for key in ("Facility ID", "Unit ID"):
            selected[key] = selected[key].map(norm_id)
        selected["Date"] = pd.to_datetime(selected["Date"], errors="raise").dt.strftime("%Y-%m-%d")
        selected["Hour"] = pd.to_numeric(selected["Hour"], errors="raise")
        selected = selected.sort_values(["Date", "Hour"]).reset_index(drop=True)
        after = sha256(path)
        if before != after:
            raise RuntimeError(f"Input changed while reading: {path.name}")
        return selected, {"file_name": path.name, "logical_repository_path": "pipeline/" + path.name, "sha256_before": before, "sha256_after": after,
                          "size_bytes": path.stat().st_size, "rows": len(frame), "role": "selection_2025_linkage"}
    selection, selection_manifest = read(selection_path)
    annual, annual_manifest = read(annual_path)
    mismatch = {}
    if len(selection) == len(annual):
        for key in fields:
            same = selection[key].eq(annual[key]) | (selection[key].isna() & annual[key].isna())
            mismatch[key] = int((~same).sum())
    return {
        "original_selection_file": "pipeline/" + selection_path.name,
        "annual_2025_file": "data/interim/03A04_multiyear/" + annual_path.name,
        "original_selection_sha256": selection_manifest["sha256_before"],
        "annual_2025_sha256": annual_manifest["sha256_before"],
        "rows_selection": len(selection), "rows_annual": len(annual),
        "normalization": "Facility/unit identifiers normalized; dates ISO day; hours numeric; chronological sorting; nulls considered equal. No numeric tolerance used.",
        "mismatched_rows_by_field": mismatch,
        "equivalent_on_compared_fields": len(selection) == len(annual) and not any(mismatch.values()),
    }, selection_manifest


def write_csv(path, rows):
    if isinstance(rows, pd.DataFrame):
        rows.to_csv(path, index=False)
    else:
        pd.DataFrame(rows).to_csv(path, index=False)


def snapshot_comparison(rows, sources):
    relevant = [r for r in rows if
                (r["kind"] in ["method", "formula"] and str(r.get("parameterCode", "")).startswith("CO2"))
                or (r["kind"] in ["system", "system_component"] and r.get("systemTypeCode") in ["CO2", "FLOW"])
                or (r["kind"] in ["component", "span", "analyzer_range"] and r.get("componentTypeCode") in ["CO2", "FLOW"])]
    def fingerprint(r):
        return tuple([r["kind"]] + [canon(r.get(k)) for k in COMMON_KEY_FIELDS])
    sets = {source: {fingerprint(r) for r in relevant if r["source"] == source} for source in sources}
    output = []
    for i, a in enumerate(sources):
        for b in sources[i + 1:]:
            output.append({"source_a": a, "source_b": b, "relevant_unique_rows_a": len(sets[a]),
                           "relevant_unique_rows_b": len(sets[b]), "common_rows": len(sets[a] & sets[b]),
                           "only_in_a": len(sets[a] - sets[b]), "only_in_b": len(sets[b] - sets[a]),
                           "equivalent_on_compared_fields": sets[a] == sets[b]})
    return output


def create_report(out, annual, coverage, all_rows, metadata, comparison, findings, selection_comparison=None, component_coverage=None):
    y25 = next((r for r in annual if r["year"] == 2025), None)
    lines = [
        "# Auditoria de monitoramento histórico: Iatan Unit 2",
        "", "## Escopo e procedimento",
        "", "Auditoria descritiva dos arquivos anuais originais e das vigências registradas nos planos de monitoramento. Nenhuma amostra experimental, arquivo de entrada ou seleção de unidade foi alterada.",
        "", "As fontes públicas no repositório são extratos técnicos dos planos, com omissão de identificadores administrativos, campos de contato e comentários livres. Os hashes das respostas integrais, as URLs oficiais e os campos de extração constam de sources/source_provenance.json e source_extracts.py.",
        "", f"Foram auditados {sum(r['input_rows'] for r in annual)} registros, dos quais {sum(r['n_on'] for r in annual)} são horas ON. Os arquivos de 2010, período anterior à janela principal, não integram estes totais.",
        "", "ON corresponde a Operating Time > 0. Os percentuais de indicadores usam todas as horas ON como denominador, incluindo eventuais rótulos ausentes. 'Measured' e 'Measured and Substitute' são categorias separadas.",
        "", "BeginDate/BeginHour incluem a primeira hora de vigência; EndDate/EndHour incluem a última hora. Um término nulo significa registro ainda ativo. Os registros encerrados permanecem na auditoria histórica. Não se aplica ajuste de horário de verão às horas locais reportadas.",
        "", "## Evidência dos planos", "",
    ]
    for source in sorted({m["source"] for m in metadata}):
        records = [r for r in all_rows if r["source"] == source and r["kind"] == "method" and str(r.get("parameterCode", "")).startswith("CO2")]
        for r in records:
            lines.append(f"- {source}: {r.get('parameterCode')} / {r.get('monitoringMethodCode')}, substituição {r.get('substituteDataCode')}, início {canon(r.get('begin'))}, término {canon(r.get('end')) or 'aberto'}.")
    for source in sorted({m["source"] for m in metadata}):
        rows = [r for r in coverage if r["source"] == source]
        if rows:
            lines += ["", f"Cobertura CEM declarada em {source}: {min(r['pct_calendar_with_co2_cem'] for r in rows):.6f}% a {max(r['pct_calendar_with_co2_cem'] for r in rows):.6f}% das horas de calendário por ano; {sum(r['n_on_without_declared_cem'] for r in rows)} horas ON fora da vigência CEM."]
    formulas = [r for r in all_rows if r["kind"] == "formula" and r.get("parameterCode") == "CO2"]
    lines += ["", "Fórmulas CO2 declaradas:", ""]
    for r in formulas:
        lines.append(f"- {r['source']}: fórmula {r.get('formulaCode')}, ID {r.get('formulaId')}, início {canon(r.get('begin'))}, término {canon(r.get('end')) or 'aberto'}.")
    lines += ["", "A fórmula F-11 combina concentração de CO2 e vazão volumétrica em base úmida para determinar a taxa de emissão de massa, conforme a Tabela 43 do manual ECMPS. O alvo estatístico continua sendo o campo original CO2 Mass (short tons); esta auditoria não reconstrói nem substitui esse alvo."]
    lines += [
        "", "A constância do código de método não prova homogeneidade instrumental. As tabelas de sistemas, componentes, fórmulas e faixas preservam as alterações declaradas.",
        "", "## Cobertura e indicadores por ano",
        "", "| Ano | Registros | Horas ON | Measured puro (%) | Measured and Substitute (%) | Substitute (%) | Ausente em ON | Lacunas horárias |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in annual:
        def f(k):
            return "NA" if r.get(k) is None else f"{r[k]:.6f}"
        lines.append(f"| {r['year']} | {r['input_rows']} | {r['n_on']} | {f('pct_measured_only_of_on')} | {f('pct_mixed_measured_substitute_of_on')} | {f('pct_substitute_only_of_on')} | {r['n_missing_on']} | {r['calendar_gap_hours']} |")
    if y25:
        lines += [
            "", "## Esclarecimento do critério de seleção em 2025",
            "", f"O notebook original usa contains('measured'). Em {y25['n_on']} horas ON, esse critério contabiliza {y25['n_legacy_contains_measured_on']} horas ({y25['pct_legacy_contains_measured_of_on']:.6f}%).",
            "", f"A decomposição exata é: Measured = {y25['n_measured_only_on']} ({y25['pct_measured_only_of_on']:.6f}%); Measured and Substitute = {y25['n_mixed_measured_substitute_on']} ({y25['pct_mixed_measured_substitute_of_on']:.6f}%); Substitute = {y25['n_substitute_only_on']} ({y25['pct_substitute_only_of_on']:.6f}%).",
            "", "Portanto, o critério aplicado na seleção expressa participação de medição no valor reportado. Ele não demonstra que todas as horas sejam classificadas como integralmente medidas. Esta auditoria descreve o critério executado e não refaz a seleção.",
        ]
        if selection_comparison is not None:
            lines += ["", f"O arquivo da etapa de seleção e o anual de 2025 contêm, respectivamente, {selection_comparison['rows_selection']} e {selection_comparison['rows_annual']} registros. Equivalência exata nos oito campos comparados, após normalização de identificadores e datas: {selection_comparison['equivalent_on_compared_fields']}. Os hashes e os campos constam de selection_2025_annual_comparison.json."]
    lines += ["", "## Alterações declaradas dos componentes CO2/FLOW", "",
              "| Fonte | Sistema | Componente | Tipo | Fabricante / modelo | Início | Última hora |",
              "|---|---|---|---|---|---|---|"]
    rows = [r for r in all_rows if r["kind"] == "system_component" and r.get("systemTypeCode") in ["CO2", "FLOW"]]
    for r in sorted(rows, key=lambda r: (r["source"], canon(r.get("systemTypeCode")), canon(r.get("begin")), canon(r.get("componentId")))):
        lines.append("| " + " | ".join([
            r["source"], canon(r.get("systemTypeCode")), canon(r.get("componentId")),
            canon(r.get("componentTypeCode")), f"{canon(r.get('manufacturer'))} / {canon(r.get('modelVersion'))}",
            canon(r.get("begin")), canon(r.get("end")) or "aberto"]) + " |")
    if component_coverage:
        lines += ["", f"Os {len(component_coverage)} cruzamentos fonte/ano/sistema/tipo de componente apresentam {sum(r['hours_without_declared_component'] for r in component_coverage)} horas sem associação declarada e {sum(r['hours_with_multiple_component_ids'] for r in component_coverage)} horas com múltiplos IDs simultâneos do mesmo tipo. Essa continuidade documental não demonstra precisão constante nem estabilidade de calibração."]
    lines += ["", "## Comparação entre fontes", ""]
    for r in comparison:
        lines.append(f"- {r['source_a']} versus {r['source_b']}: {r['common_rows']} registros comparáveis em comum; exclusivos A/B = {r['only_in_a']}/{r['only_in_b']}; equivalência dos campos comparados = {r['equivalent_on_compared_fields']}.")
    lines += [
        "", "## Limites de interpretação",
        "", "- Os planos consultados contêm vigências históricas em snapshots posteriores. Eles não constituem uma coleção de quinze versões anuais preservadas no momento de cada operação.",
        "- O rótulo horário descreve a forma de determinação do valor reportado. 'Measured' não significa um sensor que mede diretamente massa de CO2, nem prova ausência de erro de medição.",
        "- Nas horas 'Measured and Substitute', não se conhece, por esse indicador agregado, a fração intrahorária ou da massa efetivamente substituída. As massas associadas a essas horas não são estimativas de massa substituída.",
        "- Alterações de analisador, sonda, registrador e DAHS documentam diferenças de configuração. Esta auditoria não estima seu efeito sobre a série e não permite atribuir causalmente mudanças de erro do modelo à instrumentação.",
        "- Não foram reprocessados relatórios de calibração, certificação, auditoria relativa de precisão ou dados brutos sub-horários.",
        "- Ausência de registro horário, ausência de indicador em hora OFF e uso regulatório de dado substituto são situações distintas, reportadas separadamente.",
        "", "## Fontes oficiais e rastreabilidade",
        "", f"- [Instruções oficiais ECMPS, 20/12/2024]({DOC_URL}), seção 6, páginas impressas 32 e 33 (vigência dos métodos); seção 8.2, página 61 (vigência dos componentes); seção 9, Tabela 43, página 80 (F-11).",
        f"- [OpenAPI de planos]({API_BASE}/monitor-plan-mgmt/swagger-json) e [OpenAPI de emissões]({API_BASE}/emissions-mgmt/swagger-json).",
        f"- [Tabelas de códigos oficiais]({API_BASE}/master-data-mgmt/list). Os JSONs consultados estão no diretório sources.",
        "- input_manifest.json e sources_manifest.json registram hashes SHA-256. Caminhos de entrada são nomes lógicos relativos ao repositório; os argumentos da execução podem apontar para outra cópia dos mesmos arquivos. As entradas foram abertas somente para leitura.",
        "", "## Achados de integridade", "",
    ]
    lines.extend(["- " + f for f in findings] or ["Nenhuma anomalia de integridade detectada nos testes descritos."])
    (out / "audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args):
    out = Path(args.output_dir).resolve()
    hourly_dir = Path(args.hourly_dir).resolve()
    if out == hourly_dir or hourly_dir in out.parents:
        raise ValueError("Output directory must be outside the original hourly-data directory")
    out.mkdir(parents=True, exist_ok=True)
    plan_rows, plan_meta = [], []
    plan_paths = [Path(p).resolve() for p in args.plan]
    for p in plan_paths:
        rows, metadata = flatten_plan(p, args.facility, args.unit)
        plan_rows += rows
        plan_meta += metadata
    source_names = sorted({m["source"] for m in plan_meta})
    frames, annual, monthly, counts, gaps, manifests, coverage, findings = [], [], [], [], [], [], [], []
    component_coverage = []
    for year in range(args.start_year, args.end_year + 1):
        paths = [hourly_dir / f"iatan_unit2_{year}{suffix}" for suffix in [".parquet", ".csv"]]
        paths = [p for p in paths if p.exists()]
        if len(paths) != 1:
            raise ValueError(f"Expected exactly one original annual file for {year}; found {len(paths)}")
        frame, summary, missing, manifest = load_year(paths[0], year, args.facility, args.unit)
        frames.append(frame)
        annual.append(summary)
        gaps += missing
        manifests.append(manifest)
        counts += raw_label_counts(frame, year)
        for month, group in frame.groupby(frame["_timestamp"].dt.to_period("M")):
            monthly.append(summarize(group, str(month)))
        for source in source_names:
            methods = [r for r in plan_rows if r["source"] == source and r["kind"] == "method"]
            coverage.append(coverage_summary(source, methods, year, frame))
            component_coverage += component_coverage_summary(source, [r for r in plan_rows if r["source"] == source], year, frame)
        for key in ["calendar_gap_hours", "duplicate_extra_rows", "invalid_timestamp_rows",
                    "timestamp_outside_file_year_rows", "stored_timestamp_disagreement_rows",
                    "n_missing_on", "n_other_on", "n_co2_missing_on", "n_load_missing_on",
                    "n_operating_time_missing", "n_operating_time_outside_0_1", "n_co2_negative_on", "n_co2_positive_off"]:
            if summary.get(key):
                findings.append(f"{year}: {key} = {summary[key]}.")
    all_hourly = pd.concat(frames, ignore_index=True).sort_values("_timestamp").reset_index(drop=True)
    cohorts = []
    for name, years in [("2011-2022", range(2011, 2023)), ("2023-2024", [2023, 2024]), ("2025", [2025]), ("all_audited_years", range(args.start_year, args.end_year + 1))]:
        cohorts.append(summarize(all_hourly[all_hourly["_timestamp"].dt.year.isin(years)], name))
    any_sub = all_hourly["_op"].gt(0) & all_hourly["_category"].isin(["mixed_measured_substitute", "substitute_only"])
    episodes = []
    if all_hourly["_timestamp"].duplicated().any():
        findings.append("Substitution episodes not calculated because duplicate timestamps require explicit resolution.")
    else:
        for episode in contiguous_ranges(all_hourly.loc[any_sub, "_timestamp"]):
            selected = all_hourly["_timestamp"].between(pd.Timestamp(episode["begin"]), pd.Timestamp(episode["end"]))
            episode.update(summarize(all_hourly[selected], episode["begin"] + "/" + episode["end"]))
            episodes.append(episode)
    comparison = snapshot_comparison(plan_rows, source_names)
    selection_comparison = None
    selection_path = Path(args.selection_file).resolve() if args.selection_file else None
    if selection_path and selection_path.exists() and args.start_year <= 2025 <= args.end_year:
        annual_paths = [hourly_dir / ("iatan_unit2_2025" + suffix) for suffix in (".parquet", ".csv")]
        annual_path = next(p for p in annual_paths if p.exists())
        selection_comparison, selection_manifest = compare_selection_2025(selection_path, annual_path)
        manifests.append(selection_manifest)
        if not selection_comparison["equivalent_on_compared_fields"]:
            findings.append("Selection-stage and annual 2025 files differ; inspect selection_2025_annual_comparison.json.")
    for record in coverage:
        if record["hours_without_co2_method"] or record["n_on_without_declared_cem"] or record["invalid_co2_intervals"] or record["hours_with_multiple_co2_method_signatures"]:
            findings.append(f"{record['source']} / {record['year']}: examine monitoring_plan_coverage.csv.")
    for record in component_coverage:
        if any(record[k] for k in ["hours_without_declared_component", "hours_with_multiple_component_ids", "invalid_association_intervals"]):
            findings.append(f"{record['source']} / {record['year']} / {record['systemTypeCode']} / {record['componentTypeCode']}: examine component_coverage.csv.")
    for comparison_row in comparison:
        if not comparison_row["equivalent_on_compared_fields"]:
            findings.append("Plan snapshots differ in relevant fields; inspect snapshot_comparison.csv and plan tables.")
    write_csv(out / "annual_measurement_summary.csv", annual)
    write_csv(out / "monthly_measurement_summary.csv", monthly)
    write_csv(out / "cohort_measurement_summary.csv", cohorts)
    write_csv(out / "indicator_raw_counts.csv", counts)
    write_csv(out / "monitoring_plan_coverage.csv", coverage)
    write_csv(out / "component_coverage.csv", component_coverage)
    write_csv(out / "calendar_gap_episodes.csv", pd.DataFrame(gaps, columns=["year", "kind", "begin", "end", "n_hours"]))
    write_csv(out / "substitution_episodes.csv", episodes)
    write_csv(out / "snapshot_comparison.csv", comparison)
    for kind in FIELDS:
        write_csv(out / f"plan_{kind}_history.csv", [r for r in plan_rows if r["kind"] == kind])
    instrument = [r for r in plan_rows if r["kind"] == "system_component" and r.get("systemTypeCode") in ["CO2", "FLOW"]]
    write_csv(out / "co2_flow_component_history.csv", instrument)
    changes = [r for r in instrument if r.get("begin") is not None and args.start_year <= r["begin"].year <= args.end_year]
    write_csv(out / "co2_flow_component_changes.csv", changes)
    source_files = sorted(set(plan_paths + list((BASE / "sources").glob("*.json")) + list((BASE / "sources").glob("*.pdf")) + list((BASE / "sources").glob("*.txt"))))
    source_manifest = [{"path": "sources/" + p.name, "size_bytes": p.stat().st_size, "sha256": sha256(p)} for p in source_files]
    summary = {
        "audit_version": VERSION, "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "facility_id": str(args.facility), "unit_id": str(args.unit),
        "start_year": args.start_year, "end_year": args.end_year,
        "audited_rows": sum(r["input_rows"] for r in annual),
        "n_on": int(all_hourly["_op"].gt(0).sum()),
        "calendar_gap_hours": sum(r["calendar_gap_hours"] for r in annual),
        "duplicate_extra_rows": sum(r["duplicate_extra_rows"] for r in annual),
        "input_files_unchanged": all(m["sha256_before"] == m["sha256_after"] for m in manifests),
        "selection_rule_unchanged": True, "model_samples_modified": False,
        "plan_metadata": plan_meta, "snapshot_comparison": comparison,
        "selection_2025_comparison": selection_comparison,
        "findings": findings,
    }
    for name, value in [("input_manifest.json", manifests), ("sources_manifest.json", source_manifest), ("audit_summary.json", summary)]:
        (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    create_report(out, annual, coverage, plan_rows, plan_meta, comparison, findings, selection_comparison, component_coverage)
    if selection_comparison is not None:
        (out / "selection_2025_annual_comparison.json").write_text(json.dumps(selection_comparison, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ["audited_rows", "n_on", "calendar_gap_hours", "duplicate_extra_rows", "input_files_unchanged"]}, ensure_ascii=False))
    print("Audit outputs: " + str(out))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hourly-dir", default=str(REPO / "data/interim/03A04_multiyear"))
    parser.add_argument("--plan", action="append", help="Repeat for XML, ZIP or exported plan JSON.")
    parser.add_argument("--output-dir", default=str(BASE / "outputs"))
    parser.add_argument("--selection-file", default=str(REPO / "pipeline/selected_unit_hourly_raw.parquet"), help="Optional original selection-stage 2025 file for exact linkage.")
    parser.add_argument("--facility", default="6065")
    parser.add_argument("--unit", default="2")
    parser.add_argument("--start-year", type=int, default=2011)
    parser.add_argument("--end-year", type=int, default=2025)
    args = parser.parse_args()
    if args.start_year > args.end_year:
        parser.error("start-year must be <= end-year")
    if args.plan is None:
        args.plan = [str(BASE / "sources/original_plan_unit2.xml"), str(BASE / "sources/current_plan_unit2.json")]
    try:
        run(args)
    except (ValueError, OSError, KeyError, RuntimeError) as exc:
        # All operations are local here; errors cannot contain authenticated URLs.
        print(f"Audit failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

