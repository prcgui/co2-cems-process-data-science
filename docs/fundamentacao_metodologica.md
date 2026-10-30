# Fundamentação metodológica e fontes dos procedimentos

Este guia relaciona os procedimentos utilizados no estudo da Iatan Unit 2 às publicações científicas, aos manuais e à documentação oficial que os fundamentam. A matriz permite localizar cada técnica nos oito notebooks e identificar quais decisões pertencem ao protocolo do projeto.

O problema consiste em estimar `CO2 Mass (short tons)` por registro horário a partir de entradas operacionais conhecidas, incluindo a carga da própria hora. A avaliação em períodos posteriores ao treinamento verifica o desempenho fora do período de ajuste; ela não transforma o problema em previsão antecipada com carga futura desconhecida. Os resultados e a implementação estão registrados neste repositório (Costa; Calmon; Menezes, 2026).

**Atualização documental de 24 de outubro de 2026.** As notas de fundamentação, os comentários de atribuição e as referências explicam procedimentos já existentes. Esta atualização não constitui nova execução, novo treinamento ou alteração dos resultados. A reprodução computacional anteriormente concluída abrange 03A.04 e 03A.05, com escopo e evidências na [documentação de reprodução](../reproducibility/README.md).

**Revisão bibliográfica de 29 de outubro de 2026.** Treze fontes originais fornecidas pelo autor foram deduplicadas e confrontadas com o texto integral; doze acrescentam referências novas e X. Liu et al. (2025) já fazia parte da fundamentação. O arquivo secundário de seleção bibliográfica não é citado como fonte científica. As novas referências foram incorporadas somente onde o conteúdo original sustenta a afirmação. A revisão bibliográfica preservou os cálculos existentes. Posteriormente, as execuções completas recebidas dos oito notebooks principais foram inspecionadas, incluindo os diagnósticos do 03A.05. Os complementos 03A.05A, 03A.05B e 03A.05C também foram executados no Colab e conferidos, conforme o relatório consolidado.

## Natureza das fontes

Os artigos fundamentam conceitos, algoritmos e cuidados de avaliação. Os manuais da EPA descrevem os dados e o monitoramento regulatório; o NIST/SEMATECH documenta procedimentos estatísticos; a documentação do scikit-learn esclarece transformações e funções implementadas. Essas fontes oficiais não são classificadas como artigos científicos. Os critérios de seleção, atributos, calendários, limiares e hiperparâmetros específicos são escolhas do estudo, explicitadas no código.

## Matriz de fundamentação

