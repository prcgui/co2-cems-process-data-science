
# Relatório: Notebook 3A.03

## 1. Objetivo

Realizar uma busca pareada de hiperparâmetros para os Cenários A
e B utilizando a mesma família de modelo, o mesmo espaço de busca,
as mesmas configurações candidatas e os mesmos cinco folds
temporais.

A pergunta investigada foi:

> Após busca controlada de hiperparâmetros da mesma família de
> modelo, a inclusão de informações de trajetória operacional
> oferece ganho preditivo consistente em relação ao uso exclusivo
> da carga instantânea?

---

## 2. Cenários avaliados

### Cenário A

Carga instantânea:

`CO₂(t) = f(P(t))`

Número de features: **1**

### Cenário B

Carga instantânea e trajetória operacional básica.

Número de features: **7**

---

## 3. Estratégia de busca

Foram sorteadas **30 configurações** de hiperparâmetros
com `ParameterSampler` e semente aleatória igual a **42**.

Cada configuração foi avaliada:

- no Cenário A;
- no Cenário B;
- nos mesmos cinco folds temporais.

Número total de ajustes:

**300 modelos**

A métrica primária de seleção foi o **MAE médio dos cinco folds**.

O holdout histórico de novembro e dezembro não participou da
seleção dos hiperparâmetros.

### Fundamentação metodológica da otimização

**Random Search (busca aleatória de hiperparâmetros).**
O `ParameterSampler` sorteia combinações do espaço de busca
previamente definido. O uso de `random_state=SEED` permite
reproduzir a seleção das configurações candidatas. Ao contrário
de uma busca exaustiva (*Grid Search*), não é necessário testar
todas as combinações possíveis. Neste experimento, o número
de árvores (`n_estimators`) é otimizado explicitamente; não se
utiliza *early stopping* durante a busca.

**Walk-forward temporal cross-validation with an expanding
training window (validação cruzada temporal com janela expansiva).**
Os cinco folds avançam cronologicamente: o treinamento começa
em janeiro e incorpora progressivamente novos meses, enquanto
cada validação utiliza o mês imediatamente posterior ao fim da
respectiva janela de treino. Essa estrutura evita embaralhar
observações futuras com dados passados e distingue o procedimento
de uma validação cruzada aleatória do tipo `KFold`.

**Paired experimental design (desenho experimental pareado).**
Os dois cenários utilizam as mesmas observações elegíveis, o
mesmo conjunto de configurações candidatas, os mesmos folds
e a mesma métrica de avaliação. Assim, as diferenças entre A
e B são examinadas sob condições experimentais comparáveis,
com a representação das variáveis como principal contraste.
Entretanto, a melhor configuração é selecionada separadamente
para cada cenário, a partir do MAE médio de validação. Portanto,
o pareamento não significa que os modelos finais precisem ter
hiperparâmetros idênticos, nem constitui um teste formal de
significância estatística.

**Final refit (reajuste final).** Após a seleção dos
hiperparâmetros, os modelos são novamente treinados com todo
o período de desenvolvimento, de janeiro a outubro. Os meses
de novembro e dezembro são utilizados apenas na avaliação
histórica posterior, com a ressalva de já terem sido observados
em etapas anteriores da pesquisa.

---

## 4. Configurações selecionadas

| Cenário   |   Features | Configuração   |   subsample |   reg_lambda |   reg_alpha |   n_estimators |   min_child_weight |   max_depth |   learning_rate |   gamma |   colsample_bytree |
|:----------|-----------:|:---------------|------------:|-------------:|------------:|---------------:|-------------------:|------------:|----------------:|--------:|-------------------:|
| A         |          1 | CFG_10         |        0.85 |            5 |         0.5 |            200 |                  5 |           6 |            0.01 |    0.25 |                  1 |
| B         |          7 | CFG_28         |        1    |           10 |         0.5 |            200 |                  3 |           6 |            0.01 |    0.5  |                  1 |

---

## 5. Validação temporal pareada

