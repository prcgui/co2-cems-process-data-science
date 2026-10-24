# Auditoria de monitoramento histórico: Iatan Unit 2

## Escopo e procedimento

Auditoria descritiva dos arquivos anuais originais e das vigências registradas nos planos de monitoramento. Nenhuma amostra experimental, arquivo de entrada ou seleção de unidade foi alterada.

As fontes públicas no repositório são extratos técnicos dos planos, com omissão de identificadores administrativos, campos de contato e comentários livres. Os hashes das respostas integrais, as URLs oficiais e os campos de extração constam de sources/source_provenance.json e source_extracts.py.

Foram auditados 131496 registros, dos quais 98799 são horas ON. Os arquivos de 2010, período anterior à janela principal, não integram estes totais.

ON corresponde a Operating Time > 0. Os percentuais de indicadores usam todas as horas ON como denominador, incluindo eventuais rótulos ausentes. 'Measured' e 'Measured and Substitute' são categorias separadas.

BeginDate/BeginHour incluem a primeira hora de vigência; EndDate/EndHour incluem a última hora. Um término nulo significa registro ainda ativo. Os registros encerrados permanecem na auditoria histórica. Não se aplica ajuste de horário de verão às horas locais reportadas.

## Evidência dos planos

- current_plan_unit2: CO2 / CEM, substituição SPTS, início 2010-10-01T00:00:00, término aberto.
- original_plan_unit2: CO2 / CEM, substituição SPTS, início 2010-10-01T00:00:00, término aberto.

Cobertura CEM declarada em current_plan_unit2: 100.000000% a 100.000000% das horas de calendário por ano; 0 horas ON fora da vigência CEM.

Cobertura CEM declarada em original_plan_unit2: 100.000000% a 100.000000% das horas de calendário por ano; 0 horas ON fora da vigência CEM.

Fórmulas CO2 declaradas:

- original_plan_unit2: fórmula F-11, ID 203, início 2010-10-01T00:00:00, término aberto.
- current_plan_unit2: fórmula F-11, ID 203, início 2010-10-01T00:00:00, término aberto.

A fórmula F-11 combina concentração de CO2 e vazão volumétrica em base úmida para determinar a taxa de emissão de massa, conforme a Tabela 43 do manual ECMPS. O alvo estatístico continua sendo o campo original CO2 Mass (short tons); esta auditoria não reconstrói nem substitui esse alvo.

A constância do código de método não prova homogeneidade instrumental. As tabelas de sistemas, componentes, fórmulas e faixas preservam as alterações declaradas.

## Cobertura e indicadores por ano

| Ano | Registros | Horas ON | Measured puro (%) | Measured and Substitute (%) | Substitute (%) | Ausente em ON | Lacunas horárias |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2011 | 8760 | 7545 | 99.430086 | 0.490391 | 0.079523 | 0 | 0 |
| 2012 | 8784 | 8186 | 99.926704 | 0.061080 | 0.012216 | 0 | 0 |
| 2013 | 8760 | 7637 | 99.803588 | 0.196412 | 0.000000 | 0 | 0 |
| 2014 | 8760 | 5929 | 98.853095 | 0.961376 | 0.185529 | 0 | 0 |
| 2015 | 8760 | 7414 | 99.568384 | 0.269760 | 0.161856 | 0 | 0 |
| 2016 | 8784 | 6082 | 99.095692 | 0.624794 | 0.279513 | 0 | 0 |
| 2017 | 8760 | 8505 | 99.600235 | 0.376249 | 0.023516 | 0 | 0 |
| 2018 | 8760 | 5287 | 99.546056 | 0.132400 | 0.321543 | 0 | 0 |
| 2019 | 8760 | 7702 | 99.610491 | 0.324591 | 0.064918 | 0 | 0 |
| 2020 | 8784 | 6566 | 99.695401 | 0.152300 | 0.152300 | 0 | 0 |
| 2021 | 8760 | 6703 | 99.537521 | 0.328211 | 0.134268 | 0 | 0 |
| 2022 | 8760 | 6277 | 99.681376 | 0.318624 | 0.000000 | 0 | 0 |
| 2023 | 8760 | 4316 | 99.096386 | 0.741427 | 0.162187 | 0 | 0 |
| 2024 | 8784 | 4401 | 98.159509 | 1.476937 | 0.363554 | 0 | 0 |
| 2025 | 8760 | 6249 | 99.359898 | 0.640102 | 0.000000 | 0 | 0 |

