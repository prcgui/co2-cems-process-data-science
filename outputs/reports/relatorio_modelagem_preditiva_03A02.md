
# Relatório: Notebook 3A.02

## 1. Objetivo

Avaliar se modelos de Gradient Boosting conseguem explorar as
informações operacionais dos Cenários A, B e C de forma mais
eficiente que as MLPs utilizadas nos experimentos anteriores.

O notebook também investiga se a inclusão de informações de
trajetória operacional apresenta ganho preditivo além do uso
exclusivo da carga instantânea quando a família de modelo é
mantida fixa.

---

## 2. Cenários avaliados

### Cenário A

Carga instantânea:

`CO₂(t) = f(P(t))`

Número de features: **1**

### Cenário B

Carga instantânea + trajetória operacional básica.

Número de features: **7**

### Cenário C

Trajetória temporal enriquecida.

Número de features: **24**

---

## 3. Validação temporal progressiva

Foram utilizados cinco folds temporais:

1. janeiro a maio -> junho;
2. janeiro a junho -> julho;
3. janeiro a julho -> agosto;
4. janeiro a agosto -> setembro;
5. janeiro a setembro -> outubro.

### Resultados médios do XGBoost

| Cenário | MAE médio | Desvio MAE | RMSE médio | Desvio RMSE | R² médio | Desvio R² |
|---|---:|---:|---:|---:|---:|---:|
| A | 56.6132 | 17.3006 | 72.1941 | 14.9393 | 0.8582 | 0.0623 |
| B | 56.2298 | 17.0684 | 71.8576 | 14.0435 | 0.8591 | 0.0606 |
| C | 55.6889 | 17.2915 | 71.0960 | 14.3441 | 0.8623 | 0.0598 |

O cenário com menor MAE médio na validação temporal foi:

**Cenário C**

---

## 4. Ganho incremental das informações de trajetória

Mantendo o algoritmo XGBoost fixo:

### Validação temporal

- A -> B: **+0.68%**
- A -> C: **+1.63%**

### Holdout histórico

- A -> B: **-1.32%**
- A -> C: **-8.96%**


Quando a família de modelo é mantida fixa no XGBoost, o ganho
incremental das informações de trajetória é pequeno.

Na validação temporal progressiva:

- A -> B: **+0.68%** de redução de MAE;
- A -> C: **+1.63%** de redução de MAE.

No holdout histórico:

- A -> B: **-1.32%**;
- A -> C: **-8.96%**.

Assim, a trajetória apresentou pequeno benefício médio durante
a validação temporal, mas esse ganho não se reproduziu no
holdout histórico.

Neste estágio, não há evidência suficientemente robusta para
afirmar que as variáveis adicionais de trajetória superam de
forma consistente o uso exclusivo da carga instantânea quando
o algoritmo utilizado é o XGBoost.


---

## 5. Comparação no holdout histórico

O período de novembro e dezembro permanece como referência para
comparação com os notebooks anteriores.

Entretanto, esse período já foi observado durante o processo de
desenvolvimento e não deve ser tratado como teste completamente
cego para novas decisões metodológicas.

### Resultados

| Cenário | Features | MAE | RMSE | R² |
|---|---:|---:|---:|---:|
| A-XGBoost | 1 | 22.9625 | 28.0571 | 0.9809 |
| B-XGBoost | 7 | 23.2657 | 28.8090 | 0.9798 |
| C-XGBoost | 24 | 25.0194 | 30.6338 | 0.9772 |

O menor MAE neste período foi obtido por:

**A-XGBoost**

---

## 6. Comparação MLP x XGBoost

A comparação com os modelos anteriores mostra forte efeito da
família de algoritmo.

### Redução de MAE ao substituir MLP por XGBoost

- Cenário A: **+65.86%**
- Cenário B: **+62.24%**
- Cenário C: **+60.06%**


A principal mudança de desempenho observada nesta sequência de
experimentos está associada à substituição da MLP pelo XGBoost.

Mantendo os mesmos conjuntos de informações, a redução de MAE
no holdout histórico foi:

- Cenário A: **+65.86%**
- Cenário B: **+62.24%**
- Cenário C: **+60.06%**

O fato de o Cenário A, utilizando apenas carga instantânea,
também apresentar forte melhora demonstra que o ganho do
Gradient Boosting não pode ser atribuído principalmente às
features de trajetória.

