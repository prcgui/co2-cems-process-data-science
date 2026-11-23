"""Registro das saídas calculadas pelos notebooks 07 e 08 no MLflow Tracking."""

from pathlib import Path
import hashlib
import json
import os
from urllib.parse import urlparse

import mlflow
import pandas as pd


def log_carbon_result(root, notebook, output, input_files, parameters, metrics, tables):
    """Registra as métricas e vincula a execução aos arquivos que as produziram."""
    database = Path(root) / "outputs/registro_carbono"
    database.mkdir(parents=True, exist_ok=True)
    uri = os.environ.get("MLFLOW_TRACKING_URI") or "sqlite:///" + (database / "mlflow.db").resolve().as_posix()
    mlflow.set_tracking_uri(uri)
    experiment = "Iatan 2 - Correcao retrospectiva da intensidade carbonica"
    if mlflow.get_experiment_by_name(experiment) is None:
        artifact_location = ((database / "artefatos").resolve().as_uri()
                             if urlparse(uri).scheme in ("", "file", "sqlite") else None)
        mlflow.create_experiment(experiment, artifact_location=artifact_location)
    experiment_id = mlflow.get_experiment_by_name(experiment).experiment_id
    name = f"Notebook {notebook}"
    with mlflow.start_run(experiment_id=experiment_id, run_name=name) as run:
        mlflow.set_tag("avaliacao", "retrospectiva - cortes identificados com CO2 observado em 2025")
        mlflow.log_params(parameters)
        hashes = {Path(path).name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in input_files}
        for filename, sha256 in hashes.items():
            mlflow.log_param(f"sha256_{filename.replace('.', '_')}", sha256)
        mlflow.log_metrics(metrics)
        for path in tables:
            mlflow.log_artifact(str(path))
        metadata = {"notebook": notebook, "experiment_id": experiment_id, "run_id": run.info.run_id,
                    "sha256": hashes}
    (output / "registro_mlflow.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata


def log_notebook07(root, output):
    report = output / "relatorios/21_resumo_reprodutibilidade.json"
    tables = output / "tabelas"
    summary = json.loads(report.read_text(encoding="utf-8"))
    parameters = {"historico": "2011-2025", "fator": summary["fator_historico_principal"],
                  "cortes": ", ".join(summary["cortes_2025"]), "unidade": "6065/2"}
    metrics = {"n_horas": summary["n_horas_2025"], "rmse_m0": summary["rmse_m0"],
               "rmse_m2": summary["rmse_m2"], "ganho_rmse_pct": summary["ganho_rmse_pct"]}
    sources = [Path(root) / "configs/iatan_inputs.json", output / "dados/22C_previsoes_2025.parquet",
               tables / "22C_fator_historico.csv", tables / "19C_reconciliacao_datas_2025.csv"]
    files = [report, tables / "04_conciliacao_anual_2025.csv", tables / "19C_reconciliacao_datas_2025.csv",
             tables / "22C_fator_historico.csv", tables / "22C_resultados_2025.csv"]
    return log_carbon_result(root, "07", output, sources, parameters, metrics, files)


def log_notebook08(root, output, pred06, factor07, dates07, parent_run06, source07):
    tables = output / "tabelas"
    path = tables / "metricas_globais.csv"
    df = pd.read_csv(path)
    recorded07 = json.loads((source07 / "registro_mlflow.json").read_text(encoding="utf-8"))
    for path in (factor07, dates07, source07 / "dados/22C_previsoes_2025.parquet"):
        if hashlib.sha256(path.read_bytes()).hexdigest() != recorded07.get("sha256", {}).get(path.name):
            raise ValueError(f"{path.name} diverge da execução 07 registrada. Conclua o 07 e repita o 08.")
    parameters = {"mlflow_origem06": parent_run06, "mlflow_origem07": recorded07["run_id"],
                  "cenario": "M0/M1/M2", "algoritmos_06": "A/B/C/D", "ano": 2025}
    metrics = {f"{r.populacao}_{r.modelo}_{r.cenario}_{metric}": getattr(r, metric)
               for r in df.itertuples() for metric in ("rmse", "mae", "vies", "n")}
    files = [path, tables / "bootstrap_pareado_7dias.csv", output / "metadados/parametros_experimento.json"]
    return log_carbon_result(root, "08", output, [pred06, factor07, dates07], parameters, metrics, files)
