# Auditoria de monitoramento histórico da Iatan Unit 2

Auditoria descritiva e reproduzível da unidade 2, Facility/ORIS 6065, entre 2011 e 2025. A análise documenta os métodos de monitoramento declarados, as vigências dos componentes, os indicadores horários de medição e substituição e a cobertura dos arquivos originais. Nenhuma amostra de modelagem, regra de seleção ou observação foi alterada.

## Resultados

Os quinze arquivos anuais contêm 131.496 registros e 98.799 horas ON. ON significa `Operating Time > 0`, incluindo operação em fração da hora e carga igual a zero. Todos os percentuais abaixo usam essas horas como denominador, antes dos filtros da amostra de modelagem. Os 2.208 registros de 2010 são anteriores à janela principal e não integram os totais.

| Período | Horas ON | Measured | Measured and Substitute | Substitute |
|---|---:|---:|---:|---:|
| 2011 a 2022 | 83.833 | 83.455 (99,549104%) | 288 (0,343540%) | 90 (0,107356%) |
| 2023 a 2024 | 8.717 | 8.597 (98,623380%) | 97 (1,112768%) | 23 (0,263852%) |
| 2025 | 6.249 | 6.209 (99,359898%) | 40 (0,640102%) | 0 (0%) |
| Total | 98.799 | 98.261 (99,455460%) | 425 (0,430166%) | 113 (0,114374%) |

Não foram encontradas horas de calendário ausentes, timestamps duplicados ou indicadores ausentes em ON. Todas as 32.697 horas OFF têm indicador ausente. Em 2019, uma hora ON tem carga ausente: 11/07/2019, hora 14. O script apenas registra essa ocorrência.

### Critério efetivamente usado em 2025

O notebook de seleção calcula `measured_share` com `str.contains("measured")`. A expressão inclui `Measured` e `Measured and Substitute`, resultando em 100% das horas ON de 2025. Esse critério expressa participação de medição no valor reportado. A categoria exata `Measured` representa 99,359898%. A seleção da unidade não foi refeita.

Os arquivos da seleção original e do multianual de 2025 coincidem nos oito campos comparados, incluindo operação, carga, massa de CO2 e indicador. São 8.760 linhas em cada arquivo, sem diferenças após normalização de identificadores e datas. A comparação não usa tolerância numérica.

### Método e instrumentação

O XML arquivado no projeto e a exportação JSON atual concordam nos 24 registros relevantes de CO2 e fluxo comparados. Ambos declaram `CO2/CEM` com rotina `SPTS`, desde 01/10/2010, hora 0, até término aberto. As vigências cobrem 100% das horas de calendário de 2011 a 2025 e todas as horas ON. A fórmula declarada é `F-11`, ID 203, desde o mesmo início.

