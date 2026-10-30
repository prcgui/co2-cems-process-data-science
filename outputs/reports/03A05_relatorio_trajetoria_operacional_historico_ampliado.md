# Relatório do Notebook 03A.05

## Trajetória operacional com histórico ampliado

### 1. Objetivo

Este notebook investigou a seguinte pergunta:

**Com histórico ampliado, a inclusão de variáveis de trajetória operacional melhora a previsão de CO₂ em relação ao uso exclusivo da carga instantânea?**

O experimento foi construído como continuação direta das análises anteriores. Os resultados prévios indicaram que a família de modelos XGBoost apresentou desempenho substancialmente superior ao MLP para a previsão horária de emissões de CO₂ da Iatan Unit 2. Também foi observado que a inclusão de informações de trajetória apresentou ganhos pequenos ou inconsistentes quando analisada predominantemente com dados de 2025.

Posteriormente, o Notebook 03A.04 mostrou que a ampliação do histórico de treinamento com dados de 2011 a 2022 trouxe ganho preditivo incremental mesmo quando dados recentes de 2025 já estavam disponíveis.

Diante dessas evidências, o 03A.05 verificou se a maior disponibilidade de histórico permitiria ao XGBoost extrair valor adicional das variáveis que representam a trajetória operacional da unidade.

---

## 2. Unidade analisada e variável-alvo

A análise permaneceu restrita à Iatan Unit 2, Facility ID 6065.

A variável-alvo foi:

`CO2 Mass (short tons)`

correspondente à massa horária de CO₂ registrada no conjunto EPA CEMS/CAMPD.

Foram mantidas apenas observações em que a unidade estava em operação para a amostra final de modelagem.

---

## 3. Delimitação temporal da base

O histórico de referência foi definido como o período de **2011 a 2022**.

O ano de 2010 não foi utilizado como referência histórica devido à entrada inicial da unidade em operação.

Os anos de 2023 e 2024 permaneceram excluídos do treinamento principal. No Notebook 03A.04, esses dois anos apresentaram características operacionais fora do intervalo empírico observado entre 2011 e 2022 em múltiplos indicadores, incluindo utilização, frequência de carga zero durante horas classificadas como operacionais, carga média, percentil inferior da carga e número de startups.

Essa classificação foi utilizada como delimitação operacional da amostra e não deve ser interpretada como prova formal de mudança de regime ou como resultado de um método estatístico de detecção de change point.

A base utilizada neste notebook combinou:

- histórico de referência: 2011 a 2022;
- dados recentes: 2025;
- 2023 e 2024 excluídos do treinamento principal.

Antes da aplicação dos critérios específicos dos Cenários A e B, foram identificadas **90,082 horas operacionais**.

---

## 4. Cenários comparados

Foram comparados dois cenários.

### Cenário A: carga instantânea

O Cenário A utilizou somente:

`load_current_mw`

Em termos conceituais:

`CO₂(t) = f(P(t))`

Esse cenário representa a hipótese de que a carga instantânea contém informação suficiente para a previsão horária de CO₂.

### Cenário B: carga e trajetória operacional

O Cenário B utilizou sete features:

1. `load_current_mw`
2. `load_lag_1h`
3. `delta_load_1h`
4. `abs_delta_load_1h`
5. `load_mean_previous_3h`
6. `operating_time_lag_1h`
7. `hours_since_startup`

Esse cenário acrescenta informações sobre o estado recente e a trajetória operacional da unidade.

A comparação foi estruturada para que a única diferença entre os modelos fosse o vetor de features utilizado.

---

## 5. Reconstrução temporal e prevenção de leakage

As features temporais foram calculadas utilizando a série horária completa, incluindo horas OFF quando necessário para reconstrução das transições operacionais.

Dois blocos temporais independentes foram estabelecidos:

- 2011 a 2022;
- 2025.

Os cálculos de `shift`, diferenças horárias e médias móveis foram executados separadamente dentro desses blocos.

