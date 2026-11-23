# Experimentos de Iatan 2 com mineração de processos

## Base e representação operacional

| Notebook | Papel |
|---|---|
| [00 · Preparação do Colab](00_PREPARAR_IATAN_2025.ipynb) | Sincroniza o código publicado, confere os insumos e prepara a raiz comum de execução. |
| [01 · Seleção da unidade](01_selecao_unidade.ipynb) | Refaz a aquisição de dados da EPA quando necessário. |
| [02 · Tratamento dos dados](02_tratamento_dados.ipynb) | Organiza o calendário horário, as variáveis e os cortes. |
| [03 · Processos operacionais](03_processos_operacionais.ipynb) | Infere estados com HMM e constrói o log e o DFG. |
| [04 · Estudo temporal](04_estudo_temporal.ipynb) | Estuda dependências da série e organiza os atributos temporais. |

## Avaliação

- [05 · Modelagem de CO₂ e Exp33](05_modelagem_co2_mlflow.ipynb). Compara geração, histórico e representação do processo em 2025.
- [06 · Validação multianual](06_validacao_multianual_iatan.ipynb). Compara cadências de reajuste e executa as ablações em janelas cronológicas.
- [07 · Mudanças de intensidade carbônica](07_mudancas_intensidade_carbonica.ipynb). Concilia potência horária e energia com o agregado anual da EPA, identifica cortes de 2025 e estima em 2017 o fator histórico.
- [08 · Avaliação retrospectiva](08_avaliacao_correcao_carbonica.ipynb). Aplica o fator do 07 às previsões anuais A–D do 06 e calcula RMSE, MAE, viés e intervalos condicionais nas mesmas horas.
- [Teste em período reservado](../../iatan/phase5_operational_holdout.py) e [comparação descritiva entre usinas](../../scripts/phase5_multiusinas). São executados pelos respectivos módulos e scripts.

## Reprodução

1. **Preparação.** No Colab, execute 00 para conferir o código, as [dependências](../../requirements-iatan.txt) e os insumos. O pacote offline `Iatan_codigo_atual.zip` identifica o commit publicado. Os notebooks 05 e 06 também preparam uma sessão nova; as variáveis de outra sessão não são necessárias. Fora do Colab, use a raiz do repositório ou `IATAN_PROJECT_ROOT`.
2. **Fluxo de 2025.** Com os insumos preservados, siga 02 → 03 → 04 → 05; use 01 somente para refazer a aquisição. O 05 reconhece uma única execução válida de cada fase. Se houver várias, solicita os identificadores sem escolher pela data. Para Exp33 isolado, execute apenas as três células desse bloco no 05. O [Parquet de 2025](../../pipeline/selected_unit_hourly_raw.parquet) acompanha o código.
3. **Validação multianual.** O 06 usa os 15 Parquets de 2011–2025 em `data/interim/03A04_multiyear/`, conferidos pelo [manifesto](../../configs/iatan_inputs.json); não exige refazer 01–05. A preparação do 00 ou do próprio 06 reutiliza arquivos válidos, recupera os ausentes do pacote local e, se necessário, baixa automaticamente a [cópia preservada dos insumos](https://github.com/prcgui/co2-cems-process-data-science/releases/tag/insumos-iatan2-2011-2025-v1), sem chave da EPA. Confere o pacote e os arquivos antes de instalar e mantém o ZIP no Drive para reutilização. Arquivos existentes divergentes são preservados e informados para conferência. Para as ablações e a comparação de treinos, indique uma rodada trimestral concluída ou use a única referência válida identificada. Cada execução cria sua pasta em `outputs/`; os resultados anteriores são preservados. A referência usou Python 3.12; outra versão é registrada como execução em seu ambiente real.
4. **Intensidade e correção de 2025.** Após o 00, execute o 07 inteiro e depois o 08. O 08 lê as datas e o fator de precisão integral que o 07 gravou em `outputs/07_intensidade_carbonica/` e, por padrão, usa as [previsões anuais preservadas do 06](../../reproducibility/iatan/06_anual_2025). Para usar outra execução anual completa do 06, defina `IATAN_RUN06_ANUAL` com o nome de sua pasta. O 08 avalia as quatro previsões nas mesmas horas e registra a rodada no MLflow.
