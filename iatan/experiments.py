"""Variação controlada e rastreável; aula e-Science (pp. 23–27,53–56).

Blocos de atributos são escolhas do grupo. Nenhuma hipótese de ganho é garantida.
"""
from datetime import datetime, timezone
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import ElasticNet
from xgboost import XGBRegressor
from .data import B0, TARGET, LOAD, HISTORY, digest, verify_inputs, load_calendar, load_splits, write_json
from .baseline import metrics
from .processes import ProcessModel, memory_features, discover
from .tracking import configure, tracked, log_metrics


def gate(root):
    path = root / 'outputs/iatan_consolidado/baseline_aprovado.json'
    if not path.exists():
        reference = root / 'outputs/iatan_consolidado/reference_verified.json'
        if not reference.exists(): raise RuntimeError('Verifique a referência congelada ou reproduza o baseline antes das extensões.')
        record = json.loads(reference.read_text(encoding='utf-8'))
        if not record.get('reference_verified') or record['reference_config_sha256'] != digest(root / 'configs/frozen_reference.json') or record['inputs_manifest_sha256'] != digest(root / 'configs/iatan_inputs.json'):
            raise RuntimeError('Verificação congelada desatualizada')
        frozen = json.loads((root / 'configs/frozen_reference.json').read_text(encoding='utf-8'))
        if digest(root / frozen['model_path']) != frozen['model_sha256']: raise RuntimeError('Modelo congelado alterado')
        verify_inputs(root)
        return 'new_controlled_experiment_with_frozen_reference; historical_retraining_not_verified'
    result = json.loads(path.read_text(encoding='utf-8'))
    if not result['passed'] or result['config_sha256'] != digest(root / 'configs/baseline_03A05.json') or result['inputs_manifest_sha256'] != digest(root / 'configs/iatan_inputs.json'):
        raise RuntimeError('Baseline sem aprovação para os insumos/configuração atuais')
    verify_inputs(root)
    return 'historical_retraining_verified'


def enrich(sample, features):
    # Use measured supervised rows as authority for the target; feature frame has no CO2 predictors.
    result = sample.merge(features, on='timestamp', how='left', validate='one_to_one')
    if len(result) != len(sample): raise ValueError('Junção alterou a amostra')
    return result


def prepare(root, cfg, out):
    splits = load_splits(root); raw = load_calendar(root)
    memory = memory_features(raw)
    cols_memory = [c for c in memory if c != 'timestamp']
    assert len(cols_memory) == 117
    for stage, train_name, eval_name in [('selection', 'train_selection', 'validation'), ('final', 'train_final', 'test')]:
        tr_end = splits[train_name].timestamp.max(); eval_end = splits[eval_name].timestamp.max()
        model = ProcessModel(**cfg['hmm']).fit(raw.loc[raw.timestamp.le(tr_end)])
        labels = model.transform(raw.loc[raw.timestamp.le(eval_end)])
        pcols = [c for c in labels if c.startswith(('hmm_p_', 'hmm_available', 'hmm_confidence', 'hmm_entropy'))]
        tcols = [c for c in labels if c.startswith('proc_')]
        features = labels[['timestamp'] + pcols + tcols].merge(memory, on='timestamp', validate='one_to_one')
        groups = {'CARGA': ['load_current_mw'], 'B0': B0,
                  'P1': B0 + pcols, 'P2': B0 + pcols + tcols, 'MEMORIA117': cols_memory}
        union = list(dict.fromkeys(c for name in cfg['scenarios'] for c in groups[name]))
        frames = {}
        audit = []
        for name in [train_name, eval_name]:
            merged = enrich(splits[name], features)
            ok = np.isfinite(merged[union].to_numpy(float)).all(axis=1)
            # All scenarios use precisely the intersection, including the B0 control.
            dropped = merged.loc[~ok, ['timestamp']].copy()
            dropped['reason'] = 'non_finite_feature_in_common_scenarios'
            folder = out / stage; folder.mkdir(exist_ok=True)
            dropped.to_csv(folder / f'exclusions_{name}.csv', index=False)
            frames[name] = merged.loc[ok].reset_index(drop=True)
            audit.append({'partition': name, 'eligible_original': len(merged), 'common': int(ok.sum()), 'excluded': int((~ok).sum())})
            if frames[name].empty: raise ValueError('Interseção amostral vazia')
        joblib.dump(model, folder / 'process_model.joblib')
        write_json(folder / 'hmm_training.json', model.audit)
        write_json(folder / 'feature_groups.json', groups)
        write_json(folder / 'sample_audit.json', audit)
        discover(model, folder)
        for name, df in frames.items(): df.to_parquet(folder / f'{name}.parquet', index=False)
        print('Preparação', stage, audit, flush=True)
    return out


