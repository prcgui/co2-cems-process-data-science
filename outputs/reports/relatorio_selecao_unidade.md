
# Relatório de seleção da unidade termelétrica

## 1. Objetivo da etapa de seleção

O objetivo desta primeira fase do estudo foi selecionar uma
unidade termelétrica a carvão adequada para a análise integrada
do comportamento operacional e das emissões horárias de CO₂.

A unidade deveria possuir dados horários ao longo de 2025,
monitoramento de CO₂ por CEMS e comportamento operacional
suficientemente variável para permitir posteriormente a análise
de estados e transições de operação.

A seleção foi realizada a partir dos dados disponibilizados pela
U.S. Environmental Protection Agency (EPA).


## 2. Etapa 1 — Configuração e acesso aos dados

Inicialmente foi configurado o ambiente de trabalho no Google
Colab, incluindo o acesso à API da EPA e a definição dos
diretórios utilizados para armazenamento temporário e saída dos
dados.

A utilização da API permite que a obtenção dos dados seja
reproduzível, evitando a seleção manual de arquivos.


## 3. Etapa 2 — Consulta ao catálogo de dados da EPA

Foi consultado o catálogo de arquivos disponibilizados pela EPA.

O objetivo foi identificar programaticamente os conjuntos de
dados necessários ao estudo, principalmente:

- informações sobre instalações e unidades;
- Monitoring Plans;
- arquivos de emissões horárias de 2025.

Essa estratégia permite rastrear exatamente quais fontes foram
utilizadas no processamento.


## 4. Etapa 3 — Identificação da população inicial

A população de unidades foi filtrada considerando unidades
associadas ao uso de carvão e tecnologias de caldeira
compatíveis com geração termelétrica a vapor.

Após essa filtragem foram identificadas:

**421 unidades candidatas iniciais.**

Essa etapa reduz o universo da base da EPA às unidades
tecnologicamente compatíveis com o objeto do estudo.


## 5. Etapa 4 — Associação aos Monitoring Plans

Os identificadores das instalações candidatas foram cruzados com
os arquivos de Monitoring Plan da EPA.

Foram encontrados:

**202 Monitoring Plans associados às instalações
candidatas.**

Os Monitoring Plans são necessários para verificar como o CO₂ é
monitorado em cada unidade.


## 6. Etapa 5 — Obtenção dos Monitoring Plans

Os arquivos de Monitoring Plan correspondentes às instalações
candidatas foram obtidos para análise.

Essa etapa possibilitou acessar a estrutura de monitoramento de
cada unidade e identificar o método utilizado para determinação
das emissões de CO₂.


## 7. Etapa 6 — Identificação do monitoramento de CO₂ por CEMS

Os arquivos XML dos Monitoring Plans foram processados
individualmente.

Foram procurados registros nos quais:

- o parâmetro monitorado fosse CO₂;
- o método de monitoramento fosse CEM;
- o monitoramento estivesse associado diretamente à unidade.

Foram identificados:

**394 registros de monitoramento CO₂-CEM.**

A exigência de CEMS foi adotada para utilizar como referência
emissões obtidas por monitoramento contínuo da unidade.


## 8. Etapa 7 — Validade do CEMS em 2025

Os registros de monitoramento foram avaliados quanto à validade
durante o período analisado.

Foram identificados:

**348 registros CO₂-CEM válidos para 2025.**

Após o cruzamento com a população inicial, restaram:

**303 unidades candidatas.**

Essas unidades constituíram a população efetivamente elegível
para a análise dos dados horários.


## 9. Etapa 8 — Identificação dos arquivos horários

Foram identificados no catálogo da EPA os arquivos estaduais de
emissões horárias referentes ao ano de 2025.

Os arquivos correspondentes aos estados que possuíam unidades
candidatas foram selecionados para processamento.

Essa abordagem evitou o download de arquivos sem relação com a
população analisada.


## 10. Etapa 9 — Extração dos dados horários

Os arquivos estaduais de 2025 foram processados e somente os
registros pertencentes às unidades candidatas foram mantidos.

Foram obtidas:

**299 unidades com dados horários em 2025.**

Cada unidade encontrada possuía até 8.760 observações, que
correspondem às horas de um ano não bissexto.

Essa etapa confirmou a disponibilidade temporal dos dados
necessários ao estudo.


## 11. Etapa 10 — Avaliação da qualidade e riqueza operacional

As unidades foram avaliadas segundo critérios de qualidade dos
dados e diversidade de comportamento operacional.

Foram considerados, entre outros:

- cobertura dos dados de CO₂;
- cobertura dos dados de carga;
- proporção de valores indicados como medidos;
- presença de operação ao longo dos meses do ano;
- número de startups e shutdowns;
- amplitude da carga;
- variabilidade da carga;
- intensidade das variações horárias de potência.

