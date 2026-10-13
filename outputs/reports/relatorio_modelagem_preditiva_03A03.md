
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

Essa hipótese deverá ser novamente testada quando períodos
históricos adicionais forem incorporados à análise.

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

## 13. Decisão metodológica

A próxima etapa da pesquisa permanecerá concentrada na
**Iatan Unit 2**.

Antes de avaliar transferência entre diferentes unidades ou
usinas, será investigada de forma mais rigorosa a capacidade de
**generalização temporal intraplanta**.

O objetivo passa a ser responder:

> **Até que ponto é possível construir, para a Iatan Unit 2, um
> modelo robusto capaz de prever períodos futuros e manter seu
> desempenho quando o horizonte histórico e as condições
> operacionais se modificam?**

Por esse motivo, nenhum dos modelos obtidos até este notebook
será denominado **modelo final da Iatan**.

O melhor A-XGBoost identificado no Notebook 3A.02 permanece como
modelo de referência, mas sua capacidade de generalização ainda
deverá ser submetida a novos experimentos.

---

## 14. Estratégia 1: efeito do volume de dados

A primeira extensão investigará se a quantidade de histórico
disponível influencia sistematicamente o desempenho.

Serão incorporados, quando disponíveis, anos adicionais da série
horária da Iatan Unit 2.

Serão construídos experimentos com janelas crescentes de
treinamento.

Exemplo conceitual:

- histórico curto;
- histórico intermediário;
- um ano;
- dois anos;
- três anos ou mais.

Para cada tamanho de histórico serão calculadas as mesmas métricas
de desempenho.

O objetivo será construir uma **curva de aprendizado temporal**:

`erro = f(volume de dados históricos)`

Essa análise permitirá distinguir duas situações.

### Situação A

O erro continua diminuindo conforme novos dados são adicionados.

Nesse caso, o modelo ainda pode estar limitado pela quantidade
de informação disponível.

### Situação B

O erro entra em um platô mesmo após a inclusão de mais dados.

Nesse caso, novos anos provavelmente produzirão ganhos marginais
pequenos, indicando possível limitação das features, do algoritmo
ou da própria previsibilidade do fenômeno.

---

## 15. Estratégia 2: teste verdadeiramente fora da amostra

Será reservado um período posterior que não poderá participar de:

- seleção de features;
- construção de thresholds;
- escolha de hiperparâmetros;
- escolha de arquitetura;
- comparação entre variantes;
- qualquer decisão metodológica.

Esse período será utilizado exclusivamente após o congelamento
do modelo.

Exemplo conceitual:

`Treino e desenvolvimento -> anos anteriores`

`Teste final -> período futuro completamente não observado`

Esse experimento permitirá avaliar a capacidade real de
generalização temporal.

---

## 16. Estratégia 3: validação temporal entre anos

Além de um único teste final, serão avaliadas múltiplas divisões
temporais.

Exemplo:

- anos iniciais -> ano seguinte;
- anos iniciais + 1 -> ano seguinte;
- anos iniciais + 2 -> ano seguinte;
- e assim sucessivamente.

Essa estratégia permitirá verificar se o desempenho é estável
entre diferentes anos ou se determinados períodos apresentam
dificuldade significativamente maior.

A análise deverá incluir:

- MAE;
- RMSE;
- R²;
- métricas de erro normalizadas;
- comparação das métricas entre anos.

---

## 17. Estratégia 4: modelo estático versus atualização periódica

Serão comparadas duas estratégias de utilização prática.

### Modelo estático

O modelo é treinado até determinada data e permanece congelado
durante todo o período seguinte.

Essa estratégia simula um cenário de implantação em que o modelo
não recebe atualização contínua.

### Modelo com atualização periódica

O modelo é recalibrado à medida que novas observações históricas
se tornam disponíveis.

Poderão ser avaliadas atualizações:

- mensais;
- trimestrais;
- anuais.

A comparação permitirá responder se o sistema exige
retreinamento frequente ou se a relação entre operação e emissão
permanece suficientemente estável ao longo do tempo.

---

## 18. Estratégia 5: estabilidade da relação carga e CO₂

Será investigado se a relação observada entre carga e emissão
permanece estável entre anos.

A relação de interesse é:

`CO₂(t) = f(P(t))`

