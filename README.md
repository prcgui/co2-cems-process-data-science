# Iatan 2 · Ciclos operacionais e emissões horárias de CO₂

Estudo de caso com dados EPA CEMS/CAMPD de Iatan 2 (6065/2). O objetivo é estimar a massa de CO₂ da própria hora em operação, com a geração bruta dessa hora já observada.

## Percurso da pesquisa

| Etapa | Onde começar | Pergunta |
|---|---|---|
| 1. Referência inicial | [Notebooks sem mineração de processos](notebooks/01_sem_mineracao_de_processos) | Quanto da emissão é explicado pela geração e pelo histórico da unidade? |
| 2. Base e representação operacional | [Notebooks 00–04](notebooks/02_com_mineracao_de_processos#base-e-representação-operacional) | Como preparar a série e representar regimes e transições da unidade? |
| 3. Experimento de 2025 | [Notebook 05 · Exp33](notebooks/02_com_mineracao_de_processos/05_modelagem_co2_mlflow.ipynb) | O histórico, os estados do HMM e o grafo de transições acrescentam informação? |
| 4. Validação multianual | [Notebook 06](notebooks/02_com_mineracao_de_processos/06_validacao_multianual_iatan.ipynb) | Os ganhos se repetem em janelas cronológicas e no período reservado? |
| 5. Contexto operacional | [Comparação descritiva entre usinas](scripts/phase5_multiusinas) | Como a operação de Iatan 2 se situa em relação às demais unidades e ao calendário regional? |

O HMM (modelo oculto de Markov) infere regimes a partir da série de geração. O DFG (grafo de sucessão direta) representa transições entre atividades consecutivas no log.

## Resultados principais

| Comparação | Resultado |
|---|---|
| Exp33 em 2025 | A geração corrente obteve RMSE de **20,25 t CO₂/h** no teste retrospectivo de 1.063 horas ON. |
| Janelas de 2023 a 2025 | Nas mesmas 14.966 horas ON, o RMSE da referência A passou de **57,65** no controle anual a **53,94 t CO₂/h** com reajuste trimestral. O acréscimo do DFG teve diferença de **+0,02 t CO₂/h** (IC de 95% de −0,15 a +0,22). |
| Período reservado de 2026 | Nas 2.070 horas ON do primeiro semestre, A teve RMSE de **22,89** e RH (rampa, religamento e HMM) de **22,00 t CO₂/h**. O intervalo da diferença (−1,95 a +0,02) inclui zero. A segue como referência e RH fica como candidato. |
| Sazonalidade | Em 2019–2025, agosto teve mais demanda, menos geração eólica no SPP e mais horas ON em Iatan 2 que outubro nos sete anos. O contraste em horas ON também aparece em 9 de 12 anos após retirar pares com parada de outubro documentada no histórico de 2011–2025. |

A validação do estimador se refere a Iatan 2. A comparação das 20 instalações é descritiva. [EIA-930](https://www.eia.gov/electricity/930-content/about.html) · [Validação temporal, FPP3 § 5.10](https://otexts.com/fpp3/toolbox.html#time-series-cross-validation)

## Reprodução e entrega

- [Ordem de execução e insumos dos notebooks](notebooks/02_com_mineracao_de_processos#reprodução). As [dependências da validação](requirements-iatan.txt), os [protocolos e manifestos](configs) e a [implementação Python](iatan) estão versionados.
- [Plano do experimento e log de resultados da Etapa 2](entregas/IND2622_Plano_do_experimento_e_pre_processamento.xlsx).
