# Experimentos de Iatan 2 com mineração de processos

## Base e representação operacional

| Notebook | Papel |
|---|---|
| [00 · Preparação do ambiente de 2025](00_PREPARAR_IATAN_2025.ipynb) | Confere os insumos preservados e prepara a raiz de execução. |
| [01 · Seleção da unidade](01_selecao_unidade.ipynb) | Refaz a aquisição de dados da EPA quando necessário. |
| [02 · Tratamento dos dados](02_tratamento_dados.ipynb) | Organiza o calendário horário, as variáveis e os cortes. |
| [03 · Processos operacionais](03_processos_operacionais.ipynb) | Infere estados com HMM e constrói o log e o DFG. |
| [04 · Estudo temporal](04_estudo_temporal.ipynb) | Estuda dependências da série e organiza os atributos temporais. |

## Avaliação

- [05 · Modelagem de CO₂ e Exp33](05_modelagem_co2_mlflow.ipynb). Compara geração, histórico e representação do processo em 2025.
- [06 · Validação multianual](06_validacao_multianual_iatan.ipynb). Compara cadências de reajuste e executa as ablações em janelas cronológicas.
- [Teste em período reservado](../../iatan/phase5_operational_holdout.py) e [comparação descritiva entre usinas](../../scripts/phase5_multiusinas). São executados pelos respectivos módulos e scripts.

## Reprodução

1. **Fluxo de 2025 com insumos preservados.** No ambiente da entrega revisada, execute 00 → 02 → 03 → 04 → 05. Use o 01 para refazer a aquisição. O notebook 00 lista os arquivos de entrada e os caminhos de execução.
2. **Exp33 isolado.** Instale as [dependências](../../requirements-iatan.txt), defina `IATAN_PROJECT_ROOT` para a raiz da cópia do repositório e execute as três células da seção Exp33 do 05. O [Parquet de 2025](../../pipeline/selected_unit_hourly_raw.parquet) está no repositório.
3. **Validação multianual.** Na raiz do projeto, coloque os 15 Parquets anuais de 2011–2025 em `data/interim/03A04_multiyear/`. O [manifesto de insumos](../../configs/iatan_inputs.json) registra os hashes. O 06 executa os modos anual e trimestral. Para os modos de ablação e janela de treino, indique a rodada trimestral concluída conforme a seção de execução do notebook. A referência usou Python 3.12.