Serão comparadas distribuições e curvas carga-emissão de
diferentes períodos históricos.

Mudanças relevantes podem indicar:

- drift operacional;
- alteração de eficiência;
- mudança na composição ou qualidade do combustível;
- envelhecimento ou manutenção dos equipamentos;
- mudanças de estratégia operacional;
- mudanças não representadas pelas features atuais.

Essa análise será necessária para determinar se um único modelo
é suficiente ao longo do tempo.

---

## 19. Estratégia 6: reavaliar a trajetória com maior histórico

A conclusão obtida no Notebook 3A.03 refere-se principalmente
ao ano de 2025.

Portanto, a hipótese de que a trajetória operacional apresenta
pequeno valor incremental também deverá ser testada novamente
quando novos anos forem incorporados.

Será avaliado se:

- a vantagem pequena de B na validação temporal permanece;
- o desempenho inferior de B no holdout se repete;
- o ganho observado durante rampas intensas é reproduzível;
- startups apresentam comportamento semelhante em diferentes
  anos.

Caso o benefício da trajetória apareça repetidamente apenas em
regimes transitórios, poderá ser investigada posteriormente uma
estratégia específica para esses períodos.

---

## 20. Estratégia 7: caracterização detalhada dos erros

Antes da escolha definitiva do modelo intraplanta, os erros serão
avaliados em diferentes condições.

Entre as análises previstas estão:

- erro por mês;
- erro por ano;
- erro por faixa de carga;
- erro em baixa carga;
- erro em carga intermediária;
- erro em alta carga;
- erro após startups;
- erro em rampas;
- distribuição dos resíduos;
- presença de viés de superestimação ou subestimação;
- identificação das observações com maiores erros.

Também serão incorporadas métricas relativas ou normalizadas,
para que a magnitude do MAE possa ser interpretada em relação
à escala real das emissões.

---

## 21. Critério para encerramento da etapa intraplanta

A etapa de modelagem da Iatan somente será considerada
suficientemente consolidada quando for possível responder, com
evidência empírica, às seguintes perguntas:

1. O modelo melhora quando mais anos de dados são utilizados?

2. Qual quantidade de histórico é suficiente para estabilizar
   o desempenho?

3. O modelo mantém precisão em períodos futuros completamente
   não observados?

4. O desempenho é estável entre diferentes anos?

5. Existe drift relevante na relação entre carga e emissão?

6. A trajetória operacional continua apresentando baixo valor
   incremental quando a análise é ampliada?

7. Em quais condições operacionais o modelo apresenta seus
   maiores erros?

8. O modelo precisa ser atualizado periodicamente para manter
   desempenho satisfatório?

Somente depois dessas respostas será selecionado um
**modelo final intraplanta para a Iatan Unit 2**.

---

## 22. Etapa posterior: generalização entre unidades

A generalização para outras unidades termelétricas permanece como
objetivo posterior da pesquisa.

Entretanto, essa etapa somente será iniciada depois da
caracterização da generalização temporal dentro da própria Iatan.

A sequência metodológica passa a ser:

### Etapa A

Compreender e validar profundamente a previsão dentro da
Iatan Unit 2.

### Etapa B

Verificar se o modelo consegue prever períodos futuros da mesma
unidade.

### Etapa C

Avaliar estabilidade, drift e efeito do volume de dados.

### Etapa D

Definir o modelo intraplanta de referência.

### Etapa E

Somente então investigar transferência e generalização para
outras unidades e instalações.

Essa sequência evita confundir duas dificuldades distintas:

- generalização ao longo do tempo;
- generalização entre diferentes sistemas físicos.

A primeira deverá ser compreendida antes da segunda.

---

## 23. Próximo experimento

O próximo notebook deverá investigar prioritariamente o
**efeito do volume histórico de dados sobre o desempenho
preditivo da Iatan Unit 2**.

Nome previsto:

`03A.04_volume_dados_generalizacao_temporal_iatan.ipynb`

A pergunta central será:

> **A ampliação do histórico de treinamento melhora de forma
> consistente a capacidade de prever emissões futuras de CO₂ da
> Iatan Unit 2?**

Esse experimento iniciará a transição entre a avaliação realizada
em 2025 e uma análise efetiva de robustez temporal do modelo.
