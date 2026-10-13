# Caracterização técnica e operacional da Iatan Unit 2

## 1. Finalidade do relatório

Este relatório caracteriza a **Iatan Unit 2**, Facility ID 6065, com o objetivo de dar suporte à análise de processos e às decisões experimentais de predição de emissões horárias de CO₂.

A unidade não deve ser interpretada apenas como uma série temporal de carga e emissões. Ela é um sistema físico específico, com tecnologia de geração, combustível, equipamentos de controle ambiental, sistemas de monitoramento e práticas operacionais que condicionam a relação entre potência elétrica, consumo de combustível e emissões.

A caracterização abaixo distingue:

1. informações documentadas sobre a instalação;
2. implicações físicas para o processo de geração;
3. implicações para análise de processos;
4. implicações para modelagem preditiva;
5. pontos ainda não confirmados que precisam de investigação específica.

Última revisão das fontes: **13 de outubro de 2026**.

---

## 2. Identificação da instalação

A Iatan Generating Station está localizada em Platte County, Missouri, próxima a Weston, às margens do Missouri River. O atual Part 70 Operating Permit identifica a instalação como **Evergy Inc. - Iatan Generating Station**, endereço 20250 Highway 45 North, Weston, Missouri. A estação produz eletricidade a partir da combustão de carvão e óleo combustível em duas caldeiras. [1]

A unidade objeto deste estudo é:

| Campo | Valor |
|---|---|
| Facility | Iatan Generating Station |
| Facility ID / ORIS | 6065 |
| Unidade | Unit 2 |
| Estado | Missouri |
| Localização | Weston / Platte County |
| Tipo | Unidade termelétrica a carvão |
| Combustível principal | Carvão sub-betuminoso de baixo teor de enxofre |
| Combustível auxiliar | Fuel oil nº 2 para light-off, startup e estabilização de chama |
| Fabricante da caldeira | Alstom |
| Ano de construção da Boiler #2 | 2010 |
| Operação comercial | 31/12/2010 |
| Regime tecnológico | Carvão pulverizado, ciclo a vapor supercrítico |

O Part 70 Permit classifica a Boiler #2 como **EP30**, com capacidade térmica máxima de **8.100 MMBtu/h**, alimentada por carvão sub-betuminoso e fuel oil nº 2. [1]

A operação comercial da Iatan Unit 2 começou em **31 de dezembro de 2010**. Documentação regulatória e societária contemporânea registra a unidade como uma instalação de aproximadamente 850 MW concebida para geração de base. [2][3]

### Implicação para a base histórica

O catálogo estadual da EPA possuir arquivos anteriores a 2010 não significa que a Unit 2 possua histórico operacional nesses anos.

Como a unidade entrou em operação comercial no último dia de 2010, **2011 tende a ser o primeiro ano civil completo potencialmente utilizável** para análise histórica. O ano de 2010 deve ser tratado separadamente como período de comissionamento e entrada em serviço, caso existam registros.

---

## 3. Papel da unidade e escala de geração

A Iatan 2 foi construída como uma grande unidade de geração a carvão voltada à oferta de **base load**. A Missouri Public Service Commission descreveu a entrada da unidade em 2010 como a primeira nova geração a carvão de base instalada por uma utility investor-owned do Missouri desde 1980. [3]

As fontes reportam diferentes valores de capacidade:

| Fonte / contexto | Capacidade reportada |
|---|---:|
| Projeto e documentação de 2010-2011 | 850 MW líquidos |
| Turbina Toshiba, documentação técnica | 930 MW brutos / 850 MW líquidos |
| Documento de financiamento de 2023 | 870 MW líquidos |
| Apresentação técnica da planta em 2023 | cerca de 900 MW líquidos |

Esses valores não devem ser tratados como uma contradição automática. Diferentes documentos podem utilizar conceitos como capacidade bruta, líquida, nominal, capacidade sazonal ou capacidade atualizada após mudanças operacionais. [4][5][6]

### Consequência para a modelagem

A base EPA utilizada neste projeto contém a variável **Gross Load (MW)**. Portanto, qualquer normalização futura da carga pela capacidade deve utilizar uma referência fisicamente compatível com **potência bruta**, e não simplesmente dividir Gross Load por um valor de capacidade líquida como 850 MW.

