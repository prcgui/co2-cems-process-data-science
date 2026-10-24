"""Audit the cited boosting/temporal code without rerunning the research fits.

Run with the project's reproduction dependencies (xgboost 3.4.1, sklearn 1.8.0,
pandas 2.2.3, numpy 2.3.5, pyarrow 26.0.0). Inputs and notebooks are read only. Paths are supplied as command-line arguments.
Only small synthetic models are trained; saved research models are only loaded.
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import hashlib
import io
import json
import math
import platform
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent

import numpy as np
import pandas as pd
import sklearn
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import ParameterSampler
from xgboost import XGBRegressor

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--repo", type=Path, required=True, help="Project repository, including outputs/tables and input manifest")
parser.add_argument("--notebooks", type=Path, help="Notebook directory; defaults to REPO/notebooks")
parser.add_argument("--zip", dest="input_zip", type=Path, required=True, help="Preserved reproduction package ZIP")
parser.add_argument("--output", type=Path, required=True, help="Audit JSON destination")
parser.add_argument("--source-evidence", type=Path, help="Optional source evidence JSON")
parser.add_argument("--reference-commit", default="unspecified", help="Commit identifying the notebook version being checked")
args = parser.parse_args()
REPO = args.repo.expanduser().resolve()
NB_DIR = (args.notebooks or REPO / "notebooks").expanduser().resolve()
TABLES = REPO / "outputs/tables"
ZIP_PATH = args.input_zip.expanduser().resolve()
OUTPUT_PATH = args.output.expanduser().resolve()
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
COMMIT = args.reference_commit
NBS = {p: next(NB_DIR.glob(p + "*.ipynb")) for p in ("03A.02", "03A.03", "03A.04", "03A.05")}
NOTEBOOKS = {p: json.loads(path.read_text()) for p, path in NBS.items()}
CHECKS = []


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source(nb, cell):
    return "".join(NOTEBOOKS[nb]["cells"][cell - 1]["source"])


def nodes(nb, cell):
    return ast.parse(source(nb, cell)).body


def assigned(node):
    if isinstance(node, ast.Assign):
        return {t.id for t in node.targets if isinstance(t, ast.Name)}
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return {node.name}
    return set()


def namespace(**extra):
    return dict(np=np, pd=pd, XGBRegressor=XGBRegressor, ParameterSampler=ParameterSampler,
                mean_absolute_error=mean_absolute_error, mean_squared_error=mean_squared_error,
                r2_score=r2_score, SEED=42, SEED_LOCAL=42, selected_unit={"year": 2025},
                Path=Path, print=lambda *a, **k: None, display=lambda *a, **k: None, **extra)


def execute(nb, cell, env, names=None, body=None):
    body = nodes(nb, cell) if body is None else body
    if names is not None:
        body = [n for n in body if assigned(n) & set(names)]
    tree = ast.fix_missing_locations(ast.Module(body=copy.deepcopy(body), type_ignores=[]))
    exec(compile(tree, f"{NBS[nb].name}:cell-{cell}", "exec"), env)


def span(nb, cell, start, before):
    body = nodes(nb, cell)
    i = next(i for i, n in enumerate(body) if start in assigned(n))
    j = next(i for i, n in enumerate(body) if before in assigned(n))
    return body[i:j]


def add(key, method, cells, conditions, results, passed=True, conclusion="Verificação aprovada."):
    CHECKS.append(dict(id=key, method=method, code_cells=cells, conditions=conditions,
                       results=results, passed=bool(passed), conclusion=conclusion))
    if not passed:
        raise AssertionError(key)


def stamp_hash(frame):
    return sha(pd.to_datetime(frame["timestamp"]).to_numpy(dtype="datetime64[ns]").tobytes())


def summary(frame):
    return {"n": len(frame), "start": str(frame.timestamp.min()), "end": str(frame.timestamp.max()),
            "timestamp_sha256": stamp_hash(frame), "duplicates": int(frame.timestamp.duplicated().sum())}


def native_tree_value(tree, row):
    if "leaf" in tree:
        return tree["leaf"]
    index = int(tree["split"].removeprefix("f"))
    branch = tree["yes"] if row[index] < tree["split_condition"] else tree["no"]
    child = next(c for c in tree["children"] if c["nodeid"] == branch)
    return native_tree_value(child, row)


def run():
    z = zipfile.ZipFile(ZIP_PATH)
    read = lambda name: pd.read_parquet(io.BytesIO(z.read(name)))
    early_df = read("originais_preservados/data/interim/step05_feature_engineering.parquet")
    early_df["timestamp"] = pd.to_datetime(early_df.timestamp)
    early_df = early_df.sort_values("timestamp").reset_index(drop=True)

    # Execute actual constructors and assignments, without any research fit.
    e2 = namespace(df=early_df.copy())
    execute("03A.02", 6, e2)
    execute("03A.02", 7, e2)
    execute("03A.02", 11, e2)
    execute("03A.02", 14, e2)
    execute("03A.02", 16, e2)
    execute("03A.02", 20, e2)
    e3 = namespace(df=early_df.copy())
    for c in (5, 8, 11, 13):
        execute("03A.03", c, e3)
    e4 = namespace(FACILITY_ID="6065", UNIT_ID="2")
    execute("03A.04", 3, e4, names=["XGB_PARAMS", "build_xgb", "load_verified_annual_frame"])
    execute("03A.04", 11, e4, names=["build_xgb_03A04"])
    execute("03A.04", 16, e4, names=["build_selection_model", "build_final_model", "calculate_metrics"])
    e5 = namespace()
    execute("03A.05", 3, e5, names=["TARGET", "FEATURES_A", "FEATURES_B", "REFERENCE_START_YEAR",
        "REFERENCE_END_YEAR", "TARGET_YEAR", "TRAIN_RECENT_END", "VALIDATION_START", "VALIDATION_END",
        "TEST_START", "TEST_END", "XGB_PARAMS_SELECTION", "regression_metrics"])
    params = {
        "03A.02_reference": e2["build_xgb"]().get_params(),
        "03A.03_first_candidate": e3["build_xgb_from_config"](e3["sampled_configs"][0]).get_params(),
        "03A.04_backtest": e4["build_xgb_03A04"]().get_params(),
        "03A.04_selection": e4["build_selection_model"]().get_params(),
        "03A.04_final_example": e4["build_final_model"](123).get_params(),
        "03A.05_selection": XGBRegressor(**e5["XGB_PARAMS_SELECTION"]).get_params(),
    }
    assert all(p["objective"] == "reg:squarederror" for p in params.values())
    assert e2["XGB_PARAMS"] == e4["XGB_PARAMS"] == e5["XGB_PARAMS_SELECTION"]
    assert params["03A.03_first_candidate"]["tree_method"] == "hist"
    assert params["03A.03_first_candidate"]["early_stopping_rounds"] is None
    assert params["03A.04_final_example"]["early_stopping_rounds"] is None
    add("constructors", "Instanciação das funções e dicionários reais, sem ajuste.",
        {"03A.02": [14, 16], "03A.03": [11, 13], "03A.04": [3, 11, 16], "03A.05": [3]},
        "None abaixo significa parâmetro não explicitado; não foi atribuído retroativamente ao experimento.",
        {k: {a: b for a, b in v.items() if b is not None} for k, v in params.items()},
        conclusion="Objetivo quadrático e regularização L2 são efetivamente passados. A referência usa L1=0; a busca varia L1, L2 e gamma. RMSE/MAE de seleção não substituem o objetivo quadrático.")

    # Small mathematical checks with the real notebook factory and real CPU XGBoost.
    X = np.array([[0.], [0.], [1.], [1.]], dtype=np.float32)
    y = np.array([0., 2., 8., 10.], dtype=np.float32)
    toy = dict(n_estimators=1, learning_rate=1., max_depth=1, min_child_weight=1,
               subsample=1., colsample_bytree=1., reg_alpha=0., reg_lambda=1., gamma=0.)
    model = e3["build_xgb_from_config"](toy).set_params(n_jobs=1, base_score=5.)
    model.fit(X, y, verbose=False)
    tree = json.loads(model.get_booster().get_dump(dump_format="json", with_stats=True)[0])
    expected_weights = np.array([-8 / 3, 8 / 3])
    actual_weights = np.array([c["leaf"] for c in tree["children"]])
    np.testing.assert_allclose(actual_weights, expected_weights, atol=2e-7, rtol=1e-7)
    expected_pred = 5 + expected_weights[[0, 0, 1, 1]]
    np.testing.assert_allclose(model.predict(X), expected_pred, atol=1e-6)
    initial_loss = .5 * np.square(y - 5).sum()
    final_objective = .5 * np.square(y - model.predict(X)).sum() + .5 * np.square(actual_weights).sum()
    add("chen_leaf_weights", "Conferência numérica da equação (5) de Chen e Guestrin.",
        {"03A.03": [13]},
        "Caso sintético de quatro observações, uma árvore, intercepto 5, eta=1, lambda=1, alpha=gamma=0, sem subamostragem. g=pred-y e h=1, correspondentes a metade do erro quadrático.",
        {"expected_leaf_weights": expected_weights.tolist(), "actual_leaf_weights": actual_weights.tolist(),
         "max_prediction_difference": float(np.max(abs(model.predict(X) - expected_pred))),
         "initial_data_loss": float(initial_loss), "final_data_loss_plus_L2": float(final_objective)},
        conclusion="Pesos e predições coincidem com a minimização regularizada da formulação original nas condições declaradas.")

    # L1 is an API extension; do not attribute it to the paper's displayed L2 objective.
    l1 = e3["build_xgb_from_config"]({**toy, "reg_alpha": 2.}).set_params(n_jobs=1, base_score=5.)
    l1.fit(X, y, verbose=False)
    np.testing.assert_allclose(l1.predict(X), [3., 3., 7., 7.], atol=1e-6)
    high_gamma = e3["build_xgb_from_config"]({**toy, "gamma": 1e6}).set_params(n_jobs=1, base_score=5.)
    high_gamma.fit(X, y, verbose=False)
    gamma_tree = json.loads(high_gamma.get_booster().get_dump(dump_format="json")[0])
    assert "leaf" in gamma_tree
    add("regularization_api", "Teste de soft threshold L1 e bloqueio de divisão por gamma.", {"03A.03": [11, 13]},
        "Mesmo caso sintético; L1=2 em um teste; gamma=1e6 no outro. Sem inferência sobre ganhos de Iatan.",
        {"L1_predictions": l1.predict(X).tolist(), "large_gamma_produces_single_leaf": "leaf" in gamma_tree},
        conclusion="Os parâmetros de regularização da busca têm efeito verificável na API utilizada. L1 é documentado pela biblioteca, não pela equação (2) de Chen.")

    sequential_config = {**toy, "n_estimators": 3, "learning_rate": .03}
    seq = e3["build_xgb_from_config"](sequential_config).set_params(n_jobs=1, base_score=5.)
    seq.fit(X, y, verbose=False)
    trees = [json.loads(t) for t in seq.get_booster().get_dump(dump_format="json")]
    additive = np.array([5. + sum(native_tree_value(t, row) for t in trees) for row in X])
    np.testing.assert_allclose(seq.predict(X), additive, atol=1e-6)
    custom = e3["build_xgb_from_config"](sequential_config).set_params(
        n_jobs=1, base_score=5., objective=lambda y_true, pred: (pred - y_true, np.ones_like(pred)))
    custom.fit(X, y, verbose=False)
    np.testing.assert_allclose(seq.predict(X), custom.predict(X), atol=1e-7)
    add("additive_and_squared_objective", "Soma das árvores e equivalência ao gradiente/hessiana quadráticos explícitos.",
        {"03A.03": [13]}, "Três árvores sintéticas com eta=.03; mesmo intercepto, regularização e estrutura.",
        {"n_trees": len(trees), "max_additive_difference": float(max(abs(seq.predict(X) - additive))),
         "max_custom_objective_difference": float(max(abs(seq.predict(X) - custom.predict(X))))},
        conclusion="A implementação realiza construção aditiva e o objetivo reg:squarederror coincide com g=pred-y, h=1. Isso verifica o mecanismo aplicado, não os benchmarks de Friedman ou Chen.")

    es = e2["build_xgb"]().set_params(n_estimators=100, learning_rate=.3, max_depth=1,
        min_child_weight=1, subsample=1., colsample_bytree=1., early_stopping_rounds=5,
        n_jobs=1, base_score=20.)
    xx = np.arange(40, dtype=np.float32).reshape(-1, 1)
    xv = np.arange(10, dtype=np.float32).reshape(-1, 1)
    es.fit(xx, xx[:, 0], eval_set=[(xv, np.full(10, 1000.))], verbose=False)
    default = es.predict(xv)
    best = es.predict(xv, iteration_range=(0, es.best_iteration + 1))
    full = es.predict(xv, iteration_range=(0, es.get_booster().num_boosted_rounds()))
    np.testing.assert_allclose(default, best, atol=0)
    assert es.get_booster().num_boosted_rounds() > es.best_iteration + 1
    assert np.max(abs(full - default)) > 0
    add("early_stopping_prediction", "Comportamento real de best_iteration e predict.",
        {"03A.02": [14, 16, 21], "03A.05": [15, 18]},
        "Exemplo sintético que provoca parada; paciência reduzida a 5 apenas para o teste da API.",
        {"best_iteration_zero_based": es.best_iteration, "selected_trees": es.best_iteration + 1,
         "trees_stored": es.get_booster().num_boosted_rounds(),
         "default_equals_selected_iteration_range": True,
         "max_full_vs_selected_difference": float(np.max(abs(full - default)))},
        conclusion="Somar 1 a best_iteration é correto. predict usa automaticamente a melhor iteração, embora a árvore armazenada possa incluir rodadas posteriores.")

    # Random candidate reproduction and saved 300 fits.
    candidates = e3["sampled_configs"]
    keys = [json.dumps(c, sort_keys=True) for c in candidates]
    assert len(keys) == len(set(keys)) == 30
    assert candidates == list(ParameterSampler(e3["SEARCH_SPACE"], n_iter=30, random_state=42))
    space_size = math.prod(len(v) for v in e3["SEARCH_SPACE"].values())
    results = pd.read_csv(TABLES / "03A03_tuning_results_AB.csv")
    saved_summary = pd.read_csv(TABLES / "03A03_tuning_summary_AB.csv")
    assert len(results) == 300 and not results.duplicated(["config_id", "cenario", "fold"]).any()
    expected_keys = {(cid, s, f) for cid in e3["config_ids"] for s in ("A", "B") for f in range(1, 6)}
    assert set(results[["config_id", "cenario", "fold"]].itertuples(index=False, name=None)) == expected_keys
    for cid, config in e3["config_lookup"].items():
        for _, row in saved_summary.loc[saved_summary.config_id == cid].iterrows():
            for name, value in config.items():
                assert np.isclose(row[name], value, rtol=0, atol=1e-12)
    e3["tuning_results"] = results
    execute("03A.03", 17, e3)
    execute("03A.03", 18, e3)
    a = e3["tuning_summary"].sort_values(["cenario", "config_id"]).reset_index(drop=True)
    b = saved_summary.sort_values(["cenario", "config_id"]).reset_index(drop=True)
    metric_cols = [c for c in a if c.endswith("_mean") or c.endswith("_std")]
    np.testing.assert_allclose(a[metric_cols], b[metric_cols], rtol=1e-12, atol=1e-10)
    best_saved = json.loads(z.read("projeto/outputs/tables/03A03_best_configs_AB.json"))
    assert best_saved["A"] == e3["best_config_A"] and best_saved["B"] == e3["best_config_B"]
    add("paired_random_search", "Reexecução da amostragem e da classificação reais, usando as 300 métricas salvas.",
        {"03A.03": [8, 11, 13, 16, 17, 18]},
        "Não houve novo treinamento dos 300 modelos. Todas as nove dimensões usam listas; sorteio finito sem reposição.",
        {"space_size": space_size, "draws": len(candidates), "unique_candidates": len(set(keys)),
         "coverage_percent": 100 * len(candidates) / space_size,
         "same_seed_exact_candidates": True, "all_saved_parameters_match": True,
         "saved_fit_rows": len(results), "complete_config_scenario_fold_product": True,
         "best_A": e3["best_config_A_id"], "best_B": e3["best_config_B_id"],
         "saved_best_config_file": best_saved},
        conclusion="A busca aleatória pareada foi aplicada corretamente. A ordenação usa MAE médio, seguido por RMSE médio e desvio padrão do MAE. Trinta tentativas são um orçamento, não demonstração de suficiência.")

    # Actual temporal assignments on actual preserved 2025 features.
    assert e2["FOLDS"] == e3["FOLDS"]
    assert stamp_hash(e2["experiment_data"]) == stamp_hash(e3["experiment_data"])
    fold_details = []
    for f in e3["FOLDS"]:
        frame = e3["experiment_data"]
        train = frame.loc[frame.timestamp <= pd.Timestamp(f["train_end"])]
        val = frame.loc[frame.timestamp.between(pd.Timestamp(f["val_start"]), pd.Timestamp(f["val_end"]))]
        assert set(train.timestamp).isdisjoint(val.timestamp)
        assert train.timestamp.max() < val.timestamp.min()
        rows = results[results.fold == f["fold"]]
        assert rows.n_train.eq(len(train)).all() and rows.n_validation.eq(len(val)).all()
        fold_details.append({"fold": f["fold"], "train": summary(train), "validation": summary(val)})
    execute("03A.03", 21, e3, names=["DEVELOPMENT_END", "development_data", "holdout_data"])
    assert set(e3["development_data"].timestamp).isdisjoint(e3["holdout_data"].timestamp)
    assert len(e3["development_data"]) == 5105 and len(e3["holdout_data"]) == 1144
    add("2025_temporal_splits", "Divisões reais dos notebooks aplicadas aos Parquets preservados.",
        {"03A.02": [6, 7, 11, 17, 20, 21, 28], "03A.03": [5, 8, 16, 21]},
        "Mesma base elegível e mesmos timestamps entre A/B/C; folds junho-outubro; teste novembro-dezembro.",
        {"common_eligible_rows": len(e3["experiment_data"]), "folds": fold_details,
         "reference_train": summary(e2["train_data"]), "reference_validation": summary(e2["validation_data"]),
         "reference_test": summary(e2["test_data"]), "search_refit": summary(e3["development_data"]),
         "search_test": summary(e3["holdout_data"])},
        conclusion="Não há sobreposição temporal de linhas. A referência usa janeiro-setembro para ajuste; a busca reajusta janeiro-outubro. Os escores dos folds participam do desenvolvimento e o teste já era conhecido no projeto.")

    # Load saved research models: inference only, no research fit.
    saved_preds = pd.read_csv(TABLES / "03A02_previsoes_xgboost.csv")
    saved_model_checks = []
    for scenario in ("B", "C"):
        name = f"originais_preservados/outputs/models/03A02_xgboost_{scenario}.json"
        loaded = XGBRegressor()
        loaded.load_model(bytearray(z.read(name)))
        features = e2["FEATURES_B"] if scenario == "B" else e2["FEATURES_C"]
        actual = loaded.predict(e2["test_data"][features])
        col = f"pred_{scenario}_XGBoost"
        expected = saved_preds[col].to_numpy()
        np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-4)
        native = json.loads(loaded.get_booster().save_config())
        saved_model_checks.append({"scenario": scenario, "model_member": name, "sha256": sha(z.read(name)),
            "objective": native["learner"]["objective"]["name"], "n_test": len(actual),
            "best_iteration": loaded.best_iteration,
            "trees_stored": loaded.get_booster().num_boosted_rounds(),
            "max_prediction_difference": float(np.max(abs(actual - expected)))})
    add("saved_xgboost_inference", "Inferência dos modelos B/C realmente preservados, com a base reconstruída.",
        {"03A.02": [6, 7, 20, 21]},
        "Somente load_model e predict; tolerância absoluta 1e-4, relativa 1e-6 para serialização/versão CPU.",
        saved_model_checks, conclusion="Os modelos preservados reproduzem as previsões salvas no teste, sem retreino.")

    # Verify annual input identity with the real input validator, and rebuild history.
    input_manifest = json.loads((REPO / "outputs/reproducibility/input_manifest.json").read_text())
    input_by_path = {r["path"]: r for r in input_manifest}
    annual_checks, annual_frames = [], []
    with tempfile.TemporaryDirectory(prefix="annual-check-", dir=OUTPUT_PATH.parent) as temp:
        for year in range(2010, 2026):
            rel = f"data/interim/03A04_multiyear/iatan_unit2_{year}.parquet"
            data = z.read("projeto/" + rel)
            assert sha(data) == input_by_path[rel]["sha256"]
            path = Path(temp) / Path(rel).name
            path.write_bytes(data)
            frame = e4["load_verified_annual_frame"](path, year)
            annual_frames.append(frame)
            annual_checks.append({"year": year, "n": len(frame), "sha256": sha(data), "manifest_matches": True})
    history = pd.concat(annual_frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    history["year"] = history.timestamp.dt.year
    assert history.timestamp.is_unique
    assert len(pd.date_range(history.timestamp.min(), history.timestamp.max(), freq="h")) == len(history)
    e4["history"] = history
    execute("03A.04", 11, e4, names=["TARGET_YEARS", "HISTORY_WINDOWS", "FEATURE_A", "TARGET_A", "VALIDATION_START_MONTH", "experiment_A"])
    # Use the original nested loops and date filters, cutting only the model-fitting tail.
    outer = copy.deepcopy(next(n for n in nodes("03A.04", 11) if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "target_year"))
    inner = next(n for n in outer.body if isinstance(n, ast.For) and isinstance(n.target, ast.Name) and n.target.id == "history_years")
    stop = next(i for i, n in enumerate(inner.body) if "model" in assigned(n))
    captured = []
    def capture_backtest():
        tr, va, te = e4["train_data"], e4["validation_data"], e4["test_data"]
        assert set(tr.timestamp).isdisjoint(va.timestamp)
        assert set(tr.timestamp).isdisjoint(te.timestamp)
        assert set(va.timestamp).isdisjoint(te.timestamp)
        captured.append(dict(target_year=e4["target_year"], history_years=e4["history_years"],
            n_train=len(tr), n_validation=len(va), n_test=len(te),
            train_start=str(tr.timestamp.min()), train_end=str(tr.timestamp.max()),
            validation_start=str(va.timestamp.min()), validation_end=str(va.timestamp.max()),
            test_start=str(te.timestamp.min()), test_end=str(te.timestamp.max())))
    e4["capture_backtest"] = capture_backtest
    inner.body = inner.body[:stop] + ast.parse("capture_backtest()").body
    execute("03A.04", 11, e4, body=[outer])
    saved_backtests = pd.read_csv(TABLES / "03A04_backtest_volume_historico_A.csv")
    for rec in captured:
        row = saved_backtests[(saved_backtests.target_year == rec["target_year"]) & (saved_backtests.history_years == rec["history_years"])].iloc[0]
        for k, v in rec.items():
            assert row[k] == v, (k, row[k], v)
    add("historical_backtest_splits", "Validador anual real e laços reais de datas, interrompidos antes do fit.",
        {"03A.04": [3, 7, 11]},
        "Os 16 anuais coincidem com o manifesto da reprodução; 25 divisões conferidas com a tabela original. Nenhuma predição sintética substitui resultado do estudo.",
        {"annual_inputs": annual_checks, "history_rows": len(history), "backtest_splits": captured,
         "all_counts_and_dates_match_saved_table": True},
        conclusion="Treino, validação no trimestre anterior e ano-alvo são disjuntos. As janelas variam quantidade, antiguidade e composição dos dados; seu melhor MAE por ano é diagnóstico retrospectivo.")

    execute("03A.04", 13, e4, names=["REFERENCE_START_YEAR", "REFERENCE_END_YEAR", "DISTINCT_REGIME_YEARS", "GENERALIZATION_TARGET_YEAR", "primary_training_sample", "generalization_target"])
    # Repeat the chronological tail of 2022 used to choose trees, before model creation.
    execute("03A.04", 14, e4, names=["VALIDATION_FRACTION_2022", "data_2022", "n_validation", "validation_2022", "validation_start", "development_train"])
    assert e4["development_train"].timestamp.max() < e4["validation_2022"].timestamp.min()
    assert e4["validation_2022"].timestamp.max() < e4["generalization_target"].timestamp.min()
    execute("03A.04", 16, e4, names=["data_2025", "TRAIN_RECENT_END", "VALIDATION_START", "VALIDATION_END", "TEST_START", "TEST_END", "recent_train_initial", "validation_2025", "test_2025", "historical_reference", "recent_train_final", "history_plus_recent_initial", "history_plus_recent_final"])
    add("history_selection_and_refits", "Filtros reais de 2011-2022, validação em 2022 e acréscimo de dados de 2025.",
        {"03A.04": [9, 11, 13, 14, 16]},
        "Cortes de histórico são constantes explícitas. Indicadores com referência 2025 e backtests precedem a delimitação no notebook; não se atribui independência global ao ano-alvo.",
        {k: summary(e4[k]) for k in ["primary_training_sample", "development_train", "validation_2022", "generalization_target", "recent_train_initial", "validation_2025", "test_2025", "recent_train_final", "history_plus_recent_final"]},
        conclusion="A aplicação dos cortes e reajustes é coerente. A exclusão exploratória de 2023/2024 não equivale a um critério confirmatório definido antes dos resultados e deve continuar explicitada como limitação.")

    # Rebuild eligibility and sample splits from the exact actual notebook operations.
    e5["df_features"] = read("projeto/data/interim/03A05_trajectory_history/03A05_base_features_trajetoria.parquet")
    execute("03A.05", 9, e5, body=nodes("03A.05", 9)[:next(i for i,n in enumerate(nodes("03A.05", 9)) if "STARTUP_AGE_AUDIT_PATH" in assigned(n))])
    execute("03A.05", 12, e5, body=span("03A.05", 12, "common_eligibility_mask", "sample_sizes"))
    final_splits = {"train_selection_common": "03A05_treino_selecao_A_B.parquet",
                    "validation_common": "03A05_validacao_outubro_2025_A_B.parquet",
                    "train_final_common": "03A05_treino_final_A_B.parquet",
                    "test_common": "03A05_teste_nov_dez_2025_A_B.parquet"}
    for variable, filename in final_splits.items():
        saved = read("projeto/data/interim/03A05_trajectory_history/" + filename)
        actual = e5[variable]
        assert stamp_hash(actual) == stamp_hash(saved)
        np.testing.assert_allclose(actual[e5["FEATURES_B"] + [e5["TARGET"]]], saved[e5["FEATURES_B"] + [e5["TARGET"]]], atol=0, rtol=0)
    tr, va, fin, te = (e5[k] for k in final_splits)
    assert set(tr.timestamp).isdisjoint(va.timestamp)
    assert set(fin.timestamp).isdisjoint(te.timestamp)
    assert set(va.timestamp).isdisjoint(te.timestamp)
    assert set(fin.timestamp) == set(tr.timestamp) | set(va.timestamp)
    assert not fin.source_year.isin([2023, 2024]).any()
    selection = pd.read_csv(TABLES / "03A05_selecao_complexidade_A_B.csv")
    assert (selection.selected_trees == selection.best_iteration + 1).all()
    assert selection.n_train.eq(len(tr)).all() and selection.n_validation.eq(len(va)).all()
    e5["SELECTED_TREES"] = dict(zip(selection.scenario, selection.selected_trees))
    execute("03A.05", 18, e5, body=nodes("03A.05", 18)[:next(i for i,n in enumerate(nodes("03A.05", 18)) if "X_train_final_A" in assigned(n))])
    assert "early_stopping_rounds" not in e5["FINAL_BASE_PARAMS"]
    assert "n_estimators" not in e5["FINAL_BASE_PARAMS"]
    final_params = {s: XGBRegressor(**e5["FINAL_BASE_PARAMS"], n_estimators=int(n)).get_params() for s,n in e5["SELECTED_TREES"].items()}
    assert final_params["A"]["n_estimators"] == 498 and final_params["B"]["n_estimators"] == 721
    add("final_paired_sample_and_refit", "Reexecução da elegibilidade e dos filtros reais; construção dos modelos finais sem fit.",
        {"03A.05": [3, 9, 12, 15, 18]},
        "A/B usam as mesmas linhas e respostas; vetores com 1/7 entradas. Seleção RMSE em outubro e reajuste com outubro incorporado.",
        {"unknown_startup_age_hours": e5["n_unknown_startup_age"], "common_rows": len(e5["common_sample"]),
         "splits": {k: summary(e5[k]) for k in final_splits}, "all_saved_frames_match_exactly": True,
         "selected_trees": e5["SELECTED_TREES"], "early_stopping_removed_before_refit": True,
         "same_final_parameters_except_trees": {k:v for k,v in e5["FINAL_BASE_PARAMS"].items()}},
        conclusion="Pareamento, exclusões, datas, 498/721 árvores e retirada do early stopping são aplicados corretamente. A comparação envolve modelos ajustados pela mesma regra, com complexidades próprias.")

    preds = read("projeto/data/interim/03A05_trajectory_history/03A05_previsoes_pareadas_A_B_nov_dez_2025.parquet")
    assert stamp_hash(preds) == stamp_hash(te)
    saved_metrics = pd.read_csv(TABLES / "03A05_resultado_final_A_B.csv")
    recomputed = {}
    for s in ("A", "B"):
        measured = e5["regression_metrics"](preds[e5["TARGET"]], preds["pred_" + s])
        row = saved_metrics.loc[saved_metrics.scenario == s].iloc[0]
        for name, value in measured.items():
            assert np.isclose(value, row[name], rtol=1e-10, atol=1e-8), (s,name,value,row[name])
        recomputed[s] = measured
    add("preserved_metrics", "Função de métricas real aplicada às previsões preservadas.",
        {"03A.05": [3, 18]}, "Sem treinamento. Confere também identidade e ordem dos 1.144 timestamps.",
        {"recomputed": recomputed, "all_metric_columns_match_saved_table": True},
        conclusion="As métricas finais correspondem às predições preservadas. Nenhum resultado numérico precisou ser corrigido nestas verificações.")

    return {"audit_date_utc": datetime.now(timezone.utc).isoformat(), "notebook_commit": COMMIT,
        "cell_numbering": "1-based, incluindo células Markdown", "scope": list(NBS),
        "environment": {"python": platform.python_version(), "xgboost": xgb.__version__,
            "xgboost_build": "CPU wheel, same library version as reproduction; no GPU used",
            "scikit_learn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__},
        "notebooks": {p: {"path": str(f), "sha256": sha(f.read_bytes())} for p,f in NBS.items()},
        "preserved_input_zip": {"path": str(ZIP_PATH), "sha256": sha(ZIP_PATH.read_bytes())},
        "research_models_retrained": 0, "research_models_loaded_for_inference": 2,
        "synthetic_models_trained": 6, "checks": CHECKS,
        "all_checks_passed": all(c["passed"] for c in CHECKS),
        "conclusion": "Os mecanismos examinados são coerentes com o uso de boosting quadrático regularizado, busca aleatória pareada e divisão temporal descritos. As verificações não encontraram erro numérico que exija alterar resultados. São necessárias correções documentais das alegações de suficiência da busca, isolamento exclusivo de efeitos e independência global do teste. A seleção exploratória do histórico e o teste reutilizado permanecem limitações do desenho.",
        "limits": ["Não foram reexecutados os 300 ajustes da busca nem os 25 backtests.",
                   "O teste numérico sintético verifica a operação matemática e a API, não a qualidade preditiva de todos os modelos de Iatan.",
                   "As árvores finais de 03A.05 foram conferidas pelas seleções e resultados preservados; não houve novo treinamento para procurar outro resultado.",
                   "Datas disjuntas dentro de cada ajuste não tornam independente uma pesquisa que já consultou o período de teste."]}


if __name__ == "__main__":
    result = run()
    source_path = args.source_evidence or HERE / "boosting_source_evidence.json"
    if source_path.exists():
        result["source_evidence"] = json.loads(source_path.read_text())
    output = OUTPUT_PATH
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=lambda x: x.item() if isinstance(x,np.generic) else str(x)) + "\n")
    print(json.dumps({"output": str(output), "checks": len(CHECKS), "all_passed": result["all_checks_passed"]}, ensure_ascii=False))