| Procedimento | Fonte e natureza | Local de uso | Alcance e decisões do estudo |
|---|---|---|---|
| Interpretação dos registros CAMPD/CEMS e do alvo `CO2 Mass (short tons)` | United States (2022), guia oficial da EPA | 01, 02 e 03A.04; leitura e caracterização dos dados | O guia orienta a leitura dos dados reportados. A massa é mantida por registro horário, inclusive nas horas parcialmente operadas, sem divisão por `Operating Time`. Não se presume que todo registro tenha sido inteiramente medido. |
| Elegibilidade pelo método CO₂/CEM e interpretação das vigências | United States (2024), instruções oficiais ECMPS | 01; [auditoria de monitoramento](../reproducibility/monitoring/README.md) | O manual sustenta a interpretação dos campos e das vigências. Limiares de completude, ranking e escolha retrospectiva de Iatan são próprios do estudo. O filtro original com `contains("measured")` inclui `Measured` e `Measured and Substitute`; a auditoria distingue as categorias. |
| Motivação para examinar carga e condições operacionais | Gu, Sward e Zhang (2023); Suri, de Chalendar e Azevedo (2025), artigos | 01, 02, 03A, 03A.01 e 03A.05 | Gu et al. incluem carga, tempo de operação, fator de capacidade e fator de rampa em modelos horários; Suri et al. discutem rampas, partidas e operação térmica subótima. As fontes motivam a representação, mas não prescrevem os sete ou 24 atributos nem seus limiares. |
| Sinalização de valores extremos por intervalo interquartil | Guthrie (2020), NIST/SEMATECH e-Handbook, manual oficial | 02, função `calculate_iqr_limits` | São utilizados os limites Q1 − 1,5 × IQR e Q3 + 1,5 × IQR. Os indicadores `load_outlier_iqr` e `co2_outlier_iqr` sinalizam registros; os pontos são mantidos. Um extremo estatístico não comprova erro de medição. |
| Análise de componentes principais | Jolliffe e Cadima (2016), artigo | 02, análise exploratória dos sete atributos | A PCA utiliza entradas padronizadas por escore z e examina variância e correlação. A decisão de manter os atributos originais nos modelos pertence ao estudo; as componentes não são entradas dos estimadores. |
| Representação explícita da memória operacional | Gu, Sward e Zhang (2023); Suri, de Chalendar e Azevedo (2025); construção própria | 02, 03A.01, 03A.02 e 03A.05; listas `FEATURES_B`, `FEATURES_C` e atributos derivados | Gu et al. fornecem referência direta para variáveis operacionais e rampa; Suri et al. sustentam a relevância dos transientes. Defasagens, janelas, contador de partida, comprimentos e limiares são definidos no projeto. |
| Separação cronológica e validação por períodos sucessivos | Cerqueira, Torgo e Mozetič (2020); Cawley e Talbot (2010); Gu, Sward e Zhang (2023) | 02, 03A, 03A.01 e etapas XGBoost; `FOLDS` em 03A.02 e 03A.03 | Cerqueira et al. fundamentam avaliação temporal; Gu et al. usam separações entre anos, horizontes crescentes e curvas de aprendizado em emissões de EGUs. O calendário específico é próprio do projeto e o teste reutilizado não é completamente cego. |
| Transformação MinMax | Scikit-learn (2025), documentação oficial versionada | 02, 03A e 03A.01; `MinMaxScaler` | Os extremos são ajustados no treinamento e reutilizados nos conjuntos reservados. Quando o alvo é normalizado, as estimativas retornam à unidade original antes da avaliação. A arquitetura temporal e o uso da transformação são decisões do protocolo. |
| Rede neural multicamadas e retropropagação | Rumelhart, Hinton e Williams (1986), artigo | 03A e 03A.01; `build_mlp`, com TensorFlow/Keras | A publicação fundamenta a aprendizagem por retropropagação. A rede de camadas densas 64/32 e a saída linear são configurações do projeto; a retropropagação é executada pela biblioteca, sem reimplementação manual. |
| Unidades retificadoras e otimização Adam | Glorot, Bordes e Bengio (2011); Kingma e Ba (2015), trabalhos de conferência | 03A e 03A.01; ativação ReLU e treinamento da MLP | As fontes fundamentam as técnicas. Taxa de aprendizagem, lotes, limite de épocas, paciência, restauração de pesos e semente são escolhas experimentais, sem alegação de que esses artigos recomendem os valores usados. |
| Gradient boosting e XGBoost | Friedman (2001); Chen e Guestrin (2016); aplicações de domínio em Gu, Sward e Zhang (2023), Potts, Hackney e Leontidis (2023) e Wang et al. (2025) | 03A.02 a 03A.05; `XGBRegressor` e funções de construção dos modelos | Friedman e Chen/Guestrin fundamentam o algoritmo. Os artigos de domínio confirmam seu uso em problemas de emissões tabulares, mas não prescrevem os hiperparâmetros deste projeto. |
| Busca aleatória de hiperparâmetros | Bergstra e Bengio (2012), artigo; Scikit-learn (2025), documentação | 03A.03; `ParameterSampler`, `N_CONFIGS` e `SEARCH_SPACE` | Foram definidos 30 sorteios, semente 42, dois cenários e cinco partições. A mesma lista gera 300 ajustes; `n_estimators` integra a busca, sem interrupção antecipada nessa etapa. Esses valores não são prescritos pela fonte. |
| MAE, mediana do erro absoluto e RMSE | Hyndman e Koehler (2006), artigo; Scikit-learn (2025), documentação das funções | 03A a 03A.05; funções `regression_metrics`, `metrics_03A04` e `calculate_metrics`, conforme a etapa | As medidas descrevem a magnitude do erro na unidade do alvo. Sua comparação exige o mesmo conjunto de observações ou a explicitação das diferenças de amostra e protocolo. |
| R², NMAE, viés e ganho pareado | Scikit-learn (2025), documentação para R²; convenções explícitas do estudo para NMAE, viés e ganhos | Etapas de avaliação, especialmente 03A.04 e 03A.05; `regression_metrics` e `summarize_context` | NMAE = 100 × MAE / média observada no conjunto avaliado. Resíduo e viés seguem observado menos previsto. Ganho de B = 100 × (MAE A − MAE B) / MAE A. Essas convenções não são atribuídas a uma definição universal. A análise pareada é descritiva, sem teste de significância. |
| Janelas históricas e diagnóstico de diferenças entre períodos | Cerqueira, Torgo e Mozetič (2020); Gama *et al.* (2014); Cawley e Talbot (2010); Gu, Sward e Zhang (2023) | 03A.04 e diagnósticos de 03A.01 | Gu et al. variam quantidade de treinamento e horizonte de predição; 03A.04 adapta a pergunta a janelas históricas cronológicas da Iatan. As janelas de 1, 2, 3, 5 e 10 anos permanecem escolhas próprias. |
| Comparação final em amostra comum e análise por contexto | Cawley e Talbot (2010); Gu, Sward e Zhang (2023); Suri, de Chalendar e Azevedo (2025); desenho específico do projeto | 03A.05; elegibilidade comum A/B e `summarize_context` | Gu et al. usam fator de rampa e excluem partidas; Suri et al. sustentam relevância de rampas e partidas. O projeto preserva esses transientes e define P90 e primeiras seis horas como recortes próprios. |
| Diagnóstico de cobertura operacional do teste | Potts *et al.* (2026), preprint | 03A.05; célula `DIAGNÓSTICO ADICIONAL: COBERTURA OPERACIONAL DO TESTE` | Adota somente o sinal simples de atributos fora dos mínimos e máximos observados no treinamento. Não reproduz Mahalanobis, incerteza de ensemble, predição auxiliar ou *trust score*. A célula foi adicionada na revisão de 29/10/2026 e não integra os resultados numéricos do artigo até reexecução. |
| Integridade, rastreabilidade e reprodução | Implementação e evidências do projeto, Costa, Calmon e Menezes (2026) | `load_verified_annual_frame` em 03A.04; validações em 03A.05; `scripts/reproduce_history.py`; `outputs/reproducibility/` | Identificação da unidade, calendário, duplicatas, hashes e comparação das saídas são controles implementados no projeto. A revisão documental não equivale a nova execução. Os registros preservados delimitam quais etapas foram efetivamente reproduzidas. |

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