Esse cuidado será particularmente importante em estudos de generalização entre unidades.

---

## 4. Tecnologia de geração

A Iatan Unit 2 utiliza uma **caldeira Alstom supercrítica a carvão pulverizado**. Fontes técnicas descrevem o equipamento como uma caldeira de pressão deslizante, balanced draft e corner-fired, associada a uma turbina a vapor Toshiba com reaquecimento. [4][7]

O processo físico pode ser resumido como:

```text
carvão
  ↓
pulverização
  ↓
combustão na caldeira
  ↓
geração de vapor em condição supercrítica
  ↓
turbina a vapor com reaquecimento
  ↓
gerador elétrico
  ↓
eletricidade
```

A apresentação técnica da planta em 2023 reporta condições de vapor principal da ordem de **3.600 psi e 1.080 °F**, além de circulação de água de resfriamento por cooling tower. [5]

### 4.1. Significado da condição supercrítica

Em uma unidade supercrítica, água e vapor operam acima do ponto crítico da água durante parte relevante do ciclo, permitindo maior eficiência termodinâmica do que muitas unidades subcríticas de gerações anteriores.

A eficiência superior reduz a quantidade de combustível necessária por unidade de eletricidade produzida. Consequentemente, para carvão de características semelhantes:

```text
maior eficiência
      ↓
menor combustível por MWh
      ↓
menor CO₂ por MWh
```

A configuração tecnológica da Iatan 2 ajuda a explicar por que a relação entre carga e CO₂ pode ser relativamente regular ao longo de grande parte da operação.

---

## 5. Turbina, ciclo de vapor e possibilidade de operação fora do ponto nominal

A turbina foi fornecida pela Toshiba. Documentação técnica publicada na época do projeto reporta **930 MW gross e 850 MW net**. [4]

Um aspecto particularmente relevante para este estudo é a existência de **oito estágios de aquecimento regenerativo da água de alimentação**, cinco no lado de baixa pressão e três no lado de alta pressão. Uma característica de projeto permite retirar de serviço o aquecedor superior de alta pressão e direcionar mais vapor através da turbina, aumentando a potência em até aproximadamente **40 MW**. Essa condição de operação implica penalidade no heat rate. [4]

### Implicação experimental

Esse mecanismo mostra que a relação:

```text
carga elétrica ↔ combustível ↔ CO₂
```

não é necessariamente única em toda a faixa operacional.

Duas horas com carga semelhante podem corresponder a configurações internas diferentes do ciclo térmico e, portanto, a eficiências diferentes.

Isso oferece uma explicação física plausível para investigar:

- dispersão da relação carga x CO₂ em determinadas faixas;
- regimes de alta carga;
- transições para operação de pico;
- comportamento diferenciado durante rampas;
- possível ganho de features de processo além da carga instantânea.

---

## 6. Combustível

O Part 70 Permit determina o uso de **carvão sub-betuminoso de baixo teor de enxofre** como combustível principal da Boiler #2. Fuel oil nº 2 é utilizado para light-off, startup e estabilização de chama. [1]

Documentação do projeto identifica como combustível principal carvão da **Powder River Basin, PRB**, proveniente principalmente de Wyoming e Montana. Trata-se de carvão sub-betuminoso ocidental, relativamente úmido e de baixo teor de enxofre. [6][7]

### 6.1. Relação com o CO₂

A emissão de CO₂ depende diretamente da quantidade de carbono introduzida com o combustível e da quantidade de combustível necessária para gerar energia.

Em termos conceituais:

```text
carga elétrica
    ↓
demanda térmica
    ↓
alimentação de carvão
    ↓
carbono queimado
    ↓
CO₂
```

Isso fornece fundamento físico para o forte desempenho observado em modelos baseados apenas na carga.

Entretanto, propriedades do carvão podem variar entre lotes e contratos, incluindo:

- poder calorífico;
- umidade;
- teor de carbono;
- teor de cinzas;
- teor de enxofre.

Mudanças persistentes no combustível podem deslocar a relação carga x CO₂ e produzir **concept drift** ao longo dos anos.

### 6.2. Startup como regime fisicamente diferente

Como o permit prevê fuel oil nº 2 durante light-off, startup e estabilização, a partida não é apenas uma condição de baixa carga.

