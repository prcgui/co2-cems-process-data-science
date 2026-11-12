"""Sensor → estados → eventos → atributos; Diba (2020), Moradbeikie (2025).

Adaptação própria de Iatan; HMM/DFG ajustados no treino. Os artigos não
prescrevem K=5, os limiares nem demonstram ganho em CO2 nesta unidade.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.special import logsumexp
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM
from .data import LOAD, OP


def observations(raw):
    d = raw.sort_values('timestamp').reset_index(drop=True).copy()
    contiguous = d.timestamp.diff().eq(pd.Timedelta(hours=1))
    on = d[OP].gt(0)
    d['cycle_id'] = (~(on & on.shift(fill_value=False) & contiguous)).cumsum()
    load = d[LOAD].where(on, 0.)
    delta = load.diff().where(contiguous & on & on.shift(fill_value=False))
    d['hmm_load'] = load
    d['hmm_delta'] = delta
    d['hmm_valid'] = on & np.isfinite(load) & np.isfinite(delta)
    return d


def lengths_for_valid(d):
    part = d.loc[d.hmm_valid]
    cut = part.cycle_id.ne(part.cycle_id.shift()) | part.timestamp.diff().ne(pd.Timedelta(hours=1))
    return part.groupby(cut.cumsum(), sort=False).size().tolist()


@dataclass
class ProcessModel:
    k: int = 5
    seed: int = 42
    n_iter: int = 100
    ramp_threshold: float = 10.

    def fit(self, raw):
        d = observations(raw)
        x = d.loc[d.hmm_valid, ['hmm_load', 'hmm_delta']].to_numpy(float)
        if len(x) < 20 * self.k:
            raise ValueError('Amostra insuficiente para HMM')
        self.scaler = StandardScaler().fit(x)
        z = self.scaler.transform(x)
        self.hmm = GaussianHMM(n_components=self.k, covariance_type='diag', random_state=self.seed,
                               n_iter=self.n_iter, tol=1e-3, min_covar=1e-3)
        self.hmm.fit(z, lengths=lengths_for_valid(d))
        # Rank-based names avoid claiming physical identity of heuristic labels.
        self.order = np.argsort(self.hmm.means_[:, 0], kind='stable')
        self.train_end = d.timestamp.max()
        self.edges = {}; self.totals = {}; self.activities = []
        labels = self.transform(raw)
        train_events = events(labels)
        for _, g in train_events.groupby('cycle_id', sort=False):
            acts = g.activity.tolist()
            for a, b in zip(acts[:-1], acts[1:]):
                self.edges[(a, b)] = self.edges.get((a, b), 0) + 1
                self.totals[a] = self.totals.get(a, 0) + 1
        self.activities = sorted(train_events.activity.unique())
        self.training_events = train_events
        self.audit = {'train_until': str(self.train_end), 'rows_fit': len(x), 'k': self.k,
                      'seed': self.seed, 'iterations': self.hmm.monitor_.iter,
                      'converged': bool(self.hmm.monitor_.converged),
                      'decoding': 'forward_per_contiguous_on_sequence', 'co2_used': False,
                      'learned_edges': len(self.edges), 'ramp_threshold_mw': self.ramp_threshold}
        return self

    def transform(self, raw):
        d = observations(raw)
        columns = [f'hmm_p_{i}' for i in range(self.k)]
        d[columns] = 0.
        d['hmm_available'] = d.hmm_valid.astype('int8')
        d['hmm_confidence'] = 0.; d['hmm_entropy'] = 0.
        d['activity'] = np.where(d[OP].gt(0), 'ON_UNRESOLVED', 'OFF')
        valid = d.loc[d.hmm_valid]
        if not valid.empty:
            x = self.scaler.transform(valid[['hmm_load', 'hmm_delta']].to_numpy(float))
            emission = self.hmm._compute_log_likelihood(x)
            cut = valid.cycle_id.ne(valid.cycle_id.shift()) | valid.timestamp.diff().ne(pd.Timedelta(hours=1))
            probs = np.empty((len(x), self.k)); alpha = None
            log_trans = np.log(np.clip(self.hmm.transmat_, 1e-300, None))
            log_start = np.log(np.clip(self.hmm.startprob_, 1e-300, None))
            for i, reset in enumerate(cut):
                alpha = emission[i] + (log_start if reset else logsumexp(alpha[:, None] + log_trans, axis=0))
                alpha -= logsumexp(alpha)
                probs[i] = np.exp(alpha)[self.order]
            d.loc[valid.index, columns] = probs
            d.loc[valid.index, 'hmm_confidence'] = probs.max(axis=1)
            d.loc[valid.index, 'hmm_entropy'] = -(probs * np.log(np.clip(probs, 1e-300, None))).sum(axis=1)
            states = probs.argmax(axis=1)
            directions = np.where(valid.hmm_delta > self.ramp_threshold, 'UP',
                                  np.where(valid.hmm_delta < -self.ramp_threshold, 'DOWN', 'FLAT'))
            d.loc[valid.index, 'activity'] = [f'E{s}_{direction}' for s, direction in zip(states, directions)]
        derived = np.zeros((len(d), 6), dtype=float)
        previous = None; previous_time = None; previous_cycle = None
        elapsed = age = changes = 0; probability = 0.; known = 0
        for i, row in d.iterrows():
            if row[OP] <= 0:
                previous = previous_time = previous_cycle = None
                continue
            reset = previous_time is None or row.timestamp - previous_time != pd.Timedelta(hours=1) or row.cycle_id != previous_cycle
            activity = row.activity
            if reset:
                elapsed = age = 1; changes = 0; probability = 0.; known = 0
            else:
                age += 1
                if activity == previous: elapsed += 1
                else:
                    elapsed = 1; changes += 1
                    count = self.edges.get((previous, activity), 0)
                    probability = (count + 1.) / (self.totals.get(previous, 0) + max(1, len(self.activities) + 1))
                    known = int(count > 0)
            derived[i] = [
                elapsed, age, changes, probability, -np.log(probability) if probability > 0 else 0., known]
            previous, previous_time, previous_cycle = activity, row.timestamp, row.cycle_id
        d[['proc_elapsed_activity_h', 'proc_elapsed_cycle_h', 'proc_changes',
           'proc_transition_probability', 'proc_transition_surprise', 'proc_edge_known']] = derived
        return d


def events(labels):
    d = labels.loc[labels[OP].gt(0)].copy()
    if d.empty: return pd.DataFrame(columns=['cycle_id', 'activity', 'start', 'end', 'duration_h'])
    cut = d.cycle_id.ne(d.cycle_id.shift()) | d.activity.ne(d.activity.shift()) | d.timestamp.diff().ne(pd.Timedelta(hours=1))
    return d.groupby(cut.cumsum(), sort=False).agg(cycle_id=('cycle_id', 'first'), activity=('activity', 'first'),
            start=('timestamp', 'min'), end=('timestamp', 'max'), duration_h=('timestamp', 'size')).reset_index(drop=True)


def discover(model, path):
    import pm4py
    log = model.training_events.rename(columns={'cycle_id': 'case:concept:name', 'activity': 'concept:name', 'start': 'time:timestamp'}).copy()
    log['case:concept:name'] = log['case:concept:name'].astype(str)
    log['time:timestamp'] = pd.to_datetime(log['time:timestamp'], utc=True)
    tree = pm4py.discover_process_tree_inductive(log)
    net, im, fm = pm4py.convert_to_petri_net(tree)
    pm4py.write_pnml(net, im, fm, str(path / 'process_train.pnml'))
    (path / 'process_tree.txt').write_text(str(tree), encoding='utf-8')
    log.to_csv(path / 'event_log_train.csv', index=False)
    pd.DataFrame([dict(origin=a, destination=b, count=n) for (a, b), n in model.edges.items()]).to_csv(path / 'dfg_train.csv', index=False)


def memory_features(raw):
    """117 atributos adaptados da Fase 5; shift(1) e blocos horários sem unir lacunas."""
    d = raw.sort_values('timestamp').reset_index(drop=True).copy()
    block = d.timestamp.diff().ne(pd.Timedelta(hours=1)).cumsum()
    g = d[LOAD].where(d[OP].gt(0), 0.)
    values = {'timestamp': d.timestamp, 'mem_current': g}
    for lag in range(1, 97): values[f'mem_lag_{lag}'] = g.groupby(block).shift(lag)
    past = g.groupby(block).shift(1)
    for n in [3, 6, 12, 24, 48, 96]:
        values[f'mem_mean_{n}'] = past.groupby(block).transform(lambda x: x.rolling(n, min_periods=n).mean())
        values[f'mem_std_{n}'] = past.groupby(block).transform(lambda x: x.rolling(n, min_periods=n).std(ddof=0))
    values['mem_delta_1'] = g - values['mem_lag_1']; values['mem_delta_24'] = g - values['mem_lag_24']
    values['mem_on'] = d[OP].gt(0).astype(int); values['mem_weekday'] = d.timestamp.dt.dayofweek
    for name, value, period in [('hour', d.timestamp.dt.hour, 24), ('month', d.timestamp.dt.month - 1, 12)]:
        values[f'mem_{name}_sin'] = np.sin(2 * np.pi * value / period)
        values[f'mem_{name}_cos'] = np.cos(2 * np.pi * value / period)
    return pd.DataFrame(values)
