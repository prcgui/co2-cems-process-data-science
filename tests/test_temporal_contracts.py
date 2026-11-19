"""Tests with synthetic data: temporal availability, gaps, and target exclusion."""
import numpy as np
import pandas as pd
from iatan.data import LOAD, OP, TARGET, audit_hourly
from iatan.processes import ProcessModel, memory_features, observations


def sample(n=700):
    rng = np.random.default_rng(42)
    load = 500 + 150 * np.sin(np.arange(n) / 15) + rng.normal(0, 15, n)
    return pd.DataFrame({'timestamp': pd.date_range('2025-01-01', periods=n, freq='h'),
                         LOAD: load, OP: np.ones(n), TARGET: .7 * load,
                         'facilityId_norm': '6065', 'unitId_norm': '2'})


def test_future_observations_do_not_change_past_features():
    raw = sample()
    model = ProcessModel(k=2, seed=42, n_iter=30).fit(raw.iloc[:400])
    prefix = model.transform(raw.iloc[:500])
    altered = raw.copy(); altered.loc[500:, LOAD] *= 5
    full = model.transform(altered)
    cols = [c for c in prefix if c.startswith(('hmm_p_', 'proc_'))]
    np.testing.assert_allclose(prefix[cols], full.loc[:499, cols], atol=1e-12, rtol=0)


def test_co2_does_not_enter_process_features_or_hmm():
    raw = sample(400)
    a = ProcessModel(k=2, n_iter=30).fit(raw)
    raw[TARGET] = np.arange(len(raw)) * 1e6
    b = ProcessModel(k=2, n_iter=30).fit(raw)
    np.testing.assert_array_equal(a.hmm.means_, b.hmm.means_)
    assert a.edges == b.edges


def test_memory_and_delta_reset_at_calendar_gap():
    raw = sample(250)
    raw.loc[150:, 'timestamp'] += pd.Timedelta(days=2)
    mem = memory_features(raw)
    assert pd.isna(mem.loc[150, 'mem_lag_1'])
    assert pd.isna(mem.loc[150, 'mem_mean_3'])
    assert not observations(raw).loc[150, 'hmm_valid']


def test_off_measurements_preserved_and_features_do_not_read_future():
    raw = sample(250); raw.loc[50:80, OP] = 0.; raw.loc[50:80, [LOAD, TARGET]] = np.nan
    before = raw.copy(deep=True)
    prefix = memory_features(raw.iloc[:200]); full = memory_features(raw)
    pd.testing.assert_frame_equal(prefix, full.iloc[:200].reset_index(drop=True))
    pd.testing.assert_frame_equal(raw, before)
    assert full.loc[50:80, 'mem_current'].eq(0).all()


def test_wrong_unit_rejected():
    import pytest
    raw = sample(30); raw['unitId_norm'] = '3'
    with pytest.raises(ValueError, match='Iatan'): audit_hourly(raw)