Ela representa um **regime de combustão diferente**, potencialmente com mistura de combustíveis e desempenho térmico fora do estado estacionário.

Essa característica reforça a decisão de analisar startups separadamente em vez de tratá-las apenas como horas comuns de baixa potência.

---

## 7. Sistemas de controle de poluentes

A Boiler #2 utiliza uma cadeia avançada de controle ambiental. O permit registra: [1]

- low-NOx burners;
- over-fire air;
- Selective Catalytic Reduction, SCR, com injeção de amônia;
- Flue Gas Desulfurization, FGD;
- baghouse;
- Activated Carbon Injection, ACI.

A literatura técnica do projeto confirma uma sequência composta por SCR, filtro de mangas e wet FGD, com ACI para controle de mercúrio. [7]

### Função principal dos sistemas

| Sistema | Função principal |
|---|---|
| Low-NOx burners / over-fire air | Redução da formação de NOx durante combustão |
| SCR | Redução catalítica de NOx com injeção de NH₃ |
| Baghouse / fabric filter | Remoção de material particulado |
| Wet FGD | Remoção de SO₂ |
| ACI | Controle de mercúrio |

Esses sistemas não constituem captura de carbono. O CO₂ produzido pela combustão continua majoritariamente presente no gás de exaustão.

Entretanto, os equipamentos de controle ambiental consomem energia e possuem condições próprias de operação, podendo afetar eficiência global, carga auxiliar e dinâmica da planta.

---

## 8. Variáveis de processo registradas pela própria instalação

O permit da Unit 2 contém uma informação especialmente importante para análise de processos.

A instalação deve manter registro de startups, shutdowns e malfunctions da Boiler #2 e de seus sistemas de controle. Além disso, deve monitorar continuamente os seguintes parâmetros: [1]

- status operacional da Boiler #2;
- gross kilowatts produzidos pela turbina;
- mass feed rate de carvão;
- pressão diferencial do baghouse;
- taxa de injeção de amônia no SCR;
- NOx na entrada do SCR;
- temperatura do gás próxima à injeção de amônia;
- temperatura do gás na saída do catalisador SCR;
- pressão diferencial através do catalisador SCR.

### Implicação para análise de processos

A operação física da Iatan possui um conjunto de estados e eventos muito mais rico do que aquele representado atualmente apenas por:

- carga;
- lags;
- rampas;
- startup;
- shutdown.

Caso dados adicionais se tornem publicamente acessíveis ou possam ser derivados de outras fontes, candidatos a atributos de processo incluem:

```text
startup
shutdown
malfunction
coal feed rate
SCR active state
ammonia injection regime
baghouse pressure regime
flue-gas temperature regime
high-load / normal-load configuration
```

Isso pode levar a um Event Log mais próximo do processo físico real.

---

## 9. CEMS e origem da variável de emissão

### 9.1. O que é confirmado para a Iatan Unit 2

O Part 70 Permit exige para a Boiler #2: [1]

- CEMS para NOx, SO₂ e CO;
- equipamentos auxiliares necessários ao monitoramento;
- COMS para opacidade;
- CEMS de mercúrio;
- CEMS de material particulado;
- Data Acquisition and Handling System, DAHS, para calcular emissões segundo os limites regulatórios.

### 9.2. CO₂ no sistema EPA Part 75

A EPA estabelece em 40 CFR Part 75 monitoramento e reporte contínuo de CO₂, NOx e SO₂ no setor elétrico. A EPA informa que, em sistemas Part 75, a massa de CO₂ pode ser determinada a partir de sistemas de monitoramento contínuo envolvendo concentração de CO₂ ou O₂, vazão de gases e DAHS. [8][9]

Para unidades a carvão, documentação técnica da EPA descreve o uso de CEMS para medição de CO₂, com duas arquiteturas gerais:

1. monitor de CO₂ + monitor de vazão;
2. monitor de O₂ + cálculo da concentração de CO₂ por fatores específicos do combustível + monitor de vazão.

Assim, a variável horária **CO2 Mass (short tons)** utilizada neste projeto deve ser interpretada como uma **grandeza regulatória produzida pelo sistema de monitoramento e cálculo**, e não necessariamente como leitura direta de um único sensor de massa.

### 9.3. O que ainda não foi confirmado

O permit consultado não é suficiente para afirmar:

