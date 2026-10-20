
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

Esse critério é conhecido como **Tukey's fences (regra de Tukey)**:
limite inferior Q1 − 1,5 × IQR e limite superior Q3 + 1,5 × IQR.
Trata-se de uma triagem estatística exploratória e univariada,
sem equivaler a um teste formal ou à confirmação de erros nos dados.

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

Do ponto de vista metodológico, `shift(1)` constrói
**lagged features (variáveis defasadas)**, como P(t−1) e o
Operating Time da hora anterior. Já `shift(1).rolling(...)`
constrói uma **rolling-window feature (estatística em janela móvel)**:
a média de carga das três horas anteriores, sem incluir a hora
corrente no histórico. A defasagem anterior à média móvel
reduz o risco de **look-ahead bias (antecipação de informação)**
e de vazamento temporal nessa variável.

A identificação de startups e shutdowns corresponde a
**state-transition event detection (detecção de eventos por
transição de estado)**: as transições OFF → ON e ON → OFF são
reconhecidas por regras determinísticas, sem treinamento de
um classificador. O primeiro registro não gera transição
inferida porque não se conhece o estado da hora anterior.

Foram identificados:

- **38 startups**;
- **37 shutdowns**.

Nenhuma variável derivada de CO₂ foi utilizada como feature,
evitando target leakage.

Essa representação permite futuramente comparar um modelo
baseado apenas na carga instantânea com outro que incorpora
informações sobre trajetória e estado operacional.


## 6. PCA exploratória

Foi aplicada Análise de Componentes Principais (PCA), conforme
a técnica de feature extraction estudada na disciplina.

Antes da PCA, as variáveis foram submetidas à
**z-score standardization (padronização por escore z)**,
implementada com `StandardScaler`, de forma que cada variável
é centralizada por sua média e dividida pelo desvio-padrão.
Isso evita predomínio artificial de variáveis por suas escalas.
O ajuste nesta etapa utiliza a amostra exploratória e as
componentes não integram os modelos preditivos; seu eventual
uso supervisionado exigiria ajuste apenas no conjunto de treino.

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

Para a futura modelagem das emissões de CO₂ foram mantidas
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

Esse protocolo denomina-se **temporal holdout**, isto é,
separação cronológica em conjuntos fixos e não sobrepostos
para treinamento, validação e teste. Não corresponde a uma
validação cruzada temporal walk-forward, que empregaria
múltiplas origens de avaliação.

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
normalização Min–Max, técnica abordada na disciplina.

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


## 10.1. Distinção entre os métodos de escalonamento

A padronização z-score foi aplicada exclusivamente no contexto
da PCA exploratória; a normalização Min–Max foi aplicada à
preparação de entradas para modelagem, com ajuste apenas no
treino. São técnicas diferentes e com finalidades diferentes,
embora ambas modifiquem a escala das variáveis.


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

## 12. Técnicas de pré-processamento e validação temporal

A preparação dos dados emprega as seguintes técnicas estatísticas,
de engenharia de atributos e de validação temporal:

- **Tukey's fences:** detecção exploratória de outliers usando
  1,5 × IQR, sem exclusão automática de observações;
- **Lagged features:** variáveis defasadas de uma hora via
  `shift(1)`;
- **Rolling-window features:** média móvel das três horas
  anteriores via `shift(1).rolling(...)`;
- **State-transition event detection:** identificação de
  startups e shutdowns pelas passagens OFF/ON e ON/OFF;
- **Z-score standardization:** padronização com `StandardScaler`
  antes da PCA exclusivamente exploratória;
- **Temporal holdout:** divisão cronológica fixa de 2025 em
  treino, validação e teste;
- **Min-Max sem data leakage:** scaler ajustado apenas no treino
  e reutilizado nos períodos seguintes.

Essas técnicas compõem o pré-processamento e a preparação
da base operacional para os experimentos preditivos subsequentes.
Este notebook não treina, por si só, um modelo de IA. A avaliação
de modelos deve respeitar a separação cronológica entre
treinamento, validação e teste.


Com isso, a base encontra-se preparada para a futura etapa de
modelagem das emissões horárias de CO₂.