Gu, Sward e Zhang (2023) é a referência temática mais próxima do presente estudo: utiliza CEMS e outras bases públicas, modela emissões de unidades geradoras com XGBoost e redes neurais, inclui fator horário de rampa e examina horizontes de predição e curvas de aprendizado. O protocolo, contudo, remove horas parcialmente operadas para excluir partidas e desligamentos, enquanto o projeto Iatan preserva esses registros e avalia transientes separadamente.

Suri, de Chalendar e Azevedo (2025) fornecem evidência empírica com dados horários de que rampas, partidas e operação térmica em regimes subótimos podem alterar a eficiência e as emissões. Essa evidência fundamenta a análise por contexto, sem determinar os limiares do projeto. Fayaz *et al.* (2026), em preprint multiplanta na indústria de cimento, encontram forte dependência de histórico para NOx, mas não a mesma dependência temporal para CO e CO₂; a comparação é usada apenas para reforçar que memória de processo precisa ser testada por poluente e processo.

Wang *et al.* (2025), X. Liu *et al.* (2025) e Gu, Sward e Zhang (2023) contextualizam diferentes estratégias de predição de emissões em unidades geradoras. Kaya, Tüfekci e Uzun (2019), Potts, Hackney e Leontidis (2023) e Zuo *et al.* (2024) ampliam o contexto de PEMS e aprendizado de máquina em plantas fósseis. Guevara *et al.* (2024) sustenta a importância de explicitar a resolução temporal em inventários de emissões.

