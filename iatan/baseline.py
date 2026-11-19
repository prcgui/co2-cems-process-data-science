"""Reprodução controlada do 03A.05. Chen & Guestrin (2016); Hyndman & Koehler (2006)."""
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd
import xgboost
from xgboost import XGBRegressor
from .data import B0, TARGET, HISTORY, digest, freeze, load_splits, write_json
from .tracking import configure, tracked, log_metrics


def metrics(y, pred):
    y, pred = np.asarray(y, float), np.asarray(pred, float)
    e = pred - y
    return {'MAE': float(np.abs(e).mean()), 'RMSE': float(np.sqrt(np.mean(e * e))),
            'R2': float(1 - np.sum(e * e) / np.sum((y - y.mean()) ** 2)),
            'Bias_pred_minus_real': float(e.mean()), 'n': int(len(y))}


def verify_frozen_reference(root):
    """Verify preserved model inference; never label this a successful retraining.

    A retains prediction-level evidence; B additionally has a preserved fitted model.
    """
    freeze(root)
    cfg = json.loads((root / 'configs/frozen_reference.json').read_text(encoding='utf-8'))
    path = root / cfg['model_path']
    if digest(path) != cfg['model_sha256']:
        raise ValueError('Modelo congelado alterado')
    reference_path = root / HISTORY / '03A05_previsoes_pareadas_com_contextos.parquet'
    if digest(reference_path) != cfg['expected_prediction_sha256']:
        raise ValueError('Previsões de referência alteradas')
    test = load_splits(root)['test']; ref = pd.read_parquet(reference_path)
    np.testing.assert_array_equal(test.timestamp, ref.timestamp)
    np.testing.assert_array_equal(test[TARGET], ref[TARGET])
    model = XGBRegressor(); model.load_model(path)
    pred = model.predict(test[B0])
    delta = float(np.max(np.abs(pred - ref.pred_B)))
    if delta > 1e-6: raise AssertionError('Inferência congelada divergente')
    expected = pd.read_csv(root / 'reproducibility/baselines/03A05_resultado_final_A_B.csv')
    rows = []
    for name in ['A', 'B']:
        row = metrics(test[TARGET], ref['pred_' + name])
        for col in ['MAE', 'RMSE', 'R2']:
            np.testing.assert_allclose(row[col], expected.loc[expected.scenario.eq(name), col].iloc[0], rtol=0, atol=1e-6)
        rows.append(dict(scenario=name, **row, evidence='frozen_model_inference' if name == 'B' else 'preserved_predictions_only'))
    configure(root)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out = root / 'outputs/iatan_consolidado/frozen_reference' / stamp; out.mkdir(parents=True)
    result = {'reference_verified': True, 'B_inference_max_difference': delta,
              'historical_retraining_verified': False, 'A_model_available': False,
              'reference_config_sha256': digest(root / 'configs/frozen_reference.json'),
              'inputs_manifest_sha256': digest(root / 'configs/iatan_inputs.json'),
              'metrics': rows, 'note': 'Inferência B e métricas A/B verificadas. Não equivale a retreinamento histórico idêntico.'}
    with tracked(root, 'REFERENCIA_CONGELADA_03A05', out, {'kind': 'frozen_reference_verification', 'historical_retraining_verified': False}):
        write_json(out / 'verification.json', result)
        pd.DataFrame(rows).to_csv(out / 'metrics.csv', index=False)
        log_metrics({'B_inference_max_difference': delta})
        write_json(root / 'outputs/iatan_consolidado/reference_verified.json', result)
    return result


def run(root):
    freeze(root)
    cfg = json.loads((root / 'configs/baseline_03A05.json').read_text(encoding='utf-8'))
    name = '03A.05_trajetoria_operacional_historico_ampliado.ipynb'
    notebook = root / 'notebooks/01_sem_mineracao_de_processos' / name
    if not notebook.is_file():
        notebook = root / 'notebooks' / name
    if digest(notebook) != cfg['source_notebook_sha256']:
        raise RuntimeError('Notebook fonte do baseline foi alterado')
    if xgboost.__version__ != cfg['xgboost_version']:
        raise RuntimeError('Baseline exige XGBoost ' + cfg['xgboost_version'])
    splits = load_splits(root); train, test = splits['train_final'], splits['test']
    ref = pd.read_parquet(root / HISTORY / '03A05_previsoes_pareadas_com_contextos.parquet')
    pd.testing.assert_series_equal(test.timestamp.reset_index(drop=True), ref.timestamp.reset_index(drop=True))
    np.testing.assert_array_equal(test[TARGET], ref[TARGET])
    config_hash = digest(root / 'configs/baseline_03A05.json')
    configure(root)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    out = root / 'outputs/iatan_consolidado/baseline' / stamp; out.mkdir(parents=True)
    rows = []; preds = test[['timestamp', TARGET]].copy()
    with tracked(root, 'REPRODUCAO_03A05', out, {'kind': 'baseline_reproduction', 'n_train': len(train), 'n_test': len(test)}):
        for scenario, features in [('A', ['load_current_mw']), ('B', B0)]:
            params = dict(cfg['params']); params.pop('early_stopping_rounds')
            params['n_estimators'] = cfg['selected_trees'][scenario]
            model = XGBRegressor(**params)
            model.fit(train[features], train[TARGET], verbose=False)
            pred = model.predict(test[features]); preds['pred_' + scenario] = pred
            delta = float(np.max(np.abs(pred - ref['pred_' + scenario].to_numpy())))
            row = dict(scenario=scenario, **metrics(test[TARGET], pred), max_prediction_difference=delta,
                       passed=delta <= cfg['prediction_atol'])
            rows.append(row)
            model.save_model(out / f'xgboost_{scenario}.json')
            log_metrics(metrics(test[TARGET], pred), scenario + '_')
            print('Baseline', scenario, row, flush=True)
        result = {'passed': all(r['passed'] for r in rows), 'checks': rows,
                  'config_sha256': config_hash, 'inputs_manifest_sha256': digest(root / 'configs/iatan_inputs.json'),
                  'tolerance': cfg['prediction_atol'], 'output': out.relative_to(root).as_posix()}
        pd.DataFrame(rows).to_csv(out / 'metrics.csv', index=False)
        preds.to_parquet(out / 'predictions.parquet', index=False)
        write_json(out / 'baseline_check.json', result)
        if not result['passed']:
            raise AssertionError('Baseline divergente: extensões bloqueadas; consultar baseline_check.json')
        write_json(root / 'outputs/iatan_consolidado/baseline_aprovado.json', result)
    return result
