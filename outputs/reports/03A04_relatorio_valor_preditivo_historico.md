# Relatório do valor preditivo do histórico operacional

## Notebook 03A.04

### Cenário A

`CO2(t) = f(P(t))`

Este relatório consolida os resultados obtidos após a ampliação da
base histórica da Iatan Unit 2 e registra a conclusão metodológica
sobre a utilidade dos dados de 2011 a 2022 para a previsão de emissões
horárias de CO2 no Cenário A.

Nenhum novo experimento é realizado nesta etapa.

---

## 1. Objetivo

O objetivo desta sequência experimental foi determinar se a ampliação
do histórico disponível acrescenta informação útil ao modelo do
Cenário A.

A análise foi conduzida em três etapas sucessivas:

1. delimitação do período histórico de referência;
2. avaliação da capacidade de generalização do histórico para 2025;
3. avaliação do ganho incremental do histórico quando dados recentes
   de 2025 já estão disponíveis.

A pergunta central desta etapa é:

> O processamento do histórico de 2011 a 2022 acrescenta valor
> preditivo ao Cenário A?

---

## 2. Delimitação da amostra histórica

O período de 2011 a 2022 foi definido como histórico operacional de
referência.

O ano de 2010 foi retirado por representar um período parcial
associado ao commissioning e à entrada em operação comercial da
Iatan Unit 2.

Os anos de 2023 e 2024 foram classificados como período de regime
operacional distinto.

A delimitação de 2011 a 2022 foi exploratória e consolidada após os backtests, que incluíram avaliação em 2025. Sua justificativa operacional baseou-se em
indicadores operacionais da própria unidade, incluindo:

- proporção anual de horas em operação;
- ocorrência de carga zero durante horas operacionais;
- carga média;
- distribuição inferior de carga;
- frequência de startups.

Os anos de 2023 e 2024 permanecem preservados para análises
específicas sobre comportamento operacional e process drift, mas não
integram a amostra histórica principal desta etapa.

---

## 3. Generalização do histórico para 2025

O primeiro experimento avaliou se um modelo treinado exclusivamente no
período histórico de referência seria capaz de prever o comportamento
de 2025.

O desenho experimental foi:

**Treinamento: 2011 a 2022**

**Teste out-of-time: 2025**

O modelo final utilizou 83,832 observações históricas e
foi avaliado em 6,249 observações válidas de 2025.

Foram selecionadas 202 árvores.

Resultados:

- MAE = 50.2740 short tons de CO2;
- RMSE = 68.4650 short tons de CO2;
- R² = 0.8894;
- NMAE = 8.65%;
- Bias = -33.9686 short tons de CO2.

O resultado demonstra que a relação entre carga instantânea e emissão
de CO2 aprendida no período de 2011 a 2022 mantém capacidade relevante
de transferência temporal para 2025.

O R² de 0.8894 indica que o modelo histórico preservou
capacidade substancial de explicar a variabilidade das emissões de
2025.

Ao mesmo tempo, o NMAE de 8.65% e o bias de
-33.9686 mostram que a transferência não é perfeita e
que existe deslocamento da relação carga e emissão entre o histórico
e 2025.

---

## 4. Valor incremental do histórico

Demonstrar que o histórico consegue prever 2025 não é suficiente para
concluir que ele acrescenta informação quando dados recentes já estão
disponíveis.

Por isso, foi executado um segundo experimento, com comparação
pareada.

Os dois modelos utilizaram:

- a mesma variável preditora;
- o mesmo alvo;
- o mesmo algoritmo;
- os mesmos hiperparâmetros;
- o mesmo período de validação;
- exatamente as mesmas 1.144 observações de teste de novembro e
  dezembro de 2025.

A diferença experimental foi a disponibilidade do histórico de
2011 a 2022.

### Modelo 1

**2025 apenas**

Treinamento final:

`Jan-Out/2025`

Número de árvores selecionado:

119

### Modelo 2

**Histórico + 2025**

Treinamento final:

`2011-2022 + Jan-Out/2025`

Número de árvores selecionado:

524

---

## 5. Resultados consolidados

| experiment | training | test | MAE | RMSE | R2 | NMAE_pct | Bias |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Historical generalization | 2011-2022 | 2025 completo | 50.2740 | 68.4650 | 0.8894 | 8.6461 | -33.9686 |
| Paired baseline | Jan-Oct/2025 | Nov-Dec/2025 | 23.3470 | 28.5786 | 0.9802 | 3.9669 | 9.0645 |
| Paired historical model | 2011-2022 + Jan-Oct/2025 | Nov-Dec/2025 | 20.2454 | 25.1240 | 0.9847 | 3.4399 | -10.4354 |

---

## 6. Ganho incremental do histórico

