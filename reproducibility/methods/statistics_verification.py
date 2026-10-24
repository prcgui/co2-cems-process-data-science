#!/usr/bin/env python3
"""Verify the public repository's corrected statistical code numerically.

Only AST-selected functions/statements are executed. No model is trained, no
notebook is rewritten, no network is used, and no project input is modified.
Cell numbers start at one and include every cell type.

Python 3.12; dependencies: numpy, pandas, scipy, scikit-learn.
From the repository root, for example:
    python reproducibility/methods/statistics_verification.py --repo .

Uses only public notebooks/, outputs/tables/ and reproducibility/monitoring/.
An external SHA-256 notebook manifest can optionally be supplied with --manifest.
The original bin-edge defect is demonstrated only by an isolated fixture; the
actual corrected notebook must retain its maximum-load observations.
"""
from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import math
import platform
import re
import statistics
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import sklearn
from sklearn.decomposition import PCA
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import MinMaxScaler, StandardScaler


# Paths are configured exclusively by command-line arguments in main().
NOTEBOOKS: Path
REPO: Path
TABLES: Path
MONITORING: Path
TARGET = "CO2 Mass (short tons)"
EXECUTED = []


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cell(name, number):
    obj = json.loads((NOTEBOOKS / name).read_text())
    item = obj["cells"][number - 1]
    assert item["cell_type"] == "code"
    return ast.parse("".join(item["source"]))


def assigned_names(node):
    if isinstance(node, ast.Assign):
        return {n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)}
    return set()


def prefix(tree, stop_name):
    answer = []
    for node in tree.body:
        if stop_name in assigned_names(node):
            break
        if not isinstance(node, (ast.Import, ast.ImportFrom, ast.Expr)):
            answer.append(node)
    else:
        raise AssertionError(f"Stop assignment not found: {stop_name}")
    return answer


def env(**extra):
    result = dict(np=np, pd=pd, re=re, PCA=PCA, StandardScaler=StandardScaler,
                  MinMaxScaler=MinMaxScaler, mean_absolute_error=mean_absolute_error,
                  mean_squared_error=mean_squared_error, r2_score=r2_score,
                  display=lambda *a, **k: None, print=lambda *a, **k: None)
    result.update(extra)
    return result


def execute(nodes, namespace, label):
    nodes = copy.deepcopy(nodes)
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    EXECUTED.append({
        "location": label,
        "original_cell_lines": [[n.lineno, n.end_lineno] for n in nodes],
        "selected_ast_sha256": hashlib.sha256(ast.dump(module).encode()).hexdigest(),
    })
    exec(compile(module, label, "exec"), namespace)
    return namespace


def function(name, number, function_name, namespace=None):
    nodes = [n for n in cell(name, number).body
             if isinstance(n, ast.FunctionDef) and n.name == function_name]
    assert len(nodes) == 1
    namespace = env() if namespace is None else namespace
    execute(nodes, namespace, f"{name}:célula {number}:{function_name}")
    return namespace[function_name]


def close(actual, expected, atol=1e-10, rtol=1e-10):
    np.testing.assert_allclose(actual, expected, atol=atol, rtol=rtol, equal_nan=True)


def manual_quantile(values, probability):
    values = sorted(float(x) for x in values if not math.isnan(float(x)))
    position = (len(values) - 1) * probability
    left = math.floor(position)
    right = math.ceil(position)
    return values[left] + (position - left) * (values[right] - values[left])


def manual_metrics(y, prediction):
    y = [float(x) for x in y]
    prediction = [float(x) for x in prediction]
    residuals = [a - b for a, b in zip(y, prediction, strict=True)]
    absolute = [abs(e) for e in residuals]
    n = len(y)
    mean = statistics.fmean(y)
    ss_res = sum(e * e for e in residuals)
    ss_tot = sum((a - mean) ** 2 for a in y)
    # Explicitly test the documented force_finite default for constant targets.
    score = 1 - ss_res / ss_tot if ss_tot else (1.0 if ss_res == 0 else 0.0)
    mae = statistics.fmean(absolute)
    nmae = 100 * mae / mean if mean != 0 else math.nan
    denom = sum(abs(a) for a in y)
    return dict(MAE=mae, RMSE=math.sqrt(ss_res / n), R2=score,
                MedianAE=statistics.median(absolute), Bias=statistics.fmean(residuals),
                NMAE_pct=nmae, **{"NMAE_%": nmae,
                "WAPE_%": 100 * sum(absolute) / denom if denom else math.nan})


def verify_iqr():
    name = "02_tratamento_dados.ipynb"
    series = pd.Series(list(range(10)) + [100, np.nan], dtype=float)
    f = function(name, 7, "calculate_iqr_limits")
    observed = f(series)
    q1 = manual_quantile(series, .25)
    q3 = manual_quantile(series, .75)
    reference = dict(q1=q1, q3=q3, iqr=q3-q1,
                     lower_limit=q1-1.5*(q3-q1), upper_limit=q3+1.5*(q3-q1))
    close(list(observed.values()), list(reference.values()))
    values = [-7, -6, 0, 1, 2, 3, 4, 10, 11, np.nan, 1e9]
    frame = pd.DataFrame({"timestamp": pd.date_range("2025-01-01", periods=11, freq="h"),
                          "is_on": [True]*10 + [False],
                          "Gross Load (MW)": list(range(10)) + [1e9],
                          TARGET: values, "operational_state_basic": ["ON"]*10+["OFF"]})
    original = frame.copy(deep=True)
    ns = execute(prefix(cell(name, 7), "fig"), env(df=frame), f"{name}:célula 7:sinalização")
    result = ns["df"]
    pd.testing.assert_frame_equal(result[original.columns], original)
    assert len(result) == 11
    assert result.index[result["co2_outlier_iqr"]].tolist() == [0, 8]
    assert not result.loc[[1, 7, 9, 10], "co2_outlier_iqr"].any()
    close([ns["co2_limits"]["lower_limit"], ns["co2_limits"]["upper_limit"]], [-6, 10])
    return {
        "status": "aplicada corretamente",
        "source": {"author": "NIST/SEMATECH", "locator": "1.3.3.7, Box plots with fences, itens 3 a 6; 1.3.5.17, introdução, item 2",
                   "urls": ["https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm", "https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm"]},
        "formula": "IQR=Q3-Q1; limite inferior=Q1-1,5 IQR; superior=Q3+1,5 IQR; máscara estrita fora das cercas em horas ON.",
        "checks": {"independent_quartiles_and_fences": reference,
                   "boundary_fixture_fences": [-6, 10], "flagged_values": [-7, 11],
                   "boundary_values_retained": [-6, 10], "all_11_rows_and_original_values_preserved": True,
                   "missing_and_off_rows_not_flagged": True},
        "conclusion": "A função e as máscaras reais concordam com as cercas de 1,5 IQR. Quantis usam interpolação linear do Pandas; valores ausentes não entram no cálculo. A rotina só acrescenta indicadores: não exclui nem altera os registros originais.",
        "correction": None,
    }


