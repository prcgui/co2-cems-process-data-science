# Fundamentação metodológica e fontes dos procedimentos

Este guia relaciona os procedimentos utilizados no estudo da Iatan Unit 2 às publicações científicas, aos manuais e à documentação oficial que os fundamentam. A matriz permite localizar cada técnica nos oito notebooks e identificar quais decisões pertencem ao protocolo do projeto.

O problema consiste em estimar `CO2 Mass (short tons)` por registro horário a partir de entradas operacionais conhecidas, incluindo a carga da própria hora. A avaliação em períodos posteriores ao treinamento verifica o desempenho fora do período de ajuste; ela não transforma o problema em previsão antecipada com carga futura desconhecida. Os resultados e a implementação estão registrados neste repositório (Costa; Calmon; Menezes, 2026).

**Revisão de 24 de outubro de 2026.** As referências foram confrontadas com as formulações originais e com a aplicação nos notebooks. A [verificação técnica](../reproducibility/methods/README.md) reúne cálculos independentes, ensaios controlados e inferência com modelos preservados. Os valores dos resultados do estudo foram mantidos. A reprodução computacional de 03A.04 e 03A.05 permanece documentada em [reprodução](../reproducibility/README.md).

## Natureza das fontes

Os artigos fundamentam conceitos, algoritmos e cuidados de avaliação. Os manuais da EPA descrevem os dados e o monitoramento regulatório; o NIST/SEMATECH documenta procedimentos estatísticos; a documentação do scikit-learn esclarece transformações e funções implementadas. Essas fontes oficiais não são classificadas como artigos científicos. Os critérios de seleção, atributos, calendários, limiares e hiperparâmetros específicos são escolhas do estudo, explicitadas no código.

## Matriz de fundamentação