| metric | 2025_only | history_plus_2025 | relative_improvement_pct |
| --- | --- | --- | --- |
| MAE | 23.3470 | 20.2454 | 13.2849 |
| RMSE | 28.5786 | 25.1240 | 12.0881 |
| NMAE | 3.9669 | 3.4399 | 13.2849 |

Ao acrescentar o histórico de 2011 a 2022, o MAE foi reduzido de
23.3470 para 20.2454 short tons de CO2.

Isso corresponde a uma redução relativa de:

**13.28%**

O RMSE foi reduzido de 28.5786 para
25.1240, correspondendo a uma melhoria de:

**12.09%**

O NMAE foi reduzido de 3.97% para
3.44%.

Além da melhoria nas métricas agregadas, o modelo com histórico
apresentou menor erro absoluto em:

**65.30% das horas do teste.**

A redução média pareada do erro absoluto foi de:

**3.1016 short tons de CO2 por hora.**

Portanto, a melhoria não decorre apenas de um conjunto pequeno de
observações com erros extremos.

O modelo enriquecido pelo histórico apresentou menor erro absoluto na
maioria das horas avaliadas.

---

## 7. Coeficiente de determinação

O R² aumentou de:

`0.9802`

para:

`0.9847`

correspondendo a uma variação absoluta de:

`+0.0045`

Ambos os modelos já apresentam coeficiente de determinação elevado.

Por isso, a variação absoluta de R² é menor do que as mudanças
observadas no MAE e no RMSE.

Neste experimento, a redução dos erros absolutos e quadráticos é mais
informativa para avaliar o ganho incremental produzido pela inclusão
do histórico.

---

## 8. Comportamento do bias

O modelo treinado apenas com dados recentes apresentou:

`Bias = 9.0645`

O modelo com histórico apresentou:

`Bias = -10.4354`

Como o bias foi definido por:

`observado - previsto`

o modelo treinado apenas com 2025 apresenta pequena tendência média de
subestimação.

O modelo enriquecido pelo histórico apresenta pequena tendência média
de superestimação.

Em magnitude absoluta, o bias passou de
9.0645 para 10.4354 short tons.

A redução de MAE e RMSE, portanto, não foi acompanhada por redução da
magnitude absoluta do bias.

Esse comportamento deve ser registrado como característica do modelo
com histórico, mas não invalida a melhoria observada nas métricas de
erro global.

---

## 9. Validação e complexidade dos modelos

Durante a etapa de seleção da complexidade, o modelo treinado apenas
com dados de 2025 apresentou RMSE de validação inferior ao modelo
contendo o histórico.

O período de validação correspondeu a outubro de 2025.

Essa validação foi utilizada para selecionar o número de árvores de
cada modelo antes do ajuste final.

O modelo treinado apenas com 2025 utilizou:

**119 árvores**

O modelo contendo histórico utilizou:

**524 árvores**

Após essa etapa, outubro foi reincorporado aos respectivos conjuntos
de treinamento.

A comparação final foi realizada sobre o mesmo conjunto futuro de
novembro e dezembro de 2025.

Nesse teste comum, o modelo contendo histórico apresentou menores MAE
e RMSE.

Portanto, a avaliação final do ganho do histórico é baseada no teste
pareado e não no desempenho observado durante a etapa de seleção da
complexidade.

---

## 10. Conclusão do Notebook 03A.04

Os resultados fornecem evidência consistente de que o histórico de 2011 a 2022 possui valor preditivo incremental para o Cenário A.

O principal resultado desta etapa foi a redução de:

**13.28% no MAE**

quando o histórico de 2011 a 2022 foi incorporado aos dados recentes
de 2025.

Esse ganho foi acompanhado por:

- redução de 12.09% no RMSE;
- aumento do R² de 0.9802 para 0.9847;
- redução do NMAE de 3.97% para 3.44%;
- menor erro absoluto em 65.30% das horas avaliadas.

Os resultados permitem concluir que o histórico de 2011 a 2022 não é
apenas capaz de produzir previsões transferíveis para 2025.

O histórico também acrescenta informação preditiva quando combinado
com dados recentes do próprio ano de 2025.

Assim, a pergunta central do Notebook 03A.04 pode ser respondida
positivamente:

> O processamento do histórico de 2011 a 2022 acrescenta valor
> preditivo ao Cenário A?

**Sim.**

Esse resultado encerra o objetivo experimental deste notebook.

---

## 11. Relação com os experimentos anteriores

Nos experimentos anteriores, conduzidos com uma base temporal mais
restrita, a inclusão de variáveis de trajetória operacional não
produziu ganho global robusto em relação ao uso exclusivo da carga
instantânea.

Naquele contexto, o Cenário A, baseado apenas na carga instantânea,
permaneceu competitivo ou superior ao Cenário B nas avaliações
globais.

O Notebook 03A.04 introduz uma mudança importante no problema.

A base disponível para treinamento foi ampliada de forma substancial,
incorporando o período histórico de 2011 a 2022.