## Esclarecimento do critério de seleção em 2025

O notebook original usa contains('measured'). Em 6249 horas ON, esse critério contabiliza 6249 horas (100.000000%).

A decomposição exata é: Measured = 6209 (99.359898%); Measured and Substitute = 40 (0.640102%); Substitute = 0 (0.000000%).

Portanto, o critério aplicado na seleção expressa participação de medição no valor reportado. Ele não demonstra que todas as horas sejam classificadas como integralmente medidas. Esta auditoria descreve o critério executado e não refaz a seleção.

O arquivo da etapa de seleção e o anual de 2025 contêm, respectivamente, 8760 e 8760 registros. Equivalência exata nos oito campos comparados, após normalização de identificadores e datas: True. Os hashes e os campos constam de selection_2025_annual_comparison.json.

## Alterações declaradas dos componentes CO2/FLOW

| Fonte | Sistema | Componente | Tipo | Fabricante / modelo | Início | Última hora |
|---|---|---|---|---|---|---|
| current_plan_unit2 | CO2 | 222 | CO2 | TECO / 410I | 2010-10-01T00:00:00 | 2024-09-18T09:00:00 |
| current_plan_unit2 | CO2 | 224 | DL | ESC / 8832 | 2010-10-01T00:00:00 | 2017-08-28T09:00:00 |
| current_plan_unit2 | CO2 | 229 | PRB | M&C / SP2000H | 2010-10-01T00:00:00 | 2024-09-18T09:00:00 |
| current_plan_unit2 | CO2 | 230 | DAHS | ESC / STACKVISION | 2010-10-01T00:00:00 | 2018-01-04T14:00:00 |
| current_plan_unit2 | CO2 | 225 | DL | ESC / 8864 | 2017-08-28T10:00:00 | aberto |
| current_plan_unit2 | CO2 | 235 | DAHS | ESC / STACKVISION | 2018-01-04T15:00:00 | aberto |
| current_plan_unit2 | CO2 | 234 | PRB | M&C / SP2006 | 2024-09-18T10:00:00 | aberto |
| current_plan_unit2 | CO2 | 422 | CO2 | TELEDYNE / T360 | 2024-09-18T10:00:00 | aberto |
| current_plan_unit2 | FLOW | 223 | FLOW | TELEDYNE INSTRUMENTS / ULTRAFLOW 150 | 2010-10-01T00:00:00 | aberto |
| current_plan_unit2 | FLOW | 224 | DL | ESC / 8832 | 2010-10-01T00:00:00 | 2017-08-28T09:00:00 |
| current_plan_unit2 | FLOW | 230 | DAHS | ESC / STACKVISION | 2010-10-01T00:00:00 | 2018-01-04T14:00:00 |
| current_plan_unit2 | FLOW | 225 | DL | ESC / 8864 | 2017-08-28T10:00:00 | aberto |
| current_plan_unit2 | FLOW | 235 | DAHS | ESC / STACKVISION | 2018-01-04T15:00:00 | aberto |
| original_plan_unit2 | CO2 | 222 | CO2 | TECO / 410I | 2010-10-01T00:00:00 | 2024-09-18T09:00:00 |
| original_plan_unit2 | CO2 | 224 | DL | ESC / 8832 | 2010-10-01T00:00:00 | 2017-08-28T09:00:00 |
| original_plan_unit2 | CO2 | 229 | PRB | M&C / SP2000H | 2010-10-01T00:00:00 | 2024-09-18T09:00:00 |
| original_plan_unit2 | CO2 | 230 | DAHS | ESC / STACKVISION | 2010-10-01T00:00:00 | 2018-01-04T14:00:00 |
| original_plan_unit2 | CO2 | 225 | DL | ESC / 8864 | 2017-08-28T10:00:00 | aberto |
| original_plan_unit2 | CO2 | 235 | DAHS | ESC / STACKVISION | 2018-01-04T15:00:00 | aberto |
| original_plan_unit2 | CO2 | 234 | PRB | M&C / SP2006 | 2024-09-18T10:00:00 | aberto |
| original_plan_unit2 | CO2 | 422 | CO2 | TELEDYNE / T360 | 2024-09-18T10:00:00 | aberto |
| original_plan_unit2 | FLOW | 223 | FLOW | TELEDYNE INSTRUMENTS / ULTRAFLOW 150 | 2010-10-01T00:00:00 | aberto |
| original_plan_unit2 | FLOW | 224 | DL | ESC / 8832 | 2010-10-01T00:00:00 | 2017-08-28T09:00:00 |
| original_plan_unit2 | FLOW | 230 | DAHS | ESC / STACKVISION | 2010-10-01T00:00:00 | 2018-01-04T14:00:00 |
| original_plan_unit2 | FLOW | 225 | DL | ESC / 8864 | 2017-08-28T10:00:00 | aberto |
| original_plan_unit2 | FLOW | 235 | DAHS | ESC / STACKVISION | 2018-01-04T15:00:00 | aberto |