- se a Unit 2 atualmente utiliza monitor direto de CO₂ ou O₂ para a determinação de CO₂;
- fabricante do analisador;
- modelo do analisador;
- faixa de operação;
- histórico de substituição dos componentes;
- mudanças de metodologia ao longo de 2011-2025.

Esses dados devem ser buscados no **EPA ECMPS Monitoring Plan**, que possui registros públicos de methods, systems, components, analyzer ranges, unit fuels e unit capacities. [10][11]

Portanto, qualquer afirmação sobre fabricante ou tecnologia específica do analisador de CO₂ deve ser evitada até a consulta ao Monitoring Plan da Facility 6065.

---

## 10. Por que a carga instantânea pode ser tão preditiva

A forte relação observada entre Gross Load e CO₂ não é apenas estatística.

Para uma unidade térmica estável:

```text
mais potência elétrica
      ↓
mais energia térmica requerida
      ↓
mais carvão queimado
      ↓
mais carbono oxidado
      ↓
mais CO₂
```

Como a Iatan Unit 2 é uma grande unidade supercrítica concebida para geração de base, é plausível que grande parte de sua operação ocorra em condições relativamente regulares de eficiência.

Isso ajuda a explicar por que o XGBoost baseado somente em carga apresentou desempenho competitivo.

Entretanto, essa relação pode se alterar em:

- startup;
- shutdown;
- rampas intensas;
- baixa carga;
- condições de pico;
- mudanças na qualidade do carvão;
- manutenção;
- degradação térmica;
- modificações de equipamento;
- mudanças de instrumentação CEMS.

---

## 11. Hipóteses de drift temporal

O estudo multianual deve considerar pelo menos quatro formas de drift.

### 11.1. Drift de combustível

Mudanças de poder calorífico, umidade e carbono do carvão podem modificar a quantidade necessária para produzir a mesma carga.

### 11.2. Drift de eficiência

Envelhecimento de equipamentos, fouling, manutenção de turbina, caldeira e trocadores, além de intervenções de retrofit, podem mudar o heat rate.

### 11.3. Drift operacional

Mudanças no despacho do sistema elétrico podem alterar o perfil da unidade. Uma planta originalmente usada como base load pode passar a ciclar mais frequentemente com aumento da participação de fontes renováveis e mudanças no mercado.

### 11.4. Drift de medição

Alterações em componentes do CEMS, métodos de cálculo, spans, analyzer ranges ou DAHS podem produzir mudanças na série observada sem mudança equivalente no processo físico.

A auditoria multianual não deve, portanto, limitar-se a comparar erros de modelos. Ela deve verificar se houve alteração estrutural no processo ou no sistema de medição.

---

## 11.5. Contexto histórico e possível mudança no regime de operação

A extração histórica da Iatan Unit 2 mostrou variação expressiva no número anual de horas em operação. Em 2017 foram observadas aproximadamente **8.505 horas operacionais**, enquanto em 2023 e 2024 esse total caiu para aproximadamente **4.316** e **4.401 horas**, respectivamente. Essa diferença sugere uma possível mudança no regime de utilização da unidade ao longo do tempo.

A redução das horas operacionais não deve ser interpretada automaticamente como falha técnica ou indisponibilidade. O período de 2023 e 2024 coincide com mudanças relevantes no contexto econômico e operacional do sistema elétrico regional.

No **Southwest Power Pool, SPP**, a participação do carvão na geração caiu de **33% em 2022 para 27% em 2023**, enquanto a geração eólica respondeu por **37%** da energia produzida e o gás natural em ciclo combinado aumentou de 13% para 17%. O próprio Market Monitoring Unit do SPP relaciona essa mudança, em parte, à redução dos preços do gás natural em 2023. [12]

Em 2024, a transformação do mix continuou. O SPP reportou aproximadamente **38% da produção de energia a partir de vento**, **28,4% de gás natural** e **24,7% de carvão**. O relatório anual de mercado também registrou preço médio de gás de **US$ 1,81/MMBtu** no hub Panhandle Eastern, 16% inferior ao valor de 2023. [13][14]

O comportamento regional é coerente com a tendência observada em escala nacional. A U.S. Energy Information Administration registrou queda de aproximadamente **19% na geração a carvão entre 2022 e 2023**, ao mesmo tempo em que o preço médio do gás natural Henry Hub caiu mais de 60%. A EIA associa a redução da geração a carvão, entre outros fatores, à maior competitividade do gás natural e à expansão de outras fontes de geração. [15]