A transferência para ativos não observados não foi testada. Couture *et al.* (2024) estrutura validação para plantas não vistas, Ashraf, Dua e Debnath (2026) enfatiza consistência de domínio em aplicações de aprendizado de máquina a plantas a carvão e Potts *et al.* (2026), em preprint, relaciona condições fora da distribuição de treinamento a menor confiança. Do trabalho de Potts *et al.* foi incorporado ao 03A.05 apenas um diagnóstico simples de atributos fora da faixa observada no treinamento, sem reproduzir seu framework completo e sem alterar os resultados já publicados.

Saito e Fujiwara (2023) são usados para distinguir predição de identificação causal: os autores aplicam LiNGAM a dados de uma planta a carvão e restringem a análise a condições consideradas estáveis. O projeto Iatan não emprega descoberta causal e inclui regimes transitórios; portanto, seus ganhos são tratados como preditivos e descritivos.

## Referências

As entradas usam o sistema autor-data e a apresentação bibliográfica adotados no artigo. Os links identificam a publicação, a documentação oficial ou o repositório correspondente. As publicações científicas fundamentam as técnicas; documentos de software, guias e registros do projeto preservam sua natureza específica.

ASHRAF, W. M.; DUA, V.; DEBNATH, R. Domain consistent industrial decarbonisation of global coal power plants. Communications Sustainability, [s. l.], v. 1, art. 10, 2026. DOI: https://doi.org/10.1038/s44458-025-00010-w. Disponível em: https://www.nature.com/articles/s44458-025-00010-w. Acesso em: 29 out. 2026.

BERGSTRA, J.; BENGIO, Y. Random Search for Hyper-Parameter Optimization. Journal of Machine Learning Research, [s. l.], v. 13, n. 10, p. 281-305, 2012. Disponível em: https://jmlr.org/papers/v13/bergstra12a.html. Acesso em: 24 out. 2026.

CAWLEY, G. C.; TALBOT, N. L. C. On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation. Journal of Machine Learning Research, [s. l.], v. 11, n. 70, p. 2079-2107, 2010. Disponível em: https://jmlr.org/papers/v11/cawley10a.html. Acesso em: 24 out. 2026.

CERQUEIRA, V.; TORGO, L.; MOZETIČ, I. Evaluating time series forecasting models: an empirical study on performance estimation methods. Machine Learning, [s. l.], v. 109, n. 11, p. 1997-2028, 2020. DOI: https://doi.org/10.1007/s10994-020-05910-7. Disponível em: https://link.springer.com/article/10.1007/s10994-020-05910-7. Acesso em: 24 out. 2026.

CHEN, T.; GUESTRIN, C. XGBoost: A Scalable Tree Boosting System. In: ACM SIGKDD INTERNATIONAL CONFERENCE ON KNOWLEDGE DISCOVERY AND DATA MINING, 22., 2016, San Francisco. Proceedings [...]. New York: ACM, 2016. p. 785-794. DOI: https://doi.org/10.1145/2939672.2939785. Disponível em: https://www.kdd.org/kdd2016/papers/files/rfp0697-chenAemb.pdf. Acesso em: 24 out. 2026.