def operational_fixture():
    rng = np.random.default_rng(20261024)
    n = 160
    a = rng.normal(size=(n, 7))
    load = 600 + 90*a[:, 0]
    lag = load + 20*a[:, 1]
    frame = pd.DataFrame({
        "load_current_mw": load, "load_lag_1h": lag,
        "delta_load_1h": load-lag, "abs_delta_load_1h": abs(load-lag),
        "load_mean_previous_3h": .6*load+.4*lag+5*a[:, 2],
        "operating_time_lag_1h": rng.choice([0., .4, 1.], n),
        "hours_since_startup": rng.integers(1, 500, n).astype(float),
        "timestamp": pd.date_range("2025-01-01", "2025-12-31", periods=n),
        "is_on": True, "operational_state_basic": "ON", TARGET: load*.8+10,
    })
    frame.loc[0, "is_on"] = False
    frame.loc[0, "load_current_mw"] = 1e10
    frame.loc[1, "load_mean_previous_3h"] = np.nan
    return frame


def verify_pca():
    name = "02_tratamento_dados.ipynb"
    original = operational_fixture()
    ns = execute(prefix(cell(name, 11), "components"), env(df=original.copy()), f"{name}:célula 11:PCA")
    x = ns["pca_data"].to_numpy(float)
    n = len(x)
    centered = x - x.mean(axis=0)
    z = centered / np.sqrt(np.mean(centered**2, axis=0))
    correlation = z.T @ z / n
    eigenvalues, eigenvectors = np.linalg.eigh(correlation)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    ratios = eigenvalues / eigenvalues.sum()
    close(ns["X_scaled"], z)
    close(ns["explained_variance"], ratios)
    close(ns["pca"].explained_variance_, eigenvalues*n/(n-1))
    pc = ns["pca"].components_.T
    rank = int((eigenvalues > 1e-10).sum())
    subspace_errors = {}
    for k in [1, 2, 5, rank]:
        projector_a = pc[:, :k] @ pc[:, :k].T
        projector_b = eigenvectors[:, :k] @ eigenvectors[:, :k].T
        error = float(np.linalg.norm(projector_a-projector_b, ord=2))
        assert error < 1e-9
        subspace_errors[str(k)] = error
    signs = np.sign(np.sum(pc[:, :rank]*eigenvectors[:, :rank], axis=0))
    close(pc[:, :rank], eigenvectors[:, :rank]*signs)
    score_error = float(np.max(abs(ns["X_pca"][:, :rank] - z @ (eigenvectors[:, :rank]*signs))))
    assert score_error < 1e-9
    manual_n90 = next(i+1 for i in range(len(ratios)) if sum(ratios[:i+1]) >= .90)
    assert int(ns["n_components_90"]) == manual_n90
    assert ns["rows_before"] == 159 and ns["rows_after"] == 158
    assert rank == 6  # delta_load = load_current - load_lag is exactly redundant.

    # Execute the real downstream export/scaling precursor with and without
    # deliberately corrupted PCA outputs. It must still use original columns.
    downstream_nodes = prefix(cell(name, 13), "normalization_summary")
    first = env(df=original.copy(), selected_unit={"year": 2025}, **{k: ns[k] for k in ["X_pca", "pca", "scaler_pca"]})
    execute(downstream_nodes, first, f"{name}:célula 13:atributos originais")
    second = env(df=original.copy(), selected_unit={"year": 2025}, X_pca=np.full((158, 7), 1e99), pca=None, scaler_pca=None)
    execute(downstream_nodes, second, f"{name}:célula 13:teste de independência da PCA")
    pd.testing.assert_frame_equal(first["model_data"], second["model_data"])
    assert first["model_features"] == ns["pca_features"]
    downstream_pca_references = []
    identifiers = {"X_pca", "pca", "pca_data", "pca_scores", "scaler_pca"}
    for path in sorted(NOTEBOOKS.glob("03A*.ipynb")):
        for number, c in enumerate(json.loads(path.read_text())["cells"], 1):
            if c["cell_type"] != "code":
                continue
            try:
                tree = ast.parse("".join(c["source"]))
            except SyntaxError:
                continue
            found = sorted({t.id for t in ast.walk(tree) if isinstance(t, ast.Name)} & identifiers)
            if found:
                downstream_pca_references.append({"file": path.name, "cell": number, "identifiers": found})
    assert not downstream_pca_references
    saved = pd.read_csv(TABLES / "pca_variance_explained.csv")
    close(saved.variancia_explicada_pct.cumsum(), saved.variancia_acumulada_pct)
    saved_n90 = int(np.flatnonzero(saved.variancia_acumulada_pct.to_numpy() >= 90)[0]+1)
    return {
        "status": "aplicada corretamente",
        "source": {"author": "Jolliffe e Cadima (2016)", "locator": "§2(a), p. 3; §2(c)(i), pp. 5 a 6, eqs.(2.7) e (2.8)",
                   "url": "https://doi.org/10.1098/rsta.2015.0202", "doi": "10.1098/rsta.2015.0202"},
        "checks": {"rows_after_on_and_missing_filter": n, "rank": rank,
                   "variance_ratio": ratios.tolist(), "subspace_projector_errors": subspace_errors,
                   "max_score_error_after_sign_alignment": score_error,
                   "synthetic_components_for_90pct": manual_n90,
                   "saved_table_components_for_90pct": saved_n90,
                   "downstream_PCA_identifier_references": downstream_pca_references,
                   "changing_PCA_outputs_does_not_change_predictor_dataset": True},
        "conclusion": "PCA real concorda com eigendecomposição independente da matriz de correlação, inclusive subespaços, sinais, escores e proporções de variância. StandardScaler usa desvio com divisor n; a diferença n/(n-1) apenas escala os autovalores, sem mudar eixos ou proporções. A PCA anual é exploratória: suas saídas não alimentam os modelos. Portanto, esse ajuste sobre 2025 inteiro não causa vazamento no preditor.",
        "correction": None,
    }


