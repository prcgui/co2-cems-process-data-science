# CO₂ CEMS Process Data Science

Projeto desenvolvido na disciplina **IND2622: Ciência de Dados e Modelos de Processos de Negócio**, utilizando dados horários U.S. EPA CEMS/CAMPD de uma unidade termelétrica a carvão.

A unidade piloto é a **Iatan Unit 2**, Facility ID 6065, Missouri, com série horária de 2025.

## Objetivo do projeto

O projeto combina análise de dados operacionais, engenharia de atributos, modelagem preditiva e análise de processos para compreender como o comportamento operacional de uma termelétrica se relaciona com suas emissões horárias de CO₂.

As duas frentes principais são:

1. **linha preditiva**, que avalia carga, trajetória operacional, famílias de modelos e robustez temporal;
2. **linha de processos**, que organiza ciclos operacionais, eventos, variantes e indicadores para futura aplicação de Process Mining.

## Notebooks

| Etapa | Notebook | Objetivo | Google Colab |
|---|---|---|---|
| 01 | [01_selecao_unidade_estudo.ipynb](notebooks/01_selecao_unidade_estudo.ipynb) | Seleção da unidade de estudo | [Abrir no Colab](https://colab.research.google.com/drive/11KpbBLZD8xo9CS2H6HKUW2Bd32spE-_S) |
| 02 | [02_tratamento_dados.ipynb](notebooks/02_tratamento_dados.ipynb) | Auditoria, tratamento e engenharia de atributos | [Abrir no Colab](https://colab.research.google.com/drive/1PtW8T_oWDK9-e9OHMkgngsNpGTJ87PyN) |
| 03A | [03A_modelagem_preditiva_co2.ipynb](notebooks/03A_modelagem_preditiva_co2.ipynb) | Modelagem preditiva inicial | [Abrir no Colab](https://colab.research.google.com/drive/18alc2xYDM511l5pSXpIXXxkDFrSWAC8M) |
| 03A.01 | [03A.01_modelagem_preditiva_co2.ipynb](notebooks/03A.01_modelagem_preditiva_co2.ipynb) | Enriquecimento da representação temporal | [Abrir no Colab](https://colab.research.google.com/drive/1DVjl1v-wgQgWWtIyfE_bkCAdiVVjqJuW) |
| 03A.02 | [03A.02_comparacao_modelos_gradient_boosting.ipynb](notebooks/03A.02_comparacao_modelos_gradient_boosting.ipynb) | Comparação MLP x XGBoost e validação temporal | [Abrir no Colab](https://colab.research.google.com/drive/1BRbZkilK4omkxV7QjMbx3uPYkI7acsNY) |
| 03A.03 | [03A.03_otimizacao_pareada_xgboost.ipynb](notebooks/03A.03_otimizacao_pareada_xgboost.ipynb) | Busca pareada A x B e efeito da trajetória | [Abrir no Colab](https://colab.research.google.com/drive/1wbDqQxBoOi4qURULPh9EFTnNXpFUhgYj) |

## Seleção e preparação dos dados

A seleção partiu de unidades termelétricas a carvão com dados públicos da EPA.

A Iatan Unit 2 foi escolhida por combinar:

- cobertura horária completa;
- qualidade de dados;
- amplitude relevante de carga;
- número suficiente de startups e shutdowns;
- variabilidade operacional adequada para análise de trajetórias.

A série de 2025 contém:

- 8.760 registros horários;
- 6.249 horas operacionais;
- 2.511 horas OFF;
- 38 startups;
- 37 shutdowns.

Foram criadas variáveis de carga, memória, variação, rampas, startups, shutdowns, tempo desde startup e contexto temporal.

## PCA exploratória

A PCA foi utilizada para avaliar redundância entre sete variáveis operacionais.

Foram necessárias cinco componentes para superar 90% da variância explicada. Como a redução dimensional foi pequena frente à perda de interpretabilidade, as features originais foram preservadas.

A estrutura dos loadings indicou:

- PC1 associada principalmente ao nível de carga;
- PC2 associada à dinâmica e às rampas.

## Linha preditiva

### Notebook 03A.01

O enriquecimento temporal da MLP não produziu melhora global consistente.

Principais resultados:

- MAE B: **61,61**;
- MAE C: **62,65**;
- melhora de C em startups: **22,67%**;
- melhora de C em rampas intensas: **1,33%**.

### Notebook 03A.02

A comparação com XGBoost mostrou que a família de modelo teve efeito muito maior sobre o erro do que a simples inclusão de mais variáveis de trajetória.

Validação temporal progressiva:

| Cenário | Features | MAE médio |
|---|---:|---:|
| A | 1 | 56,61 |
| B | 7 | 56,23 |
| C | 24 | 55,69 |

Holdout histórico de novembro e dezembro:

| Cenário | MAE | RMSE | R² |
|---|---:|---:|---:|
| A-XGBoost | 22,96 | 28,06 | 0,9809 |
| B-XGBoost | 23,27 | 28,81 | 0,9798 |
| C-XGBoost | 25,02 | 30,63 | 0,9772 |

Os controles metodológicos não identificaram target leakage, vazamento temporal ou desalinhamento das bases.

### Notebook 03A.03

Foi executada uma busca pareada com 30 configurações de hiperparâmetros para os Cenários A e B nos mesmos cinco folds temporais.

Resultados:

- B venceu **4 de 5 folds**;
- ganho médio de B na validação temporal: **+0,89%**;
- ganho de B no holdout histórico: **-1,18%**;
- ganho de B após startup: **-4,34%**;
- ganho de B em rampas intensas: **+4,88%**.

Interpretação:

> Para a Iatan Unit 2, com os dados de 2025 e as variáveis avaliadas, a trajetória operacional não apresentou ganho preditivo global consistente além do uso da carga instantânea. O comportamento em rampas intensas permanece como hipótese relevante para investigação posterior.

O holdout de novembro e dezembro é tratado como **referência histórica de comparação**, pois já foi observado durante o desenvolvimento dos experimentos.

## Continuidade da linha preditiva

A etapa seguinte deverá ampliar o histórico da Iatan antes de qualquer conclusão definitiva sobre o melhor modelo.

Questões a investigar:

- efeito do aumento do volume de dados;
- estabilidade do erro entre anos;
- previsão de períodos futuros completamente fora da amostra;
- drift da relação carga x CO₂;
- modelo estático versus atualização periódica;
- reavaliação de startups e rampas com maior histórico;
- métricas relativas e normalizadas de erro.

Notebook planejado:

**03A.04_volume_dados_generalizacao_temporal_iatan.ipynb**

## Linha de processos

A análise de processos utilizará a série tratada para organizar a operação como Event Log.

Elementos previstos:

- definição de `case_id` ou `cycle_id`;
- identificação de ciclos entre startup e shutdown;
- definição de atividades operacionais;
- reconstrução do processo AS-IS;
- identificação de variantes;
- frequência e duração dos ciclos;
- indicadores de carga e emissões por ciclo;
- comparação entre trajetórias;
- análise de regimes e transições;
- aplicação de Process Mining.

Essa frente deverá permitir avaliar a operação não apenas como série temporal, mas como sequência estruturada de eventos e execuções de processo.

## Artefatos

Os novos artefatos da linha preditiva estão versionados em:

- [outputs/reports](outputs/reports);
- [outputs/tables](outputs/tables);
- [outputs/figures](outputs/figures).

Foram incluídos relatórios dos Notebooks 03A, 03A.01, 03A.02 e 03A.03, tabelas de métricas, previsões, validação temporal, sanity checks, busca pareada e figuras de diagnóstico.

Arquivos brutos e intermediários volumosos e credenciais não são versionados.

## Estrutura

```text
co2-cems-process-data-science/
├── README.md
├── requirements.txt
├── notebooks/
│   ├── 01_selecao_unidade_estudo.ipynb
│   ├── 02_tratamento_dados.ipynb
│   ├── 03A_modelagem_preditiva_co2.ipynb
│   ├── 03A.01_modelagem_preditiva_co2.ipynb
│   ├── 03A.02_comparacao_modelos_gradient_boosting.ipynb
│   └── 03A.03_otimizacao_pareada_xgboost.ipynb
├── data/
├── pipeline/
└── outputs/
    ├── reports/
    ├── tables/
    ├── figures/
    └── presentations/
```

## Apresentação

Vídeo do trabalho: https://youtu.be/EUEqmm9nRHQ

## Autores

- Guilherme Pereira Rodrigues da Costa
- Felipe Calmon
- Thiago Menezes

## Disciplina

**IND2622: Ciência de Dados e Modelos de Processos de Negócio**  
Professora: **Fernanda A. B. Amorim**  
PUC-Rio