COSTA, G. P. R.; CALMON, F.; MENEZES, T. co2-cems-thermal-modeling. [S. l.]: GitHub, 2026. Repositório de código, relatórios e resultados. Versão consultada em 24 out. 2026, com links específicos no Apêndice B. Disponível em: https://github.com/prcgui/co2-cems-thermal-modeling. Acesso em: 24 out. 2026.

COUTURE, H. D. et al. Estimating Carbon Dioxide Emissions from Power Plant Water Vapor Plumes Using Satellite Imagery and Machine Learning. Remote Sensing, Basel, v. 16, n. 7, art. 1290, 2024. DOI: https://doi.org/10.3390/rs16071290. Disponível em: https://www.mdpi.com/2072-4292/16/7/1290. Acesso em: 29 out. 2026.

FAYAZ, S. J. et al. A Multi-Plant Machine Learning Framework for Emission Prediction, Forecasting, and Control in Cement Manufacturing. arXiv, 2026. Preprint arXiv:2604.19903. Disponível em: https://arxiv.org/abs/2604.19903. Acesso em: 29 out. 2026.

FRIEDMAN, J. H. Greedy function approximation: A gradient boosting machine. The Annals of Statistics, [s. l.], v. 29, n. 5, p. 1189-1232, 2001. DOI: https://doi.org/10.1214/aos/1013203451. Disponível em: https://projecteuclid.org/journals/annals-of-statistics/volume-29/issue-5/Greedy-function-approximation-A-gradient-boosting-machine/10.1214/aos/1013203451.full. Acesso em: 24 out. 2026.

GAMA, J.; ŽLIOBAITĖ, I.; BIFET, A.; PECHENIZKIY, M.; BOUCHACHIA, A. A survey on concept drift adaptation. ACM Computing Surveys, [s. l.], v. 46, n. 4, art. 44, p. 1-37, 2014. DOI: https://doi.org/10.1145/2523813. Disponível em: https://dl.acm.org/doi/10.1145/2523813. Acesso em: 24 out. 2026.

GLOROT, X.; BORDES, A.; BENGIO, Y. Deep Sparse Rectifier Neural Networks. In: INTERNATIONAL CONFERENCE ON ARTIFICIAL INTELLIGENCE AND STATISTICS, 14., 2011, Fort Lauderdale. Proceedings [...]. [S. l.]: PMLR, 2011. v. 15, p. 315-323. Disponível em: https://proceedings.mlr.press/v15/glorot11a.html. Acesso em: 24 out. 2026.

GU, J.; SWARD, J. A.; ZHANG, K. M. Predicting power plant emissions using public data and machine learning. Environmental Science: Advances, [s. l.], v. 2, n. 12, p. 1696-1707, 2023. DOI: https://doi.org/10.1039/D3VA00191A. Disponível em: https://pubs.rsc.org/en/content/articlelanding/2023/va/d3va00191a. Acesso em: 29 out. 2026.

GUEVARA, M.; ENCISO, S.; TENA, C.; JORBA, O.; DELLAERT, S.; DENIER VAN DER GON, H.; PÉREZ GARCÍA-PANDO, C. A global catalogue of CO₂ emissions and co-emitted species from power plants, including high-resolution vertical and temporal profiles. Earth System Science Data, [s. l.], v. 16, p. 337-373, 2024. DOI: https://doi.org/10.5194/essd-16-337-2024. Disponível em: https://essd.copernicus.org/articles/16/337/2024/. Acesso em: 29 out. 2026.

HYNDMAN, R. J.; KOEHLER, A. B. Another look at measures of forecast accuracy. International Journal of Forecasting, [s. l.], v. 22, n. 4, p. 679-688, 2006. DOI: https://doi.org/10.1016/j.ijforecast.2006.03.001. Disponível em: https://robjhyndman.com/publications/another-look-at-measures-of-forecast-accuracy/. Acesso em: 24 out. 2026.

