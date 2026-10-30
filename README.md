# Análise e Modelagem de Emissões de CO₂ em Termelétrica a Carvão

## Uma abordagem orientada a processos

Projeto desenvolvido para a disciplina **IND2622: Ciência de Dados e Modelos de Processos de Negócio**, utilizando dados horários públicos da **U.S. Environmental Protection Agency (EPA)**, provenientes do ecossistema **CEMS/CAMPD**.

A unidade piloto é a **Iatan Unit 2**, Facility ID 6065, Missouri, com série horária inicial de 2025.

## Pergunta de pesquisa

> **Como o contexto e as trajetórias operacionais podem contribuir para caracterizar e estimar as emissões horárias de CO₂ de uma termelétrica a carvão?**

## Objetivo geral

> **Investigar se o conhecimento do processo operacional de uma termelétrica contribui para a caracterização das emissões horárias de CO₂ e para a precisão de sua estimação.**

## Notebooks, procedimentos metodológicos e relatórios

| Etapa | Notebook | Objetivo | Procedimentos metodológicos | Relatório | Google Colab |
|---|---|---|---|---|---|
| 01 | [`01_selecao_unidade_estudo.ipynb`](notebooks/01_selecao_unidade_estudo.ipynb) | Seleção da unidade | Triagem sucessiva de elegibilidade; cobertura CEMS; caracterização operacional | [Abrir relatório](outputs/reports/relatorio_selecao_unidade.md) | [Abrir no Colab](https://colab.research.google.com/drive/11KpbBLZD8xo9CS2H6HKUW2Bd32spE-_S) |
| 02 | [`02_tratamento_dados.ipynb`](notebooks/02_tratamento_dados.ipynb) | Auditoria e preparação | Auditoria temporal; faltantes estruturais; IQR; *feature engineering*; PCA exploratória; *temporal split*; Min–Max | [Abrir relatório](outputs/reports/relatorio_tratamento_dados.md) | [Abrir no Colab](https://colab.research.google.com/drive/1PtW8T_oWDK9-e9OHMkgngsNpGTJ87PyN) |
| 03A | [`03A_modelagem_preditiva_co2.ipynb`](notebooks/03A_modelagem_preditiva_co2.ipynb) | MLP: carga versus trajetória | *Supervised regression*; MLP *feedforward*; Adam; MSE; *EarlyStopping*; *temporal holdout*; comparação A/B | [Abrir relatório](outputs/reports/relatorio_modelagem_preditiva_3A.md) | [Abrir no Colab](https://colab.research.google.com/drive/18alc2xYDM511l5pSXpIXXxkDFrSWAC8M) |
| 03A.01 | [`03A.01_modelagem_preditiva_co2.ipynb`](notebooks/03A.01_modelagem_preditiva_co2.ipynb) | Enriquecimento temporal | *Lagged* e *rolling-window features*; prevenção de *look-ahead bias*; comparação controlada B/C; diagnóstico descritivo de *distribution shift* | [Abrir relatório](outputs/reports/relatorio_modelagem_preditiva_03A01.md) | [Abrir no Colab](https://colab.research.google.com/drive/1DVjl1v-wgQgWWtIyfE_bkCAdiVVjqJuW) |
| 03A.02 | [`03A.02_comparacao_modelos_gradient_boosting.ipynb`](notebooks/03A.02_comparacao_modelos_gradient_boosting.ipynb) | MLP versus XGBoost | GBRT/XGBoost; *walk-forward* com janela expansiva (5 folds); *early stopping*; *sanity checks*; importância por *gain* | [Abrir relatório](outputs/reports/relatorio_modelagem_preditiva_03A02.md) | [Abrir no Colab](https://colab.research.google.com/drive/1BRbZkilK4omkxV7QjMbx3uPYkI7acsNY) |
| 03A.03 | [`03A.03_otimizacao_pareada_xgboost.ipynb`](notebooks/03A.03_otimizacao_pareada_xgboost.ipynb) | Otimização pareada de XGBoost | *Random Search* (`ParameterSampler`); 30 configurações A/B × 5 folds; desenho pareado; *final refit*; sem *early stopping* na busca | [Abrir relatório](outputs/reports/relatorio_modelagem_preditiva_03A03.md) | [Abrir no Colab](https://colab.research.google.com/drive/1wbDqQxBoOi4qURULPh9EFTnNXpFUhgYj) |
| 03A.04 | [`03A.04_volume_dados_generalizacao_temporal_iatan.ipynb`](notebooks/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) | Histórico e generalização temporal | *Backtesting* com janelas de 1, 2, 3, 5 e 10 anos; validação entre anos; análise de *drift*; comparação pareada de histórico | [Abrir relatório](outputs/reports/03A04_relatorio_valor_preditivo_historico.md) | [Abrir no Colab](https://colab.research.google.com/drive/1AvnuJ-wPYravlkuZ1C0_-TWD80VWrz4m) |
| 03A.05 | [`03A.05_trajetoria_operacional_historico_ampliado.ipynb`](notebooks/03A.05_trajetoria_operacional_historico_ampliado.ipynb) | Trajetória com histórico ampliado | *Temporal feature engineering*; comparação pareada A/B em amostra comum; *early stopping*; *final refit*; análise estratificada de erros | [Abrir relatório](outputs/reports/03A05_relatorio_trajetoria_operacional_historico_ampliado.md) | [Abrir no Colab](https://colab.research.google.com/drive/1e3QA1-eq5hdaynapAQqBNFdqBlW4grJY) |

## Estratégia analítica

O trabalho articula quatro níveis de análise:

1. **Série horária:** registros de timestamp, Operating Time, carga e CO₂;
2. **Ciclo operacional:** segmentação entre startup e shutdown, com identificação por `cycle_id`;
3. **Caracterização do processo:** duração, carga média, transições e CO₂ acumulado por ciclo;
4. **Análise e modelagem:** descoberta de trajetórias e variantes, comparação entre ciclos e estimação horária de CO₂.

## Fundamentação dos métodos e referências

Os oito notebooks, da seleção da unidade até 03A.05, incluem notas metodológicas, comentários junto das etapas principais e referências completas. O [guia de fundamentação metodológica](docs/fundamentacao_metodologica.md) relaciona os procedimentos às publicações científicas ou documentações oficiais que os sustentam e identifica as escolhas próprias do estudo.

A revisão documental de 24 de outubro de 2026 explicita as fontes de retropropagação, ReLU, Adam, gradient boosting, XGBoost, busca aleatória, PCA, IQR, normalização e avaliação temporal. As arquiteturas, os hiperparâmetros, os períodos, as regras operacionais e os limiares pertencem ao protocolo do projeto. As referências não são apresentadas como origem de decisões que não prescrevem.

A documentação bibliográfica preserva código e saídas. A inspeção das novas execuções recebidas e dos complementos está descrita na seção de auditoria consolidada abaixo; a reprodução independente anterior de 03A.04 e 03A.05 continua registrada no [guia de reprodução](reproducibility/README.md).

## Fonte dos dados

Os dados são provenientes da **U.S. EPA**, com resolução horária para o ano inicial de **2025**.

A seleção considerou, entre outros critérios:

- unidades termelétricas a carvão;
- disponibilidade de dados horários;
- monitoramento de CO₂ por CEMS;
- cobertura de carga e emissões;
- operação distribuída ao longo do ano;
- presença de startups, shutdowns e rampas;
- amplitude e variabilidade de carga.

Os arquivos brutos e intermediários de grande volume não são versionados neste repositório.

## Unidade selecionada

> Caracterização técnica detalhada da unidade: [relatorio_caracterizacao_tecnica_iatan_unit2.md](outputs/reports/relatorio_caracterizacao_tecnica_iatan_unit2.md)

A unidade selecionada foi:

- **Facility:** Iatan
- **Facility ID:** 6065
- **Unit:** 2
- **Estado:** Missouri (MO)
- **Ano inicial:** 2025
- **Registros horários:** 8.760
- **Horas operacionais:** 6.249
- **Horas OFF:** 2.511
- **Startups:** 38
- **Shutdowns:** 37

A escolha resulta do equilíbrio entre qualidade dos dados, amplitude de carga e riqueza operacional.

O processo completo está documentado em:

- [Notebook 1](notebooks/01_selecao_unidade_estudo.ipynb)
- [Relatório de seleção](outputs/reports/relatorio_selecao_unidade.md)

## Tratamento e preparação dos dados

O Notebook 2 recebe automaticamente a unidade selecionada e executa:

1. auditoria estrutural e temporal;
2. análise de valores ausentes;
3. representação dos estados OFF, PARTIAL_OPERATION e FULL_OPERATION;
4. detecção exploratória de outliers por IQR;
5. feature engineering orientada ao processo;
6. PCA exploratória;
7. preparação da base para análises posteriores;
8. preparação temporal para modelagem.

O processo completo está documentado em:

- [Notebook 2](notebooks/02_tratamento_dados.ipynb)
- [Relatório de tratamento](outputs/reports/relatorio_tratamento_dados.md)

## Qualidade dos dados

A série selecionada contém as **8.760 horas de 2025**, sem duplicidades ou lacunas temporais.

Foram observadas:

- **6.249 horas operacionais**;
- **2.511 horas desligadas**;
- **77 horas de operação parcial**;
- ausência de dados faltantes de carga ou CO₂ durante operação.

Os valores ausentes nas horas OFF foram tratados como **ausências estruturais**, sem aplicação indevida de interpolação.

## Engenharia de atributos orientada ao processo

A série foi enriquecida com variáveis que representam condição instantânea e histórico recente da operação:

- carga atual;
- carga da hora anterior;
- variação horária da carga;
- intensidade absoluta da variação;
- média de carga nas três horas anteriores;
- Operating Time da hora anterior;
- eventos de startup e shutdown;
- direção da mudança de carga;
- tempo desde o último startup;
- hora do dia;
- mês.

Essa estrutura permite representar estado, memória, direção e trajetória operacional, preparando a base tanto para análise de processos quanto para modelagem preditiva.

## Outliers

A análise por intervalo interquartil, aplicada somente às horas operacionais, identificou:

- **0 outliers de carga**;
- **3 outliers de CO₂**.

Os registros extremos foram preservados, pois valores estatisticamente extremos podem representar condições operacionais reais.

## PCA exploratória

A PCA foi aplicada a sete variáveis operacionais para investigar redundância e estrutura dos dados.

| Componente | Variância explicada | Variância acumulada |
|---|---:|---:|
| PC1 | 44,07% | 44,07% |
| PC2 | 16,51% | 60,57% |
| PC3 | 14,15% | 74,72% |
| PC4 | 13,27% | 87,99% |
| PC5 | 11,66% | 99,65% |

Foram necessárias cinco componentes para superar 90% da variância. Como a redução de 7 para 5 dimensões foi pequena frente à perda de interpretabilidade, as variáveis originais foram preservadas.

Os loadings indicaram:

- **PC1:** nível de carga;
- **PC2:** dinâmica e rampas.

## Preparação experimental

A base preditiva inicial considera apenas as horas de operação.

A separação temporal utilizada no primeiro experimento foi:

- **Treino:** janeiro a setembro de 2025, 4.894 observações;
- **Validação:** outubro de 2025, 211 observações;
- **Teste:** novembro e dezembro de 2025, 1.144 observações.

A normalização foi ajustada somente sobre o treino para evitar data leakage.

Nos experimentos seguintes, novembro e dezembro passaram a ser tratados como **holdout histórico de comparação**, pois já haviam sido observados no desenvolvimento.

# Linha preditiva

## Notebook 03A: MLP com carga versus trajetória

**Procedimentos metodológicos empregados.** Aprendizado supervisionado para regressão (*supervised regression*) com uma rede neural artificial *feedforward* do tipo **Multilayer Perceptron (MLP)**, composta por duas camadas ocultas densas (64 e 32 neurônios, ReLU) e saída linear. O treinamento utilizou **Mean Squared Error (MSE)**, retropropagação executada pelo TensorFlow/Keras e otimizador **Adam**, com **EarlyStopping** monitorando a validação e recuperação dos melhores pesos. A comparação A versus B seguiu um **desenho controlado de conjuntos de atributos** (*controlled feature-set comparison*), com normalização **Min–Max ajustada somente no treino** e **temporal holdout** cronológico (treino, validação e teste). A avaliação fora da amostra empregou **MAE, RMSE e R²**, complementados por erros estratificados em startups e rampas intensas (P90 calculado no treino). Essa etapa **não** empregou validação *walk-forward* nem busca de hiperparâmetros.

**Documentação:** [Notebook 03A](notebooks/03A_modelagem_preditiva_co2.ipynb) · [Relatório metodológico e resultados 03A](outputs/reports/relatorio_modelagem_preditiva_3A.md).


Foram comparados:

- **Cenário A:** carga instantânea;
- **Cenário B:** carga + contexto e trajetória operacional.

Resultados:

| Cenário | MAE | RMSE | R² |
|---|---:|---:|---:|
| A | 67,25 | 70,90 | 0,8779 |
| B | 61,61 | 67,04 | 0,8908 |

O Cenário B apresentou redução global de MAE de aproximadamente **8,39%** e forte melhora nas primeiras horas após startup, mas piora em rampas intensas.

## Notebook 03A.01: trajetória temporal enriquecida

**Procedimentos metodológicos empregados.** **Engenharia de atributos temporais** (*temporal feature engineering*), com **variáveis defasadas** (*lagged features*, implementadas com `shift(n)`), **estatísticas de janelas móveis** (*rolling-window features*) e representação de direção, aceleração, startups e estados operacionais. O uso de `shift(1)` antes das janelas retrospectivas foi adotado para **prevenir *look-ahead bias***. Realizou-se **comparação controlada de atributos** (*controlled feature-set comparison*) entre B e C, mantendo a arquitetura MLP, Adam, MSE, *EarlyStopping* e a partição de **temporal holdout**; a equivalência completa das amostras entre notebooks não é presumida. A comparação incluiu **MAE, RMSE, R², viés e diagnósticos por contexto**, além de um diagnóstico **descritivo** de *distribution shift* e risco de extrapolação. Não se realizou teste formal de *concept drift* ou *covariate shift*.

**Documentação:** [Notebook 03A.01](notebooks/03A.01_modelagem_preditiva_co2.ipynb) · [Relatório metodológico e resultados 03A.01](outputs/reports/relatorio_modelagem_preditiva_03A01.md).


O Cenário C ampliou o conjunto de variáveis de trajetória.

Resultados principais:

- MAE B: **61,61**;
- MAE C: **62,65**;
- melhora de C em startups: **22,67%** em relação a B;
- melhora de C em rampas intensas: **1,33%**.

O enriquecimento temporal não produziu melhora global consistente.

## Notebook 03A.02: MLP x XGBoost

**Procedimentos metodológicos empregados.** Substituição da família MLP por **Extreme Gradient Boosting (XGBoost)**, um conjunto sequencial de **árvores de regressão por *gradient boosting*** (*GBRT*), com comparação dos conjuntos de atributos A (1), B (7) e C (24). Aplicou-se **validação cruzada temporal *walk-forward* com janela de treinamento expansiva** (*expanding-window time-series cross-validation*) em **cinco folds cronológicos**, além de avaliação em *holdout* histórico de 2025. O **early stopping** selecionou a complexidade efetiva das árvores por validação; **não houve *Random Search* nesta etapa**. A comparação controlada **MLP versus XGBoost** separou o efeito da família de algoritmo do efeito dos atributos. Os **sanity checks** avaliaram a integridade das variáveis, o alinhamento das observações e a ausência de sobreposição temporal; calculou-se importância das variáveis por ***gain*** (não SHAP nem efeito causal).

**Documentação:** [Notebook 03A.02](notebooks/03A.02_comparacao_modelos_gradient_boosting.ipynb) · [Relatório metodológico e resultados 03A.02](outputs/reports/relatorio_modelagem_preditiva_03A02.md).


A comparação com XGBoost mostrou forte efeito da família de modelo.

Validação temporal progressiva:

| Cenário | Features | MAE médio |
|---|---:|---:|
| A | 1 | 56,61 |
| B | 7 | 56,23 |
| C | 24 | 55,69 |

Holdout histórico:

| Cenário | MAE | RMSE | R² |
|---|---:|---:|---:|
| A-XGBoost | 22,96 | 28,06 | 0,9809 |
| B-XGBoost | 23,27 | 28,81 | 0,9798 |
| C-XGBoost | 25,02 | 30,63 | 0,9772 |

Os sanity checks não identificaram target leakage, vazamento temporal ou desalinhamento de base.

## Notebook 03A.03: busca pareada A x B

**Procedimentos metodológicos empregados.** **Busca aleatória de hiperparâmetros** (*Random Search*) com `ParameterSampler` e semente 42: **30 configurações candidatas**, aplicadas tanto ao Cenário A quanto ao B nos **mesmos cinco folds *walk-forward* com janela expansiva**, totalizando **300 ajustes**. O **desenho experimental pareado** (*paired experimental design*) manteve observações, configurações candidatas, folds e métrica primária de seleção (**MAE médio**) comparáveis, embora cada cenário pudesse selecionar uma configuração final diferente. Nesta busca, **`n_estimators` foi hiperparâmetro explícito, sem *early stopping***. Após a seleção, realizou-se **reajuste final** (*final refit*) no período de desenvolvimento e avaliação no *holdout* histórico de novembro e dezembro de 2025, com diagnóstico estratificado por startups e rampas intensas. O desenho não constitui teste formal de significância nem demonstra superioridade causal.

**Documentação:** [Notebook 03A.03](notebooks/03A.03_otimizacao_pareada_xgboost.ipynb) · [Relatório metodológico e resultados 03A.03](outputs/reports/relatorio_modelagem_preditiva_03A03.md).


Foram testadas 30 configurações de hiperparâmetros para A e B nos mesmos cinco folds temporais.

Resultados:

- B venceu **4 de 5 folds**;
- ganho médio de B na validação temporal: **+0,89%**;
- ganho de B no holdout histórico: **-1,18%**;
- ganho de B após startup: **-4,34%**;
- ganho de B em rampas intensas: **+4,88%**.

Interpretação atual:

> Para a Iatan Unit 2, com os dados de 2025 e as variáveis avaliadas, a trajetória operacional não apresentou ganho preditivo global consistente além do uso da carga instantânea.

O efeito em rampas intensas permanece como hipótese para investigação com maior histórico.

## Notebook 03A.04: histórico ampliado e generalização temporal

**Procedimentos metodológicos empregados.** O Cenário A utiliza **aprendizado supervisionado para regressão** com **Extreme Gradient Boosting (XGBoost)**, da família *gradient-boosted regression trees (GBRT)*, tendo a carga elétrica instantânea como única variável preditora. A etapa começa pela **auditoria e delimitação da amostra histórica por indicadores operacionais**, com 2011–2022 como período principal e 2023–2024 identificados como **regimes operacionais distintos** a partir de horas em operação, distribuição da carga e startups. Trata-se de **caracterização descritiva de *process drift*** e de diagnóstico de **possível *concept drift***, não de detecção estatística formal de mudança na relação carga–emissão.

A avaliação do volume histórico emprega ***rolling-origin temporal backtesting with multiple training-window lengths***: anos-alvo de **2021 a 2025**, com **janelas retrospectivas de 1, 2, 3, 5 e 10 anos**, comparação de erros entre anos e seleção de complexidade por ***early stopping*** em validação cronológica. As janelas possuem extensões alternativas predefinidas; **não** correspondem todas a uma única janela de treinamento expansiva. O protocolo também inclui **teste de generalização *out-of-time*** (treino em 2011–2022, avaliação em 2025), **reajuste final (*final refit*)** após a seleção do número de árvores e **experimento controlado e pareado de disponibilidade do histórico** (*paired controlled experiment on training-history availability*), comparando janeiro–outubro de 2025 com 2011–2022 acrescido do mesmo período recente. São calculados **MAE, RMSE, R², NMAE, bias e diferenças horárias de erro**. Novembro e dezembro de 2025 são *holdout* temporal da comparação, mas não avaliação inteiramente cega do conjunto da pesquisa.

**Documentação:** [Notebook 03A.04](notebooks/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) · [Relatório de delimitação da amostra histórica](outputs/reports/03A04_delimitacao_amostra_historica.md) · [Relatório metodológico e resultados 03A.04](outputs/reports/03A04_relatorio_valor_preditivo_historico.md).


O Notebook 03A.04 ampliou a série temporal da Iatan Unit 2 e avaliou o valor preditivo do histórico para o **Cenário A**, baseado exclusivamente na carga instantânea:

`CO₂(t) = f(P(t))`

A delimitação temporal adotada foi:

- **2010:** período parcial de commissioning, excluído da amostra principal;
- **2011–2022:** histórico operacional de referência;
- **2023–2024:** regime operacional distinto, preservado para análises específicas, mas excluído da amostra principal;
- **2025:** período futuro de avaliação.

A delimitação de 2011 a 2022 foi exploratória e consolidada após os backtests, que incluíram avaliação em 2025. A justificativa operacional para o tratamento de 2023 e 2024 está em [03A04_delimitacao_amostra_historica.md](outputs/reports/03A04_delimitacao_amostra_historica.md).

### Generalização 2011–2022 para 2025

O modelo treinado exclusivamente com **83.832 observações de 2011 a 2022** foi avaliado nas **6.249 horas operacionais válidas de 2025**.

| Métrica | Resultado |
|---|---:|
| MAE | 50,2740 |
| RMSE | 68,4650 |
| R² | 0,8894 |
| NMAE | 8,65% |
| Bias | -33,9686 |

O resultado demonstra que o padrão histórico de carga e emissão mantém capacidade relevante de transferência temporal para 2025, embora existam deslocamentos entre períodos e degradação localizada do erro.

### Valor incremental do histórico

Em seguida, foi realizada uma comparação pareada no mesmo conjunto de teste de novembro e dezembro de 2025.

| Modelo | MAE | RMSE | R² | NMAE |
|---|---:|---:|---:|---:|
| Jan–Out/2025 | 23,3470 | 28,5786 | 0,9802 | 3,97% |
| 2011–2022 + Jan–Out/2025 | **20,2454** | **25,1240** | **0,9847** | **3,44%** |

A incorporação do histórico reduziu o MAE em **13,28%** e o RMSE em **12,09%**. O modelo com histórico apresentou menor erro absoluto em **65,30%** das horas avaliadas.

Portanto, o histórico de 2011 a 2022 não apenas permite generalização para 2025, mas também acrescenta informação quando combinado com dados recentes do próprio ano.

O relatório consolidado está em [03A04_relatorio_valor_preditivo_historico.md](outputs/reports/03A04_relatorio_valor_preditivo_historico.md).

## Arquivos-chave do Notebook 03A.04

Para facilitar a navegação pelos resultados desta etapa:

- [Notebook 03A.04](notebooks/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb)
- [Relatório de delimitação da amostra histórica](outputs/reports/03A04_delimitacao_amostra_historica.md)
- [Relatório do valor preditivo do histórico](outputs/reports/03A04_relatorio_valor_preditivo_historico.md)
- [Tabela de generalização 2011–2022 para 2025](outputs/tables/03A04_generalizacao_2011_2022_para_2025.csv)
- [Comparação pareada: 2025 versus histórico + 2025](outputs/tables/03A04_comparacao_2025_vs_historico_2025.csv)
- [Síntese das evidências do histórico](outputs/tables/03A04_sintese_evidencias_historico.csv)
- [Figura de comparação dos erros](outputs/figures/03A04_comparacao_2025_vs_historico_2025_erros.png)
- [Séries observada e previstas](outputs/figures/03A04_comparacao_2025_vs_historico_2025_series.png)

## Notebook 03A.05: trajetória operacional com histórico ampliado

**Procedimentos metodológicos empregados.** Regressão supervisionada com **XGBoost/GBRT** nos Cenários A (carga instantânea) e B (carga, memória e trajetória operacional), mantendo os **mesmos hiperparâmetros estruturais**. No Cenário B, a ***temporal feature engineering*** utiliza ***lagged features*** (`shift(1)`), ***rolling-window features*** e indicadores de transições operacionais. O agrupamento em ***temporal blocks*** impede que o final de 2022 seja interpretado como imediatamente anterior ao início de 2025, reduzindo o risco de ***look-ahead bias*** e de continuidade temporal artificial. A auditoria de qualidade identificou uma carga ausente em 2019, **preservada sem imputação**, e o tempo desde startup semanticamente desconhecido no início do histórico; as observações não elegíveis foram retiradas igualmente dos dois cenários.

A avaliação segue um ***paired experimental design on a common eligible sample*** (*desenho experimental pareado em amostra comum*): A e B utilizam as mesmas observações, o mesmo alvo e a mesma partição cronológica. O número de árvores é selecionado separadamente por ***early stopping*** em **outubro de 2025** (RMSE de validação; paciência de 50 rodadas), seguido de ***final refit*** com 2011–2022 e janeiro–outubro de 2025. A comparação em **novembro–dezembro de 2025** utiliza ***temporal holdout*** histórico e **análise pareada de erros hora a hora**, incluindo MAE, RMSE, R², NMAE e bias. A ***context-stratified error analysis*** examina startups, **rampas intensas definidas pelo P90 calculado no treino**, demais horas e casos extremos. Esta etapa **não** executa *Random Search*, *walk-forward cross-validation*, teste formal de significância, modelo híbrido ou análise causal; tampouco demonstra previsão antecipada sem conhecimento da carga da própria hora.

**Documentação:** [Notebook 03A.05](notebooks/03A.05_trajetoria_operacional_historico_ampliado.ipynb) · [Relatório metodológico e resultados 03A.05](outputs/reports/03A05_relatorio_trajetoria_operacional_historico_ampliado.md).


A linha preditiva incorporou uma comparação controlada dos modelos **XGBoost A (carga instantânea)** e **B (carga e trajetória operacional)**, utilizando o histórico operacional de 2011–2022 e dados de janeiro a outubro de 2025 para treinamento. Os modelos foram avaliados nas mesmas horas de novembro e dezembro de 2025.

| Métrica | Cenário A | Cenário B |
|---|---:|---:|
| MAE (short tons de CO₂ por registro horário) | **20,1514** | 21,1720 |
| NMAE | **3,4240%** | 3,5974% |
| Ganho global de MAE de B sobre A | Referência | **−5,06%** |

O Cenário B não melhorou o MAE global. Contudo, apresentou **redução de 22,90% do MAE nas rampas intensas** e ganho agregado nas primeiras seis horas após startup. Nas demais horas, B apresentou MAE aproximadamente **16,03% maior**, prejudicando o desempenho agregado.

Esses achados mostram que a **informação de trajetória operacional pode ser útil em determinados contextos do processo, sem necessariamente melhorar a estimação em todas as horas**. A avaliação é descritiva e não demonstra causalidade.

Arquivos associados: [notebook 03A.05](notebooks/03A.05_trajetoria_operacional_historico_ampliado.ipynb), [relatório completo](outputs/reports/03A05_relatorio_trajetoria_operacional_historico_ampliado.md), [resultados finais](outputs/tables/03A05_resultado_final_A_B.csv), [erros por contexto](outputs/tables/03A05_comparacao_contextos_operacionais.csv), [síntese das evidências](outputs/tables/03A05_sintese_evidencias_trajetoria_historico.csv), [ganhos por contexto](outputs/figures/03A05_ganho_trajetoria_por_contexto.png) e [distribuição dos ganhos horários](outputs/figures/03A05_distribuicao_ganho_horario_B_vs_A.png).

## Síntese da linha preditiva até o Notebook 03A.05

A investigação mostrou que o desempenho das estimativas de emissões depende da família algorítmica, da composição temporal do histórico e do regime operacional. No Notebook 03A.04, a incorporação de 2011–2022 aos dados recentes reduziu o MAE do Cenário A em **13,28%** na comparação com o treinamento baseado apenas em janeiro a outubro de 2025.

A inclusão de variáveis de trajetória não apresentou ganho global consistente nos experimentos XGBoost, mas revelou valor informativo em rampas intensas. Essas constatações são específicas da Iatan Unit 2 e das amostras avaliadas. Novembro e dezembro de 2025 constituem um período de comparação histórica, pois já haviam sido utilizados em análises anteriores.

A linha de processos mantém objetivos próprios, apresentados a seguir. Seus resultados e seus eventuais desenvolvimentos não são presumidos pelos experimentos preditivos.

# Linha de processos

## Leitura do processo operacional

A base permite identificar elementos típicos do processo:

- **OFF**;
- **startup**;
- aumento de carga;
- operação em diferentes níveis;
- redução de carga;
- **shutdown**.

A etapa de processos reorganizará a série em um **Event Log**, no qual:

- `case_id` representará uma execução do processo;
- `timestamp` preservará a ordem temporal;
- `activity` representará estados ou transições.

## Process Mining

A análise de processos deverá investigar:

- ciclos completos entre startup e shutdown;
- variantes de ciclo;
- frequência das trajetórias;
- duração dos ciclos;
- transições operacionais;
- comportamento de carga;
- emissões associadas;
- diferenças entre execuções;
- indicadores por ciclo.

O objetivo é reconstruir o processo **AS-IS** e avaliar de que forma a informação processual ajuda a explicar as emissões e o comportamento operacional.

## Próxima etapa da linha de processos

O próximo bloco específico de processos deverá:

- atribuir `cycle_id` ou `case_id`;
- construir o Event Log;
- definir atividades operacionais;
- identificar trajetórias e variantes;
- calcular indicadores por ciclo;
- aplicar técnicas de Process Mining;
- relacionar variantes operacionais às emissões.

## Artefatos

Os artefatos estão organizados em:

- [outputs/reports](outputs/reports): relatórios de seleção, tratamento, modelagem e diagnósticos;
- [outputs/tables](outputs/tables): métricas, previsões, validações e resultados experimentais;
- [outputs/figures](outputs/figures): figuras exploratórias e diagnósticos.

## Estrutura atual do repositório

```text
co2-cems-process-data-science/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   ├── 01_selecao_unidade_estudo.ipynb
│   ├── 02_tratamento_dados.ipynb
│   ├── 03A_modelagem_preditiva_co2.ipynb
│   ├── 03A.01_modelagem_preditiva_co2.ipynb
│   ├── 03A.02_comparacao_modelos_gradient_boosting.ipynb
│   ├── 03A.03_otimizacao_pareada_xgboost.ipynb
│   ├── 03A.04_volume_dados_generalizacao_temporal_iatan.ipynb
│   └── 03A.05_trajetoria_operacional_historico_ampliado.ipynb
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── pipeline/
└── outputs/
    ├── reports/
    ├── figures/
    ├── tables/
    └── presentations/
```

## Executar os notebooks

Os notebooks devem ser executados na ordem apresentada no início deste README.

O Notebook 1 utiliza uma chave da API da EPA armazenada como segredo do Google Colab com o nome `EPA_API_KEY`.

Os notebooks utilizam os diretórios de trabalho definidos em suas células de configuração no Google Drive. As bases horárias brutas e intermediárias, por seu volume, não são versionadas neste repositório.

Para execução local:

```bash
pip install -r requirements.txt
```


## Reprodução verificada de 03A.04 e 03A.05

O [guia de reprodução](reproducibility/README.md) documenta os insumos, o ambiente fixado, a execução local, as correções de integridade e as evidências geradas. A execução integral reproduziu os sete CSVs de referência byte a byte; nove Parquets de amostras e previsões mantiveram valores e tipos exatamente iguais aos originais preservados. O guia explicita as diferenças de serialização, a correção do consolidado e os limites científicos desta verificação.

A [auditoria do monitoramento histórico](reproducibility/monitoring/README.md) documenta métodos declarados, vigências da instrumentação, indicadores de medição e substituição e as limitações dessa evidência.


## Autores

- Guilherme Pereira Rodrigues da Costa
- Felipe Calmon
- Thiago Menezes

## Disciplina

**IND2622: Ciência de Dados e Modelos de Processos de Negócio**  
Professora: **Fernanda A. B. Amorim**  
PUC-Rio

## Verificação da aplicação dos métodos

As técnicas citadas foram conferidas por confronto com as fontes, extração das funções dos notebooks, cálculos independentes e consulta aos modelos e resultados preservados. O [relatório técnico e os scripts](reproducibility/methods/README.md) registram cada verificação e suas condições. Também foram corrigidas as alegações de suficiência de 30 configurações, de isolamento exclusivo dos efeitos e de independência global do teste.


## Biblioteca de referências

A documentação bibliográfica auditada está em [`references/`](references/README.md). O registro mestre [`source_registry.csv`](references/source_registry.csv) informa DOI/URL, status de acesso, condição de redistribuição e finalidade de cada uma das 22 fontes. PDFs públicos arquivados ficam em [`references/public_pdfs/`](references/public_pdfs/).

## Auditoria consolidada e complementos executados

As oito execuções principais recebidas em 29 de outubro de 2026 foram inspecionadas integralmente. A ablação 03A.05A, a sensibilidade temporal 03A.05B e a comparação de cinco sementes 03A.05C também estão concluídas no Colab. A conferência final dos três complementos reuniu 376 verificações aprovadas, incluindo recálculo das métricas e recarga dos 20 modelos de 03A.05C. Isso não constitui novo treinamento local independente de todos os ajustes. O notebook 03A.06 permanece histórico.

- [Artigo atualizado](Artigo_CO2_Modelagem_Matematica_IA.docx)
- [Relatório final de auditoria](outputs/auditoria_consolidada_2026-10-29/Relatorio_final_auditoria.txt)
- [Resultados, protocolos e verificações](outputs/auditoria_consolidada_2026-10-29/)
- [Ablação executada 03A.05A](notebooks/03A_05A_ablacao_controlada_features_Colab.ipynb)
- [Sensibilidade de calendário 03A.05B](notebooks/03A_05B_incerteza_pareada_calendario.ipynb)
- [MLP e XGBoost com cinco sementes 03A.05C](notebooks/03A_05C_MLP_XGBoost_sementes_protocolo_comum_Colab.ipynb)
- [Catálogo de fontes](references/metadata/source_registry.csv) e [índice dos PDFs preparados para o Drive](references/metadata/pdfs_referencias_utilizadas.csv)

Os resultados principais mantêm os ganhos descritivos já existentes de 13,28% com histórico ampliado e 22,90% nas rampas. A ablação não identificou ganho global consistente. Em 03A.05C, XGBoost teve menor MAE no teste em todos os pares de mesma semente/cenário, com inversão da ordenação na validação. Esses protocolos permanecem separados; cinco sementes não equivalem a novos períodos de teste. Os limites de 03A.05B são exploratórios.

Os PDFs privados e os dados volumosos permanecem no Drive do projeto. O índice identifica as versões e o conteúdo por SHA-256; links históricos continuam representando suas versões preservadas.

O [registro de sincronização](outputs/auditoria_consolidada_2026-10-29/sincronizacao_destinos.json) distingue a publicação no GitHub do envio ao Drive. Na consolidação de 30/10/2026, o pacote local para o Drive está pronto; o upload permanece pendente por falha do seletor de arquivos da ferramenta.
