
# Relatório de tratamento e preparação dos dados

## 1. Unidade analisada

A unidade utilizada nesta fase foi carregada automaticamente a
partir do resultado do processo de seleção realizado no Notebook 1.

**Unidade:** Iatan — Unit 2  
**Facility ID:** 6065  
**Estado:** MO  
**Ano:** 2025

O notebook de tratamento não possui dependência explícita da
identidade da usina. Caso outra unidade seja selecionada no
Notebook 1, esta etapa poderá ser executada novamente utilizando
os novos dados.


## 2. Auditoria inicial

A base recebida continha:

- **8,760 registros horários**;
- período completo de 01/01/2025 a 31/12/2025;
- ausência de registros duplicados;
- ausência de timestamps duplicados;
- ausência de timestamps inválidos;
- nenhuma lacuna na sequência horária.

A série apresentou, portanto, integridade estrutural adequada
para o pré-processamento.


## 3. Dados faltantes

Foram identificados valores ausentes em carga e emissão de CO₂.

A investigação mostrou que esses valores ocorriam exclusivamente
nas horas em que a unidade estava desligada.

Foram observadas:

- **6,249 horas operacionais**;
- **2,511 horas desligadas**;
- **77 horas de operação parcial**;
- **6,172 horas de operação completa**.

Não foram encontrados valores ausentes de carga ou CO₂ durante
as horas operacionais.

Dessa forma, não houve justificativa para utilização de
interpolação ou imputação estatística.

Os valores ausentes associados ao estado OFF foram representados
como zero apenas em novas variáveis tratadas, preservando-se as
variáveis originais para rastreabilidade.


## 4. Análise de outliers

A detecção exploratória de valores extremos foi realizada por
meio do método do intervalo interquartil (IQR).

Foram identificados:

- **0 outliers de carga**;
- **3 outliers de CO₂**.

Nenhuma observação foi automaticamente removida.

A decisão foi baseada no fato de que, em um processo industrial,
um valor estatisticamente extremo pode representar uma condição
operacional real, como rampas, startups, shutdowns ou outros
regimes transitórios.

A exclusão de um ponto somente seria justificada mediante
evidência de erro ou inconsistência no dado.


## 5. Engenharia de atributos

Foi realizada feature engineering para representar não apenas
a condição instantânea da unidade, mas também sua trajetória
operacional.

As principais features criadas foram:

- carga atual;
- carga da hora anterior;
- variação horária da carga;
- módulo da variação da carga;
- média das três horas anteriores;
- Operating Time da hora anterior;
- evento de startup;
- evento de shutdown;
- direção da alteração de carga;
- tempo desde o último startup;
- hora do dia;
- mês.

Foram identificados:

- **38 startups**;
- **37 shutdowns**.

Nenhuma variável derivada de CO₂ foi utilizada como feature,
evitando target leakage.

Essa representação permite futuramente comparar um modelo
baseado apenas na carga instantânea com outro que incorpora
informações sobre trajetória e estado operacional.


## 6. PCA exploratória

Foi aplicada Análise de Componentes Principais (PCA) como
técnica exploratória de feature extraction.

A PCA utilizou sete variáveis operacionais e foi aplicada
somente às horas em que a unidade estava operando.

A variância explicada foi:

- PC1: **44,07%**
- PC2: **16,51%**
- PC3: **14,15%**
- PC4: **13,27%**
- PC5: **11,66%**

Foram necessárias **5 componentes** para representar pelo menos
90% da variância das sete features analisadas.

Os loadings mostraram uma interpretação física clara:

**PC1 — nível de carga**

As maiores contribuições foram:

- carga da hora anterior;
- média de carga das três horas anteriores;
- carga atual.

**PC2 — dinâmica operacional**

As maiores contribuições foram:

- variação horária da carga;
- intensidade absoluta da variação.

A última componente apresentou variância praticamente nula,
resultado coerente com a dependência matemática:

**ΔP(t) = P(t) − P(t−1)**

Assim, parte da redundância identificada é decorrente da própria
engenharia de atributos.


## 7. Decisão sobre a PCA

Apesar de a PCA identificar redundância entre algumas features,
a redução dimensional não foi considerada suficientemente
expressiva para justificar a substituição das variáveis
originais pelas componentes principais.

A transformação seria aproximadamente:

**7 features → 5 componentes para explicar ≥ 90% da variância**

Como a redução é pequena e as componentes possuem menor
interpretabilidade física, optou-se por preservar as features
originais.

A PCA permanece, portanto, como ferramenta exploratória.


## 8. Definição da base experimental

Para as análises posteriores das emissões de CO₂ foram mantidas
somente as horas em que a unidade estava operando.

A base experimental possui:

**6,249 observações operacionais.**

Essa decisão evita que as horas OFF, caracterizadas
essencialmente por carga e emissão iguais a zero, aumentem
artificialmente o desempenho dos modelos.

A variável-alvo definida foi:

**CO2 Mass (short tons)**

As sete features operacionais consideradas nesta fase são:

1. load_current_mw;
2. load_lag_1h;
3. delta_load_1h;
4. abs_delta_load_1h;
5. load_mean_previous_3h;
6. operating_time_lag_1h;
7. hours_since_startup.


## 9. Divisão temporal

Como os dados constituem uma série temporal, não foi utilizada
divisão aleatória entre treino e teste.

A ordem cronológica foi preservada:

### Treino

Janeiro a setembro de 2025  
**4,894 observações**
(**78.32%**)

### Validação

Outubro de 2025  
**211 observações**
(**3.38%**)

### Teste

Novembro e dezembro de 2025  
**1,144 observações**
(**18.31%**)

Os números correspondem exclusivamente às horas operacionais da
unidade, e não ao número total de horas de cada período.

A divisão temporal impede que informações futuras sejam
utilizadas para treinamento de modelos destinados a estimar
observações anteriores.


## 10. Normalização Min–Max

As variáveis explicativas foram preparadas utilizando
normalização Min–Max.

O scaler foi ajustado exclusivamente utilizando o conjunto de
treino.

Posteriormente, o mesmo scaler foi utilizado para transformar
os conjuntos de validação e teste.

Essa estratégia evita data leakage durante o pré-processamento.

Foram identificadas:

- **0 observações de validação** com alguma
  feature fora do intervalo [0,1];
- **18 observações de teste** com alguma feature
  fora do intervalo [0,1].

Esse comportamento não representa erro de normalização.

Valores fora de [0,1] nos períodos futuros indicam apenas que
essas observações apresentaram valores além do intervalo mínimo
ou máximo observado durante o treinamento.


## 11. Resultado do pré-processamento

O fluxo de preparação dos dados foi:

**Auditoria dos dados  
→ tratamento de valores faltantes  
→ análise de outliers  
→ feature engineering  
→ PCA exploratória  
→ seleção da base operacional  
→ divisão temporal  
→ normalização Min–Max.**

As técnicas foram aplicadas de acordo com a natureza dos dados
e com o objetivo do estudo, evitando aplicação automática de
procedimentos sem justificativa metodológica.

Por exemplo:

- não foi utilizada interpolação porque não existiam lacunas
  durante a operação;
- outliers não foram removidos automaticamente;
- PCA foi analisada, mas não utilizada para substituir as
  features;
- SMOTE não foi aplicado, pois o problema é de regressão e não
  de balanceamento de classes;
- a divisão treino/teste foi adaptada para respeitar a natureza
  temporal dos dados.

Com isso, a base encontra-se preparada para análises posteriores
de Ciência de Dados e para a caracterização do processo operacional.