def feature_definitions():
    namespace = env()
    for number in [11, 14]:
        nodes = [n for n in cell("03A.01_modelagem_preditiva_co2.ipynb", number).body
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"FEATURES_B", "FEATURES_C"} for t in n.targets)]
        execute(nodes, namespace, f"03A.01_modelagem_preditiva_co2.ipynb:célula {number}:entradas")
    namespace["FEATURES_A"] = ["load_current_mw"]
    namespace["TARGET"] = TARGET
    return namespace


def verify_scalers():
    definitions = feature_definitions()
    features = definitions["FEATURES_C"]
    dates = ["2025-01-01", "2025-04-01", "2025-08-01", "2025-09-30 23:00",
             "2025-10-01", "2025-10-31 23:00", "2025-11-01", "2025-12-01"]
    data = pd.DataFrame({"timestamp": pd.to_datetime(dates, format="mixed"), "is_on": True,
                         TARGET: [20., 40., 60., 80., 10., 1000., 0., 1200.]})
    for j, feature in enumerate(features):
        data[feature] = np.array([1., 2., 3., 4., -9., 100., -19., 200.])*(j+1)+j
    data.loc[:3, "high_ramp"] = 0.0  # A valid constant-in-training column.
    data.loc[4:, "high_ramp"] = [0., 1., 0., 1.]
    ns = env(**{k: definitions[k] for k in ["FEATURES_A", "FEATURES_B", "FEATURES_C", "TARGET"]},
             selected_unit={"year": 2025}, experiment_data=data.copy())
    execute(prefix(cell("03A_modelagem_preditiva_co2.ipynb", 7), "split_summary"), ns,
            "03A_modelagem_preditiva_co2.ipynb:célula 7:partição temporal")
    execute(prefix(cell("03A_modelagem_preditiva_co2.ipynb", 9), "normalization_summary"), ns,
            "03A_modelagem_preditiva_co2.ipynb:célula 9:MinMax A/B")
    nodes = [n for n in cell("03A.01_modelagem_preditiva_co2.ipynb", 16).body if isinstance(n, ast.Assign)]
    execute(nodes, ns, "03A.01_modelagem_preditiva_co2.ipynb:célula 16:MinMax C")
    results = {}
    for scenario in ["A", "B", "C"]:
        xtrain = ns[f"X_train_{scenario}"].to_numpy(float)
        xmin = np.min(xtrain, axis=0)
        xmax = np.max(xtrain, axis=0)
        denominator = xmax-xmin
        denominator[denominator == 0] = 1
        scaler = ns[f"scaler_X_{scenario}"]
        close(scaler.data_min_, xmin)
        close(scaler.data_max_, xmax)
        assert int(scaler.n_samples_seen_) == 4
        for part in ["train", "validation", "test"]:
            manual = (ns[f"X_{part}_{scenario}"].to_numpy(float)-xmin)/denominator
            close(ns[f"X_{part}_{scenario}_scaled"], manual)
        before = (scaler.data_min_.copy(), scaler.data_max_.copy(), scaler.n_samples_seen_)
        future = ns[f"X_test_{scenario}"].copy()*1e6
        scaler.transform(future)
        close(before[0], scaler.data_min_)
        close(before[1], scaler.data_max_)
        assert before[2] == scaler.n_samples_seen_
        results[scenario] = {"n_features": xtrain.shape[1], "fitted_rows": int(scaler.n_samples_seen_),
                             "test_min_scaled": float(ns[f"X_test_{scenario}_scaled"].min()),
                             "test_max_scaled": float(ns[f"X_test_{scenario}_scaled"].max()),
                             "future_values_do_not_refit_scaler": True}
    for key in ["scaler_y", "scaler_y_C"]:
        scaler = ns[key]
        close(scaler.data_min_, [20])
        close(scaler.data_max_, [80])
        assert int(scaler.n_samples_seen_) == 4
    inverse = function("03A_modelagem_preditiva_co2.ipynb", 16, "inverse_target", ns)
    recovered = inverse(np.array([-.5, 0, 1, 1.5]))
    close(recovered, [-10, 20, 80, 110])
    ns["pred_C_scaled"] = np.array([-.5, 1.5])
    inverse_node = [n for n in cell("03A.01_modelagem_preditiva_co2.ipynb", 22).body
                    if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "pred_C" for t in n.targets)]
    execute(inverse_node, ns, "03A.01_modelagem_preditiva_co2.ipynb:célula 22:inversa do alvo")
    close(ns["pred_C"], [-10, 110])
    return {
        "status": "aplicada corretamente",
        "source": {"author": "scikit-learn 1.8.0", "locator": "MinMaxScaler, transformação e inverse_transform; Common pitfalls, §11.2",
                   "urls": ["https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.MinMaxScaler.html", "https://scikit-learn.org/1.8/common_pitfalls.html"]},
        "checks": {"scenarios": results, "target_train_range": [20, 80],
                   "inverse_inputs": [-.5, 0, 1, 1.5], "inverse_outputs": recovered.tolist(),
                   "constant_training_feature_supported_in_C": True,
                   "actual_partition_sizes": {k: len(ns[k+"_data"]) for k in ["train", "validation", "test"]}},
        "conclusion": "As instruções reais de A/B/C ajustam escalas apenas ao treino e aplicam transform aos demais subconjuntos. Extremos futuros não alteram os parâmetros aprendidos; valores fora de [0,1] são preservados conforme clip=False. As inversas reais recuperam unidades originais antes das métricas, inclusive fora da amplitude de treino.",
        "correction": None,
    }