O ZIP original foi comparado com um novo download da [URL oficial da EPA](https://api.epa.gov/easey/bulk-files/xml/mp/006065_MP.zip). Ambos têm 8.517 bytes e SHA-256 `921b6607e66a1ce75457a282899e2f5c877daa754a6c4ebcf0e8f8a967707ba8`. O membro da unidade 2 é `6065_2_20260126_2010Q4_MP.xml`. A exportação JSON informa `updateDate = 2026-01-26T20:07:00.000Z`. São dois snapshots posteriores com vigências históricas, não quinze versões anuais preservadas no momento de cada operação.

| Primeira hora declarada da nova associação | Sistemas | Mudança documentada |
|---|---|---|
| 28/08/2017, 10h | CO2 e FLOW | DL 224, ESC 8832, para DL 225, ESC 8864 |
| 04/01/2018, 15h | CO2 e FLOW | DAHS 230 para DAHS 235, ambos ESC STACKVISION |
| 18/09/2024, 10h | CO2 | Analisador 222, TECO 410I, para 422, TELEDYNE T360 |
| 18/09/2024, 10h | CO2 | Sonda 229, M&C SP2000H, para 234, M&C SP2006 |

As associações anteriores terminam na hora imediatamente anterior. Nas 210 combinações fonte/ano/sistema/tipo de componente, não há hora sem associação declarada nem sobreposição de IDs distintos do mesmo tipo. Essa continuidade documental não demonstra homogeneidade instrumental, estabilidade de calibração ou precisão constante. A auditoria não estima o efeito das trocas sobre a série nem atribui a elas mudanças de desempenho dos modelos.

## Execução

Ambiente validado: Python 3.12.14, pandas 2.2.3, NumPy 2.3.5 e PyArrow 26.0.0. A coleta usa apenas a biblioteca padrão do Python. A partir de `reproducibility/monitoring`:

```bash
python -m pip install -r requirements.txt
python fetch_sources.py --offline
python audit_monitoring.py \
  --hourly-dir ../../data/interim/03A04_multiyear \
  --selection-file ../../pipeline/selected_unit_hourly_raw.parquet
python validation_checks.py \
  --hourly-dir ../../data/interim/03A04_multiyear
```

Os argumentos acima também são os caminhos padrão, resolvidos a partir da localização do script. Quando os arquivos estiverem em outra pasta, forneça os caminhos reais por esses argumentos. Os arquivos anuais devem ter o nome `iatan_unit2_YYYY.parquet`. Há suporte a CSV se o Parquet correspondente não existir. A presença de ambos provoca erro para impedir escolha silenciosa de versão.

O script abre as entradas somente para leitura e verifica seus hashes antes e depois. Os caminhos dos manifestos são nomes lógicos relativos ao repositório. Uma execução pode usar outra cópia dos mesmos arquivos por argumento explícito. A validação integrada utilizou cópias locais dos arquivos originais preservados, com os mesmos hashes, sem modificar os insumos. Os resultados e o log dessa execução estão em `outputs`.

Há seis testes focados: separação exata de rótulos; limites horários inclusivos; detecção de lacuna e duplicata em ano bissexto; equivalência dos extratos XML/JSON; contagens de 2025; ausência de chaves administrativas nos JSONs públicos. A extração também foi comparada com os dois planos integrais, preservando os 24 registros relevantes de cada um, conforme `outputs/extract_verification.json`.

## Fontes públicas e rastreabilidade

As respostas integrais dos planos incluem identificadores administrativos e comentários livres sem utilidade para esta auditoria. O repositório contém extratos técnicos mínimos, gerados por `source_extracts.py`. O código retém somente a unidade estudada, métodos e fórmulas CO2, sistemas CO2/FLOW, os componentes associados, vigências e faixas. São omitidos identificadores de usuários, campos de contato, comentários livres e registros alheios ao escopo. Nenhum valor horário de emissão é alterado por essa extração.

`sources/source_provenance.json` registra URLs oficiais, hashes das respostas integrais e hashes dos extratos. `sources/original_zip_verification.json` documenta a igualdade de bytes entre o ZIP original e o download oficial. Os integrais permanecem na coleção original do projeto, fora deste diretório público. Os extratos podem ser reconstruídos das fontes oficiais, sujeitos às atualizações posteriores da EPA.

| Fonte | Endpoint oficial |
|---|---|
| Configuração da unidade | `https://api.epa.gov/easey/monitor-plan-mgmt/configurations?orisCodes=6065` |
| Exportação do plano | `https://api.epa.gov/easey/monitor-plan-mgmt/plans/export?planId=DWH3021DNT-5A975BAEEA3B4DE698FA731B4AE3347A` |
| Catálogo do ZIP | `https://api.epa.gov/easey/camd-services/bulk-files` |
| ZIP de monitoramento | `https://api.epa.gov/easey/bulk-files/xml/mp/006065_MP.zip` |
| Lista das tabelas de códigos | `https://api.epa.gov/easey/master-data-mgmt/list` |
| Definições dos campos horários | `https://api.epa.gov/easey/emissions-mgmt/swagger-json` |

As seis tabelas de códigos utilizadas são `method-codes`, `substitute-data-codes`, `component-type-codes`, `system-type-codes`, `acquisition-method-codes` e `parameter-codes`, sob `https://api.epa.gov/easey/master-data-mgmt/`. Elas confirmam `CEM = Continuous Emission Monitor`, `SPTS = Standard Part 75 for Missing Data`, tipo de sistema `CO2 = CO2 Concentration` e `FLOW = Stack Flow`.

O plano identifica a localização 6078 e `unitRecordId` 2732. O catálogo informa o caminho `xml/mp/006065_MP.zip`. O tamanho de 106.438 bytes registrado no catálogo corresponde à soma dos dois membros XML descompactados; o ZIP recebido tem 8.517 bytes. Essa diferença de representação não foi tratada como divergência do conteúdo.

Para uma coleta nova em outro diretório, com a chave pública de demonstração:

```bash
python fetch_sources.py --source-dir /caminho/novo --demo-key
```

O coletor faz somente requisições GET, preserva arquivos existentes e registra hashes das respostas antes da extração. A chave segue apenas no cabeçalho. Não há busca de credenciais em arquivos nem gravação delas em logs ou URLs. Uma chave fornecida legitimamente pode ser indicada por `--api-key-env NOME_DA_VARIAVEL`. O programa para no primeiro erro HTTP, inclusive 401, 403 e 429, sem repetição automática. Seu orçamento padrão é 16 requisições. A [documentação de api.data.gov](https://api.data.gov/docs/developer-manual/) limita a chave pública a 30 requisições por IP por hora e 50 por dia; o script não coordena esse limite com outras aplicações.

### Manual e localizadores

Fonte: [EPA, ECMPS Monitoring Plan Reporting Instructions, 20/12/2024](https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf). O PDF completo e os trechos de páginas verificados estão em `sources`.

| Tema | Seção | Página impressa | Página do PDF, capa = 1 |
|---|---|---:|---:|
| Início da vigência do método | 6.0 | 32 | 37 |
| Última data e hora de vigência do método | 6.0 | 33 | 38 |
| Vigência da associação componente/sistema | 8.2 | 61 | 66 |
| Fórmula F-11 | 9.0, Tabela 43 | 80 | 85 |

`EndDate/EndHour` designam a última hora e são inclusivos. Término ausente indica registro ativo. A fórmula F-11 combina concentração de CO2 e vazão volumétrica em base úmida para determinar taxa de emissão de massa. O alvo estatístico continua sendo o campo original `CO2 Mass (short tons)`; a auditoria não o recalcula.

## Saídas

| Arquivo em `outputs` | Conteúdo |
|---|---|
| `audit_report.md`, `audit_summary.json` | Relatório e resumo verificável por máquina |
| `annual_measurement_summary.csv` | Cobertura, ON/OFF, rótulos e campos ausentes por ano |
| `monthly_measurement_summary.csv` | Indicadores por mês |
| `cohort_measurement_summary.csv` | Indicadores por coorte e no total |
| `indicator_raw_counts.csv` | Rótulos literais e contagens ON/OFF |
| `monitoring_plan_coverage.csv` | Cobertura CO2/CEM por fonte e ano |
| `component_coverage.csv` | Cobertura e sobreposições das associações |
| `co2_flow_component_history.csv` | Histórico das associações CO2/FLOW |
| `co2_flow_component_changes.csv` | Associações iniciadas de 2011 a 2025 |
| `plan_*_history.csv` | Métodos, fórmulas, sistemas, componentes, faixas e associações |
| `snapshot_comparison.csv` | Equivalência dos campos especificados |
| `selection_2025_annual_comparison.json` | Correspondência dos dois arquivos originais de 2025 |
| `substitution_episodes.csv` | Horas contíguas ON com rótulo misto ou Substitute |
| `calendar_gap_episodes.csv` | Lacunas de calendário, nenhuma nesta execução |
| `input_manifest.json`, `sources_manifest.json` | Nomes, tamanhos e hashes SHA-256 |
| `verification_run.json`, `extract_verification.json` | Logs e verificação da preservação dos campos |

As massas somadas em horas com rótulo misto são massas associadas a essas horas, não estimativas da massa efetivamente substituída. O indicador agregado não revela a fração intrahorária substituída. `Measured` não significa medição direta de massa por um único sensor nem ausência de incerteza. Não foram reprocessados registros de calibração, certificação, testes de precisão ou medições brutas sub-horárias. A constância do método declarado e a completude do calendário não eliminam essas limitações.
