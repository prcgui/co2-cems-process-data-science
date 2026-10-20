
# Relatório — Notebook 3A

## 1. Unidade analisada

**Unidade:** Iatan — Unit 2
**Facility ID:** 6065
**Ano:** 2025

## 2. Pergunta experimental

Em que medida a inclusão de informações sobre estados, memória e trajetória operacional melhora a estimação das emissões horárias de CO₂ em relação ao uso apenas da carga instantânea?

## 3. Cenários

**Cenário A:** carga instantânea, P(t).
**Cenário B:** carga atual + memória e trajetória operacional.

## 4. Divisão temporal

- Treino: 2025-01-01 16:00:00 → 2025-09-30 23:00:00 — **4,894 observações**
- Validação: 2025-10-01 00:00:00 → 2025-10-31 23:00:00 — **211 observações**
- Teste: 2025-11-01 00:00:00 → 2025-12-31 23:00:00 — **1,144 observações**

## 5. Arquitetura

**MLP: entrada → Dense(64, ReLU) → Dense(32, ReLU) → Dense(1, linear)**

- Adam, learning rate = 0.001
- batch size = 64
- máximo de épocas = 500
- EarlyStopping patience = 30
- melhor época A = 24
- melhor época B = 38

## 6. Resultados no teste

| Cenário | MAE | RMSE | R² |
|---|---:|---:|---:|
| A — carga instantânea | 67.2508 | 70.9010 | 0.8779 |
| B — carga + trajetória | 61.6102 | 67.0401 | 0.8908 |

### Ganho do Cenário B

- redução de MAE: **+8.39%**
- redução de RMSE: **+5.45%**
- variação de R²: **+0.0129**

## 7. Análise por contexto operacional

Limiar de rampa intensa: **|ΔP| ≥ 130.00 MW/h**, definido pelo P90 do treino.

| contexto                           |    n |   MAE_A |   MAE_B |   reducao_MAE_A_para_B_% |
|:-----------------------------------|-----:|--------:|--------:|-------------------------:|
| Todas as horas de teste            | 1144 |  67.251 |  61.61  |                    8.387 |
| Primeiras 6 h após startup         |   30 |  13.533 |   9.994 |                   26.151 |
| Rampas intensas (>= P90 do treino) |  115 |  65.884 |  75.17  |                  -14.094 |

## 8. Interpretação metodológica

A hipótese deve ser avaliada pelo desempenho fora da amostra. Melhora apenas no treino não constitui evidência suficiente.

O Cenário B será considerado superior se apresentar ganho consistente no conjunto de teste, especialmente redução de MAE e RMSE e, idealmente, aumento de R².

A análise por contexto verifica se a informação de trajetória é particularmente útil durante startups e rampas intensas.

## 9. Artefatos gerados

### Tabelas
- 03A_divisao_temporal.csv
- 03A_comparacao_modelos.csv
- 03A_previsoes_teste.csv
- 03A_comparacao_contextos.csv

### Figuras
- 03A_curvas_validacao.png
- 03A_observado_vs_previsto.png

### Modelos
- 03A_mlp_cenario_A.keras
- 03A_mlp_cenario_B.keras
- 03A_scaler_X_A.joblib
- 03A_scaler_X_B.joblib
- 03A_scaler_y.joblib

## 10. Fundamentação metodológica da inteligência artificial

### 10.1. Classificação da técnica de IA

O problema consiste em **aprendizado supervisionado de regressão** (*supervised regression*), pois se estima uma variável-resposta numérica contínua, a massa horária de CO₂, a partir de exemplos históricos com entradas e alvos conhecidos. A técnica utilizada é uma **rede neural artificial feedforward** (*feedforward artificial neural network*), especificamente um **Perceptron Multicamadas** (*Multilayer Perceptron, MLP*).

A hierarquia conceitual é: **Inteligência Artificial → Machine Learning → Aprendizado Supervisionado → Regressão → Redes Neurais Artificiais → Redes Feedforward → MLP**.

### 10.2. Arquitetura e funcionamento da MLP