Os resultados indicam que a família de modelo possui papel
determinante na capacidade de representar a relação entre carga
operacional e massa horária de CO₂.


---

## 7. Sanity check

Como o XGBoost apresentou melhora muito expressiva em relação às
MLPs, foram realizados controles adicionais antes de interpretar
esse resultado.


Todos os controles metodológicos executados foram aprovados.

Foram verificadas:

- **23 features reconstruídas**, todas
  com diferença máxima igual a zero em relação às definições
  esperadas;
- ausência de features derivadas de CO₂;
- cálculo de `high_ramp` utilizando exclusivamente o conjunto
  de treino;
- ordem temporal correta nos cinco folds;
- ausência de sobreposição entre treino e validação;
- ausência de sobreposição entre treino, validação e holdout;
- **1144 observações** no holdout atual;
- **1144 observações** na avaliação anterior;
- **1144 timestamps** perfeitamente alinhados;
- diferença máxima de **0.0000000000** entre
  os valores observados de CO₂ usados nas comparações.

Portanto, não foram identificados sinais de target leakage,
vazamento temporal ou diferença de base capaz de explicar a
melhora apresentada pelo XGBoost.


---

## 8. Validade da comparação temporal

Todos os cinco folds apresentaram:

- treino anterior à validação;
- ausência de sobreposição de timestamps.

No split final também não houve sobreposição entre:

- treino e validação;
- treino e holdout;
- validação e holdout.

Além disso, MLP e XGBoost foram avaliados sobre exatamente as
mesmas **1144 observações** no holdout histórico.

---

## 9. Parcimônia do modelo


O Cenário A utiliza apenas **1 feature**, enquanto:

- B utiliza **7 features**;
- C utiliza **24 features**.

Apesar da diferença de complexidade, os três cenários
apresentaram resultados muito próximos na validação temporal.

Além disso, o melhor MAE observado no holdout histórico foi
obtido por:

**A-XGBoost**

Dessa forma, a inclusão de features adicionais somente deverá
ser mantida no modelo final se uma comparação após otimização
mostrar benefício consistente e reproduzível.


---

## 10. Diagnóstico final

Os experimentos realizados até este ponto permitem separar dois
efeitos.

### Efeito da família de modelo

A mudança de MLP para XGBoost produziu uma redução muito
expressiva do erro, inclusive quando apenas a carga instantânea
foi utilizada.

Portanto, o principal ganho observado decorre da capacidade do
Gradient Boosting de representar a relação não linear entre as
variáveis operacionais e a massa horária de CO₂.

### Efeito da trajetória operacional

Quando a família XGBoost é mantida fixa, os Cenários B e C
apresentam apenas pequeno ganho médio na validação temporal em
relação ao Cenário A.

Esse ganho não se reproduz no holdout histórico.

Assim, neste estágio, ainda não existe evidência robusta de que
a trajetória operacional melhore consistentemente o XGBoost em
relação ao uso exclusivo da carga instantânea.

---

## 11. Implicação para o próximo experimento

O resultado do sanity check modifica a estratégia inicialmente
planejada para o Notebook 3A.03.

Não é metodologicamente adequado otimizar apenas o Cenário B.

A próxima etapa deverá realizar uma **otimização pareada** de:

### A-XGBoost

- 1 feature;
- apenas carga instantânea.

### B-XGBoost

- 7 features;
- carga + trajetória operacional básica.

Os dois cenários deverão utilizar:

- o mesmo espaço de hiperparâmetros;
- a mesma estratégia de busca;
- os mesmos cinco folds temporais;
- MAE médio da validação temporal como métrica primária de
  seleção.

O Cenário C não será priorizado nesta etapa, pois o aumento de 7
para 24 features produziu apenas pequeno ganho médio na validação
temporal e pior desempenho no holdout histórico.

---

## 12. Pergunta para o Notebook 3A.03

A próxima etapa responderá:

> **Após otimização controlada da mesma família de modelo, a inclusão de informações de trajetória operacional oferece ganho preditivo consistente em relação ao uso exclusivo da carga instantânea?**

Essa comparação permitirá avaliar o valor incremental das
informações de trajetória sem confundir esse efeito com diferenças
de arquitetura ou de grau de otimização dos modelos.