Essa decisão impediu que o último registro de 2022 fosse tratado como a observação imediatamente anterior ao primeiro registro de 2025.

Nenhuma feature derivada de CO₂ foi utilizada como preditor.

---

## 6. Tratamento da carga ausente de 2019

Foi identificado **1 registro de carga ausente durante operação** em 2019.

O registro ocorreu em uma sequência temporal contínua e operacionalmente estável.

Optou-se por **não imputar a carga ausente**.

A justificativa foi preservar a distinção entre valores observados e valores não observados. A imputação introduziria um valor artificial em uma série utilizada para construção de lags e diferenças.

Como consequência da propagação temporal dessa ausência, duas horas de 2019 não apresentaram vetor completo do Cenário B.

Para preservar o pareamento, essas observações também foram excluídas do Cenário A dentro do experimento 03A.05.

---

## 7. Tratamento do início do histórico

A primeira observação de 2011 já apresentava a unidade em operação.

Portanto, não era possível determinar quando havia ocorrido o startup do ciclo que estava em andamento antes do início da série disponível.

Foram identificadas **250 horas operacionais** com `hours_since_startup` semanticamente desconhecido antes que um startup completo pudesse ser observado.

O primeiro startup observado no histórico ocorreu em:

`2011-01-15 22:00:00`

Essas 250 horas foram excluídas da amostra comum A x B.

Essa exclusão foi aplicada aos dois cenários, embora o Cenário A não utilize `hours_since_startup`, porque a comparação precisava utilizar exatamente as mesmas observações.

A decisão não implica que essas horas fossem inválidas para o Notebook 03A.04. Elas eram válidas para um modelo baseado exclusivamente em carga instantânea. A necessidade de exclusão surgiu apenas na comparação pareada com um cenário que utiliza explicitamente a idade do ciclo operacional.

---

## 8. Amostra comum A x B

Após os critérios de elegibilidade, a amostra comum ficou composta por:

- horas operacionais originalmente disponíveis: **90,082**;
- horas elegíveis para os dois cenários: **89,830**;
- horas excluídas: **252**;
- percentual excluído: **0,2797%**.

O histórico comum de 2011 a 2022 ficou com:

**83,581 observações**

A perda amostral foi pequena em relação ao volume total disponível e permitiu assegurar uma comparação estritamente pareada.

---

## 9. Protocolo temporal do experimento

O experimento utilizou separação temporal explícita.

### Treinamento para seleção de complexidade

Foram utilizados:

- histórico comum de 2011 a 2022;
- janeiro a setembro de 2025.

Total:

**88,475 observações**

### Validação

Outubro de 2025 foi utilizado como período de validação para early stopping:

**211 observações**

### Treinamento final

Após a seleção do número de árvores, outubro foi reincorporado à base de treinamento.

O treinamento final utilizou:

- 2011 a 2022;
- janeiro a outubro de 2025.

Total:

**88,686 observações**

### Teste temporal

O teste utilizou novembro e dezembro de 2025:

**1,144 observações**

Esse período não participou do ajuste nem da seleção de complexidade dentro do Notebook 03A.05.

Entretanto, novembro e dezembro de 2025 já haviam sido analisados em notebooks anteriores do projeto. Portanto, este período deve ser tratado como teste temporal da comparação específica A x B realizada aqui, mas não como um holdout completamente cego em relação ao projeto como um todo.

---

## 10. Modelo e controle experimental

Os dois cenários utilizaram XGBoost com os mesmos hiperparâmetros estruturais.

A configuração de seleção utilizou:

- `objective = reg:squarederror`
- `learning_rate = 0.03`
- `max_depth = 4`
- `min_child_weight = 5`
- `subsample = 0.80`
- `colsample_bytree = 0.80`
- `reg_alpha = 0`
- `reg_lambda = 1`
- `eval_metric = rmse`
- máximo de 3000 árvores
- `early_stopping_rounds = 50`
- `random_state = 42`

