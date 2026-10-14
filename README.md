# Análise e Modelagem de Emissões de CO₂ em Termelétrica a Carvão

## Uma abordagem orientada a processos

Projeto desenvolvido para a disciplina **IND2622: Ciência de Dados e Modelos de Processos de Negócio**, utilizando dados horários públicos da **U.S. Environmental Protection Agency (EPA)**, provenientes do ecossistema **CEMS/CAMPD**.

A unidade piloto é a **Iatan Unit 2**, Facility ID 6065, Missouri, com série horária inicial de 2025.

## Pergunta de pesquisa

> **Como o contexto e as trajetórias operacionais podem contribuir para caracterizar e estimar as emissões horárias de CO₂ de uma termelétrica a carvão?**

## Objetivo geral

> **Investigar se o conhecimento do processo operacional de uma termelétrica contribui para a caracterização das emissões horárias de CO₂ e para a precisão de sua estimação.**

## Notebooks e Google Colab

| Etapa | Notebook | Objetivo | Google Colab |
|---|---|---|---|
| 01 | [01_selecao_unidade_estudo.ipynb](notebooks/01_selecao_unidade_estudo.ipynb) | Seleção da unidade de estudo | [Abrir no Colab](https://colab.research.google.com/drive/11KpbBLZD8xo9CS2H6HKUW2Bd32spE-_S) |
| 02 | [02_tratamento_dados.ipynb](notebooks/02_tratamento_dados.ipynb) | Auditoria, tratamento e preparação da base | [Abrir no Colab](https://colab.research.google.com/drive/1PtW8T_oWDK9-e9OHMkgngsNpGTJ87PyN) |
| 03A | [03A_modelagem_preditiva_co2.ipynb](notebooks/03A_modelagem_preditiva_co2.ipynb) | Modelagem preditiva inicial | [Abrir no Colab](https://colab.research.google.com/drive/18alc2xYDM511l5pSXpIXXxkDFrSWAC8M) |
| 03A.01 | [03A.01_modelagem_preditiva_co2.ipynb](notebooks/03A.01_modelagem_preditiva_co2.ipynb) | Enriquecimento da representação temporal | [Abrir no Colab](https://colab.research.google.com/drive/1DVjl1v-wgQgWWtIyfE_bkCAdiVVjqJuW) |
| 03A.02 | [03A.02_comparacao_modelos_gradient_boosting.ipynb](notebooks/03A.02_comparacao_modelos_gradient_boosting.ipynb) | Comparação MLP x XGBoost e validação temporal | [Abrir no Colab](https://colab.research.google.com/drive/1BRbZkilK4omkxV7QjMbx3uPYkI7acsNY) |
| 03A.03 | [03A.03_otimizacao_pareada_xgboost.ipynb](notebooks/03A.03_otimizacao_pareada_xgboost.ipynb) | Busca pareada A x B e efeito da trajetória | [Abrir no Colab](https://colab.research.google.com/drive/1wbDqQxBoOi4qURULPh9EFTnNXpFUhgYj) |
| 03A.04 | [03A.04_volume_dados_generalizacao_temporal_iatan.ipynb](notebooks/03A.04_volume_dados_generalizacao_temporal_iatan.ipynb) | Histórico ampliado e generalização temporal do Cenário A | [Abrir no Colab](https://colab.research.google.com/drive/1AvnuJ-wPYravlkuZ1C0_-TWD80VWrz4m) |

## Estratégia analítica

O trabalho articula quatro níveis de análise:

1. **Série horária:** registros de timestamp, Operating Time, carga e CO₂;
2. **Ciclo operacional:** segmentação entre startup e shutdown, com identificação por `cycle_id`;
3. **Caracterização do processo:** duração, carga média, transições e CO₂ acumulado por ciclo;
4. **Análise e modelagem:** descoberta de trajetórias e variantes, comparação entre ciclos e estimação horária de CO₂.

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

O Cenário C ampliou o conjunto de variáveis de trajetória.

Resultados principais:

- MAE B: **61,61**;
- MAE C: **62,65**;
- melhora de C em startups: **22,67%** em relação a B;
- melhora de C em rampas intensas: **1,33%**.

O enriquecimento temporal não produziu melhora global consistente.

## Notebook 03A.02: MLP x XGBoost

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

O Notebook 03A.04 ampliou a série temporal da Iatan Unit 2 e avaliou o valor preditivo do histórico para o **Cenário A**, baseado exclusivamente na carga instantânea:

`CO₂(t) = f(P(t))`

A delimitação temporal adotada foi:

- **2010:** período parcial de commissioning, excluído da amostra principal;
- **2011–2022:** histórico operacional de referência;
- **2023–2024:** regime operacional distinto, preservado para análises específicas, mas excluído da amostra principal;
- **2025:** período futuro de avaliação.

A decisão sobre 2023 e 2024 foi baseada em indicadores operacionais antes da comparação preditiva. O detalhamento está em [03A04_delimitacao_amostra_historica.md](outputs/reports/03A04_delimitacao_amostra_historica.md).

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

## Próxima etapa da linha preditiva

Nos experimentos anteriores, conduzidos com uma base temporal mais restrita, as variáveis de trajetória operacional não apresentaram ganho global robusto em relação ao uso exclusivo da carga instantânea.

Como o histórico ampliado aumenta a quantidade e a diversidade das condições operacionais disponíveis para treinamento, a próxima pergunta é:

> **Com histórico ampliado, a inclusão de variáveis de trajetória operacional melhora a previsão de CO₂ em relação ao uso exclusivo da carga instantânea?**

A próxima etapa comparará Cenário A e Cenário B sob o mesmo protocolo temporal.

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
│   └── 03A.04_volume_dados_generalizacao_temporal_iatan.ipynb
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

A pasta persistente no Google Drive é:

```text
/content/drive/MyDrive/co2-cems-process-data-science
```

Para execução local:

```bash
pip install -r requirements.txt
```


## Autores

- Guilherme Pereira Rodrigues da Costa
- Felipe Calmon
- Thiago Menezes

## Disciplina

**IND2622: Ciência de Dados e Modelos de Processos de Negócio**  
Professora: **Fernanda A. B. Amorim**  
PUC-Rio
