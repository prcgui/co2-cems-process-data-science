"""Resultados comparáveis e limitações, sem selecionar modelos pelo teste."""
import html
import json
import pandas as pd
from .data import write_json


def build(root):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    base = root / 'outputs/iatan_consolidado'
    latest = json.loads((base / 'latest_experiment.json').read_text(encoding='utf-8'))
    folder = root / latest['output']
    metrics = pd.read_csv(folder / 'metrics.csv')
    test = metrics.loc[metrics.partition.eq('retrospective_test')].copy()
    selection = pd.read_csv(folder / 'selection.csv')
    selected = selection.sort_values('RMSE').groupby(['algorithm', 'seed']).first().reset_index()
    hmm_selection = json.loads((folder / 'selection/hmm_training.json').read_text(encoding='utf-8'))
    cfg = json.loads((folder / 'configuration.json').read_text(encoding='utf-8'))
    hmm_note = (f"HMM de seleção: {hmm_selection['iterations']} iterações; limite configurado: {cfg['hmm']['n_iter']}. "
                'O indicador converged da biblioteca também pode ser verdadeiro ao atingir o limite; examinar a sensibilidade em novas execuções.')
    selected[['algorithm', 'seed', 'scenario', 'RMSE']].to_csv(folder / 'selected_by_validation.csv', index=False)
    wide = test.pivot(index=['algorithm', 'seed'], columns='scenario', values='MAE')
    if 'B0' in wide:
        gains = wide.apply(lambda c: 100 * (wide.B0 - c) / wide.B0).reset_index()
        gains.to_csv(folder / 'relative_MAE_gain_vs_B0.csv', index=False)
    pred = pd.read_parquet(folder / 'predictions.parquet')
    # Context thresholds must be established from training data, not test residuals.
    train = pd.read_parquet(folder / 'final/train_final.parquet')
    eval_frame = pd.read_parquet(folder / 'final/test.parquet')
    threshold = float(train.abs_delta_load_1h.quantile(.9))
    ctx = eval_frame[['timestamp', 'abs_delta_load_1h', 'hours_since_startup']].copy()
    ctx['intense_ramp'] = ctx.abs_delta_load_1h.ge(threshold)
    ctx['startup_first6h'] = ctx.hours_since_startup.between(1, 6)
    pred = pred.merge(ctx, on='timestamp', validate='many_to_one')
    from .baseline import metrics as evaluate
    contexts = []
    for (alg, scenario, seed), group in pred.groupby(['algorithm', 'scenario', 'seed']):
        for name, mask in [('global', pd.Series(True, index=group.index)),
                           ('rampas', group.intense_ramp), ('partidas', group.startup_first6h),
                           ('demais', ~group.intense_ramp & ~group.startup_first6h)]:
            if mask.any(): contexts.append(dict(algorithm=alg, scenario=scenario, seed=seed,
                                               context=name, **evaluate(group.loc[mask, 'actual'], group.loc[mask, 'prediction'])))
    pd.DataFrame(contexts).to_csv(folder / 'metrics_by_context.csv', index=False)
    write_json(folder / 'context_definition.json', {'ramp_quantile_train': .9, 'threshold_mw': threshold,
                                                   'startup_age_h': [1, 6], 'source': 'final training only'})
    fig, ax = plt.subplots(figsize=(10, 5))
    for alg, group in test.groupby('algorithm'):
        g = group.groupby('scenario').MAE.mean().reindex(['CARGA', 'B0', 'P1', 'P2', 'MEMORIA117'])
        ax.plot(g.index, g.values, 'o-', label=alg)
    ax.set(ylabel='MAE (short tons de CO2/h)', title='Iatan 2 — comparação retrospectiva, mesma amostra')
    ax.grid(alpha=.2); ax.legend(); fig.tight_layout(); fig.savefig(folder / 'comparison.png', dpi=160); plt.close(fig)
    text = '''<h1>Iatan 2: consolidação e piloto rastreável</h1>
<p>Estimação contemporânea de CO2 a partir de geração conhecida. Teste histórico já consultado: resultados exploratórios.</p>
<p>B0 = sete atributos de trajetória; P1 = B0 + HMM; P2 = P1 + transições do DFG. CARGA e MEMORIA117 são controles adicionais.
Os nomes físicos dos estados não foram assumidos: estados ordenados pela média de carga do treino.</p>
<h2>Verificações</h2><p>O modelo B preservado reproduziu exatamente as 1.144 previsões históricas. Para A foram conferidas apenas previsões e métricas preservadas.
O retreinamento histórico no Windows divergiu e não foi aprovado; sua causa numérica não foi isolada. Este piloto é um novo experimento controlado no mesmo ambiente.
Alvos comparados com medições horárias originais;
HMM/DFG ajustados exclusivamente no treino; filtro forward; mesma interseção amostral para os cenários.
Os resultados deste piloto não são reprodução das Fases 2–5 do Thiago: são uma adaptação documentada.</p>
<h2>Escolhas feitas na validação</h2>'''
    text += selected[['algorithm', 'seed', 'scenario', 'RMSE']].to_html(index=False)
    text += '<h2>Avaliação retrospectiva comum</h2>' + test.to_html(index=False, float_format=lambda x: f'{x:.5f}')
    text += '<img src="comparison.png" style="max-width:100%"><h2>Por contexto operacional</h2>'
    text += pd.DataFrame(contexts).to_html(index=False, float_format=lambda x: f'{x:.5f}')
    text += '''<h2>Limites e próximas análises</h2><p>Primeira execução: uma semente, uma janela de seleção (outubro) e um bimestre de avaliação.
Não demonstra superioridade estatística ou generalização multianual. HMM_NOTE
A comparação em interseção pode ter amostras diferentes do baseline histórico;
consultar selection/sample_audit.json e final/sample_audit.json. Nenhuma correção por CO2 passado ou AutoML foi habilitada.
Antes de ampliar conclusões: sementes, ablações, blocos de calendário e validação multianual com ajuste de HMM por partição.
Tempo de partida e limiar de rampa são definições operacionais próprias, não estados físicos certificados.</p>
<p>Fontes: <a href="https://doi.org/10.1002/widm.1346">Diba et al. (2020)</a>, abstração de eventos;
<a href="https://people.eecs.berkeley.edu/~matei/papers/2018/ieee_mlflow.pdf">Zaharia et al. (2018)</a>, registro experimental;
<a href="https://jmlr.org/papers/v11/cawley10a.html">Cawley e Talbot (2010)</a>, seleção e avaliação.
O material e-Science da professora (pp. 8, 23–27 e 53–56) orienta controle de fatores e proveniência.
<a href="https://github.com/prcgui/co2-cems-process-data-science/tree/main/notebooks">Notebooks do projeto</a>.
Métricas completas, configuração e previsões estão nos arquivos desta pasta e nos registros MLflow.</p>'''
    text = text.replace('HMM_NOTE', html.escape(hmm_note))
    page = '<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Iatan — piloto consolidado</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:40px auto;padding:0 20px;color:#233548}table{border-collapse:collapse;font-size:13px}td,th{padding:8px;border:1px solid #ccd4dd}h1,h2{color:#154f67}</style>' + text + '</html>'
    (folder / 'report.html').write_text(page, encoding='utf-8')
    # Append analysis artifacts to the parent run, retaining original model execution IDs.
    import mlflow
    from .tracking import configure, provenance
    configure(root)
    write_json(folder / 'analysis_provenance.json', provenance(root))
    run_id = json.loads((folder / 'tracking.json').read_text(encoding='utf-8'))['run_id']
    with mlflow.start_run(run_id=run_id):
        for name in ['report.html', 'comparison.png', 'metrics_by_context.csv', 'relative_MAE_gain_vs_B0.csv', 'selected_by_validation.csv', 'context_definition.json', 'analysis_provenance.json']:
            if (folder / name).exists(): mlflow.log_artifact(str(folder / name))
    return folder / 'report.html'