def verify_metrics():
    locations = [
        ("03A_modelagem_preditiva_co2.ipynb", 16, "regression_metrics"),
        ("03A.02_comparacao_modelos_gradient_boosting.ipynb", 16, "regression_metrics"),
        ("03A.03_otimizacao_pareada_xgboost.ipynb", 13, "regression_metrics"),
        ("03A.04_volume_dados_generalizacao_temporal_iatan.ipynb", 3, "regression_metrics"),
        ("03A.04_volume_dados_generalizacao_temporal_iatan.ipynb", 11, "metrics_03A04"),
        ("03A.04_volume_dados_generalizacao_temporal_iatan.ipynb", 16, "calculate_metrics"),
        ("03A.05_trajetoria_operacional_historico_ampliado.ipynb", 3, "regression_metrics"),
    ]
    cases = {
        "mixed_errors_including_zero_observation": ([0, 2, 4, 8], [1, 1, 7, 6]),
        "overprediction_bias_negative": ([1, 2, 3], [3, 4, 5]),
        "underprediction_bias_positive": ([1, 2, 3], [-1, 0, 1]),
        "negative_R2": ([1, 2, 3], [10, 10, 10]),
        "constant_target_perfect": ([3, 3, 3], [3, 3, 3]),
        "constant_target_imperfect": ([3, 3, 3], [3, 4, 3]),
        "zero_target_zero_normalizer": ([0, 0, 0], [1, 2, 3]),
    }
    checks = []
    for name, number, fname in locations:
        f = function(name, number, fname)
        for case, (truth, prediction) in cases.items():
            expected = manual_metrics(truth, prediction)
            actual = f(np.array(truth), np.array(prediction))
            for key, value in actual.items():
                close(value, expected[key])
        checks.append({"notebook": name, "cell": number, "function": fname, "cases_passed": len(cases)})
    ns = env(y_true=np.array([0, 2, 4, 8]), pred_C=np.array([1, 1, 7, 6]))
    nodes = [n for n in cell("03A.01_modelagem_preditiva_co2.ipynb", 22).body
             if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "metrics_C" for t in n.targets)]
    execute(nodes, ns, "03A.01_modelagem_preditiva_co2.ipynb:célula 22:métricas C")
    for k, v in ns["metrics_C"].items():
        close(v, manual_metrics(ns["y_true"], ns["pred_C"])[k])

    # Real residual/absolute-error assignments and real context summary function.
    paired = pd.DataFrame({TARGET: [100.]*5, "pred_A": [96.]*5, "pred_B": [97.,97.,97.,97.,112.]})
    paired_ns = env(paired_test_predictions=paired, TARGET=TARGET)
    wanted = {"residual_A", "residual_B", "abs_error_A", "abs_error_B", "B_lower_error", "AE_reduction_B"}
    nodes = []
    for node in cell("03A.05_trajetoria_operacional_historico_ampliado.ipynb", 18).body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and target.value.id == "paired_test_predictions" and isinstance(target.slice, ast.Constant) and target.slice.value in wanted:
                nodes.append(node)
    execute(nodes, paired_ns, "03A.05_trajetoria_operacional_historico_ampliado.ipynb:célula 18:resíduos e reduções")
    paired_ns["context_test"] = paired_ns["paired_test_predictions"]
    summarize = function("03A.05_trajetoria_operacional_historico_ampliado.ipynb", 21, "summarize_context", paired_ns)
    ctx = summarize("fixture", np.ones(5, dtype=bool))
    close([ctx["MAE_A"], ctx["MAE_B"], ctx["Bias_A"], ctx["Bias_B"], ctx["ganho_B_vs_A_pct"], ctx["B_win_pct"], ctx["mean_AE_reduction_B"], ctx["median_AE_reduction_B"]], [4, 4.8, 4, 0, -20, 80, -.8, 1])
    gain = function("03A.03_otimizacao_pareada_xgboost.ipynb", 24, "relative_gain_B_vs_A")
    close([gain(10, 8), gain(10, 12)], [20, -20])

    # Recalculate the saved MLP predictions, not a freshly trained model.
    pred = pd.read_csv(TABLES / "03A_previsoes_teste.csv")
    saved = pd.read_csv(TABLES / "03A_comparacao_modelos.csv")
    truth = pred.co2_observed_short_tons.to_numpy(float)
    f = function("03A_modelagem_preditiva_co2.ipynb", 16, "regression_metrics")
    saved_comparison = {}
    for i, scenario in enumerate(["A", "B"]):
        yp = pred[f"co2_pred_{scenario}_short_tons"].to_numpy(float)
        actual = f(truth, yp)
        manual = manual_metrics(truth, yp)
        differences = {k: float(actual[k]-saved.iloc[i][k]) for k in actual}
        for k in actual:
            close(actual[k], manual[k])
            # CSV prediction values were serialized from float32 arrays.
            close(actual[k], saved.iloc[i][k], atol=1e-4, rtol=1e-8)
        close(truth-yp, pred[f"residual_{scenario}"], atol=1e-4, rtol=1e-8)
        saved_comparison[scenario] = {"recomputed": actual, "difference_from_saved_table": differences}
    final = pd.read_csv(TABLES / "03A05_resultado_final_A_B.csv")
    mean = statistics.fmean(truth)
    sst = sum((x-mean)**2 for x in truth)
    for row in final.to_dict("records"):
        close(row["NMAE_pct"], 100*row["MAE"]/mean)
        close(row["R2"], 1-row["RMSE"]**2*row["n_test"]/sst)
    contexts = pd.read_csv(TABLES / "03A05_comparacao_contextos_operacionais.csv")
    for row in contexts.to_dict("records"):
        close(row["ganho_B_vs_A_pct"], 100*(row["MAE_A"]-row["MAE_B"])/row["MAE_A"])
        close(row["ganho_RMSE_B_vs_A_pct"], 100*(row["RMSE_A"]-row["RMSE_B"])/row["RMSE_A"])
        close(row["mean_AE_reduction_B"], row["MAE_A"]-row["MAE_B"])
    return {
        "status": "aplicada corretamente",
        "sources": [{"author": "Hyndman e Koehler (2006)", "locator": "§2 e §2.1, pp. 7 e 8 do manuscrito autoral", "url": "https://robjhyndman.com/papers/mase.pdf"},
                    {"author": "scikit-learn 1.8.0", "locator": "§3.4.6.1, R² não ajustado; §§3.4.6.2 e 3.4.6.3", "url": "https://scikit-learn.org/1.8/modules/model_evaluation.html"}],
        "checks": {"actual_functions": checks, "known_reference_example": manual_metrics([0,2,4,8], [1,1,7,6]),
                   "paired_summary_example": ctx, "saved_MLP_rows": len(pred), "saved_MLP_recomputation": saved_comparison,
                   "final_XGBoost_table_R2_NMAE_identities_verified": True,
                   "all_four_saved_context_gain_identities_verified": True},
        "conclusion": "MAE, RMSE e R² das sete funções e do cenário C coincidem com cálculos independentes. Viés é observado menos estimado: sobrestimação dá sinal negativo. Ganho e redução pareada positivos favorecem B. A inversa precede as métricas da MLP; 1.144 previsões preservadas reproduzem a tabela dentro da precisão de serialização. NMAE é normalização pela média do alvo, não MASE ou MAPE. R² constante segue o padrão force_finite da API.",
        "scope": "Os erros finais do XGBoost foram verificados por identidades das tabelas e testes das funções; suas predições individuais não estão nesses CSVs. Não se executou treinamento.",
        "correction": None,
    }