A e B utilizaram as mesmas observações de treino, validação e teste.

Cada cenário pôde selecionar seu próprio número de árvores porque diferentes representações de entrada podem exigir diferentes níveis de complexidade.


### Fundamentação metodológica das técnicas empregadas

**Aprendizado supervisionado para regressão e XGBoost.** A emissão horária de CO₂ é a variável-alvo contínua e os preditores são variáveis operacionais. O `XGBRegressor` é um modelo de *gradient-boosted regression trees* (GBRT): um conjunto sequencial de árvores de regressão, e não uma árvore isolada. O objetivo `reg:squarederror` orienta o ajuste das árvores, enquanto `eval_metric=rmse` monitora o desempenho na validação.

**Engenharia de atributos temporais (*temporal feature engineering*).** Os preditores adicionais de B incluem *lagged features* (`shift(1)`), estatísticas em janelas móveis (*rolling-window features*) e informações de transição entre estados operacionais. `shift(1).rolling(window=3, min_periods=1).mean()` calcula uma média retrospectiva sem incluir a observação atual. O agrupamento por `temporal_block` evita conectar artificialmente o último registro de 2022 ao primeiro de 2025. As variáveis retrospectivas são construídas sem antecipar observações, mas a previsão da hora t ainda pressupõe disponibilidade de `load_current_mw(t)`.

**Desenho experimental pareado e amostra comum elegível.** A e B utilizam as mesmas horas com entradas válidas, a mesma emissão observada e as mesmas divisões temporais. Isso permite atribuir diferenças de desempenho principalmente à representação de atributos sob o protocolo aplicado. A restrição à amostra comum é necessária à comparabilidade, embora delimite a população sobre a qual se pode concluir. Não foi realizado teste formal de significância estatística das diferenças.

**Early stopping e seleção de complexidade.** Outubro de 2025 é usado para selecionar separadamente o número de árvores de A e de B, monitorando RMSE e interrompendo o ajuste após 50 rodadas sem melhora, até o limite de 3.000 árvores. Os demais hiperparâmetros estruturais são mantidos controlados entre os cenários. Este protocolo não corresponde a *Random Search* ou validação cruzada temporal *walk-forward*.

**Final refit e temporal holdout.** Após fixar as quantidades de árvores selecionadas, os dois modelos são reajustados com 2011–2022 e janeiro–outubro de 2025. O teste temporal de novembro–dezembro de 2025 não entra nesse reajuste. Como esse intervalo já havia sido estudado em notebooks anteriores, não deve ser tratado como teste completamente cego em relação à pesquisa como um todo.

**Análise estratificada de erros (*context-stratified error analysis*).** O comportamento de A e B é descrito separadamente em horas próximas de partidas, em rampas intensas e nas demais horas. O limiar de rampa intensa é o percentil 90 de `abs_delta_load_1h` calculado no conjunto de treinamento, sem utilizar o teste para defini-lo. A análise é exploratória, não causal, e não inclui um modelo híbrido ou mecanismo de seleção condicional de modelos.

---

## 11. Seleção de complexidade em outubro de 2025

O Cenário A selecionou:

**498 árvores**

Resultados de validação:

- MAE: **59,9124**
- RMSE: **75,4836**
- R²: **0,9007**
- NMAE: **10,8232%**
- Bias: **-52,3670**

O Cenário B selecionou:

**721 árvores**

Resultados de validação:

- MAE: **53,7186**
- RMSE: **67,6990**
- R²: **0,9201**
- NMAE: **9,7042%**
- Bias: **-47,0776**

Em outubro, B apresentou redução de:

- **10,3381% no MAE**;
- **10,3130% no RMSE**.

B apresentou menor erro absoluto em **55,45%** das horas de validação.

Esses resultados foram utilizados apenas para compreender o comportamento da seleção de complexidade. Outubro não foi utilizado para determinar a conclusão final sobre a superioridade dos cenários.