JOLLIFFE, I. T.; CADIMA, J. Principal component analysis: a review and recent developments. Philosophical Transactions of the Royal Society A: Mathematical, Physical and Engineering Sciences, [s. l.], v. 374, n. 2065, art. 20150202, 2016. DOI: https://doi.org/10.1098/rsta.2015.0202. Disponível em: https://pmc.ncbi.nlm.nih.gov/articles/PMC4792409/. Acesso em: 24 out. 2026.

KAYA, H.; TÜFEKCI, P.; UZUN, E. Predicting CO and NOx emissions from gas turbines: novel data and a benchmark PEMS. Turkish Journal of Electrical Engineering and Computer Sciences, [s. l.], v. 27, n. 6, p. 4783-4796, 2019. DOI: https://doi.org/10.3906/elk-1807-87. Disponível em: https://journals.tubitak.gov.tr/elektrik/vol27/iss6/53/. Acesso em: 29 out. 2026.

KINGMA, D. P.; BA, J. Adam: A Method for Stochastic Optimization. [S. l.: s. n.], 2015. Trabalho apresentado na 3rd International Conference on Learning Representations, San Diego, 2015. Disponível em: https://arxiv.org/abs/1412.6980. Acesso em: 24 out. 2026.

LIU, X.; YU, H.; LIU, H.; SUN, Z. Multi-Factor Carbon Emissions Prediction in Coal-Fired Power Plants: A Machine Learning Approach for Carbon Footprint Management. Energies, Basel, v. 18, n. 7, art. 1715, 2025. DOI: https://doi.org/10.3390/en18071715. Disponível em: https://www.mdpi.com/1996-1073/18/7/1715. Acesso em: 24 out. 2026.

NATIONAL INSTITUTE OF STANDARDS AND TECHNOLOGY; SEMATECH. NIST/SEMATECH e-Handbook of Statistical Methods. Gaithersburg: NIST, 2012. Seções 1.3.3.7, Box Plot, e 1.3.5.17, Detection of Outliers. DOI: https://doi.org/10.18434/M32189. Disponível em: https://www.itl.nist.gov/div898/handbook/eda/section3/boxplot.htm e https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h.htm. Acesso em: 24 out. 2026.

POTTS, R.; DURRANT, A.; HACKNEY, R.; LEONTIDIS, G. Trust-Aware Predictive Emissions Monitoring for Gas Turbine Fleets with Limited Labelled Data. arXiv, 2026. Preprint arXiv:2606.06156. Disponível em: https://arxiv.org/abs/2606.06156. Acesso em: 29 out. 2026.

POTTS, R.; HACKNEY, R.; LEONTIDIS, G. Tabular Machine Learning Methods for Predicting Gas Turbine Emissions. Machine Learning and Knowledge Extraction, Basel, v. 5, n. 3, p. 1055-1075, 2023. DOI: https://doi.org/10.3390/make5030055. Disponível em: https://www.mdpi.com/2504-4990/5/3/55. Acesso em: 29 out. 2026.

RUMELHART, D. E.; HINTON, G. E.; WILLIAMS, R. J. Learning representations by back-propagating errors. Nature, [s. l.], v. 323, n. 6088, p. 533-536, 1986. DOI: https://doi.org/10.1038/323533a0. Disponível em: https://www.cs.toronto.edu/~hinton/absps/naturebp.pdf. Acesso em: 24 out. 2026.

SAITO, T.; FUJIWARA, K. Causal analysis of nitrogen oxides emissions process in coal-fired power plant with LiNGAM. Frontiers in Analytical Science, [s. l.], v. 3, art. 1045324, 2023. DOI: https://doi.org/10.3389/frans.2023.1045324. Disponível em: https://www.frontiersin.org/journals/analytical-science/articles/10.3389/frans.2023.1045324/full. Acesso em: 29 out. 2026.

SCIKIT-LEARN. User Guide. Version 1.8.0. [S. l.]: The scikit-learn developers, [2025]. Seções MinMaxScaler e Regression metrics. Disponível em: https://scikit-learn.org/1.8/modules/generated/sklearn.preprocessing.MinMaxScaler.html e https://scikit-learn.org/1.8/modules/model_evaluation.html#regression-metrics. Acesso em: 24 out. 2026.

