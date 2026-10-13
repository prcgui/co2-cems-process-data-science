
# Diagnóstico do modelo: Notebook 3A

## 1. Resultado geral

A inclusão de informações sobre memória e trajetória operacional
melhorou o desempenho global da MLP em relação ao modelo baseado
somente na carga instantânea.

No conjunto de teste:

- MAE do Cenário A: **67.25 short tons**
- MAE do Cenário B: **61.61 short tons**
- redução de MAE: **8.39%**

- RMSE do Cenário A: **70.90 short tons**
- RMSE do Cenário B: **67.04 short tons**
- redução de RMSE: **5.45%**

- R² do Cenário A: **0.8779**
- R² do Cenário B: **0.8908**
- variação de R²: **+0.0129**

O Cenário B apresentou erro absoluto inferior ao Cenário A em
**794 das 1144 horas de teste**,
correspondendo a **69.4% das observações**.

Portanto, o resultado fornece evidência de que o estado
instantâneo da carga não contém sozinho toda a informação
relevante para estimar as emissões horárias de CO₂.


## 2. Resultado durante startups

Nas primeiras seis horas após um startup, a inclusão de
informações de trajetória reduziu o MAE em:

**26.15%**

Este foi o ganho relativo mais expressivo observado no
experimento.

O resultado é consistente com a hipótese de que, durante a
partida da unidade, duas horas com carga semelhante podem
representar condições operacionais diferentes dependendo da
posição da unidade dentro de sua trajetória.

Assim, a variável carga instantânea apresenta limitação
particularmente importante durante regimes transitórios de
startup.


## 3. Problema identificado nas rampas intensas

Nas rampas intensas, definidas por:

**|ΔP| ≥ 130.00 MW/h**

o resultado foi diferente.

A variação de MAE do Cenário A para o Cenário B foi:

**-14.09%**

Como o valor é negativo, o Cenário B apresentou desempenho
inferior ao Cenário A nesse regime.

Isso mostra que a informação de trajetória atualmente utilizada
não é suficiente para representar adequadamente as mudanças
mais rápidas de carga.

Uma possível explicação é que o conjunto atual de features
descreve apenas uma memória temporal relativamente curta.

Por exemplo, o modelo conhece P(t), P(t-1), ΔP(t) e uma média
das três horas anteriores, mas não representa explicitamente:

- múltiplos lags de carga;
- sequência recente das rampas;
- aceleração ou desaceleração da carga;
- variabilidade dentro de janelas temporais maiores;
- identificação explícita do regime operacional.

Este resultado será utilizado como uma das principais
justificativas para a próxima etapa de aprimoramento.


## 4. Viés de subestimação

A média das emissões observadas no conjunto de teste foi:

**588.54 short tons**

As médias previstas foram:

- Cenário A: **521.51 short tons**
- Cenário B: **527.66 short tons**

O resíduo médio, calculado como observado menos previsto, foi:

- Cenário A: **+67.04 short tons**
- Cenário B: **+60.89 short tons**

Os resíduos médios positivos indicam tendência de
**subestimação das emissões de CO₂**.

O Cenário B reduziu esse viés em relação ao Cenário A, mas não
o eliminou.

Esse comportamento deverá ser investigado antes de simplesmente
aumentar a complexidade da rede neural.


## 5. Limitações do modelo atual

O Notebook 3A deve ser interpretado como um modelo de referência
para as próximas etapas.

As principais limitações identificadas são:

1. **Representação temporal limitada**

   A trajetória é representada por poucas variáveis agregadas e
   apenas um lag explícito de carga.

2. **Desempenho não uniforme entre regimes**

   O ganho observado após startups não se repetiu durante
   rampas intensas.

3. **Viés sistemático de subestimação**

   Ambos os modelos apresentaram previsões médias inferiores às
   emissões efetivamente observadas no período de teste.

4. **Arquitetura ainda não otimizada**

   A estrutura Dense(64) → Dense(32) foi utilizada como
   arquitetura de referência. Não houve busca sistemática por
   número de camadas, neurônios, learning rate, batch size ou
   função de perda.

5. **Função de perda única**

   O treinamento utilizou MSE. Outras funções, como Huber Loss,
   ainda não foram avaliadas.

6. **Validação temporal restrita**

   Outubro foi utilizado como único período de validação.
   Estratégias de validação temporal progressiva podem produzir
   uma avaliação mais robusta da capacidade de generalização.


## 6. Conclusão do diagnóstico

O primeiro experimento confirmou que incorporar informações
sobre o processo operacional é útil para a estimação horária de
CO₂.

Entretanto, o ganho não foi uniforme.

O modelo enriquecido apresentou:

- melhora global de MAE, RMSE e R²;
- ganho expressivo após startups;
- pior desempenho durante rampas intensas;
- redução, mas não eliminação, do viés de subestimação.

Portanto, o próximo passo não deve ser simplesmente aumentar o
número de neurônios da MLP.

A prioridade será aprimorar a representação temporal do
processo e avaliar se uma descrição mais completa da trajetória
operacional permite reduzir os erros identificados neste
diagnóstico.


## 7. Direção para a próxima etapa

O próximo experimento deverá investigar principalmente:

- novos lags de carga;
- estatísticas móveis em diferentes janelas;
- comportamento recente das rampas;
- aceleração e desaceleração da carga;
- representação explícita de regimes operacionais;
- diagnóstico de diferenças entre treino, validação e teste.

Somente após avaliar o ganho dessas novas informações deverá ser
considerada a otimização da arquitetura ou a adoção de modelos
mais complexos.