| Procedimento | Fonte e natureza | Local de uso | Alcance e decisões do estudo |
|---|---|---|---|
| Origem e interpretação dos registros CAMPD/CEMS e do alvo `CO2 Mass (short tons)` | United States (2026), conjunto de dados; United States (2022), guia oficial da EPA | 01, 02 e 03A.04; leitura e caracterização dos dados | O guia orienta a leitura dos dados reportados. A massa é mantida por registro horário, inclusive nas horas parcialmente operadas, sem divisão por `Operating Time`. Não se presume que todo registro tenha sido inteiramente medido. |
| Elegibilidade pelo método CO₂/CEM e interpretação das vigências | United States (2024), instruções oficiais ECMPS | 01; [auditoria de monitoramento](../reproducibility/monitoring/README.md) | O manual sustenta a interpretação dos campos e das vigências. Limiares de completude, ranking e escolha retrospectiva de Iatan são próprios do estudo. O filtro original com `contains("measured")` inclui `Measured` e `Measured and Substitute`; a auditoria distingue as categorias. |
| Motivação para examinar carga e condições operacionais | F. Liu e Li (2025), artigos | 01, 02, 03A, 03A.01 e 03A.05 | A fonte motiva a análise da relação entre carga, características do carvão, comportamento térmico e emissão. Os sete ou 24 atributos deste projeto são escolhas próprias, cujo ganho depende da avaliação empírica. |
| Sinalização de valores extremos por intervalo interquartil | National Institute of Standards and Technology e SEMATECH (2012), manual oficial | 02, função `calculate_iqr_limits` | São utilizados os limites Q1 − 1,5 × IQR e Q3 + 1,5 × IQR. Os indicadores `load_outlier_iqr` e `co2_outlier_iqr` sinalizam registros; os pontos são mantidos. Um extremo estatístico não comprova erro de medição. |
| Análise de componentes principais | Jolliffe e Cadima (2016), artigo | 02, análise exploratória dos sete atributos | A PCA utiliza entradas padronizadas por escore z e examina variância e correlação. A decisão de manter os atributos originais nos modelos pertence ao estudo; as componentes não são entradas dos estimadores. |
| Representação explícita da memória operacional | Motivação temática em F. Liu e Li (2025); construção própria | 02, 03A.01, 03A.02 e 03A.05; listas `FEATURES_B`, `FEATURES_C` e atributos derivados | Defasagens, diferenças, janelas e contador de partida são definidos no projeto. São calculados na série de calendário antes da seleção ON. No histórico ampliado, 2011 a 2022 e 2025 são blocos distintos, evitando continuidade fictícia entre dezembro de 2022 e janeiro de 2025. |
| Separação cronológica e validação por períodos sucessivos | Cerqueira, Torgo e Mozetič (2020), artigo; Cawley e Talbot (2010), artigo sobre seleção | 02, 03A, 03A.01 e etapas XGBoost; `FOLDS` em 03A.02 e 03A.03 | Os trabalhos sustentam os cuidados de avaliação, sem prescrever o calendário utilizado. O teste não entra no ajuste de cada modelo, mas sua consulta durante o desenvolvimento limita a independência da avaliação em relação às decisões da pesquisa. |
| Transformação MinMax | Scikit-learn (2025), documentação oficial versionada | 02, 03A e 03A.01; `MinMaxScaler` | Os extremos são ajustados no treinamento e reutilizados nos conjuntos reservados. Quando o alvo é normalizado, as estimativas retornam à unidade original antes da avaliação. A arquitetura temporal e o uso da transformação são decisões do protocolo. |
| Rede neural multicamadas e retropropagação | Rumelhart, Hinton e Williams (1986), artigo | 03A e 03A.01; `build_mlp`, com TensorFlow/Keras | A publicação fundamenta a aprendizagem por retropropagação. A rede de camadas densas 64/32 e a saída linear são configurações do projeto; a retropropagação é executada pela biblioteca, sem reimplementação manual. |
| Unidades retificadoras e otimização Adam | Glorot, Bordes e Bengio (2011); Kingma e Ba (2015), trabalhos de conferência | 03A e 03A.01; ativação ReLU e treinamento da MLP | As fontes fundamentam as técnicas. Taxa de aprendizagem, lotes, limite de épocas, paciência, restauração de pesos e semente são escolhas experimentais, sem alegação de que esses artigos recomendem os valores usados. |
| Gradient boosting e XGBoost | Friedman (2001), artigo; Chen e Guestrin (2016), trabalho de conferência | 03A.02 a 03A.05; `XGBRegressor` e funções de construção dos modelos | As fontes fundamentam a combinação de árvores e a formulação regularizada. Versão da biblioteca, hiperparâmetros, métrica de seleção e reajuste pertencem à implementação e ao protocolo registrados. |
| Busca aleatória de hiperparâmetros | Bergstra e Bengio (2012), artigo; Scikit-learn (2025), documentação | 03A.03; `ParameterSampler`, `N_CONFIGS` e `SEARCH_SPACE` | Foram definidos 30 sorteios, semente 42, dois cenários e cinco partições. A mesma lista gera 300 ajustes; `n_estimators` integra a busca, sem interrupção antecipada nessa etapa. Esses valores não são prescritos pela fonte. |
| MAE, mediana do erro absoluto e RMSE | Hyndman e Koehler (2006), artigo; Scikit-learn (2025), documentação das funções | 03A a 03A.05; funções `regression_metrics`, `metrics_03A04` e `calculate_metrics`, conforme a etapa | As medidas descrevem a magnitude do erro na unidade do alvo. Sua comparação exige o mesmo conjunto de observações ou a explicitação das diferenças de amostra e protocolo. |
| R², NMAE, viés e ganho pareado | Scikit-learn (2025), documentação para R²; convenções explícitas do estudo para NMAE, viés e ganhos | Etapas de avaliação, especialmente 03A.04 e 03A.05; `regression_metrics` e `summarize_context` | NMAE = 100 × MAE / média observada no conjunto avaliado. Resíduo e viés seguem observado menos previsto. Ganho de B = 100 × (MAE A − MAE B) / MAE A. Essas convenções não são atribuídas a uma definição universal. A análise pareada é descritiva, sem teste de significância. |
| Janelas históricas e diagnóstico de diferenças entre períodos | Cerqueira, Torgo e Mozetič (2020); Gama *et al.* (2014); Cawley e Talbot (2010), artigos | 03A.04 e diagnósticos de 03A.01 | As janelas de 1, 2, 3, 5 e 10 anos e os anos-alvo são escolhas próprias. Indicadores descritivos não constituem detecção formal de concept drift. A delimitação de 2011 a 2022 foi exploratória e posterior a backtests que incluíram 2025. |
| Comparação final em amostra comum e análise por contexto | Cuidados de avaliação em Cawley e Talbot (2010); desenho específico do projeto | 03A.05; elegibilidade comum A/B e `summarize_context` | A interseção iguala os horários avaliados, mas os cenários podem selecionar quantidades distintas de árvores. As seis primeiras horas de partida e o P90 de variação absoluta são decisões próprias. Partida e rampa podem se sobrepor; limiares distintos entre etapas definem grupos diferentes. |
| Integridade, rastreabilidade e reprodução | Implementação e evidências do projeto, Costa, Calmon e Menezes (2026) | `load_verified_annual_frame` em 03A.04; validações em 03A.05; `scripts/reproduce_history.py`; `outputs/reproducibility/` | Identificação da unidade, calendário, duplicatas, hashes e comparação das saídas são controles implementados no projeto. Os registros de reprodução e de verificação dos métodos delimitam os procedimentos efetivamente executados e seus resultados. |

