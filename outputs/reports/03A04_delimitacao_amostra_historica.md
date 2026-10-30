# Delimitação da amostra histórica do Notebook 03A.04

## Objetivo

Esta etapa formaliza a composição da amostra principal utilizada
para avaliar a generalização temporal do Cenário A da Iatan Unit 2.

O Cenário A permanece definido por:

`CO2(t) = f(P(t))`

utilizando apenas a carga instantânea como variável preditora.

## Período histórico de referência

O período de 2011 a 2022 foi definido como histórico principal da
unidade.

O ano de 2010 não foi incluído porque representa apenas parte do ano
civil e coincide com o período de commissioning e entrada em operação
comercial da Iatan Unit 2.

## Identificação de regime operacional distinto em 2023 e 2024

A caracterização operacional multianual mostrou que 2023 e 2024
apresentam comportamento diferente da faixa observada entre 2011 e
2022.

No período histórico de referência:

- a menor proporção anual de operação foi
  60.354%;
- o maior percentual de horas operacionais com carga zero foi
  3.193%;
- a menor carga média anual foi
  706.682 MW;
- o menor percentil 5 da distribuição anual de carga foi
  425.600 MW;
- o maior número anual de startups foi
  25.

Os anos de 2023 e 2024 apresentaram:

| year | operating_pct | zero_load_pct | load_mean | load_p05 | n_startups | n_indicators_outside_reference | classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2023 | 49.269 | 4.008 | 691.338 | 136.750 | 20.000 | 4 | distinct_operational_regime |
| 2024 | 50.102 | 5.249 | 626.548 | 0.000 | 30.000 | 5 | distinct_operational_regime |

Esses resultados indicam que 2023 e 2024 não representam apenas
variação quantitativa normal dentro da faixa histórica anteriormente
observada. Os dois anos apresentam múltiplos indicadores operacionais
fora da faixa observada entre 2011 e 2022.

## Decisão metodológica

Os anos de 2023 e 2024 serão retirados da amostra principal utilizada
no experimento de generalização histórica.

Essa decisão NÃO implica considerar esses anos inválidos, incorretos
ou estatisticamente descartáveis.

Eles são classificados como período de regime operacional distinto e
permanecem preservados para análises posteriores de:

- process drift;
- Process Mining;
- sensibilidade;
- comparação entre regimes operacionais;
- investigação de mudanças na utilização e no despacho da unidade.

A decisão de exclusão foi baseada exclusivamente na caracterização
operacional e não utiliza MAE, RMSE, R² ou qualquer resultado de
desempenho preditivo como critério.

Isso reduz o risco de selecionar a amostra em função dos resultados do
modelo.

## Fundamentação da delimitação temporal

A caracterização inicial dos anos utiliza indicadores operacionais para
identificar **process drift**, isto é, diferenças na utilização da
unidade, incluindo frequência de operação, partidas e distribuição de
carga. Essas diferenças não comprovam, por si sós, alteração na
relação estatística entre potência e emissão.

Em previsão supervisionada, **concept drift** corresponde a uma
mudança ao longo do tempo na relação condicional entre a variável-alvo
e suas variáveis preditoras, representada aqui por
`P(CO2 | Gross Load)`. As diferenças observadas entre anos podem ser
compatíveis com essa hipótese, mas a etapa atual apresenta um
**diagnóstico descritivo**, não um teste formal de detecção de mudança.

A exclusão de 2023 e 2024 é específica da **amostra histórica de
referência para a generalização 2011-2022 -> 2025**. Esses anos
continuam disponíveis para comparações de regimes e outros testes
temporais; não são classificados como dados inválidos.

## Experimento subsequente

A amostra principal fica definida como:

**Treinamento histórico: 2011 a 2022**

Os anos de 2023 e 2024 permanecem fora do treinamento principal.

O ano de 2025 será utilizado como período futuro de teste.

Assim, o próximo experimento avaliará diretamente:

**2011–2022 → 2025**

A pergunta passa a ser:

> O conhecimento acumulado no período histórico de referência da
> Iatan Unit 2 é suficiente para generalizar a relação entre carga
> instantânea e emissão de CO2 para o ano de 2025?

## Contexto externo

A possível alteração do regime de utilização observada nos anos
recentes foi discutida separadamente no relatório técnico de
caracterização da Iatan Unit 2.

Esse contexto inclui mudanças no despacho regional, participação de
outras fontes de geração, condições econômicas do mercado elétrico e
estratégias de transição energética.

Esses elementos são utilizados apenas como contexto interpretativo.

A delimitação da amostra realizada nesta etapa é sustentada pelos
dados operacionais observados da própria Iatan Unit 2.