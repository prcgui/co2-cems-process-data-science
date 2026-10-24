# Reprodução dos notebooks 03A.04 e 03A.05

Este guia documenta a execução integral e a verificação dos experimentos de histórico de treinamento e de trajetória operacional da Iatan Unit 2, Facility ID 6065. O escopo de reprodução abrange somente os notebooks 03A.04 e 03A.05. Os dados anuais preservados, os parâmetros científicos e as partições temporais foram mantidos.

## Resultado da verificação

A execução registrada em [execution_summary.json](../outputs/reproducibility/execution_summary.json) completou os dois notebooks, em kernels separados, sem erros. Os 16 arquivos anuais de entrada mantiveram seus hashes. Os sete CSVs selecionados como referências históricas foram reproduzidos **byte a byte**, conforme [reference_comparison.json](../outputs/reproducibility/reference_comparison.json).

A [verificação independente dos artefatos](../outputs/reproducibility/independent_validation.json) também comparou três Parquets de previsões e seis de amostras com as cópias originais preservadas no Drive. Após alinhamento unívoco por `timestamp`, os nove arquivos apresentaram igualdade exata dos valores, dos tipos de dados, da ordem das colunas e dos timestamps. Não foi necessária tolerância numérica. Os arquivos Parquet têm bytes diferentes dos originais, apesar da igualdade dos dados; identidade binária não é afirmada para esses nove arquivos.

| Artefato de 03A.05 | Registros | Comparação com o original preservado |
|---|---:|---|
| Previsões de validação de outubro de 2025 | 211 | Valores e tipos idênticos |
| Previsões pareadas de novembro e dezembro de 2025 | 1.144 | Valores e tipos idênticos |
| Previsões pareadas com contextos operacionais | 1.144 | Valores e tipos idênticos |
| Base com atributos de trajetória | 113.952 | Valores e tipos idênticos |
| Amostra comum aos cenários A e B | 89.830 | Valores e tipos idênticos |
| Treino para seleção da complexidade | 88.475 | Valores e tipos idênticos |
| Amostra de validação de outubro | 211 | Valores e tipos idênticos |
| Treino final | 88.686 | Valores e tipos idênticos |
| Amostra de teste de novembro e dezembro | 1.144 | Valores e tipos idênticos |

Todos esses arquivos têm zero timestamps duplicados e zero timestamps nulos. A elegibilidade operacional e os períodos selecionados explicam por que as amostras de modelagem contêm menos observações que o calendário completo.

## Correções de execução e integridade

O carregamento de 03A.04 passou a enumerar exclusivamente os 16 nomes anuais esperados, de `iatan_unit2_2010.parquet` a `iatan_unit2_2025.parquet`. O arquivo consolidado não entra nessa lista. O carregamento anterior por padrão de nomes também podia incluir o consolidado, duplicando a série quando o notebook era executado novamente.

O consolidado preservado no Drive tinha **267.408 linhas e 133.704 timestamps duplicados**. A reconstrução a partir dos anuais produziu **133.704 registros únicos**, com todas as horas de 1º de outubro de 2010 a 31 de dezembro de 2025. Nenhuma deduplicação silenciosa é aplicada: as verificações rejeitam anuais inconsistentes e duplicatas.

As verificações exigem a unidade correta, identificadores presentes, coerência entre `Date`, `Hour` e `timestamp`, ano correto e calendário completo do período esperado. No arquivo de 2010, o período esperado começa em outubro. O reaproveitamento offline somente ocorre depois da validação dos anuais disponíveis.

Também foram corrigidos o prefixo sintaticamente inválido da primeira célula de 03A.05 e a duplicação de uma célula de relatório de 03A.04. Os caminhos podem ser definidos por `CO2_PROJECT_ROOT`; o acesso ao Colab e a aquisição online permanecem disponíveis nos notebooks. A redação sobre a escolha do histórico foi corrigida para registrar que a delimitação de 2011 a 2022 foi exploratória e consolidada após os backtests, incluindo avaliação em 2025.

Essas alterações preservam os atributos, o alvo, os hiperparâmetros, a semente, a seleção de árvores e as partições dos experimentos. A verificação de código registrada no relatório independente compara as células científicas com o commit de referência do próprio repositório.

## Insumos necessários

Disponibilize os seguintes arquivos na raiz do projeto:

- `pipeline/selected_unit.json`, identificando Facility ID 6065 e Unit ID 2;
- os 16 anuais `data/interim/03A04_multiyear/iatan_unit2_ANO.parquet`, com `ANO` de 2010 a 2025.

Os anuais totalizam 133.704 registros. Seus nomes, tamanhos, esquemas e hashes estão em [input_manifest.json](../outputs/reproducibility/input_manifest.json). Os dados brutos e intermediários permanecem fora do versionamento, conforme o `.gitignore`. O consolidado e os Parquets de 03A.05 são reconstruídos pela execução.

O runner exige todos os insumos antes de iniciar. Nesta reprodução, os anuais foram reutilizados offline; não houve nova coleta de toda a série na EPA. Se faltarem anuais, a aquisição pode ser feita pelo notebook 03A.04, que requer `EPA_API_KEY` no ambiente ou nos segredos do Colab. Um download posterior pode refletir revisões da fonte e deve ser confrontado com o manifesto antes de ser tratado como o mesmo insumo.

## Ambiente e execução