def drift_namespace(history):
    years = sorted(history.year.unique())
    annual = pd.DataFrame({"year": years, "operating_pct": 100., "n_startups": 0, "n_shutdowns": 0})
    return env(history=history.copy(), annual_summary=annual)


def drift_block(history, original_fixture=False):
    name = "03A.04_volume_dados_generalizacao_temporal_iatan.ipynb"
    nodes = prefix(cell(name, 9), "display_columns")
    if original_fixture:
        replacement = ast.parse("max_bin_edge = float(np.ceil(max_load / LOAD_BIN_WIDTH) * LOAD_BIN_WIDTH)").body[0]
        nodes = [replacement if "max_bin_edge" in assigned_names(n) else n for n in nodes]
    return execute(nodes, drift_namespace(history), f"{name}:célula 9:diagnóstico" + (":fórmula anterior em fixture isolada" if original_fixture else ":código público atual"))


def verify_drift():
    records = []
    for year, loads, offset in [(2020, [20]*20+[80]*40, 5), (2025, [10]*20+[70]*40, 5), (2021, [10]*20+[70]*40, 10)]:
        for x in loads:
            records.append({"year": year, "Operating Time": 1., "Gross Load (MW)": x, TARGET: 2*x+offset})
    ns = drift_block(pd.DataFrame(records))
    summary = ns["drift_summary"].set_index("year")
    close(summary.loc[[2020, 2025], "linear_slope"], [2, 2])
    close(summary.loc[[2020, 2025], "linear_intercept"], [5, 5])
    close(summary.loc[[2020, 2021, 2025], "curve_mae_vs_2025"], [20, 5, 0])
    # A change in X within broad bins yields distance despite unchanged y|X.
    assert summary.loc[2020, "curve_mae_vs_2025"] > 0

    curves = pd.read_csv(TABLES / "03A04_curvas_carga_co2_por_ano.csv")
    saved = pd.read_csv(TABLES / "03A04_drift_anual_cenario_A.csv")
    ref = {row["load_bin_left"]: row for row in curves.to_dict("records") if row["year"] == 2025 and row["n"] >= 20}
    differences = []
    for record in saved.to_dict("records"):
        yr = {row["load_bin_left"]: row for row in curves.to_dict("records") if row["year"] == record["year"] and row["n"] >= 20}
        common = sorted(ref.keys() & yr.keys())
        denominator = sum(ref[k]["n"] for k in common)
        distance = sum(ref[k]["n"]*abs(yr[k]["co2_median"]-ref[k]["co2_median"]) for k in common)/denominator
        reference_mean = sum(ref[k]["n"]*ref[k]["co2_median"] for k in common)/denominator
        normalized = 100*distance/reference_mean
        close([distance, normalized], [record["curve_mae_vs_2025"], record["curve_nmae_vs_2025_pct"]])
        differences.append(abs(normalized-record["curve_nmae_vs_2025_pct"]))
    counts = curves.groupby("year")["n"].sum()
    close(counts.loc[saved.year].to_numpy(), saved.n_scenario_A.to_numpy())
    annual = pd.read_csv(TABLES / "03A04_resumo_operacional_anual.csv")
    observed_max = float(annual.loc[annual.year >= 2011, "load_max"].max())
    original_upper = float(np.ceil(observed_max / 50) * 50)
    corrected_upper = float((np.floor(observed_max / 50) + 1) * 50)
    original_edges = np.arange(0, original_upper + 50, 50, dtype=float)
    corrected_edges = np.arange(0, corrected_upper + 50, 50, dtype=float)
    close(original_edges, corrected_edges, atol=0, rtol=0)
    assert observed_max == 957 and original_upper == corrected_upper == 1000
    assert float(curves.load_bin_right.max()) == original_upper
    saved_ranking = pd.read_csv(TABLES / "03A04_similaridade_curva_vs_2025.csv")
    expected_ranking = saved[saved.year.ne(2025)].sort_values("curve_nmae_vs_2025_pct")
    close(saved_ranking.year.to_numpy(), expected_ranking.year.to_numpy(), atol=0, rtol=0)
    close(saved_ranking.curve_nmae_vs_2025_pct.to_numpy(), expected_ranking.curve_nmae_vs_2025_pct.to_numpy())

    boundary = pd.DataFrame({"year": [2025]*60, "Operating Time": 1.,
                             "Gross Load (MW)": [10]*20+[50]*20+[100]*20})
    boundary[TARGET] = 2*boundary["Gross Load (MW)"]+5
    old = drift_block(boundary, original_fixture=True)
    fixed = drift_block(boundary)
    old_count = int(old["curve_by_year"]["n"].sum())
    fixed_count = int(fixed["curve_by_year"]["n"].sum())
    assert old_count == 40 and fixed_count == 60
    unchanged = drift_block(pd.DataFrame(records), original_fixture=True)
    pd.testing.assert_frame_equal(ns["curve_by_year"], unchanged["curve_by_year"])

    # Show a changed diagnostic, not only a changed row count: one historical
    # year differs from the reference exclusively at the excluded maximum.
    older = boundary.copy()
    older["year"] = 2024
    older.loc[older["Gross Load (MW)"].eq(100), TARGET] += 20
    metric_fixture = pd.concat([older, boundary], ignore_index=True)
    metric_old = drift_block(metric_fixture, original_fixture=True)["drift_summary"].set_index("year")
    metric_fixed = drift_block(metric_fixture)["drift_summary"].set_index("year")
    close(metric_old.loc[2024, "curve_mae_vs_2025"], 0)
    close(metric_fixed.loc[2024, "curve_mae_vs_2025"], 20/3)
    close(metric_fixed.loc[2024, "curve_nmae_vs_2025_pct"], 100*20/335)

    # The sample-selection rule consumes unbinned indicators from drift_summary.
    decision_node = next(n for n in cell("03A.04_volume_dados_generalizacao_temporal_iatan.ipynb", 13).body
                         if "operational_decision" in assigned_names(n))
    drift_projection = next(n for n in ast.walk(decision_node) if isinstance(n, ast.Subscript)
                            and isinstance(n.value, ast.Name) and n.value.id == "drift_summary")
    decision_columns = ast.literal_eval(drift_projection.slice)
    assert decision_columns == ["year", "operating_pct", "n_startups", "n_shutdowns", "load_mean", "load_p05", "load_p95"]
    main_source = "".join(json.loads((NOTEBOOKS / "03A.04_volume_dados_generalizacao_temporal_iatan.ipynb").read_text())["cells"][8]["source"])
    current_assignment = next(n for n in cell("03A.04_volume_dados_generalizacao_temporal_iatan.ipynb", 9).body
                               if "max_bin_edge" in assigned_names(n))
    expected_assignment = ast.parse("max_bin_edge = float((np.floor(max_load / LOAD_BIN_WIDTH) + 1) * LOAD_BIN_WIDTH)").body[0]
    assert ast.dump(current_assignment) == ast.dump(expected_assignment), "A fórmula pública da borda deve corresponder à correção verificada."
    return {
        "status": "aplicada corretamente; correção da borda verificada no notebook público",
        "source": {"author": "Gama et al. (2014)", "locator": "§2.1, pp. 3 a 4 do manuscrito aceito, eq.(2); Fig.1, p. 5",
                   "url": "https://eprints.bournemouth.ac.uk/22491/1/ACM%20computing%20surveys.pdf"},
        "source_role": "Orientação conceitual para distinguir mudanças de P(X) e P(y|X). A distância entre medianas por faixa, ponderada pelas frequências de 2025, é um diagnóstico construído neste estudo; não é um detector de Gama reproduzido.",
        "checks": {"same_conditional_relation_slope_intercept": [2, 5],
                   "curve_distance_despite_unchanged_conditional_relation": 20,
                   "max_saved_curve_distance_recalculation_error": max(differences),
                   "all_15_years_saved_bin_counts_equal_scenario_counts": True,
                   "observed_max_load_mw": observed_max,
                   "current_data_original_upper_edge_mw": original_upper,
                   "current_data_corrected_upper_edge_mw": corrected_upper,
                   "current_data_bin_edges_identical": True,
                   "current_data_bin_edges_mw": original_edges.tolist(),
                   "saved_14_year_similarity_ranking_matches_recomputed_distances": True,
                   "boundary_probe_rows": 60, "original_binned_rows": old_count,
                   "corrected_binned_rows": fixed_count,
                   "actual_public_notebook_retains_all_boundary_rows": True,
                   "actual_public_formula_matches_corrected_expression": True,
                   "boundary_metric_before_after": {
                       "fixture": "60 observações por ano; cargas 10, 50 e 100 MW com 20 observações cada. Em 2025, y=2x+5; em 2024, somente as observações de 100 MW recebem +20.",
                       "original_common_bins": int(metric_old.loc[2024, "n_common_bins"]),
                       "corrected_common_bins": int(metric_fixed.loc[2024, "n_common_bins"]),
                       "original_curve_mae": float(metric_old.loc[2024, "curve_mae_vs_2025"]),
                       "corrected_curve_mae": float(metric_fixed.loc[2024, "curve_mae_vs_2025"]),
                       "original_curve_nmae_pct": float(metric_old.loc[2024, "curve_nmae_vs_2025_pct"]),
                       "corrected_curve_nmae_pct": float(metric_fixed.loc[2024, "curve_nmae_vs_2025_pct"])},
                   "sample_decision_consumed_drift_columns": decision_columns,
                   "correction_preserves_nonboundary_case": True},
        "conclusion": "A orientação de Gama é usada corretamente: os indicadores são descritivos e não constituem prova de mudança de P(CO2|carga). Um contraexemplo executado mantém y=2x+5 e produz distância 20 apenas por mudança das cargas dentro das faixas. As 15 distâncias anuais publicadas foram reapuradas e todas as contagens fecham. A fórmula corrigida do notebook público inclui o máximo mesmo quando ele é múltiplo exato de 50 MW; a falha anterior foi reproduzida somente em fixture isolada.",
        "correction": {"location": "03A.04_volume_dados_generalizacao_temporal_iatan.ipynb, célula 9, max_bin_edge",
                       "original": "max_bin_edge = float(np.ceil(max_load / LOAD_BIN_WIDTH) * LOAD_BIN_WIDTH)",
                       "current_source_exact": ast.get_source_segment(main_source, current_assignment),
                       "verified_current_formula": "max_bin_edge = float((np.floor(max_load / LOAD_BIN_WIDTH) + 1) * LOAD_BIN_WIDTH)",
                       "reason": "pd.cut(..., right=False) exclui valores iguais à última borda. A borda final deve ser estritamente maior que o máximo.",
                       "observed_dataset_effect": "Melhoria preventiva neste recorte: máximo observado de 957 MW, borda original e corrigida de 1.000 MW e vetores de bordas idênticos. As contagens fecham em todos os 15 anos. Nenhuma distância, ordenação, tabela, figura ou conclusão muda com essa substituição nos dados utilizados.",
                       "directly_dependent_tables": ["outputs/tables/03A04_curvas_carga_co2_por_ano.csv", "outputs/tables/03A04_drift_anual_cenario_A.csv", "outputs/tables/03A04_similaridade_curva_vs_2025.csv"],
                       "affected_columns_in_annual_table_if_boundary_occurs": ["n_common_bins", "reference_observations", "curve_mae_vs_2025", "curve_nmae_vs_2025_pct"],
                       "directly_dependent_figures": ["outputs/figures/03A04_curvas_carga_co2_anuais.png", "outputs/figures/03A04_distancia_curva_vs_2025.png"],
                       "unaffected_paths": ["Indicadores anuais de utilização, carga, partidas, intensidade e regressão linear, calculados antes das faixas.", "Decisão exploratória de 2023/2024, que não utiliza distâncias por faixa; outputs/tables/03A04_decisao_amostral_2023_2024.csv e outputs/reports/03A04_delimitacao_amostra_historica.md.", "Treinamento, atributos, divisão temporal, predições, métricas e relatórios dos modelos; a faixa load_bin não integra as matrizes preditoras."],
                       "article_effect": "Nenhuma alteração numérica ou de conclusão. O artigo não publica as distâncias por faixa; os indicadores operacionais do apêndice são calculados fora desse agrupamento. A interpretação descritiva de Gama permanece correta.",
                       "applied_to_notebook": True},
    }