## Mapa dos notebooks

Os códigos abaixo identificam arquivos, não versões metodologicamente idênticas. As respectivas células descrevem diferenças de atributos, seleção de complexidade, amostras e reajuste.

| Identificador | Arquivo | Conteúdo principal |
|---|---|---|
| 01 | [Seleção da unidade](../notebooks/01_selecao_unidade_estudo.ipynb) | População de candidatas, qualidade dos dados, monitoramento e seleção retrospectiva de Iatan. |
| 02 | [Tratamento dos dados](../notebooks/02_tratamento_dados.ipynb) | Estados operacionais, valores extremos, atributos, PCA, partição cronológica e normalização. |
| 03A | [Modelagem preditiva de CO₂](../notebooks/03A_modelagem_preditiva_co2.ipynb) | MLP para carga atual e carga com trajetória, com avaliação global e por contexto. |
| 03A.01 | [Ampliação dos atributos na MLP](../notebooks/03A.01_modelagem_preditiva_co2.ipynb) | Cenário C com 24 atributos e comparação com os resultados anteriores. |
| 03A.02 | [Comparação com gradient boosting](../notebooks/03A.02_comparacao_modelos_gradient_boosting.ipynb) | Cenários A/B/C, validação cronológica do XGBoost e comparação com MLP. |
| 03A.03 | [Otimização pareada do XGBoost](../notebooks/03A.03_otimizacao_pareada_xgboost.ipynb) | Busca aleatória com orçamento comum e seleção por MAE médio nas cinco validações. |
| 03A.04 | [Histórico e generalização temporal em Iatan](../notebooks/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) | Backtests, janelas históricas, transferência temporal na mesma unidade e valor incremental do histórico. |
| 03A.05 | [Trajetória com histórico ampliado](../notebooks/03A.05_trajetoria_operacional_historico_ampliado.ipynb) | Amostra comum, comparação final A/B e análise de partida e rampas. |

## Campos e decisões operacionais

O cenário A utiliza `load_current_mw`. O cenário B contém `load_current_mw`, `load_lag_1h`, `delta_load_1h`, `abs_delta_load_1h`, `load_mean_previous_3h`, `operating_time_lag_1h` e `hours_since_startup`. O cenário C acrescenta 17 atributos, conforme suas listas nos notebooks. A presença de variáveis operacionais da hora corrente caracteriza a estimação contemporânea; a memória é representada explicitamente nos atributos, sem arquitetura recorrente.

As regras ON/OFF derivam de `Operating Time > 0` e `Operating Time = 0`. A preservação de horas ON com operação parcial ou carga zero, a formação da amostra comum, as datas de treinamento e o tratamento do início de cada bloco estão descritos nas respectivas células. Os artigos citados não determinam essas escolhas. A engenharia e a avaliação devem ser interpretadas em conjunto com a implementação e suas saídas preservadas (Costa; Calmon; Menezes, 2026).

Na comparação final, o teste de novembro e dezembro de 2025 permaneceu fora do ajuste dos modelos, porém já havia sido examinado em etapas anteriores. A seleção retrospectiva da unidade e do histórico, as diferenças de complexidade entre cenários, a semente única por configuração e a análise sem intervalos de confiança limitam a extensão das conclusões. A divisão cronológica e a reprodução computacional não eliminam o risco de seleção discutido por Cawley e Talbot (2010).

## Trabalhos temáticos e limites de transferência

Zhou *et al.* (2023), Tu *et al.* (2024) e X. Liu *et al.* (2025) contextualizam a estimação de emissões por aprendizado de máquina. Zhou *et al.* avaliam emissões simuladas. Tu *et al.* combinam seleção de atributos, Deep Forest e otimização. X. Liu *et al.* trabalham com observações diárias e informações diferentes das utilizadas neste caso. Seu papel é a comparação com trabalhos relacionados; os algoritmos aplicados neste projeto são identificados nas linhas específicas da matriz.

