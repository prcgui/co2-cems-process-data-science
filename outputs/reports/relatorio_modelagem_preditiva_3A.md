
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
