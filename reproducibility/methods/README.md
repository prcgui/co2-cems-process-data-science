# Verificação da aplicação dos métodos

As técnicas citadas foram confrontadas com suas formulações originais, as funções reais dos notebooks e os artefatos preservados do estudo da Iatan Unit 2. Os resultados abaixo decorrem de verificações executadas em 24 de outubro de 2026. As fontes e suas localizações específicas constam dos registros de cada grupo.

## Parecer

IQR, PCA exploratória, MinMaxScaler, retropropagação, ReLU, Adam, XGBoost, busca aleatória pareada e métricas foram aplicados corretamente nas condições verificadas. O uso das bibliotecas foi examinado por cálculos independentes e por modelos salvos. A separação de datas também está correta dentro de cada ajuste.

Foi corrigido um defeito na borda final das faixas de carga usadas em um diagnóstico descritivo. Em faixas abertas à direita, a última borda deve ser estritamente maior que o máximo. O código corrigido preserva 60 de 60 observações em um caso limite no qual a formulação anterior preservava 40. No conjunto do estudo, o máximo é 957 MW e ambas as formulações produzem a mesma borda de 1.000 MW; nenhuma tabela numérica, figura ou conclusão do artigo muda.

A independência global do teste é uma questão separada da correção dos cálculos. Novembro e dezembro de 2025 ficaram fora do ajuste de cada modelo, mas foram consultados no desenvolvimento. O estudo permanece exploratório. A revisão retirou afirmações de teste intocado ou verdadeiramente independente, de suficiência demonstrada de 30 candidatos e de isolamento exclusivo do efeito da família de algoritmo ou do volume histórico.

## Evidências executadas

| Grupo | Verificação | Resultado |
|---|---|---|
| Redes neurais | Três modelos originais, 8.579 gradientes, 243 coordenadas por diferenças finitas, ReLU e propagação independente | Maior diferença nos gradientes: 3,37 × 10⁻⁸; nas previsões normalizadas: 2,72 × 10⁻⁸. |
| Adam e parada | Momentos e três atualizações; funções reais de treinamento em casos controlados | Atualizações diferiram no máximo 8,26 × 10⁻⁸; parada e restauração conferiram. O epsilon-hat do Keras corresponde à forma eficiente de Kingma e Ba. |
| Boosting | Pesos de folhas pela fórmula de Chen, soma aditiva, objetivo quadrático, regularização e melhor iteração | Operações conferidas; os modelos B/C preservados reproduziram as previsões com diferença inferior a 0,000031 short ton. |
| Busca e calendário | Candidatos, ranking, 300 combinações, cinco folds e 25 divisões anuais | Candidatos e seleção conferiram. A amostra final tem 88.475/211/88.686/1.144 linhas em seleção/validação/reajuste/teste. |
| Estatística e métricas | Quartis e cercas, eigendecomposição independente da correlação, escalas A/B/C, métricas e sinais | Seis blocos de verificação concluídos; inversa antes das métricas; PCA não alimenta os preditores. |
| Diagnósticos e EPA | Faixas de carga, 15 distâncias anuais, contraexemplo de mudança de composição, intervalos inclusivos | Borda corrigida sem efeito no recorte; diagnósticos não provam mudança condicional; última hora ativa incluída. |

As pequenas diferenças acima comparam implementações ou serializações. Não são erros de previsão do estudo. Os limites e tolerâncias de cada comparação estão nos JSONs.

## Resultados e correções

- [Redes neurais e otimizador](../../outputs/reproducibility/methods/nn_verification.json).
- [Boosting, busca e avaliação temporal](../../outputs/reproducibility/methods/boosting_validation.json).
- [Estatística, métricas e monitoramento](../../outputs/reproducibility/methods/statistics_verification.json).
- [Registro das correções aplicadas](../../outputs/reproducibility/methods/corrections_manifest.json).
- [Fundamentação e papel de cada fonte](../../docs/fundamentacao_metodologica.md).

Os registros de redes e boosting identificam o snapshot conferido antes das correções de texto. A validação de conteúdo registra que seus cálculos e parâmetros foram preservados. A verificação estatística pública também foi executada sobre a versão com a borda corrigida. A proveniência do treinamento original e a [reprodução integral anterior de 03A.04 e 03A.05](../README.md) permanecem preservadas.

## Repetição

Use Python 3.12 em um ambiente próprio para verificação. Os scripts não regravam modelos, notebooks ou tabelas de entrada. A instalação pode ser feita com:

```bash
python -m pip install -r reproducibility/methods/requirements.txt
```

### Estatística, métricas e EPA

Este verificador usa apenas os notebooks, as tabelas e o script de monitoramento já presentes no repositório:

```bash
python reproducibility/methods/statistics_verification.py \
  --repo . \
  --output outputs/reproducibility/methods/statistics_verification_new.json
```

O manifesto é opcional. O caso antigo de perda na borda é demonstrado em um exemplo isolado, e a rotina atual é testada separadamente. Consulte `--help` para indicar outra cópia dos notebooks.

### Redes neurais

Indique o diretório que contém `03A_mlp_cenario_A.keras`, `03A_mlp_cenario_B.keras` e `03A01_mlp_cenario_C.keras`, preservados no pacote do experimento:

```bash
python reproducibility/methods/nn_verification.py \
  --notebooks notebooks \
  --models /caminho/dos/modelos \
  --output outputs/reproducibility/methods/nn_verification_new.json
```

O teste carrega os pesos originais, confronta gradientes e previsões e executa pequenos exemplos controlados de treinamento. Não repete integralmente o treinamento dos três modelos de Iatan.

### Boosting e avaliação temporal

O pacote preservado deve manter os diretórios `projeto/` e `originais_preservados/`, contendo os Parquets anuais, os dados de 2025 e os modelos B/C de 03A.02:

```bash
python reproducibility/methods/verify_boosting_validation.py \
  --repo . \
  --zip /caminho/Pacote_Reproducao_CO2_2026-10-24.zip \
  --output outputs/reproducibility/methods/boosting_validation_new.json
```

O verificador treina seis modelos sintéticos pequenos e carrega dois modelos preservados para inferência. Os 300 ajustes da busca e os 25 backtests são conferidos pelos candidatos, dados, cortes e resultados preservados. Os arquivos volumosos permanecem no pacote do projeto; um clone do código, sozinho, não contém todos os insumos dos testes de redes e boosting.

## Limites de interpretação

Os testes confirmam as correspondências examinadas e as condições registradas. A escolha de arquitetura, limiares, janelas, número de candidatos e atributos pertence ao estudo. Os artigos sobre emissões usados como trabalhos relacionados contextualizam a investigação; o guia de fundamentação identifica separadamente as fontes das técnicas implementadas. A comparação na própria Iatan não estabelece causalidade, transferência entre usinas ou independência confirmatória do período já consultado.