def verify_epa():
    tree = ast.parse(MONITORING.read_text())
    needed = {"norm_key", "get", "timestamp_from_date_hour", "interval", "mask_for_intervals"}
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in needed]
    ns = execute(nodes, env(), f"{MONITORING.name}:funções de intervalo")
    interval, mask = ns["interval"], ns["mask_for_intervals"]

    def parsed(begin_date, begin_hour, end_date=None, end_hour=None):
        start, end, status, note = interval(dict(beginDate=begin_date, beginHour=begin_hour, endDate=end_date, endHour=end_hour))
        return dict(begin=start, end=end, interval_status=status, interval_note=note)

    record = parsed("2025-01-01", 10, "2025-01-01", 12)
    times = pd.Series(pd.to_datetime(["2025-01-01 09:00", "2025-01-01 10:00", "2025-01-01 11:00", "2025-01-01 12:00", "2025-01-01 13:00", None]))
    expected = [False, True, True, True, False, False]
    assert mask(times, [record]).tolist() == expected
    point = parsed("2025-01-01", 12, "2025-01-01", 12)
    assert mask(times, [point]).tolist() == [False, False, False, True, False, False]
    open_record = parsed("2025-01-01", 12)
    assert mask(times, [open_record]).tolist() == [False, False, False, True, True, False]
    adjacent = parsed("2025-01-01", 13, "2025-01-01", 14)
    assert mask(times, [record, adjacent]).tolist() == [False, True, True, True, True, False]
    invalid = parsed("2025-01-01", 24, "2025-01-01", 23)
    assert invalid["interval_status"] == "invalid"
    assert not mask(times, [invalid]).any()
    reversed_interval = parsed("2025-01-01", 12, "2025-01-01", 11)
    assert reversed_interval["interval_status"] == "invalid"

    saved_path = REPO / "reproducibility/monitoring/outputs/plan_system_component_history.csv"
    saved = pd.read_csv(saved_path)
    assert saved.interval_status.eq("valid").all()
    assert saved.interval_note.isna().all()
    boundaries = []
    for row in saved.to_dict("records"):
        nullable = lambda value: None if pd.isna(value) else value
        item = parsed(row["beginDate"], row["beginHour"], nullable(row["endDate"]), nullable(row["endHour"]))
        assert item["interval_status"] == "valid" and item["interval_note"] == ""
        assert item["begin"] == pd.Timestamp(row["begin"])
        assert (item["end"] is None) == pd.isna(row["end"])
        if item["end"] is not None:
            assert item["end"] == pd.Timestamp(row["end"])
            probes = pd.Series([item["begin"]-pd.Timedelta(hours=1), item["begin"], item["end"], item["end"]+pd.Timedelta(hours=1)])
            assert mask(probes, [item]).tolist() == [False, True, True, False]
            boundaries.append({"begin": str(item["begin"]), "end": str(item["end"]), "verified_inclusive": True})
        else:
            probes = pd.Series([item["begin"]-pd.Timedelta(hours=1), item["begin"], item["begin"]+pd.Timedelta(days=365)])
            assert mask(probes, [item]).tolist() == [False, True, True]
    return {
        "status": "aplicada corretamente",
        "source": {"author": "EPA (2024)", "locator": "§8.2, p. impressa 61, p. 66 do PDF; Begin Date/Hour e End Date/Hour",
                   "url": "https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf"},
        "checks": {"closed_interval_mask": expected, "point_interval_verified": True,
                   "open_end_and_NaT_verified": True, "adjacent_intervals_union_verified": True,
                   "invalid_hours_and_reversed_intervals_rejected": True,
                   "preserved_system_component_records_checked": len(saved),
                   "implicit_hour_assumptions_in_saved_records": 0,
                   "closed_interval_boundaries": boundaries},
        "conclusion": "A comparação inclusiva corresponde à última hora ativa definida pela EPA. As funções reais incluem início e término, excluem as horas vizinhas, preservam intervalos ainda ativos e ignoram intervalos inválidos. Os 26 registros preservados de associação sistema/componente foram novamente convertidos e tiveram suas fronteiras verificadas; nenhum exigiu hora presumida.",
        "correction": None,
    }


