# Análise e Modelagem de Emissões de CO₂ em Termelétrica a Carvão

## Uma abordagem orientada a processos

[![Open Notebook 1 in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_selecao_unidade_estudo.ipynb)
[![Open Notebook 2 in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/02_tratamento_dados.ipynb)
[![Open Notebook 3A in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/03A_modelagem_preditiva_co2.ipynb)

Projeto desenvolvido para a disciplina **IND2622 — Ciência de Dados e Modelos de Processos de Negócio**, com foco na integração entre **dados horários de operação e emissões**, **representação do processo operacional**, **Process Mining** e **modelagem preditiva de CO₂**.

O estudo utiliza dados públicos da **U.S. Environmental Protection Agency (EPA)**, provenientes do ecossistema **CEMS/CAMPD**, para analisar uma unidade termelétrica a carvão ao longo de 2025.

A proposta parte da ideia de que uma termelétrica não deve ser observada apenas como uma coleção de registros horários independentes. Ao longo do tempo, a unidade percorre estados, transições e trajetórias operacionais que podem ser reconstruídos a partir dos dados e utilizados tanto para **caracterizar o processo** quanto para **avaliar sua contribuição à estimação das emissões horárias de CO₂**.

## Pergunta de pesquisa

> **Como o contexto e as trajetórias operacionais podem contribuir para caracterizar e estimar as emissões horárias de CO₂ de uma termelétrica a carvão?**

## Objetivo geral

> **Investigar se o conhecimento do processo operacional de uma termelétrica contribui para a caracterização das emissões horárias de CO₂ e para a precisão de sua estimação.**

## Estratégia analítica

O trabalho articula quatro níveis de análise:

1. **Série horária:** registros de timestamp, Operating Time, carga e CO₂.
2. **Ciclo operacional:** segmentação entre startup e shutdown, com identificação por cycle_id.
3. **Caracterização do processo:** duração, carga média, número de transições e CO₂ acumulado por ciclo.
4. **Análise e modelagem:** descoberta de trajetórias e variantes, comparação entre ciclos e estimação horária de CO₂.

## Escopo atual

Até o momento, o projeto contempla:

- seleção reprodutível da unidade de estudo;
- avaliação da qualidade e completude dos dados;
- tratamento de valores ausentes associados ao estado OFF;
- análise exploratória de outliers;
- engenharia de atributos orientada ao processo;
- identificação de startups e shutdowns;
- representação da direção e intensidade das mudanças de carga;
- construção de variáveis de memória e trajetória;
- análise exploratória por PCA;
- preparação da base para **segmentação em ciclos, Process Mining e modelagem preditiva**;
- **Notebook 3A implementado**, comparando carga instantânea versus carga + contexto e trajetória operacional.

A próxima frente específica da disciplina será a **análise de processos operacionais no Notebook 3B**, com segmentação em ciclos, Event Log, trajetórias e variantes.

## Fonte dos dados

Os dados são provenientes da **U.S. EPA**, com resolução horária para o ano de **2025**.

A seleção considera, entre outros critérios:

- unidades termelétricas a carvão;
- disponibilidade de dados horários;
- monitoramento de CO₂ por CEMS;
- cobertura de carga e emissões;
- operação distribuída ao longo do ano;
- presença de startups, shutdowns e rampas;
- amplitude e variabilidade de carga.

Os arquivos brutos e intermediários de grande volume não são versionados neste repositório.

## Unidade selecionada

A unidade selecionada foi:

- **Facility:** Iatan
- **Facility ID:** 6065
- **Unit:** 2
- **Estado:** Missouri (MO)
- **Ano:** 2025
- **Registros horários:** 8.760
- **Horas operacionais:** 6.249
- **Horas OFF:** 2.511
- **Startups:** 38
- **Shutdowns:** 37

A escolha resulta do equilíbrio entre qualidade dos dados, amplitude de carga e riqueza operacional.

O processo completo está documentado em:

- [Notebook 1 — seleção da unidade](notebooks/01_selecao_unidade_estudo.ipynb)
- [Relatório de seleção](outputs/reports/relatorio_selecao_unidade.md)

## Tratamento e preparação dos dados

O segundo notebook recebe automaticamente a unidade selecionada e executa:

1. auditoria estrutural e temporal;
2. análise de valores ausentes;
3. representação básica dos estados OFF, PARTIAL_OPERATION e FULL_OPERATION;
4. detecção exploratória de outliers por IQR;
5. feature engineering orientada ao processo;
6. PCA exploratória;
7. preparação da base para análises posteriores.

O processo completo está documentado em:

- [Notebook 2 — tratamento dos dados](notebooks/02_tratamento_dados.ipynb)
- [Relatório de tratamento](outputs/reports/relatorio_tratamento_dados.md)

## Engenharia de atributos orientada ao processo

A série foi enriquecida com variáveis que representam não apenas a condição instantânea, mas também o histórico recente da operação:

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

Essa estrutura permite representar estado, memória, direção e trajetória operacional, preparando os dados tanto para a análise de processos quanto para a modelagem preditiva.

## Qualidade dos dados

A série selecionada contém as **8.760 horas de 2025**, sem duplicidades ou lacunas temporais.

Foram observadas:

- 6.249 horas operacionais;
- 2.511 horas desligadas;
- 77 horas de operação parcial;
- ausência de dados faltantes de carga ou CO₂ durante operação.

Os valores ausentes nas horas OFF foram tratados como **ausências estruturais**, sem aplicação indevida de interpolação.

## Outliers

A análise por intervalo interquartil (IQR), aplicada somente às horas operacionais, identificou:

- **0 outliers de carga**;
- **3 outliers de CO₂**.

Os registros extremos foram preservados. Em processos industriais, um ponto estatisticamente extremo pode representar uma condição operacional real e não necessariamente um erro.

## PCA exploratória

A PCA foi aplicada a sete variáveis operacionais para investigar redundância e estrutura dos dados.

| Componente | Variância explicada | Variância acumulada |
|---|---:|---:|
| PC1 | 44,07% | 44,07% |
| PC2 | 16,51% | 60,57% |
| PC3 | 14,15% | 74,72% |
| PC4 | 13,27% | 87,99% |
| PC5 | 11,66% | 99,65% |

Foram necessárias cinco componentes para superar 90% da variância. Como a redução de 7 para 5 dimensões é pequena frente à perda de interpretabilidade física, as variáveis originais foram preservadas.

Os loadings indicam uma leitura coerente:

- **PC1:** nível de carga;
- **PC2:** dinâmica e rampas.

## Leitura do processo operacional

A base já permite identificar elementos típicos do processo:

- **estado OFF**;
- **startup**;
- **aumento de carga**;
- **operação em diferentes níveis**;
- **redução de carga**;
- **shutdown**.

A etapa de processos deverá reorganizar essa informação em um **Event Log**, no qual:

- **case_id** representa uma execução do processo;
- **timestamp** preserva a ordem temporal;
- **activity** representa o estado ou a transição operacional.

Essa estrutura permitirá reconstruir o **processo AS-IS**, identificar trajetórias e variantes observadas, medir seu desempenho e comparar diferentes ciclos operacionais.

## Process Mining

Após a construção do Event Log, o Process Mining será utilizado para identificar quais trajetórias efetivamente ocorreram nos dados.

A análise deverá considerar:

- variantes de ciclo;
- frequência das trajetórias;
- duração dos ciclos;
- comportamento de carga;
- transições operacionais;
- emissões associadas;
- comparação entre diferentes execuções.

A informação extraída do processo será relacionada ao problema preditivo central:

> **A informação do processo melhora a estimação do CO₂?**

## Modelagem preditiva

A etapa preditiva deverá comparar modelos construídos com diferentes níveis de informação operacional.

A lógica experimental prevê:

- um cenário de referência baseado na carga instantânea;
- um cenário enriquecido com informações de contexto e trajetória operacional;
- comparação por métricas de regressão;
- análise do ganho obtido com a inclusão da informação de processo.

A modelagem deverá ser mantida comparável entre os cenários para que a diferença de desempenho possa ser associada ao conjunto de informações fornecido ao modelo.

## Estrutura atual do repositório

```text
co2-cems-process-data-science/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   ├── 01_selecao_unidade_estudo.ipynb
│   ├── 02_tratamento_dados.ipynb
│   └── 03A_modelagem_preditiva_co2.ipynb
├── data/
│   ├── raw/
│   ├── interim/
│   └── processed/
├── pipeline/
│   └── selected_unit.json
└── outputs/
    ├── reports/
    │   ├── relatorio_selecao_unidade.md
    │   └── relatorio_tratamento_dados.md
    ├── figures/
    ├── tables/
    └── presentations/
        └── README.md
```

## Executar os notebooks

Os notebooks atualmente disponíveis devem ser executados na ordem:

1. **Notebook 1 — seleção da unidade de estudo**
2. **Notebook 2 — tratamento e preparação dos dados**
3. **Notebook 3A — modelagem preditiva de CO₂**

O Notebook 1 utiliza uma chave da API da EPA armazenada como segredo do Google Colab com o nome `EPA_API_KEY`. A chave não é armazenada no repositório.

No Notebook 2, a pasta persistente do projeto no Google Drive é:

```text
/content/drive/MyDrive/co2-cems-process-data-science
```

Para execução local:

```bash
pip install -r requirements.txt
```

## Próxima etapa

O **Notebook 3A — modelagem preditiva de CO₂** já foi incorporado ao repositório. Ele compara carga instantânea versus carga + contexto operacional com a mesma arquitetura de MLP, split temporal e métricas MAE, RMSE e R².

A próxima etapa específica de Ciência de Dados e Processos é:

### Notebook 3B — análise de processos operacionais

- identificar ciclos completos entre startup e shutdown;
- atribuir cycle_id / case_id;
- construir o Event Log;
- definir atividades operacionais;
- aplicar Process Mining;
- identificar trajetórias e variantes;
- calcular indicadores por ciclo;
- comparar comportamento de carga e emissões entre execuções.

A integração entre o Notebook 3A e o futuro Notebook 3B permitirá avaliar o processo operacional tanto como **objeto de caracterização** quanto como **fonte de informação para a modelagem preditiva**.

## Autores

- Guilherme Pereira Rodrigues da Costa
- Felipe Calmon
- Thiago Menezes

## Disciplina

**IND2622 — Ciência de Dados e Modelos de Processos de Negócio**  
Professora: **Fernanda A. B. Amorim**  
PUC-Rio