SHMUELI, G. To Explain or to Predict? Statistical Science, [s. l.], v. 25, n. 3, p. 289-310, 2010. DOI: https://doi.org/10.1214/10-STS330. Disponível em: https://www.stat.berkeley.edu/~aldous/157/Papers/shmueli.pdf. Acesso em: 24 out. 2026.

SURI, D.; DE CHALENDAR, J.; AZEVEDO, I. M. L. Assessing the real implications for CO₂ as generation from renewables increases. Nature Communications, [s. l.], v. 16, art. 7124, 2025. DOI: https://doi.org/10.1038/s41467-025-59800-4. Disponível em: https://www.nature.com/articles/s41467-025-59800-4. Acesso em: 29 out. 2026.

UNITED STATES. Environmental Protection Agency. Clean Air Markets Division. CAMD’s Power Sector Emissions Data Guide. [S. l.]: EPA, 18 jul. 2022. Disponível em: https://www.epa.gov/system/files/documents/2022-07/CAMD%27s%20Power%20Sector%20Emissions%20Data%20Guide%20-%2007182022.pdf. Acesso em: 24 out. 2026.

UNITED STATES. Environmental Protection Agency. Clean Air Markets Division. ECMPS Reporting Instructions: Monitoring Plan. [S. l.]: EPA, 20 dez. 2024. Disponível em: https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf. Acesso em: 24 out. 2026.

UNITED STATES. Environmental Protection Agency. Power Sector Data. Washington, DC: Office of Atmospheric Protection, Clean Air and Power Division, 2026. Conjunto de dados horários disponibilizado pelo CAMPD. Recorte: Iatan Unit 2, Facility ID 6065, out. 2010 a dez. 2025. Disponível em: https://www.epa.gov/power-sector/power-sector-data. Acesso em: 24 out. 2026.

WANG, S.; FANG, B.; ZHANG, J.; XING, S.; WU, J.; XIAO, H. Comparative study of machine learning methods for carbon metering in power generation enterprises. Scientific Reports, [s. l.], v. 15, art. 41333, 2025. DOI: https://doi.org/10.1038/s41598-025-25227-6. Disponível em: https://www.nature.com/articles/s41598-025-25227-6. Acesso em: 29 out. 2026.

ZUO, Z.; NIU, Y.; LI, J.; FU, H.; ZHOU, M. Machine Learning for Advanced Emission Monitoring and Reduction Strategies in Fossil Fuel Power Plants. Applied Sciences, Basel, v. 14, n. 18, art. 8442, 2024. DOI: https://doi.org/10.3390/app14188442. Disponível em: https://www.mdpi.com/2076-3417/14/18/8442. Acesso em: 29 out. 2026.

## Complementos executados e alcance da auditoria

- **03A.05A:** ablação de representação motivada pela auditoria de redundâncias, com amostras, semente e hiperparâmetros fixados; baseline B reproduzido antes da comparação.
- **03A.05B:** diferenças pareadas de perda absoluta (Diebold e Mariano, 1994) e sensibilidade a blocos de calendário (princípio de Künsch, 1989). A adaptação não executa teste DM/HAC nem demonstra cobertura nominal dos percentis.
- **03A.05C:** comparação de MLP e XGBoost com cinco sementes e uma configuração por família/cenário, documentando orçamento e representação (Grinsztajn et al., 2022). São 20 ajustes e mesmas amostras, sem reajuste com outubro. Tempos e capacidade não são igualados. Si et al. (2019) fornece contexto de redes/Keras em PEMS, sem adoção de seu particionamento aleatório.

A conferência final aprovou 376 verificações dos três complementos. O [relatório de auditoria](../outputs/auditoria_consolidada_2026-10-29/Relatorio_final_auditoria.txt) distingue resultados já existentes, novos experimentos e alterações bibliográficas.