Essa ampliação acrescenta dezenas de milhares de observações e
aumenta a diversidade de condições operacionais representadas no
treinamento.

Por isso, a conclusão obtida anteriormente sobre as variáveis de
trajetória precisa ser reavaliada sob essa nova disponibilidade de
dados.

O Notebook 03A.04 não responde essa questão.

---

## 12. Próxima etapa

A próxima etapa será conduzida em um novo notebook.

A pergunta central será:

> Com histórico ampliado, a inclusão de variáveis de trajetória
> operacional melhora a previsão de CO2 em relação ao uso exclusivo
> da carga instantânea?

A análise comparará duas formulações:

### Cenário A

`CO2(t) = f(P(t))`

O modelo utiliza apenas a carga instantânea.

### Cenário B

`CO2(t) = f(P(t), trajetória operacional)`

O modelo incorpora, além da carga instantânea, informações que
representam o comportamento operacional recente da unidade.

A comparação deverá utilizar o mesmo protocolo temporal e o mesmo
conjunto futuro de teste para os dois cenários.

O objetivo será determinar se a ampliação da base histórica modifica
a conclusão obtida anteriormente sobre a utilidade das variáveis de
trajetória operacional.

Essa é a única questão experimental aberta ao final do Notebook
03A.04.
## 13. Fundamentação metodológica da avaliação temporal

### 13.1. Modelo supervisionado de regressão

O Cenário A emprega **XGBoost** para regressão supervisionada com
apenas `Gross Load (MW)` como variável preditora e `CO2 Mass
(short tons)` como variável-alvo. O algoritmo pertence à família
de **gradient-boosted regression trees (GBRT)**: um conjunto de
árvores de regressão é ajustado sequencialmente, de modo que as
novas árvores contribuem para reduzir o erro da função objetivo.
Não se trata de uma única árvore de decisão.

### 13.2. Process drift e possível concept drift

**Process drift** é utilizado para descrever alterações observadas
no padrão de operação da Iatan Unit 2, tais como frequência de
partidas, horas de funcionamento e distribuição da carga.

Em problemas preditivos, **concept drift** corresponde à mudança
temporal da distribuição condicional `P(Y | X)`. Para este cenário,
considera-se `P(CO2 | Gross Load)`. Diferenças nas curvas empíricas
entre anos motivam o **diagnóstico de possível concept drift**, mas
não demonstram sua ocorrência: as comparações realizadas são
descritivas e não incluem teste formal de ponto de mudança ou de
detecção estatística de concept drift.

Uma mudança na distribuição da carga ou na intensidade de operação
não implica necessariamente mudança na relação condicional entre
carga e emissões.

### 13.3. Backtesting temporal com origem móvel

A comparação de volumes históricos utiliza **rolling-origin temporal
backtesting with multiple training-window lengths**. A origem de
teste avança pelos anos-alvo de 2021, 2022, 2023, 2024 e 2025.
Para cada ano, são avaliadas janelas históricas alternativas de
1, 2, 3, 5 e 10 anos, com teste no mesmo ano-alvo.

O trimestre final do ano anterior é reservado à validação para
**early stopping**. Trata-se de múltiplas extensões fixadas para
comparação; não de uma única janela de treino automaticamente
expansiva em todas as rodadas.

### 13.4. Generalização temporal fora da amostra

O experimento `2011-2022 -> 2025` constitui um **temporal
out-of-sample generalization test**, também denominado teste
**out-of-time**. O ajuste utiliza um período histórico anterior
ao período de avaliação. O ano de 2025 é posterior ao conjunto
de treinamento dessa etapa, mas já havia sido examinado em
experimentos anteriores; por isso, não é descrito como um teste
completamente cego em toda a pesquisa.

### 13.5. Early stopping e final refit

O **early stopping** identifica a complexidade de cada XGBoost,
expressa pelo número selecionado de árvores, a partir do erro
na validação temporal. Após essa escolha, a complexidade é fixada
e ocorre um **final refit**: treinamento de um novo modelo com as
observações que estavam disponíveis antes do teste, reincorporando
os dados de validação. O teste futuro permanece separado dessa
seleção de complexidade.

### 13.6. Comparação controlada e pareada do histórico

A comparação **2025 recente** versus **2011-2022 + 2025 recente**
constitui um **paired controlled experiment on training-history
availability**. Ambos os modelos utilizam a mesma variável de
entrada, o mesmo alvo, a mesma família de algoritmo, a mesma
regra de seleção de complexidade e as mesmas observações futuras
para avaliação. O número de árvores é escolhido separadamente
para cada modelo, como previsto no protocolo.

A comparação do erro absoluto **hora a hora**, além das métricas
agregadas, caracteriza a análise pareada do valor incremental
dos dados históricos. O efeito é observado nas condições e nos
períodos avaliados e não implica, isoladamente, garantia de
benefício em outras unidades ou em anos futuros.

---