Após os critérios de qualidade, permaneceram:

**156 unidades.**

A seleção não foi realizada por um score único. O ranking foi
utilizado apenas como ferramenta de triagem, uma vez que o
objetivo não era simplesmente selecionar a unidade com maior
número de transições.


## 12. Etapa 11 — Comparação aprofundada das finalistas

Três unidades foram selecionadas para uma análise mais detalhada:

1. George Neal North — Unit 3;
2. Iatan — Unit 2;
3. Martin Lake — Unit 2.

### George Neal North — Unit 3

Apresentou:

- 75 transições em 2025;
- P05 de carga igual a
  0 MW;
- P95 de carga igual a
  543 MW;
- aproximadamente
  5.07%
  das horas operacionais com carga menor ou igual a zero.

Embora apresente elevada quantidade de transições, a ocorrência
relativamente maior de horas operacionais com carga nula exige
uma interpretação mais cuidadosa.


### Martin Lake — Unit 2

Apresentou:

- 70 transições;
- faixa P05–P95 de
  645 MW;
- P95 da variação absoluta horária de carga de
  301.45 MW/h.

A unidade possui comportamento operacional bastante dinâmico,
especialmente em relação às rampas de potência. Entretanto,
essas variações são mais extremas que nas demais finalistas.


### Iatan — Unit 2

Apresentou:

- 38 startups;
- 37 shutdowns;
- 75 transições;
- P05 de carga de
  136 MW;
- P95 de carga de
  945 MW;
- amplitude P05–P95 de
  809 MW;
- P95 da variação absoluta horária de carga de
  175.50 MW/h;
- aproximadamente
  3.95%
  das horas operacionais com carga menor ou igual a zero.

Iatan apresentou simultaneamente elevado número de transições,
ampla faixa de carga e variações relevantes de potência, sem
apresentar o comportamento extremo observado em algumas das
demais finalistas.


## 13. Etapa 12 — Seleção definitiva da unidade

Com base na análise conjunta dos indicadores, foi selecionada:

### Iatan — Unit 2

- **Facility ID:** 6065
- **Estado:** Missouri (MO)
- **Combustível principal:** carvão
- **Tipo de unidade:** Dry bottom wall-fired boiler
- **Período:** 01/01/2025 a 31/12/2025
- **Registros:** 8,760
- **Horas operacionais:** 6,249
- **Horas desligada:** 2,511
- **Startups observados:** 38
- **Shutdowns observados:** 37
- **Carga média em operação:** 666.30 MW
- **Carga mediana em operação:** 696.00 MW
- **P05 da carga:** 136.00 MW
- **P95 da carga:** 945.00 MW
- **Amplitude P05–P95:** 809.00 MW


## 14. Justificativa da escolha

A unidade Iatan — Unit 2 foi selecionada por apresentar o melhor
equilíbrio entre **qualidade dos dados, disponibilidade temporal
e diversidade operacional**.

A unidade possui um número elevado de partidas e paradas,
períodos significativos tanto em operação quanto desligada e uma
ampla faixa de potência durante o funcionamento.

Essas características são particularmente adequadas ao objetivo
do estudo, pois permitem investigar não apenas a relação entre
carga instantânea e emissão de CO₂, mas também o possível efeito
do **estado e da trajetória operacional da unidade**.

A escolha não foi baseada exclusivamente na posição de um
ranking. Foram avaliados conjuntamente qualidade, completude,
transições operacionais, distribuição da carga e intensidade das
rampas.


## 15. Dataset final desta fase

A partir da seleção, o estudo passa a considerar exclusivamente
os **8.760 registros horários de Iatan — Unit 2 em 2025**.

As principais variáveis disponíveis nesta fase são:

- Operating Time;
- Gross Load (MW);
- CO₂ Mass (short tons);
- indicador de medição de CO₂;
- timestamp.

Também foram inicialmente derivadas:

- estado ligado/desligado;
- carga da hora anterior;
- variação horária de carga;
- eventos de startup;
- eventos de shutdown.

Os valores ausentes de carga e CO₂ observados nas horas
desligadas não devem ser interpretados automaticamente como
falhas de qualidade da base. Para Iatan 2, eles coincidem com os
períodos em que `Operating Time = 0`.


## 16. Resultado da fase de seleção

O procedimento realizado pode ser resumido como:

**421 candidatas iniciais  
→ 303 candidatas com os critérios estruturais e CEMS  
→ 299 unidades com dados horários  
→ 156 unidades com qualidade adequada  
→ 3 finalistas  
→ 1 unidade selecionada: Iatan — Unit 2.**

Com isso, encerra-se a fase de seleção da unidade.

As etapas seguintes do trabalho poderão se concentrar na
caracterização dos estados, transições e ciclos operacionais,
relacionando-os às emissões horárias de CO₂.