|   fold | validation_month   |   MAE_A |   RMSE_A |   R2_A |   MAE_B |   RMSE_B |   R2_B |   ganho_MAE_B_vs_A_% |
|-------:|:-------------------|--------:|---------:|-------:|--------:|---------:|-------:|---------------------:|
|      1 | 2025-06            |  51.332 |   86.273 |  0.855 |  50.605 |   85.393 |  0.858 |                1.415 |
|      2 | 2025-07            |  75.011 |   88.364 |  0.814 |  73.275 |   86.502 |  0.822 |                2.314 |
|      3 | 2025-08            |  52.349 |   58.449 |  0.854 |  53.011 |   59.109 |  0.85  |               -1.263 |
|      4 | 2025-09            |  78.181 |   82.875 |  0.78  |  78.082 |   81.886 |  0.785 |                0.126 |
|      5 | 2025-10            |  53.609 |   62.941 |  0.931 |  52.75  |   63.869 |  0.929 |                1.602 |

O Cenário B apresentou menor MAE em **4 de 5 folds**.

O ganho médio de MAE de A para B foi de:

**+0.89%**

Apesar de B vencer quatro dos cinco folds, a magnitude média do
ganho foi inferior a 1%.

---

## 6. Comparação com as configurações de referência

A busca do Notebook 3A.03 utiliza um protocolo de treinamento
diferente daquele utilizado no Notebook 3A.02.

No Notebook 3A.02:

- `n_estimators` máximo igual a 3000;
- `early_stopping_rounds` igual a 50.

No Notebook 3A.03:

- `n_estimators` foi tratado explicitamente como hiperparâmetro;
- não foi utilizado early stopping.

Por esse motivo, a diferença absoluta de MAE entre os dois
notebooks não deve ser interpretada isoladamente como efeito
da busca de hiperparâmetros.

O objetivo principal desta comparação é verificar a consistência
da relação relativa entre A e B.

| protocolo            | avaliacao          |   MAE_A |   MAE_B |   ganho_B_vs_A_% |
|:---------------------|:-------------------|--------:|--------:|-----------------:|
| 3A.02: referência    | Validação temporal |  56.613 |  56.23  |            0.677 |
| 3A.03: busca pareada | Validação temporal |  62.096 |  61.545 |            0.888 |
| 3A.02: referência    | Holdout histórico  |  22.962 |  23.266 |           -1.32  |
| 3A.03: busca pareada | Holdout histórico  |  38.898 |  39.356 |           -1.176 |

Nos dois protocolos foi observado o mesmo padrão:

- B apresenta pequena vantagem média na validação temporal;
- essa vantagem não se reproduz no holdout histórico.

Essa repetição do comportamento em dois protocolos distintos
reforça a interpretação de que o benefício global das variáveis
adicionais de trajetória é limitado.

---

## 7. Holdout histórico

| cenario                   |   n_features |     MAE |    RMSE |     R2 |
|:--------------------------|-------------:|--------:|--------:|-------:|
| A-XGBoost (busca pareada) |            1 | 38.8984 | 45.0646 | 0.9507 |
| B-XGBoost (busca pareada) |            7 | 39.3558 | 46.2507 | 0.948  |

O ganho de MAE de B em relação a A no holdout histórico foi:

**-1.18%**

Portanto, o Cenário B não superou o Cenário A no desempenho
global de novembro e dezembro.

É importante ressaltar que esse período já foi utilizado ao longo
do desenvolvimento dos experimentos anteriores.

Por esse motivo, novembro e dezembro devem ser tratados como
**holdout histórico de comparação**, e não como teste final
completamente cego.

---

## 8. Contextos operacionais

O limiar utilizado para identificar rampas intensas foi:

**130.00 MW/h**

Esse valor corresponde ao percentil 90 de `abs_delta_load_1h`
calculado exclusivamente no período de desenvolvimento.

| contexto                   |    n |   MAE_A |   MAE_B |   ganho_B_vs_A_% |
|:---------------------------|-----:|--------:|--------:|-----------------:|
| Todas as horas             | 1144 |  38.898 |  39.356 |           -1.176 |
| Primeiras 6 h após startup |   30 |  83.66  |  87.287 |           -4.335 |
| Rampas intensas            |  115 |  30.381 |  28.898 |            4.879 |

Nas primeiras seis horas após startup, B apresentou desempenho
inferior a A.

Em rampas intensas, entretanto, B apresentou redução de MAE de:

**+4.88%**

Esse resultado sugere que as informações de trajetória podem
possuir valor preditivo localizado durante mudanças operacionais
mais intensas.

Entretanto, o subconjunto de rampas contém apenas
**115 observações**.

Portanto, esse resultado deve ser interpretado como evidência
exploratória e não como demonstração definitiva de superioridade
do Cenário B em regimes transitórios.

---

## 9. Interpretação

