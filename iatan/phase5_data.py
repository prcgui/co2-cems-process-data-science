"""Calendário anual preservado para a validação temporal da Fase 5."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from iatan.data import LOAD, OP, TARGET, audit_hourly, digest, load_calendar


START_YEAR = 2011
END_YEAR = 2025
TARGET_TONS = "co2_metric_tons"
SHORT_TON_TO_TONNE = 0.90718474


def load_phase5_calendar(root: Path) -> tuple[pd.DataFrame, list[dict]]:
    """Confere os anuais de Iatan 2 e preserva o calendário com seus faltantes."""
    years = tuple(range(START_YEAR, END_YEAR + 1))
    manifest = json.loads((root / "configs/iatan_inputs.json").read_text(encoding="utf-8"))
    expected_hashes = {entry["path"]: entry["sha256"] for entry in manifest["files"]}
    metadata = []
    for year in years:
        relative = f"data/interim/03A04_multiyear/iatan_unit2_{year}.parquet"
        path = root / relative
        if relative not in expected_hashes:
            raise ValueError(f"Insumo fora do manifesto preservado: {relative}")
        if not path.is_file():
            raise FileNotFoundError(f"Insumo ausente: {relative}. Restaure o Parquet anual preservado.")
        sha256 = digest(path)
        if sha256 != expected_hashes[relative]:
            raise ValueError(f"Insumo alterado: {relative}")
        metadata.append({"year": year, "path": relative, "sha256": sha256})

    calendar = load_calendar(root, years=years)
    if (not calendar["Facility ID"].eq(6065).fillna(False).all()
            or not calendar["Unit ID"].astype(str).eq("2").all()):
        raise ValueError("Os identificadores originais devem corresponder à Iatan 2 (6065/2).")
    if calendar[OP].isna().any():
        raise ValueError("O calendário deve ter tempo de operação em todas as horas.")
    values = calendar[[LOAD, TARGET]].to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(values).any() or (values < 0).any():
        raise ValueError("A carga e o CO₂ medidos devem ser finitos e não negativos.")

    for entry, (_, part) in zip(metadata, calendar.groupby(calendar.timestamp.dt.year), strict=True):
        on = part[OP].gt(0)
        missing = part[[LOAD, TARGET]].isna()
        entry.update(audit_hourly(part),
                     partial_on=int((on & part[OP].lt(1)).sum()),
                     eligible_on=int((on & ~missing.any(axis=1)).sum()),
                     load_missing_off=int((~on & missing[LOAD]).sum()),
                     co2_missing_off=int((~on & missing[TARGET]).sum()))

    result = calendar[["timestamp", LOAD, OP]].assign(**{TARGET_TONS: calendar[TARGET] * SHORT_TON_TO_TONNE})
    return result, metadata
