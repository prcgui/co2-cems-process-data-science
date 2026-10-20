
# Relatório: Notebook 3A.01

## 1. Objetivo

Avaliar se uma representação temporal mais completa da
trajetória operacional melhora a estimação horária de CO₂ em
relação ao Cenário B do Notebook 3A.

## 2. Controle experimental

Foram mantidos:

- mesma arquitetura MLP;
- mesmo otimizador Adam;
- mesma função de perda MSE;
- mesmo learning rate;
- mesmo batch size;
- mesma divisão temporal;
- mesma estratégia de EarlyStopping.

A principal modificação foi o conjunto de features.

## 3. Resultados

### Cenário B

- MAE: **61.6102**
- RMSE: **67.0401**
- R²: **0.8908**

### Cenário C

- MAE: **62.6466**
- RMSE: **66.9842**
- R²: **0.8910**

### Variação B → C

- redução de MAE: **-1.68%**
- redução de RMSE: **+0.08%**
- variação de R²: **+0.0002**

## 4. Comparação hora a hora

O Cenário C apresentou erro inferior ao Cenário B em:

**491 de 1144 horas**

ou:

**42.9% das observações.**

## 5. Viés

- viés médio B: **+60.89 short tons**
- viés médio C: **+62.13 short tons**

## 6. Startup

Melhora B → C nas primeiras 6 horas após startup:

**+22.67%**

## 7. Rampas intensas

Limiar:

**|ΔP| ≥ 130.00 MW/h**

Melhora B → C:

**+1.33%**

## 8. Diagnóstico global


O Cenário C não apresentou melhora consistente nas três métricas
globais em relação ao Cenário B.

Isso sugere que simplesmente acrescentar mais informações de
trajetória não é suficiente para melhorar a capacidade de
generalização da MLP atual.


## 9. Diagnóstico das rampas


O Cenário C também reduziu o erro durante rampas intensas.

Esse resultado é particularmente relevante porque as rampas
constituíam a principal deficiência identificada no Notebook 3A.


## 10. Próxima decisão metodológica

O resultado deste notebook deverá determinar o próximo
experimento.

Se o enriquecimento temporal produzir ganho consistente,
a próxima etapa poderá investigar:

- otimização de hiperparâmetros;
- Huber Loss;
- validação temporal progressiva.

Se o ganho for pequeno ou inexistente, deverá ser considerada
a comparação com outra família de modelos, como gradient
boosting.

Se as métricas globais melhorarem, mas as rampas continuarem
problemáticas, poderá ser testada uma estratégia orientada a
regimes, incluindo ponderação de erros ou modelos especializados.

Nenhuma dessas alternativas será aplicada automaticamente antes
da análise dos resultados obtidos neste notebook.


## 11. Fundamentação metodológica das técnicas de modelagem e avaliação

### 11.1. Aprendizado supervisionado, regressão e arquitetura da IA

O problema é formulado como **supervised regression**, com CO₂ horário como variável-alvo contínua. O Cenário C utiliza uma **Multilayer Perceptron (MLP)**, uma rede neural artificial do tipo **feedforward** com camadas densas, ReLU nas camadas ocultas e saída linear. O treinamento é realizado por **backpropagation**, calculada internamente pelo TensorFlow/Keras, e os pesos são ajustados pelo **otimizador Adam**, com **MSE** como função de perda. Não se trata de uma rede neural recorrente: a memória do processo é fornecida pelas features temporais construídas explicitamente.

### 11.2. Engenharia de variáveis temporais (temporal feature engineering)

- **Lagged features**: `shift(n)` cria defasagens observacionais de carga e de rampas, incluindo `P(t−2)`, `P(t−3)` e `P(t−6)`.
- **Rolling-window features**: `shift(1).rolling(...)` seguido de média, desvio padrão, mínimo e máximo resume janelas de observações anteriores à hora atual.
- **Look-ahead bias prevention**: aplicar `shift(1)` antes de `rolling(...)` impede que a própria hora `t` integre estatísticas destinadas a descrever apenas o histórico; essa é uma medida de prevenção de **temporal data leakage**.
- **Representação temporal operacional**: histórico ON/OFF, fase após startup, aceleração e direção das rampas descrevem regimes de operação.
- **Ressalva**: `shift(n)` representa `n` linhas e só pode ser interpretado como `n` horas quando a frequência temporal estiver efetivamente regular.

A carga da própria hora `P(t)` permanece como entrada. Assim, o experimento é de **estimação contemporânea de CO₂** e não demonstra capacidade de previsão antecipada a partir de dados exclusivamente anteriores à hora prevista.

### 11.3. Comparação controlada dos conjuntos de features

O estudo de B para C é uma **controlled feature-set comparison**, com lógica de **ablação incremental**: acrescentam-se variáveis temporais mantendo a arquitetura geral da MLP, os principais parâmetros de treinamento e a divisão cronológica. Como o Cenário B provém do Notebook 3A, a interpretação de diferenças deve considerar eventuais diferenças na amostra efetivamente elegível entre os experimentos; não se pressupõe pareamento completo sem verificação explícita.

### 11.4. Protocolo temporal e prevenção de vazamento

A separação cronológica do conjunto de dados é um **temporal holdout**: janeiro a setembro para treinamento, outubro para validação, novembro e dezembro para teste. A normalização Min-Max é ajustada somente ao treino e depois aplicada à validação e ao teste. O limiar de rampas intensas (P90) também é estimado exclusivamente no treino. Esses controles reduzem riscos de **data leakage**. Como o período de teste já foi examinado em trabalhos anteriores, futuras decisões de desenvolvimento não devem tratá-lo como teste inteiramente cego.

### 11.5. Distribution shift e risco de extrapolação

A comparação das médias das features entre treino e teste, juntamente com a proporção de valores do teste fora dos limites mínimo e máximo de treinamento, constitui um **diagnóstico descritivo de distribution shift e extrapolation risk**. Esse procedimento não é um teste formal de **covariate shift** ou **concept drift** e não comprova alteração na relação entre variáveis operacionais e emissões. Conclusões mais fortes exigiriam procedimentos específicos adicionais.

### 11.6. Síntese das técnicas empregadas

| Técnica | Aplicação no Notebook 3A.01 | Limite de interpretação |
|---|---|---|
| Supervised regression / MLP feedforward | Estima CO₂ a partir das features operacionais | Não constitui RNN nem previsão antecipada obrigatoriamente |
| Temporal feature engineering | Constrói memória operacional explícita | Exige coerência da ordenação temporal |
| Lagged features | `shift(n)` | Linhas não equivalem necessariamente a horas se houver lacunas |
| Rolling-window features | `shift(1).rolling(...)` | As estatísticas descrevem somente períodos passados |
| Look-ahead bias prevention | `shift(1)` nas janelas históricas | Não elimina automaticamente todas as possibilidades de leakage |
| Temporal holdout | Treino, validação e teste cronológicos | Teste já conhecido dos experimentos anteriores |
| Controlled feature-set comparison | Comparação B versus C mantendo arquitetura | A equivalência de amostras deve ser avaliada |
| Distribution shift (descritivo) | Médias e limites das features no teste | Não prova covariate shift nem concept drift |

A interpretação dos resultados deve considerar que o experimento avalia a estimação contemporânea das emissões, que o período de teste foi reutilizado após o Notebook 3A e que o diagnóstico de alterações na distribuição das entradas é descritivo, não uma comprovação formal de *covariate shift* ou *concept drift*.