A própria **Evergy** já havia declarado em seu planejamento integrado de recursos que suas usinas a carvão tenderiam a **operar menos horas à medida que sua geração fosse deslocada por recursos renováveis de menor custo**, mantendo as unidades fósseis despacháveis como suporte para períodos de baixa disponibilidade renovável ou demanda elevada. [16]

Existe também um contexto regulatório de longo prazo favorável à incorporação de fontes renováveis. O Renewable Energy Standard do Missouri estabelece que, desde 2021, pelo menos **15% das vendas de eletricidade das utilities abrangidas pela norma** sejam atendidas por recursos renováveis elegíveis ou mecanismos equivalentes previstos na legislação. [17]

Esses elementos não demonstram que uma política específica tenha causado diretamente a redução das horas da Iatan Unit 2 em 2023 e 2024. Até o momento, não foi identificada evidência de uma determinação regulatória específica para reduzir a operação dessa unidade. A interpretação mais adequada é que sua utilização pode estar sendo influenciada por uma combinação de:

- disponibilidade e manutenção da própria planta;
- preços relativos de carvão e gás natural;
- maior participação de geração eólica e outras renováveis;
- condições de demanda e preços do mercado atacadista;
- decisões de despacho do SPP;
- estratégia de descarbonização e planejamento de recursos da Evergy;
- políticas energéticas que alteram a composição do portfólio de geração.

### Implicação para Process Mining

Essa possível mudança de regime deve ser tratada como hipótese a ser testada na análise de processos.

Uma unidade originalmente concebida para operação predominantemente de base pode, ao longo do tempo, assumir comportamento mais flexível, com maior proporção de períodos OFF, mais ciclos de partida e parada, mudanças na permanência em determinadas faixas de carga e diferentes padrões de ramp-up e ramp-down.

O Process Mining deverá, portanto, comparar os anos e períodos históricos quanto a:

- número de ciclos operacionais;
- duração dos ciclos;
- frequência de startups e shutdowns;
- tempo médio em operação contínua;
- permanência em baixa, média e alta carga;
- intensidade e frequência das rampas;
- variantes de trajetória operacional;
- emissões associadas a cada variante.

Essa análise permitirá verificar se a redução de horas observada em anos recentes corresponde apenas a menor utilização quantitativa ou se representa uma **mudança estrutural no processo operacional**.

Se forem identificadas variantes distintas entre períodos, essa informação também deverá ser considerada na modelagem preditiva, pois dados históricos oriundos de regimes de despacho diferentes podem não possuir o mesmo valor para prever períodos futuros.

## 12. Implicações para o Notebook 03A.04

A caracterização física da Iatan modifica e fortalece o desenho do experimento de generalização temporal.

### Decisão 1: tratar 2010 separadamente

A operação comercial começou em 31/12/2010. Caso existam dados de 2010, eles devem ser classificados como commissioning / entrada em serviço e não misturados automaticamente aos anos completos seguintes.

### Decisão 2: investigar 2011 em diante como série operacional madura

Se a auditoria da EPA confirmar cobertura adequada, 2011 pode representar o primeiro ano civil completo de operação comercial.

### Decisão 3: não assumir que mais histórico sempre é melhor

Dados antigos podem aumentar o volume amostral e, ao mesmo tempo, introduzir observações de um regime tecnológico, operacional ou instrumental diferente.

O experimento deve testar:

```text
1 ano
2 anos
3 anos
5 anos
10 anos
todo histórico disponível
```

sempre mantendo o mesmo ano-alvo para comparação justa.

### Decisão 4: construir curvas carga x CO₂ por ano

Antes do treinamento multianual, devem ser comparadas curvas anuais:

```text
CO₂ = f(Gross Load)
```

para identificar deslocamentos, mudanças de inclinação e dispersão.

### Decisão 5: investigar intensidade de emissão

Além da massa horária, será útil analisar de forma diagnóstica:

```text
CO₂ / MWh
```

ou uma medida equivalente de intensidade, especialmente para identificar mudanças de eficiência entre anos.

A intensidade não precisa substituir o alvo principal, mas pode revelar drift escondido pela forte relação entre escala de carga e massa de CO₂.