def serializable(value):
    if isinstance(value, dict):
        return {k: serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serializable(v) for v in value]
    if isinstance(value, np.ndarray):
        return serializable(value.tolist())
    if isinstance(value, np.generic):
        return serializable(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("+Inf" if value > 0 else "-Inf")
    return value


def main():
    global NOTEBOOKS, REPO, TABLES, MONITORING
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path("."), help="Raiz do repositório público; padrão: diretório atual.")
    parser.add_argument("--notebooks", type=Path, help="Diretório alternativo dos notebooks; padrão: REPO/notebooks.")
    parser.add_argument("--monitoring-script", type=Path, help="Script alternativo; padrão: REPO/reproducibility/monitoring/audit_monitoring.py.")
    parser.add_argument("--manifest", type=Path, help="Manifesto SHA-256 opcional: lista de objetos com file e sha256 para os notebooks.")
    parser.add_argument("--output", type=Path, help="Arquivo JSON de saída; padrão: REPO/outputs/reproducibility/statistics_verification.json.")
    args = parser.parse_args()
    REPO = args.repo.resolve()
    NOTEBOOKS = (args.notebooks or REPO / "notebooks").resolve()
    MONITORING = (args.monitoring_script or REPO / "reproducibility/monitoring/audit_monitoring.py").resolve()
    TABLES = REPO / "outputs/tables"
    manifest_path = args.manifest.resolve() if args.manifest else None
    output_path = args.output or REPO / "outputs/reproducibility/statistics_verification.json"
    required_tables = ["pca_variance_explained.csv", "03A_previsoes_teste.csv", "03A_comparacao_modelos.csv",
                       "03A05_resultado_final_A_B.csv", "03A05_comparacao_contextos_operacionais.csv",
                       "03A04_curvas_carga_co2_por_ano.csv", "03A04_drift_anual_cenario_A.csv",
                       "03A04_resumo_operacional_anual.csv", "03A04_similaridade_curva_vs_2025.csv"]
    protected_paths = {f"notebooks/{p.name}": p for p in sorted(NOTEBOOKS.glob("*.ipynb"))}
    protected_paths.update({f"repo/outputs/tables/{name}": TABLES / name for name in required_tables})
    protected_paths.update({"repo/reproducibility/monitoring/audit_monitoring.py": MONITORING,
                            "repo/reproducibility/monitoring/outputs/plan_system_component_history.csv":
                                REPO / "reproducibility/monitoring/outputs/plan_system_component_history.csv"})
    if manifest_path is not None:
        protected_paths["optional_notebook_manifest"] = manifest_path
    missing = [label for label, path in protected_paths.items() if not path.is_file()]
    if missing or not NOTEBOOKS.is_dir():
        parser.error("Entradas ausentes: " + ", ".join(missing or ["diretório de notebooks"]))
    hashes_before = {label: sha(path) for label, path in protected_paths.items()}
    if manifest_path is not None:
        manifest = json.loads(manifest_path.read_text())
        for item in manifest:
            if sha(NOTEBOOKS/item["file"]) != item["sha256"]:
                parser.error(f"Notebook diverge do manifesto opcional: {item['file']}.")
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "Equações e aplicação dos métodos no código público corrigido; execução de funções e trechos reais sobre casos analíticos independentes e reapuração de tabelas/predições preservadas. Não houve treinamento de modelos.",
        "notebook_version": "Arquivos públicos utilizados nesta execução, identificados individualmente pelos hashes SHA-256 registrados no resultado.",
        "optional_manifest_verified": manifest_path is not None,
        "cell_numbering": "Inicia em 1 e conta todas as células, inclusive Markdown.",
        "environment": {"python": sys.version, "executable_name": Path(sys.executable).name, "platform": platform.platform(),
                        "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "scikit_learn": sklearn.__version__},
        "input_layout": {"repo": "Raiz pública configurada por --repo; padrão: diretório atual.",
                         "notebooks": "notebooks/ ou diretório --notebooks.",
                         "monitoring_script": "reproducibility/monitoring/audit_monitoring.py ou arquivo --monitoring-script.",
                         "tables": "outputs/tables/ e reproducibility/monitoring/outputs/plan_system_component_history.csv.",
                         "manifest": "Opcional, configurado somente por --manifest."},
        "dependencies_installed_for_verification": [],
        "methods": {},
    }
    for key, check in [("iqr_nist", verify_iqr), ("pca_jolliffe", verify_pca),
                       ("minmax_scaler", verify_scalers), ("metrics_and_r2", verify_metrics),
                       ("drift_gama", verify_drift), ("epa_inclusive_intervals", verify_epa)]:
        try:
            result["methods"][key] = check()
            print(key, result["methods"][key]["status"], flush=True)
        except Exception as exc:
            result["methods"][key] = {"status": "verificação interrompida", "error": f"{type(exc).__name__}: {exc}", "traceback": traceback.format_exc()}
            print(key, "VERIFICATION ERROR", repr(exc), flush=True)
    hashes_after = {label: sha(path) for label, path in protected_paths.items()}
    assert hashes_before == hashes_after
    result["source_hashes_sha256"] = hashes_before
    result["source_files_unchanged"] = True
    result["executed_actual_code_fragments"] = EXECUTED
    result["verification_script_sha256"] = sha(__file__)
    result["completed"] = all(m["status"] != "verificação interrompida" for m in result["methods"].values())
    result["verified_corrections"] = [m["correction"] for m in result["methods"].values() if m.get("correction")]
    result["overall_conclusion"] = ("IQR, PCA exploratória, escalonamento, inversão, métricas e intervalos EPA aplicados corretamente nos caminhos verificados. A orientação de Gama é respeitada. A borda superior das faixas está corrigida no notebook público e passou no caso limite. As faixas e os resultados do recorte publicado permanecem iguais."
                                    if result["completed"] else "Há verificações interrompidas que precisam ser resolvidas; não generalizar os testes concluídos às partes pendentes.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(serializable(result), ensure_ascii=False, indent=2)+"\n")
    print("OUTPUT", output_path.name)
    return 0 if result["completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
