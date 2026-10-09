# CO₂ CEMS Process Data Science

[![Open Notebook 1 in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/01_selecao_unidade_estudo.ipynb)
[![Open Notebook 2 in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/prcgui/co2-cems-process-data-science/blob/main/notebooks/02_tratamento_dados.ipynb)

Análise de dados operacionais e de emissões de uma unidade termelétrica a carvão, com ênfase na **representação do processo operacional a partir de dados horários**.

O projeto utiliza dados públicos da **U.S. Environmental Protection Agency (EPA)**, provenientes do ecossistema **CEMS/CAMPD**, para selecionar uma unidade de estudo, auditar e tratar a série temporal, construir atributos operacionais e organizar informações capazes de representar estados, transições e trajetória do processo.

## Questão orientadora

> **Como dados horários de operação e emissões podem ser estruturados para descrever estados, transições e ciclos operacionais de uma unidade termelétrica a carvão?**

A proposta parte da ideia de que uma termelétrica não deve ser observada apenas como uma coleção de registros independentes. Ao longo do tempo, a unidade liga, desliga, altera carga e percorre diferentes condições operacionais. Por isso, a série horária pode ser interpretada também como registro de um processo.

## Escopo atual

Até o momento, o projeto contempla:

- seleção reprodutível da unidade de estudo;
- avaliação da qualidade e completude dos dados;
- tratamento de valores ausentes associado ao estado OFF;
- análise exploratória de outliers;
- engenharia de atributos orientada ao processo;
- identificação de startups e shutdowns;
- representação da direção e intensidade das mudanças de carga;
- análise exploratória por PCA;
- preparação da base para análises posteriores.

A próxima extensão específica para a abordagem de processos será deliberadamente enxuta: **segmentar a operação em ciclos startup → shutdown e calcular indicadores por ciclo**, como duração, carga média, número de transições e emissão total de CO₂.

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

Essa estrutura permite descrever a dinâmica da unidade e constitui a base para a identificação de ciclos operacionais.

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

A base já permite identificar elementos típicos de um processo:

- **estado OFF**;
- **startup**;
- **aumento de carga**;
- **operação em diferentes níveis**;
- **redução de carga**;
- **shutdown**.

A etapa específica de processo deverá associar cada sequência completa entre uma partida e uma parada a um identificador de ciclo, permitindo calcular indicadores e comparar o comportamento entre ciclos sem exigir a criação de uma segunda infraestrutura de dados.

## Estrutura do repositório

```text
co2-cems-process-data-science/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   ├── 01_selecao_unidade_estudo.ipynb
│   └── 02_tratamento_dados.ipynb
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

Os notebooks devem ser executados na ordem:

1. **Notebook 1 — seleção da unidade de estudo**
2. **Notebook 2 — tratamento e preparação dos dados**

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

A continuação planejada é pequena e orientada ao processo:

1. utilizar os startups e shutdowns já detectados;
2. atribuir um `cycle_id` a cada ciclo operacional completo;
3. calcular poucos indicadores por ciclo;
4. comparar os ciclos sob a ótica de duração, carga, transições e emissões.

Essa extensão aproveita diretamente toda a preparação já realizada e muda a unidade de leitura da **hora isolada** para o **ciclo operacional**.

## Autores

- Guilherme Pereira Rodrigues da Costa
- Felipe Calmon
- Thiago Menezes

## Disciplina

**IND2622 — Ciência de Dados e Modelos de Processos de Negócio**  
Professora: **Fernanda A. B. Amorim**  
PUC-Rio