### Decisão 6: auditar o Monitoring Plan da EPA

Antes da conclusão do estudo multianual, deve ser criado um histórico de mudanças dos sistemas de monitoramento para verificar se existem datas de:

- mudança de método;
- troca de componente;
- alteração de span;
- alteração de analyzer range;
- recertificação relevante;
- mudança de configuração do monitoramento.

### Decisão 7: analisar regimes fisicamente significativos

Os grupos operacionais devem incluir pelo menos:

- operação estável;
- baixa carga;
- alta carga;
- primeiras horas após startup;
- ramp-up;
- ramp-down;
- rampas intensas.

A informação sobre fuel oil no startup torna a separação desse regime particularmente importante.

---

## 13. Implicações para análise de processos

A caracterização da planta sugere que o processo não deve ser representado apenas como:

```text
OFF → STARTUP → ON → SHUTDOWN
```

Uma representação mais rica pode considerar:

```text
OFF
↓
LIGHT-OFF
↓
STARTUP
↓
RAMP-UP
↓
LOW LOAD
↓
NORMAL / BASE LOAD
↓
HIGH LOAD / PEAKING
↓
RAMP-DOWN
↓
SHUTDOWN
```

Dependendo da disponibilidade de dados adicionais, também podem ser consideradas atividades ou atributos associados aos sistemas ambientais e à alimentação de combustível.

Essa distinção é relevante porque estados com mesma carga podem não representar a mesma condição termodinâmica.

---

## 14. Questões de pesquisa derivadas da caracterização técnica

A caracterização da Iatan Unit 2 gera novas perguntas testáveis:

1. A relação carga x CO₂ permaneceu estável de 2011 a 2025?
2. O erro preditivo diminui monotonamente quando anos adicionais são incluídos?
3. Existe um ponto a partir do qual dados antigos deixam de ajudar?
4. Startup apresenta comportamento diferente por utilizar fuel oil nº 2?
5. A dispersão aumenta em alta carga ou em condições de peaking?
6. A relação CO₂/MWh apresenta tendência temporal compatível com degradação ou melhoria de eficiência?
7. Mudanças no Monitoring Plan coincidem com mudanças estatísticas na série?
8. Rampas intensas tornam a trajetória mais informativa em múltiplos anos?
9. Um modelo treinado em anos antigos consegue prever anos recentes sem recalibração?
10. Qual frequência de retreinamento seria necessária para manter o desempenho?

---

## 15. Conclusão

A Iatan Unit 2 é uma grande unidade termelétrica a carvão pulverizado, de ciclo a vapor supercrítico, construída em 2010 e colocada em operação comercial em 31 de dezembro daquele ano.

Seu processo combina:

- caldeira Alstom supercrítica;
- turbina a vapor Toshiba com reaquecimento;
- carvão sub-betuminoso de baixo enxofre da Powder River Basin como combustível principal;
- fuel oil nº 2 durante startup e estabilização;
- sistemas avançados de controle de NOx, SO₂, particulados e mercúrio;
- monitoramento contínuo de variáveis operacionais e ambientais.

A configuração ajuda a explicar a forte capacidade preditiva da carga instantânea, mas também revela mecanismos físicos capazes de gerar diferenças entre horas aparentemente semelhantes.

Para este projeto, a principal consequência é que **aumentar o volume de dados não deve ser tratado apenas como acrescentar linhas ao conjunto de treinamento**.

A ampliação histórica deve ser acompanhada por análise de:

- estabilidade tecnológica;
- combustível;
- eficiência;
- regime operacional;
- sistema de monitoramento;
- mudanças na relação carga x CO₂.

O objetivo do Notebook 03A.04 passa, portanto, a ser não apenas responder se mais dados reduzem o erro, mas determinar **em quais condições o histórico adicional contém informação transferível para períodos futuros**.

---

# Referências

[1] Missouri Department of Natural Resources. **Evergy Inc. - Iatan Generating Station, Part 70 Operating Permit**, 2022.  
https://dnr.mo.gov/sites/dnr/files/vfc/2022/02/main/evergy-iatan-op2022-003.pdf

[2] Empire District Electric Company. **Form 10-K**, informações sobre Iatan 2 e entrada em operação comercial em 31/12/2010, SEC, 2011.  
https://www.sec.gov/Archives/edgar/data/32689/000104746911001023/a2202053z10-k.htm