Os dois cenários usam a mesma configuração de camadas ocultas: **Dense(64, ReLU) → Dense(32, ReLU) → Dense(1, linear)**. Camadas *Dense* realizam combinações afins parametrizadas; a ativação *ReLU* introduz não linearidade; a saída linear é compatível com um alvo contínuo. O Cenário A usa uma variável de entrada, enquanto B usa sete; consequentemente, o número total de parâmetros treináveis difere entre cenários.

### 10.3. Retropropagação e otimização

O treinamento minimiza o **erro quadrático médio (Mean Squared Error, MSE)**. O cálculo dos gradientes é realizado por **retropropagação do erro (*backpropagation*) internamente pelo TensorFlow/Keras**, sem implementação manual desse algoritmo neste notebook. O **otimizador Adam (*Adam optimizer*)** emprega os gradientes para atualizar os parâmetros. O **EarlyStopping** monitora `val_loss` e, com `restore_best_weights=True`, recupera os pesos correspondentes à melhor época de validação; isso limita treinamento desnecessário e pode reduzir sobreajuste, sem garantir sua eliminação.

### 10.4. Normalização sem vazamento de dados

A técnica aplicada é a **normalização Min–Max (*min-max scaling*)**. Os parâmetros de escala são ajustados exclusivamente no conjunto de treino (`fit_transform`) e aplicados sem novo ajuste à validação e ao teste (`transform`). Há transformações separadas para as entradas de A, para as entradas de B e para o alvo. As métricas de erro são calculadas após retorno das previsões à unidade original do CO₂. Valores fora da amplitude observada no treino podem ser transformados para fora do intervalo de zero a um.

### 10.5. Divisão temporal e avaliação fora da amostra

A separação de janeiro a setembro para treino, outubro para validação e novembro a dezembro para teste é denominada **temporal holdout**, uma partição cronológica fixa. A validação apoia a escolha da época por EarlyStopping e o teste permanece reservado para a avaliação final **fora da amostra (*out-of-sample evaluation*)**. Este protocolo não corresponde a divisão aleatória nem a validação cruzada temporal *walk-forward*.

### 10.6. Comparação controlada dos conjuntos de variáveis

O desenho A versus B é uma **comparação controlada de conjuntos de features (*controlled feature-set comparison*) com lógica de ablação aditiva** (*feature ablation logic*): o Cenário A usa apenas carga instantânea; o B mantém essa entrada e adiciona memória e trajetória operacional. São mantidos os mesmos períodos, a configuração das camadas ocultas e as condições básicas de treinamento. Como o número de entradas e parâmetros aumenta em B, a comparação não isola perfeitamente todos os efeitos de capacidade, tampouco constitui prova causal. A conclusão empírica é condicionada aos resultados observados no teste.

### 10.7. Técnicas de modelagem e avaliação utilizadas

| Etapa | Técnica explicitada | Aplicação efetiva |
|---|---|---|
| Formulação | Aprendizado supervisionado de regressão | Estimar massa horária de CO₂ |
| Modelo de IA | Feedforward ANN / MLP | Rede densa com duas camadas ocultas |
| Treinamento | Backpropagation e Adam | Gradientes internos ao TensorFlow/Keras; atualização de pesos por Adam |
| Função objetivo | Mean Squared Error, MSE | Perda de treinamento e validação |
| Controle de treinamento | EarlyStopping | Recuperação dos pesos da melhor época de validação |
| Pré-processamento | Train-only min-max scaling | Ajuste dos scalers somente no treino |
| Divisão da amostra | Temporal holdout | Treino, validação e teste cronológicos |
| Comparação | Controlled feature-set comparison | A como baseline e B com trajetória operacional |
| Avaliação | Temporal out-of-sample evaluation | MAE, RMSE e R² no conjunto de teste |

**Delimitação:** esta seção nomeia procedimentos já presentes no código; não afirma a execução de técnicas adicionais como *walk-forward validation*, otimização de hiperparâmetros ou teste formal de significância. A comparação deve ser interpretada conforme as métricas e a análise por contexto efetivamente calculadas.