Essas diferenças de alvo, frequência, origem dos dados e informação disponível impedem ordenar os estudos pelos seus valores brutos de erro. A aplicação em Iatan é um estudo da própria unidade, sem demonstração de transferência para outras instalações. A fundamentação não substitui a validação empírica dos atributos e configurações escolhidos.

## Referências

As entradas usam o sistema autor-data e a apresentação bibliográfica adotados no artigo. Os links identificam a publicação, a documentação oficial ou o repositório correspondente. As publicações científicas fundamentam as técnicas; documentos de software, guias e registros do projeto preservam sua natureza específica.


BERGSTRA, J.; BENGIO, Y. Random Search for Hyper-Parameter Optimization. **Journal of Machine Learning Research**, *[s. l.]*, v. 13, n. 10, p. 281-305, 2012. Disponível em: https://jmlr.org/papers/v13/bergstra12a.html. Acesso em: 24 out. 2026.

CAWLEY, G. C.; TALBOT, N. L. C. On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation. **Journal of Machine Learning Research**, *[s. l.]*, v. 11, n. 70, p. 2079-2107, 2010. Disponível em: https://jmlr.org/papers/v11/cawley10a.html. Acesso em: 24 out. 2026.

CERQUEIRA, V.; TORGO, L.; MOZETIČ, I. Evaluating time series forecasting models: an empirical study on performance estimation methods. **Machine Learning**, *[s. l.]*, v. 109, n. 11, p. 1997-2028, 2020. DOI: https://doi.org/10.1007/s10994-020-05910-7. Disponível em: https://link.springer.com/article/10.1007/s10994-020-05910-7. Acesso em: 24 out. 2026.

CHEN, T.; GUESTRIN, C. XGBoost: A Scalable Tree Boosting System. *In:* ACM SIGKDD INTERNATIONAL CONFERENCE ON KNOWLEDGE DISCOVERY AND DATA MINING, 22., 2016, San Francisco. **Proceedings [...]**. New York: ACM, 2016. p. 785-794. DOI: https://doi.org/10.1145/2939672.2939785. Disponível em: https://www.kdd.org/kdd2016/papers/files/rfp0697-chenAemb.pdf. Acesso em: 24 out. 2026.

COSTA, G. P. R.; CALMON, F.; MENEZES, T. **co2-cems-process-data-science**. *[S. l.]*: GitHub, 2026. Repositório de código, relatórios e resultados. Versões utilizadas identificadas na seção Disponibilidade de dados e código. Disponível em: https://github.com/prcgui/co2-cems-process-data-science. Acesso em: 24 out. 2026.

FRIEDMAN, J. H. Greedy function approximation: A gradient boosting machine. **The Annals of Statistics**, *[s. l.]*, v. 29, n. 5, p. 1189-1232, 2001. DOI: https://doi.org/10.1214/aos/1013203451. Disponível em: https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-5/Greedy-function-approximation-A-gradient-boosting-machine/10.1214/aos/1013203451.full. Acesso em: 24 out. 2026.

GAMA, J.; ŽLIOBAITĖ, I.; BIFET, A.; PECHENIZKIY, M.; BOUCHACHIA, A. A survey on concept drift adaptation. **ACM Computing Surveys**, *[s. l.]*, v. 46, n. 4, art. 44, p. 1-37, 2014. DOI: https://doi.org/10.1145/2523813. Disponível em: https://dl.acm.org/doi/10.1145/2523813. Acesso em: 24 out. 2026.

GLOROT, X.; BORDES, A.; BENGIO, Y. Deep Sparse Rectifier Neural Networks. *In:* INTERNATIONAL CONFERENCE ON ARTIFICIAL INTELLIGENCE AND STATISTICS, 14., 2011, Fort Lauderdale. **Proceedings [...]**. *[S. l.]*: PMLR, 2011. v. 15, p. 315-323. Disponível em: https://proceedings.mlr.press/v15/glorot11a.html. Acesso em: 24 out. 2026.


HYNDMAN, R. J.; KOEHLER, A. B. Another look at measures of forecast accuracy. **International Journal of Forecasting**, *[s. l.]*, v. 22, n. 4, p. 679-688, 2006. DOI: https://doi.org/10.1016/j.ijforecast.2006.03.001. Disponível em: https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/. Acesso em: 24 out. 2026.

JOLLIFFE, I. T.; CADIMA, J. Principal component analysis: a review and recent developments. **Philosophical Transactions of the Royal Society A**: Mathematical, Physical and Engineering Sciences, *[s. l.]*, v. 374, n. 2065, art. 20150202, 2016. DOI: https://doi.org/10.1098/rsta.2015.0202. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC4792409/. Acesso em: 24 out. 2026.

