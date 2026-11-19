# Sequência inicial de Ciência de Dados

Os 11 notebooks apresentam a seleção da unidade, os dados e os modelos de referência de Iatan 2, antes da representação por mineração de processos. As células conservam os resultados científicos salvos.

| Notebook, na ordem de execução | Executar |
|---|---|
| [Seleção da unidade](01_selecao_unidade_estudo.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/01_selecao_unidade_estudo.ipynb) |
| [Preparação dos dados](02_tratamento_dados.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/02_tratamento_dados.ipynb) |
| [MLP: carga e trajetória](03A_modelagem_preditiva_co2.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A_modelagem_preditiva_co2.ipynb) |
| [Atributos temporais](03A.01_modelagem_preditiva_co2.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A.01_modelagem_preditiva_co2.ipynb) |
| [MLP e XGBoost](03A.02_comparacao_modelos_gradient_boosting.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A.02_comparacao_modelos_gradient_boosting.ipynb) |
| [Otimização pareada](03A.03_otimizacao_pareada_xgboost.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A.03_otimizacao_pareada_xgboost.ipynb) |
| [Volume de histórico](03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) |
| [Comparação final A/B](03A.05_trajetoria_operacional_historico_ampliado.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A.05_trajetoria_operacional_historico_ampliado.ipynb) |
| [Ablação de atributos](03A_05A_ablacao_controlada_features_Colab.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A_05A_ablacao_controlada_features_Colab.ipynb) |
| [Sensibilidade temporal](03A_05B_incerteza_pareada_calendario.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A_05B_incerteza_pareada_calendario.ipynb) |
| [Comparação entre sementes](03A_05C_MLP_XGBoost_sementes_protocolo_comum_Colab.ipynb) | [Colab](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_sem_mineracao_de_processos/03A_05C_MLP_XGBoost_sementes_protocolo_comum_Colab.ipynb) |

## Executar no Colab

Use uma sessão nova com CPU. A pasta própria desta sequência em Meu Drive é `Ciência de Dados - Iatan - Process Mining e Experimentos/Iatan 2025 - entrega revisada/01 - Sem mineração de processos`, com `notebooks/`, `scripts/`, `pipeline/` e `data/`. A primeira célula conecta o Drive e localiza essa pasta. Para outra localização, defina `IATAN_BASELINE_ROOT`.

Instale as dependências dessa raiz com `requirements-baseline.txt`; `constraints-baseline.txt` fixa as versões. Para a aquisição de dados, configure o segredo Colab `EPA_API_KEY`. Os demais notebooks reutilizam os insumos preservados.

Os anuais ficam em `data/interim/03A04_multiyear/`; as partições e previsões comuns em `data/interim/03A05_trajectory_history/`. O 5A utiliza os insumos do 5; o 5B utiliza previsões preservadas do 5 e da ablação; o 5C utiliza as partições comuns. `03A05BC_insumos.zip` é uma alternativa de transporte desses arquivos. As rodadas de 5A–5C criam subpastas exclusivas em `outputs/` e preservam os resultados anteriores.

Para execução local, instale `requirements-baseline.txt` e abra os notebooks a partir da raiz que contém `scripts/baseline_paths.py`. A raiz do repositório também é aceita. As [tabelas de referência](../../reproducibility/baselines/) acompanham o código. A pesquisa prossegue nos [notebooks de mineração de processos](../02_com_mineracao_de_processos/).