---

## 12. Refit final

Depois da seleção da complexidade:

- A foi fixado em **498 árvores**;
- B foi fixado em **721 árvores**.

O early stopping foi removido.

Os modelos foram então ajustados novamente sobre as mesmas **88,686 observações**, correspondentes ao histórico de 2011 a 2022 e aos meses de janeiro a outubro de 2025.

---

## 13. Resultado global no teste de novembro e dezembro de 2025

### Cenário A

- MAE: **20,1514 short tons de CO₂/h**
- MedianAE: **17,3853**
- RMSE: **25,0653**
- R²: **0,9847**
- NMAE: **3,4240%**
- Bias: **-10,3467 short tons de CO₂/h**

### Cenário B

- MAE: **21,1720 short tons de CO₂/h**
- MedianAE: **17,8556**
- RMSE: **26,5779**
- R²: **0,9828**
- NMAE: **3,5974%**
- Bias: **-2,5503 short tons de CO₂/h**

A inclusão das variáveis de trajetória produziu:

- ganho de MAE: **-5,0645%**;
- ganho de RMSE: **-6,0346%**;
- variação de R²: **-0,001897**.

Como os ganhos de MAE e RMSE foram negativos, B apresentou maior erro global que A.

O MAE passou de:

**20,1514 para 21,1720**

correspondendo a uma piora de aproximadamente:

**5,06%**

O RMSE passou de:

**25,0653 para 26,5779**

correspondendo a uma piora de aproximadamente:

**6,03%**

Portanto, o Cenário B não apresentou benefício global sobre o Cenário A no período de teste.

---

## 14. Comparação pareada hora a hora

Apesar do maior erro agregado, B apresentou menor erro absoluto em:

**50,96% das horas**

A redução média pareada do erro absoluto foi:

**-1,0206 short tons de CO₂/h**

enquanto a redução mediana foi:

**0,2814 short tons de CO₂/h**

A mediana ligeiramente positiva e a média negativa indicam que o comportamento de B não foi uniformemente pior.

B melhorou muitas observações de forma moderada, mas apresentou algumas deteriorações suficientemente grandes para aumentar o MAE e, principalmente, o RMSE.

---

## 15. Bias

O Bias foi definido como:

`observado - previsto`

Portanto:

- Bias positivo indica subestimação média;
- Bias negativo indica superestimação média.

No teste:

- A: **-10,3467**
- B: **-2,5503**

A magnitude do Bias foi reduzida em aproximadamente:

**75,35%**

pela inclusão das variáveis de trajetória.

Portanto, B reduziu substancialmente o deslocamento sistemático médio da previsão, mas essa melhora de calibração média não se converteu em menor erro global.

---

## 16. Diagnóstico por contexto operacional

Para investigar se o efeito da trajetória dependia do estado operacional, o teste foi analisado em contextos definidos previamente.

As rampas intensas foram identificadas utilizando:

`|delta P| >= P90 do conjunto de treinamento`

O limiar obtido foi:

**56,0000 MW/h**

### 16.1 Primeiras seis horas após startup

Número de observações:

**30 horas**

Isso corresponde a aproximadamente **2,62%** do teste.

Resultados:

- MAE A: **11,7288**
- MAE B: **10,4517**
- ganho de MAE de B: **10,8884%**
- RMSE A: **16,3533**
- RMSE B: **13,1659**
- ganho de RMSE de B: **19,4904%**
- B apresentou menor erro em **43,33%** das horas.

Embora as métricas agregadas tenham melhorado, B não apresentou menor erro na maioria das observações e a amostra possui apenas 30 horas.

Portanto, o resultado de startup deve ser interpretado como evidência localizada e não como demonstração de benefício consistente em todas as horas posteriores a partidas.

### 16.2 Rampas intensas

Número de observações:

**258 horas**

Isso corresponde a aproximadamente **22,55%** do teste.

Resultados:

- MAE A: **24,0577**
- MAE B: **18,5491**
- ganho de MAE de B: **22,8974%**
- RMSE A: **29,3609**
- RMSE B: **22,4809**
- ganho de RMSE de B: **23,4327%**
- B apresentou menor erro em **61,63%** das horas;
- redução média pareada do erro: **5,5086**;
- redução mediana pareada do erro: **3,8456**.

As diferentes métricas apontaram na mesma direção.

Nesse contexto, as variáveis de trajetória apresentaram benefício preditivo consistente.

### 16.3 Demais horas

Foram classificadas como demais horas as observações que não pertenciam às primeiras seis horas após startup nem às rampas intensas.

Número de observações:

**857 horas**

Isso corresponde a aproximadamente:

**74,91% do teste**

Resultados:

- MAE A: **19,2544**
- MAE B: **22,3416**
- ganho de MAE de B: **-16,0337%**
- RMSE A: **23,8711**
- RMSE B: **28,0262**
- ganho de RMSE de B: **-17,4062%**
- B apresentou menor erro em **47,96%** das horas.

Nesse grupo, a trajetória deteriorou claramente o desempenho.

Como essas observações representam aproximadamente 74,91% do conjunto de teste, a deterioração nesse regime predominante foi suficiente para superar os ganhos obtidos em condições mais dinâmicas.

---

## 17. Casos extremos

A análise das 20 maiores pioras de B mostrou:

- horas nas primeiras seis horas após startup: **0**;
- rampas intensas: **0**;
- redução média pareada do erro: **-45,1914**.

Portanto, nenhuma das 20 maiores deteriorações de B ocorreu em startup inicial ou em rampa intensa.

Por outro lado, entre as 20 maiores melhorias de B:

- horas nas primeiras seis horas após startup: **0**;
- rampas intensas: **13**;
- redução média pareada do erro: **43,2439**.

Das 20 maiores melhorias de B, **13** ocorreram em rampas intensas.

Esse resultado reforça a interpretação de que a informação de trajetória apresentou maior valor em períodos de mudança operacional acentuada.

---

## 18. Interpretação integrada

Os resultados permitem separar duas questões.

A primeira é se as variáveis de trajetória melhoram globalmente a previsão.

Para essa pergunta, a resposta observada foi negativa.

Mesmo com a ampliação substancial do histórico de treinamento, o Cenário B apresentou MAE e RMSE maiores que o Cenário A no teste temporal.

A segunda questão é se as informações de trajetória possuem algum conteúdo preditivo útil.

Para essa pergunta, a resposta é mais específica.

O benefício dependeu do contexto operacional.

Em rampas intensas, B apresentou redução expressiva e consistente dos erros. Em contrapartida, nas demais horas, que representam a maior parte do teste, a inclusão das variáveis adicionais deteriorou o desempenho.

Portanto, os resultados não sustentam a utilização indiscriminada das sete features de trajetória em todas as condições operacionais.

Ao mesmo tempo, também não sustentam a conclusão de que a trajetória seja irrelevante.

As evidências indicam valor preditivo localizado principalmente em regimes dinâmicos de carga.

---

## 19. Relação com os resultados anteriores

Nos experimentos anteriores, a trajetória já havia apresentado benefício global pequeno ou inconsistente quando comparada à utilização exclusiva da carga.

O 03A.04 mostrou posteriormente que o aumento do histórico de treinamento era útil para o próprio Cenário A.

O 03A.05 testou, então, uma explicação possível para o desempenho limitado das features de trajetória: a hipótese de que o modelo anteriormente não possuía quantidade ou diversidade histórica suficiente para aprender essas relações.

O resultado atual não sustentou essa explicação em nível global.

Mesmo com histórico ampliado, B permaneceu inferior a A na avaliação agregada.

Entretanto, o novo experimento revelou com maior clareza que a trajetória apresenta valor preditivo localizado em condições de variação intensa de carga.

---

## 20. Limitações

