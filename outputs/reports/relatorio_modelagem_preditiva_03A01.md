
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