[3] Missouri Public Service Commission. **2011 Annual Report**, seção "Completion of the Iatan 2 Generating Station".  
https://psc.mo.gov/CMSInternetData/Annual%20Reports/PSC%20Annual%20Reports%20-%20By%20Decade/Annual%20Reports%202010-2019/2011%20PSC%20Annual%20Report.pdf

[4] POWER Magazine. **Plant of the Year: KCP&L's Iatan 2 Earns POWER's Highest Honor**, 2011.  
https://www.powermag.com/plant-of-the-yearkcpls-iatan-2-earns-powers-highest-honor/

[5] Missouri Public Service Commission. **Iatan Generating Station Tour**, June 20, 2023.  
https://efis.psc.mo.gov/Document/Display/28119

[6] Missouri Joint Municipal Electric Utility Commission. **Power Project Revenue Refunding Bonds, Iatan 2 Series 2023**, descrição das instalações e combustível.  
https://www.stephens.com/uploads/shared/transactions-pdf/POS-MOJointMuniElectric-MEC-Power-Project-Rev-Refunding-Iatan-2-Series-2023.pdf

[7] U.S. EPA administrative record / technical material on Iatan Unit 2. **Project Features and Technical Description**, incluindo Alstom supercritical pulverized coal unit, Toshiba turbine and PRB coal.  
https://www3.epa.gov/region1/npdes/merrimackstation/pdfs/ar/AR-640.pdf

[8] U.S. Environmental Protection Agency. **Part 75 Policy and Technical Resources**.  
https://www.epa.gov/power-sector/part-75-policy

[9] U.S. Environmental Protection Agency. **Plain English Guide to the Part 75 Rule**, tabela de sistemas CEMS e componentes para CO₂.  
https://www.epa.gov/sites/production/files/2015-05/documents/plain_english_guide_to_the_part_75_rule.pdf

[10] U.S. Environmental Protection Agency. **ECMPS Reporting Instructions**.  
https://www.epa.gov/power-sector/ecmps-reporting-instructions

[11] U.S. Environmental Protection Agency. **Monitor Plan Management API, OpenAPI Specification**.  
https://api.epa.gov/easey/monitor-plan-mgmt/swagger

[12] Southwest Power Pool, Market Monitoring Unit. **2023 Annual State of the Market Report**. Wind represented 37% of total generation in 2023; coal fell from 33% in 2022 to 27% in 2023; combined-cycle gas increased from 13% to 17%.  
https://www.spp.org/documents/71645/2023%20annual%20state%20of%20the%20market%20report%20v2.pdf

[13] Southwest Power Pool. **2025 State of the Grid Report**, reporting the 2024 energy production mix: wind 38.0%, natural gas 28.4% and coal 24.7%.  
https://spp.org/Documents/73919/SPP%20State%20of%20the%20Grid%20Report%20May%202025.pdf

[14] Southwest Power Pool, Market Monitoring Unit. **2024 Annual State of the Market Report**. Average Panhandle Eastern natural gas price of US$ 1.81/MMBtu in 2024, 16% below 2023.  
https://www.spp.org/documents/73953/2024_annual_state_of_the_market_report.pdf

[15] U.S. Energy Information Administration. **U.S. coal-fired electricity generation decreased in 2022 and 2023**, May 10, 2024. Coal-fired generation fell approximately 19% from 2022 to 2023 while the average Henry Hub natural gas spot price declined by more than 60%.  
https://www.eia.gov/todayinenergy/detail.php?id=62043

[16] Evergy, Inc. **Evergy Files Kansas Integrated Resource Plan**, May 28, 2021. The company states that its coal plants are expected to run fewer hours as their energy is displaced by lower-cost renewable resources, while remaining available as dispatchable generation.  
https://investors.evergy.com/news-releases/news-release-details/evergy-files-kansas-integrated-resource-plan

[17] Missouri Revisor of Statutes. **RSMo Section 393.1030, Renewable Energy Portfolio Requirements**. The standard establishes a renewable portfolio requirement of no less than 15% beginning in 2021 for covered electric utilities.  
https://revisor.mo.gov/main/OneSection.aspx?bid=36065&section=393.1030