KINGMA, D. P.; BA, J. **Adam**: A Method for Stochastic Optimization. *[S. l.: s. n.]*, 2015. Trabalho apresentado na 3rd International Conference on Learning Representations, San Diego, 2015. Disponível em: https://arxiv.org/abs/1412.6980. Acesso em: 24 out. 2026.

LIU, F.; LI, S. Prediction of Carbon Emissions from Coal-Fired Power Plants During Load Cycling with Varying Coal Characteristics. **Fuels**, Basel, v. 6, n. 1, art. 1, 2025. DOI: https://doi.org/10.3390/fuels6010001. Disponível em: https://www.mdpi.com/2673-3994/6/1/1. Acesso em: 24 out. 2026.

LIU, X.; YU, H.; LIU, H.; SUN, Z. Multi-Factor Carbon Emissions Prediction in Coal-Fired Power Plants: A Machine Learning Approach for Carbon Footprint Management. **Energies**, Basel, v. 18, n. 7, art. 1715, 2025. DOI: https://doi.org/10.3390/en18071715. Disponível em: https://www.mdpi.com/1996-1073/18/7/1715. Acesso em: 24 out. 2026.

NATIONAL INSTITUTE OF STANDARDS AND TECHNOLOGY; SEMATECH. **NIST/SEMATECH e-Handbook of Statistical Methods**. Gaithersburg: NIST, 2012. DOI: https://doi.org/10.18434/M32189. Seções Box Plot e Detection of Outliers. Disponível em: https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm e https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm. Acesso em: 24 out. 2026.

RUMELHART, D. E.; HINTON, G. E.; WILLIAMS, R. J. Learning representations by back-propagating errors. **Nature**, *[s. l.]*, v. 323, n. 6088, p. 533-536, 1986. DOI: https://doi.org/10.1038/323533a0. Disponível em: https://www.cs.toronto.edu/~hinton/absps/naturebp.pdf. Acesso em: 24 out. 2026.

SCIKIT-LEARN. **User Guide**. Version 1.8.0. *[S. l.]*: The scikit-learn developers, [2025]. Seções MinMaxScaler e Regression metrics. Disponível em: https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.MinMaxScaler.html e https://scikit-learn.org/1.8/modules/model_evaluation.html#regression-metrics. Acesso em: 24 out. 2026.

TU, K.; WANG, Y.; LI, X.; WANG, X.; HU, Z.; LUO, B.; SHI, L.; LI, M.; LUO, G.; YAO, H. CO2 Emission Prediction for Coal-Fired Power Plants by Random Forest-Recursive Feature Elimination-Deep Forest-Optuna Framework. **Energies**, Basel, v. 17, n. 24, art. 6449, 2024. DOI: https://doi.org/10.3390/en17246449. Disponível em: https://www.mdpi.com/1996-1073/17/24/6449. Acesso em: 24 out. 2026.

UNITED STATES. Environmental Protection Agency. Clean Air Markets Division. **CAMD’s Power Sector Emissions Data Guide**. *[S. l.]*: EPA, 18 jul. 2022. Disponível em: https://www.epa.gov/system/files/documents/2022-07/CAMD%27s%20Power%20Sector%20Emissions%20Data%20Guide%20-%2007182022.pdf. Acesso em: 24 out. 2026.

UNITED STATES. Environmental Protection Agency. Clean Air Markets Division. **ECMPS Reporting Instructions**: Monitoring Plan. *[S. l.]*: EPA, 20 dez. 2024. Disponível em: https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf. Acesso em: 24 out. 2026.

ZHOU, S.; HE, H.; ZHANG, L.; ZHAO, W.; WANG, F. A Data-Driven Method to Monitor Carbon Dioxide Emissions of Coal-Fired Power Plants. **Energies**, Basel, v. 16, n. 4, art. 1646, 2023. DOI: https://doi.org/10.3390/en16041646. Disponível em: https://www.mdpi.com/1996-1073/16/4/1646. Acesso em: 24 out. 2026.

UNITED STATES. Environmental Protection Agency. **Power Sector Data**. Washington, DC: Office of Atmospheric Protection, Clean Air and Power Division, 2026. Conjunto de dados horários disponibilizado pelo CAMPD. Recorte: Iatan Unit 2, Facility ID 6065, out. 2010 a dez. 2025. Disponível em: https://www.epa.gov/power-sector/power-sector-data. Acesso em: 24 out. 2026.