A busca pareada não fornece evidência de que a trajetória
operacional produza ganho preditivo global suficientemente
consistente para justificar, neste momento, a maior complexidade
do Cenário B.

A validação temporal favoreceu B em quatro dos cinco folds, mas
o ganho médio foi pequeno:

**+0.89%**

Além disso, o resultado não se reproduziu no holdout histórico:

**-1.18%**

A comparação com o Notebook 3A.02 reforça essa interpretação,
pois o mesmo padrão qualitativo foi observado utilizando outro
protocolo de treinamento.

Isso não significa que os processos ou estágios operacionais
sejam irrelevantes para as emissões de CO₂.

A conclusão é mais específica:

> Para a Iatan Unit 2, considerando os dados de 2025 e as
> variáveis de trajetória avaliadas, essas informações não
> apresentaram ganho preditivo global consistente além daquele
> obtido com a carga instantânea.

A melhora observada durante rampas intensas sugere que o valor
da trajetória pode depender do regime operacional.

---

## 10. Parcimônia

O Cenário A utiliza apenas **1 feature**.

O Cenário B utiliza **7 features**.

Como o aumento de complexidade não produziu benefício global
consistente, o princípio de parcimônia favorece o Cenário A
como representação de referência para os experimentos seguintes
na Iatan.

Essa escolha não significa que A seja considerado, neste estágio,
o modelo final da unidade.

Ela significa apenas que a carga instantânea constitui o ponto
de partida mais simples e competitivo para os próximos testes.

---

## 11. Conclusão do Notebook 3A.03

A resposta à pergunta específica deste notebook é:

> **Não foi observada evidência robusta de que a inclusão das
> informações de trajetória operacional melhore de forma global
> e consistente o XGBoost em relação ao uso exclusivo da carga
> instantânea.**

O Cenário B apresentou pequeno ganho médio na validação temporal,
mas esse ganho não se reproduziu no holdout histórico.

O ganho observado durante rampas intensas indica, entretanto,
que a trajetória operacional pode possuir valor localizado em
regimes dinâmicos específicos.

A persistência desse possível benefício em outros períodos
permanece indeterminada neste notebook.

---

## 12. Limitação da evidência disponível

Os resultados obtidos até o Notebook 3A.03 não são suficientes
para afirmar que foi encontrado o melhor modelo possível para a
Iatan Unit 2.

Até este ponto, a maior parte dos experimentos utiliza apenas o
ano de **2025**.

Consequentemente, ainda não foi respondida uma questão central:

> **O desempenho preditivo melhora quando o volume de dados
> históricos utilizado no treinamento aumenta?**

Também permanece em aberto outra questão fundamental:

> **Um modelo desenvolvido com dados históricos consegue manter
> desempenho satisfatório em um período futuro completamente
> ausente das etapas de treinamento, seleção de features e
> escolha de hiperparâmetros?**

A diferença observada entre os erros da validação temporal e do
holdout histórico também indica que a dificuldade da previsão
varia ao longo do tempo.

Portanto, um bom resultado em novembro e dezembro de 2025 não
deve ser interpretado isoladamente como demonstração definitiva
da precisão do modelo.

---

## 13. Limitações e direcionamento da investigação subsequente

Este notebook avaliou o ganho incremental das variáveis de trajetória
operacional para a Iatan Unit 2, a partir dos dados de 2025, com
otimização pareada do XGBoost. Os resultados não demonstraram
superioridade global consistente do Cenário B sobre o Cenário A.
A melhora observada nas rampas intensas permanece uma evidência
exploratória restrita ao subconjunto avaliado.

O desempenho nos cinco folds variou entre meses, e novembro e
dezembro de 2025 já haviam sido utilizados em experimentos
anteriores. Portanto, esta análise **não constitui uma avaliação
final e independente da generalização temporal**, tampouco define
um modelo definitivo para a unidade.

Uma questão permaneceu sem resposta ao término do experimento:
**qual é o efeito da quantidade de histórico de treinamento sobre
o erro de previsão e sua estabilidade entre períodos?** Essa
limitação motivou o Notebook 3A.04, voltado à avaliação do volume
de dados históricos e da generalização temporal na própria Iatan
Unit 2.

A identificação dessa questão não implica assumir outras etapas
experimentais. Investigações adicionais dependem dos resultados
obtidos, de sua pertinência para a pergunta de pesquisa e das
condições efetivas de análise.