Os 210 cruzamentos fonte/ano/sistema/tipo de componente apresentam 0 horas sem associação declarada e 0 horas com múltiplos IDs simultâneos do mesmo tipo. Essa continuidade documental não demonstra precisão constante nem estabilidade de calibração.

## Comparação entre fontes

- current_plan_unit2 versus original_plan_unit2: 24 registros comparáveis em comum; exclusivos A/B = 0/0; equivalência dos campos comparados = True.

## Limites de interpretação

- Os planos consultados contêm vigências históricas em snapshots posteriores. Eles não constituem uma coleção de quinze versões anuais preservadas no momento de cada operação.
- O rótulo horário descreve a forma de determinação do valor reportado. 'Measured' não significa um sensor que mede diretamente massa de CO2, nem prova ausência de erro de medição.
- Nas horas 'Measured and Substitute', não se conhece, por esse indicador agregado, a fração intrahorária ou da massa efetivamente substituída. As massas associadas a essas horas não são estimativas de massa substituída.
- Alterações de analisador, sonda, registrador e DAHS documentam diferenças de configuração. Esta auditoria não estima seu efeito sobre a série e não permite atribuir causalmente mudanças de erro do modelo à instrumentação.
- Não foram reprocessados relatórios de calibração, certificação, auditoria relativa de precisão ou dados brutos sub-horários.
- Ausência de registro horário, ausência de indicador em hora OFF e uso regulatório de dado substituto são situações distintas, reportadas separadamente.

## Fontes oficiais e rastreabilidade

- [Instruções oficiais ECMPS, 20/12/2024](https://www.epa.gov/system/files/documents/2024-12/ecmps_monitoring_plan_reporting_instructions-12202024.pdf), seção 6, páginas impressas 32 e 33 (vigência dos métodos); seção 8.2, página 61 (vigência dos componentes); seção 9, Tabela 43, página 80 (F-11).
- [OpenAPI de planos](https://api.epa.gov/easey/monitor-plan-mgmt/swagger-json) e [OpenAPI de emissões](https://api.epa.gov/easey/emissions-mgmt/swagger-json).
- [Tabelas de códigos oficiais](https://api.epa.gov/easey/master-data-mgmt/list). Os JSONs consultados estão no diretório sources.
- input_manifest.json e sources_manifest.json registram hashes SHA-256. Caminhos de entrada são nomes lógicos relativos ao repositório; os argumentos da execução podem apontar para outra cópia dos mesmos arquivos. As entradas foram abertas somente para leitura.

## Achados de integridade

- 2019: n_load_missing_on = 1.