def run(root, config_path=None):
    reference_mode = gate(root)
    config_path = config_path or root / 'configs/experimento_iatan.json'
    cfg = json.loads(config_path.read_text(encoding='utf-8'))
    if cfg['automl'] or cfg['correction']: raise ValueError('AutoML/correção não estão habilitados neste protocolo')
    if set(cfg['algorithms']) - {'XGBoost', 'ElasticNet'}: raise ValueError('Algoritmo desconhecido')
    if set(cfg['scenarios']) - {'CARGA', 'B0', 'P1', 'P2', 'MEMORIA117'}: raise ValueError('Cenário desconhecido')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out = root / 'outputs/iatan_consolidado/experiments' / stamp; out.mkdir(parents=True)
    write_json(out / 'configuration.json', cfg)
    write_json(out / 'reference_mode.json', {'mode': reference_mode})
    configure(root)
    rows = []; predictions = []; selectors = []
    with tracked(root, cfg['name'], out, {'kind': 'controlled_feature_experiment', 'config_sha256': digest(config_path)}):
        prepare(root, cfg, out)
        sel = out / 'selection'; fin = out / 'final'
        train = pd.read_parquet(sel / 'train_selection.parquet'); val = pd.read_parquet(sel / 'validation.parquet')
        full = pd.read_parquet(fin / 'train_final.parquet'); test = pd.read_parquet(fin / 'test.parquet')
        groups = json.loads((sel / 'feature_groups.json').read_text(encoding='utf-8'))
        assert groups == json.loads((fin / 'feature_groups.json').read_text(encoding='utf-8'))
        assert train.timestamp.max() < val.timestamp.min() and full.timestamp.max() < test.timestamp.min()
        for alg in cfg['algorithms']:
            seeds = cfg['seeds'] if alg == 'XGBoost' else cfg['seeds'][:1]
            for seed in seeds:
                for name in cfg['scenarios']:
                    columns = groups[name]
                    artifact = out / f'{alg}_{name}_{seed}'; artifact.mkdir()
                    with tracked(root, f'{alg}_{name}_seed{seed}', artifact,
                                 {'algorithm': alg, 'scenario': name, 'seed': seed,
                                  'features_count': len(columns), 'train_selection_n': len(train),
                                  'validation_n': len(val), 'train_final_n': len(full), 'test_n': len(test)}, nested=True) as run_info:
                        write_json(artifact / 'features.json', columns)
                        if alg == 'XGBoost':
                            params = dict(cfg['xgboost'], random_state=seed)
                            candidate = XGBRegressor(**params)
                            candidate.fit(train[columns], train[TARGET], eval_set=[(val[columns], val[TARGET])], verbose=False)
                            count = int(candidate.best_iteration) + 1
                            pv = candidate.predict(val[columns])
                            params.pop('early_stopping_rounds'); params['n_estimators'] = count
                            final_model = XGBRegressor(**params)
                        else:
                            params = cfg['elasticnet']
                            candidate = make_pipeline(StandardScaler(), ElasticNet(**params))
                            candidate.fit(train[columns], train[TARGET]); pv = candidate.predict(val[columns]); count = 0
                            final_model = make_pipeline(StandardScaler(), ElasticNet(**params))
                        # Save the choice BEFORE predicting the test, never choose using its metrics.
                        choice = dict(algorithm=alg, scenario=name, seed=seed, selected_trees=count,
                                      selection_metric='validation_RMSE', **metrics(val[TARGET], pv))
                        selectors.append(choice); write_json(artifact / 'selection_before_test.json', choice)
                        final_model.fit(full[columns], full[TARGET]); pred = final_model.predict(test[columns])
                        for split, y, p in [('validation', val[TARGET], pv), ('retrospective_test', test[TARGET], pred)]:
                            m = metrics(y, p); log_metrics(m, split + '_')
                            rows.append(dict(algorithm=alg, scenario=name, seed=seed, partition=split,
                                             mlflow_run_id=run_info.info.run_id, **m))
                        joblib.dump(final_model, artifact / 'model.joblib')
                        pd.DataFrame({'timestamp': test.timestamp, 'actual': test[TARGET], 'prediction': pred}).to_parquet(artifact / 'predictions.parquet', index=False)
                        predictions.append(pd.DataFrame({'timestamp': test.timestamp, 'actual': test[TARGET], 'prediction': pred,
                                                         'algorithm': alg, 'scenario': name, 'seed': seed}))
                        pd.DataFrame(rows).to_csv(out / 'metrics.csv', index=False)
                        print(alg, name, seed, metrics(test[TARGET], pred), flush=True)
        pd.DataFrame(selectors).to_csv(out / 'selection.csv', index=False)
        pd.concat(predictions, ignore_index=True).to_parquet(out / 'predictions.parquet', index=False)
        result = {'completed': True, 'configuration_sha256': digest(config_path), 'output': out.relative_to(root).as_posix(),
                  'model_fits': len(selectors), 'test_reused': True, 'automl': False, 'correction': False,
                  'note': 'Piloto exploratório; uma semente não demonstra robustez. Seleção feita na validação.'}
        write_json(out / 'completed.json', result)
        write_json(root / 'outputs/iatan_consolidado/latest_experiment.json', result)
    return result