Os resultados devem ser interpretados dentro do escopo experimental utilizado.

### 20.1 Uma única unidade

O estudo foi realizado exclusivamente para a Iatan Unit 2.

Os resultados não devem ser generalizados automaticamente para outras unidades termelétricas.

### 20.2 Um único conjunto de features de trajetória

O Cenário B representa uma definição específica de memória operacional.

O resultado não demonstra que toda forma possível de representação temporal seja ineficaz.

### 20.3 Modelo específico

O experimento utilizou XGBoost com uma configuração estrutural controlada.

Outros algoritmos ou representações sequenciais podem responder de forma diferente às mesmas informações.

### 20.4 Período de teste

Novembro e dezembro de 2025 foram mantidos fora do treinamento e da seleção de complexidade do 03A.05.

Entretanto, esses meses já haviam sido analisados em notebooks anteriores do projeto.

Portanto, o resultado deve ser entendido como teste temporal controlado desta comparação, mas não como avaliação completamente cega de todo o processo de pesquisa.

### 20.5 Número de horas de startup

O diagnóstico de startup utilizou apenas **30 observações**.

A interpretação desse contexto deve ser mais cautelosa que a análise das rampas intensas ou do conjunto global.

### 20.6 Interpretação não causal

O modelo identifica relações preditivas.

Os resultados não demonstram que rampas, duração de operação ou qualquer outra feature sejam causas diretas das alterações observadas nas emissões.

---

## 21. Conclusão

O Notebook 03A.05 avaliou se a ampliação do histórico de treinamento permitiria que variáveis de trajetória operacional acrescentassem valor ao modelo baseado apenas na carga instantânea.

No teste temporal de novembro e dezembro de 2025, o Cenário A apresentou MAE de **20,1514 short tons de CO₂/h**, enquanto o Cenário B apresentou MAE de **21,1720 short tons de CO₂/h**.

Isso correspondeu a uma variação de **-5,0645%**, indicando piora global com a inclusão das variáveis de trajetória.

O RMSE também aumentou em **6,03%**.

Portanto, **a ampliação do histórico não tornou o Cenário B globalmente superior ao Cenário A**.

Entretanto, o efeito das variáveis de trajetória não foi uniforme.

Em rampas intensas, B reduziu o MAE em **22,90%** e o RMSE em **23,43%**, apresentando menor erro em **61,63%** das horas.

Nas demais condições operacionais, o MAE de B foi aproximadamente **16,03% maior** que o de A.

Assim, a evidência obtida neste notebook indica que **as variáveis de trajetória possuem valor preditivo localizado em regimes operacionais dinâmicos, especialmente durante rampas intensas, mas sua utilização indiscriminada em todas as condições operacionais deteriora o desempenho global**.

O Cenário A permanece, portanto, como a representação global mais parcimoniosa e mais precisa entre os dois cenários avaliados neste experimento.

O achado localizado nas rampas é exploratório e não justifica modificar retroativamente o resultado global ou selecionar um novo modelo com base no próprio conjunto de teste.

---

## 22. Síntese objetiva

| Questão | Evidência |
|---|---|
| Histórico ampliado tornou B globalmente superior? | Não |
| MAE A | 20,1514 |
| MAE B | 21,1720 |
| Ganho global de MAE de B | -5,0645% |
| RMSE A | 25,0653 |
| RMSE B | 26,5779 |
| Ganho global de RMSE de B | -6,0346% |
| B venceu na maioria das horas globais? | Sim, marginalmente: 50,96% |
| B reduziu a magnitude do bias? | Sim |
| Trajetória ajudou em startups? | Houve melhora agregada, mas não benefício consistente na maioria das horas |
| Trajetória ajudou em rampas intensas? | Sim, ganho de MAE de 22,90% |
| Trajetória ajudou nas demais horas? | Não, piora de MAE de 16,03% |
| Conclusão principal | Valor preditivo localizado em regimes dinâmicos, sem benefício global |