O ambiente verificado usa **Python 3.12.14**, Linux, XGBoost 3.4.1, NumPy 2.3.5, pandas 2.2.3 e scikit-learn 1.8.0. As versões completas estão em [requirements-reproduction.lock](../requirements-reproduction.lock) e a configuração efetiva da execução está em [environment.json](../outputs/reproducibility/environment.json). O lock descreve esta reprodução; não reconstrói o ambiente original do Colab.

Na raiz do repositório, utilizando Python 3.12.14:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-reproduction.lock
python -m pip check
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python scripts/reproduce_history.py
```

O runner determina a raiz pelo próprio caminho. Para indicar outra localização explicitamente:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 python scripts/reproduce_history.py --root /caminho/co2-cems-process-data-science
```

As quatro variáveis de ambiente controlam as bibliotecas de paralelismo para evitar contenção de recursos em execuções simultâneas. Seus valores efetivos e a afinidade de CPU são registrados em `environment.json`. O parâmetro `n_jobs=-1` dos notebooks permanece preservado. As durações registradas descrevem esta execução e não constituem um benchmark de desempenho.

Para executar os notebooks diretamente fora do Colab, defina `CO2_PROJECT_ROOT` com a raiz do projeto. No Colab, a ausência dessa variável mantém a montagem do Drive e o diretório padrão `MyDrive/co2-cems-process-data-science`.

O runner limpa as saídas em memória, executa cada notebook do início ao fim e somente substitui a versão salva após a execução integral daquele notebook. Em caso de erro, salva uma cópia diagnóstica com sufixo `.failed.ipynb`, ignorada pelo Git, e interrompe o procedimento. O executor precisa permitir a comunicação local entre o cliente Jupyter e seu kernel.

Os metadados de usuário e de sessão herdados do Colab são removidos antes da execução: `colab` e `reproduction` no nível do notebook, e `executionInfo`, `colab`, `outputId` e `execution` no nível das células. Os registros `execution` e `reproduction` são então gerados novamente. Os registros salvos correspondem ao novo processamento, com código e resultados científicos preservados.

## Referências e evidências

As referências pertencem a este repositório e são preservadas em [baselines](baselines). Os três CSVs de 03A.04 provêm do [commit histórico sem duplicação](https://github.com/prcgui/co2-cems-process-data-science/commit/0fa317271ec2cd08d66e0d9e2723c01008667412), e os quatro de 03A.05 do [commit da comparação final](https://github.com/prcgui/co2-cems-process-data-science/commit/8f23aa9488cdab980d2dcd875e720c15242f4845).

| Etapa | CSVs de referência |
|---|---|
| 03A.04 | `03A04_comparacao_2025_vs_historico_2025.csv`, `03A04_ganho_incremental_historico_2011_2022.csv`, `03A04_sintese_evidencias_historico.csv` |
| 03A.05 | `03A05_comparacao_contextos_operacionais.csv`, `03A05_delimitacao_amostras_experimento.csv`, `03A05_resultado_final_A_B.csv`, `03A05_selecao_complexidade_A_B.csv` |

Esses commits documentam os resultados históricos. A execução integral registrada nesta reprodução utiliza os notebooks corrigidos presentes na árvore de trabalho. Os hashes do runner, dos códigos e dos notebooks executados vinculam as evidências à execução efetiva.

O comparador numérico do runner aceita tolerância absoluta de `1e-6` e relativa de `1e-8`. Nesta execução, o resultado foi mais estrito: os sete arquivos CSV têm SHA256 idêntico e diferença numérica máxima igual a zero.

As evidências ficam em `outputs/reproducibility`:

- [execution_summary.json](../outputs/reproducibility/execution_summary.json): conclusão, horários, duração, quantidade de células e hashes de execução;
- [environment.json](../outputs/reproducibility/environment.json): Python, sistema e versões instaladas;
- [input_manifest.json](../outputs/reproducibility/input_manifest.json): identificação e integridade dos insumos;
- [output_manifest.json](../outputs/reproducibility/output_manifest.json): hashes dos artefatos produzidos;
- [reference_comparison.json](../outputs/reproducibility/reference_comparison.json): comparação dos sete CSVs;
- [independent_validation.json](../outputs/reproducibility/independent_validation.json): comparação exata dos nove Parquets com os originais preservados, integridade temporal, contagens e preservação do código científico.

## Auditoria do monitoramento histórico

O pacote [monitoring](monitoring/README.md) examina a cobertura temporal, os métodos declarados, os componentes e os indicadores horários de medição e substituição de 2011 a 2025. Ele contém fontes técnicas públicas, scripts, testes e relatórios próprios. Essa auditoria descritiva complementa a reprodução dos modelos e preserva as amostras e as regras de seleção.

## Limites da evidência

A reprodução demonstra que os resultados históricos podem ser recuperados com os anuais preservados e o ambiente documentado. Ela não constitui uma nova amostra independente da EPA nem comprova a qualidade metrológica de cada registro.

Os resultados se referem a uma única unidade. A seleção de 2011 a 2022 foi exploratória, e novembro e dezembro de 2025 já tinham sido examinados durante o desenvolvimento. A reprodução não elimina o risco de otimismo associado a essas decisões nem transforma o período de comparação em teste cego.

As comparações A/B e por contexto são descritivas, sem teste formal de significância ou identificação causal. O alvo é a massa de CO₂ em short tons por registro horário. O modelo utiliza a carga da própria hora; sua avaliação corresponde à estimação condicionada a essa informação. As amostras de 03A.04 e 03A.05 têm critérios de elegibilidade diferentes e seus resultados não devem ser interpretados como uma única comparação pareada entre etapas.
