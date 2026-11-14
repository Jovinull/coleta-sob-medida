# Evidências para parâmetros da simulação

Levantamento de 14/11/2026. As chaves remetem a `referencias.bib`. Coluna "TC": **sim** = trecho lido no texto completo/PDF oficial; **resumo** = valor tirado apenas do resumo; **não** = não verificado.

> Regra de uso: todo valor do simulador deve citar a chave e a localização abaixo. Quando houver faixa ou divergência entre fontes, use o valor central como cenário-base e as demais fontes na análise de sensibilidade.

## 1. Geração per capita de RSU

| Parâmetro | Valor | Unidade | Fonte (chave) | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| RSU **coletado** per capita, Brasil (IRS1004) | 1,14 | kg/hab·dia | `brasil2025sinisa` | p. 25 | sim | SINISA 2025, ano-base 2024. Inclui resíduo público (varrição, poda etc.) |
| RSU coletado per capita, Nordeste (IRS1004) | 1,21 | kg/hab·dia | `brasil2025sinisa` | p. 25 | sim | |
| RDO (domiciliar) coletado per capita, Brasil (IRS1005) | 0,84 | kg/hab·dia | `brasil2025sinisa` | p. 26 | sim | É o indicador mais adequado para o enchimento de contêineres domiciliares |
| RDO coletado per capita, **Nordeste** (IRS1005) | **0,88** | kg/hab·dia | `brasil2025sinisa` | p. 26 | sim | **Sugestão de valor-base** para Aracaju (não há valor municipal verificado) |
| RDO coletado per capita, Nordeste (ano-base 2023) | 0,84 | kg/hab·dia | `brasil2025sinisa2024` | p. 24 | sim | Para sensibilidade |
| RSU coletado per capita, Brasil / Nordeste (ano-base 2023) | 1,04 / 1,14 | kg/hab·dia | `brasil2025sinisa2024` | p. 23 | sim | |
| RSU **gerado** per capita, Brasil (estimativa) | 1,051 | kg/hab·dia | `abrema2026panorama` | Seç. 3.1, p. 20 (ed. em inglês) | sim | Estimativa por projeção; metodologia diferente da do SINISA |
| RSU gerado per capita, Nordeste (estimativa) | 0,967 (2024); 0,959 (2023) | kg/hab·dia | `abrema2026panorama` | Fig. 3.3, p. 22 | sim | Menor que o SINISA-NE: são métodos diferentes; não misturar |
| Aracaju, per capita municipal | — | — | — | — | não | **Não encontrado em fonte verificável.** Os dados municipais do SINISA estão em planilhas (`SINISA_RESIDUOS_Planilhas_*`), que não foram abertas nesta etapa. Pendência |
| População residente de Aracaju (2022) | 602.757 | hab. | `ibge2022censo` | SIDRA, tabela 4709, var. 93, mun. 2800308 | sim | |

Nota: os indicadores IRS1005 e IRS1006 não devem ser somados para obter o IRS1004 (`brasil2025sinisa`, p. 26, nota de rodapé).

## 2. Densidade (peso específico aparente) nos contêineres e no caminhão

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Peso específico aparente do lixo domiciliar (solto) | **230** | kg/m³ | `monteiro2001manual` | Seç. 5.3.1, p. 35 | sim | "na ausência de dados mais precisos". **Valor-base recomendado** |
| RSU misto não compactado (residencial/institucional/comercial) | 250–300 lb/yd³ ≈ **148–178** | kg/m³ | `epa2016volume` | Tabela, p. 5 | sim | Conversão: 1 lb/yd³ = 0,5933 kg/m³. A fonte primária citada pela EPA é o *Caterpillar Performance Handbook*, 40ª ed. |
| RSU misto compactado | 400–700 lb/yd³ ≈ **237–415** | kg/m³ | `epa2016volume` | p. 5 | sim | Use como faixa para a densidade no compactador |
| Taxa de compactação mínima desejável do caminhão | ≥ 3:1 | — | `monteiro2001manual` | Seç. 8.1.6, p. 71 | sim | Com 230 kg/m³ solto, isso dá ≈ 690 kg/m³ no compartimento, valor acima da faixa da EPA. Recomenda-se limitar a carga do caminhão pela massa (ver item 3) |

## 3. Caminhão compactador de carregamento traseiro

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Capacidade volumétrica útil (coletor compactador traseiro) | 6, 10, 12, 15 e 19 | m³ | `monteiro2001manual` | p. 72 | sim | Com PBT compatível de 9, 12, 14, 16 e 23 t, respectivamente |
| Carga média por viagem, compactador de 12 m³ (exemplo) | 5,5 | t/viagem | `monteiro2001manual` | Tabela 1, p. 17–18 | sim | Cidade **hipotética** de 50 mil hab.; ≈ 458 kg/m³ |
| Compactador com 12 t/viagem (exemplo de dimensionamento) | 12 | t/viagem | `monteiro2001manual` | p. 70 | sim | Exemplo ilustrativo |
| Caminhão traseiro observado em campo | 16 m³; equipe de 3 | m³ | `carlos2019influence` | Tabela 1 | sim | Burriana (Espanha) |
| Tempo de descarga no destino | ≤ 3 min (especificação desejável); 15 min de descarga no exemplo da Tab. 1 | min | `monteiro2001manual` | p. 71; Tab. 1, p. 18 | sim | |

## 4. Tempo de serviço por contêiner/parada

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Tempo no ponto, traseiro, 1 contêiner de 1,1 m³, sem transbordo | **41,95** (CV 30,97%; n = 58) | s | `carlos2019influence` | Tabela 2 (S4-1b) | sim | **Valor-base sugerido** para contêiner de 1.000–1.200 L |
| Idem, com transbordo | 79,00 | s | `carlos2019influence` | Tabela 2 | sim | Permite modelar uma penalidade de tempo quando há overflow |
| Traseiro, 2 contêineres de 1,1 m³ por ponto | 73,53 (CV 35,24%) | s | `carlos2019influence` | Tabelas 2 e 4 (S4-2b) | sim | |
| Valor agregado S1/S2/S4-1b (carga lateral automática + traseiro com 1 contêiner) | 40,34 | s | `carlos2019influence` | Tabela 4 | sim | |
| Contêiner de 240 L, coleta manual | — | — | — | — | não | Não encontrado em fonte aberta verificada. Sonesson (2000) apresenta valores-padrão, mas o artigo está atrás de paywall (`sonesson2000modelling`, apenas o resumo foi lido) |

## 5. Velocidade dos veículos

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Velocidade em operação de coleta | 4 | km/h | `monteiro2001manual` | Tabela 1, p. 17–18 | sim | Exemplo de cidade **hipotética**; corresponde à velocidade de percurso porta a porta |
| Velocidade em transferência ao aterro | 40 | km/h | `monteiro2001manual` | Tabela 1, p. 17–18 | sim | Idem. Para o deslocamento entre pontos na malha de Aracaju, prefira tempos derivados da rede viária (OSM) com velocidade urbana parametrizada e análise de sensibilidade |

## 6. Volumes típicos de contêiner

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Contêineres plásticos padronizados no Brasil (duas rodas) | 120, 240, 360 | L | `monteiro2001manual` | p. 48–49 | sim | |
| Contêineres plásticos de quatro rodas | 760 e 1.100 | L | `monteiro2001manual` | p. 49 | sim | |
| Contêineres metálicos | 750–1.500 | L | `monteiro2001manual` | p. 50 | sim | |
| Contêiner observado em campo | 1,1 m³ | m³ | `carlos2019influence` | Tabela 1 | sim | |

Para a capacidade em massa: 1.100 L × 230 kg/m³ ≈ 253 kg; 240 L × 230 kg/m³ ≈ 55 kg (cálculo próprio a partir de `monteiro2001manual`).

## 7. Sensores

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| HC-SR04: faixa | 2–400 | cm | `elecfreakssdhcsr04` | p. 1 ("Electric Parameter") | sim | |
| HC-SR04: precisão declarada | "can reach to 3 mm" | mm | `elecfreakssdhcsr04` | p. 1 | sim | É o valor de melhor caso; a folha não informa as condições de ensaio |
| HC-SR04: ângulo de medição | 15 | graus | `elecfreakssdhcsr04` | p. 1 | sim | Relevante para os ecos nas paredes de contêineres estreitos |
| HC-SR04: ciclo mínimo recomendado | > 60 | ms | `elecfreakssdhcsr04` | p. 2 | sim | |
| HC-SR04: requisito de alvo | área ≥ 0,5 m², superfície "o mais lisa possível" | — | `elecfreakssdhcsr04` | p. 2 ("Attention") | sim | A superfície irregular dos resíduos viola essa condição, o que justifica injetar ruído e outliers no modelo |
| HC-SR04: v_som usada | 340 | m/s | `elecfreakssdhcsr04` | p. 1 | sim | Não há compensação de temperatura, o que justifica o uso do DHT11 |
| DHT11: umidade | 20–90 %UR; ±4 %UR a 25 °C (máx. ±5 %UR) | %UR | `drobotics2010dht11` | "Detailed Specifications" | sim | |
| DHT11: temperatura | 0–50 °C; ±1 °C típ. (máx. ±2 °C) | °C | `drobotics2010dht11` | idem | sim | |
| DHT11: período de amostragem | ≥ 1 | s | `drobotics2010dht11` | tabela elétrica | sim | |
| ESP32: Deep-sleep | 10 | µA | `espressif2026esp32` | Product Overview (v5.3) | sim | |
| Comparação empírica entre sensor ultrassônico e observação visual | — | — | `brouwer2023comparison` | resumo | resumo | Os números de erro do sensor não foram extraídos |

## 8. Combustível e emissões

| Parâmetro | Valor | Unidade | Fonte | Localização | TC | Observações |
|---|---|---|---|---|---|---|
| Consumo de compactador ("normal packer") dentro da área de coleta | 1,26 | L diesel/km | `nguyen2010fuel` | resumo | resumo | Contexto canadense (GPS + registros de abastecimento) |
| Consumo de caminhão de co-coleta | 1,8 | L diesel/km | `nguyen2010fuel` | resumo | resumo | |
| Fator de emissão CO₂, gasóleo/diesel (transporte rodoviário) | 74.100 (72.600–74.800) | kg CO₂/TJ | `ipcc2006guidelines` | Vol. 2, Cap. 3, Tab. 3.2.1 (p. 3.16) | sim | |
| PCI padrão do gasóleo/diesel | 43,0 (41,4–43,3) | TJ/Gg | `ipcc2006guidelines` | Vol. 2, Cap. 1, Tab. 1.2 | sim | 74.100 × 43,0 × 10⁻³ ≈ 3,19 kg CO₂/kg diesel (cálculo próprio) |
| Fator em kg CO₂/L | — | — | — | — | não | Requer a densidade do diesel brasileiro (fonte ANP/MCTI), **não verificada**. Não usar um valor por litro sem essa fonte |

## 9. Ganhos reportados na literatura (para calibrar expectativas, não como parâmetro de entrada)

| Evidência | Valor | Fonte | TC |
|---|---|---|---|
| Redução média de distância com roteirização IoT (meta-análise) | −21,51%; simulação −39,79% vs implantação real −12,37% | `maciel2025impact` | resumo |
| Limiar ótimo de nível para coleta (CVRP + BSA) | 70–75%; −36,80% de distância | `akhtar2017backtracking` | resumo |
| Rotas variáveis vs fixas (limiar de 70%) | +26,08% de eficiência; −44,44% de custo; −17,60% de CO₂ | `hannan2020waste` | resumo |
| Política antecipatória (inventory routing) | até −40% de custo | `mes2014inventory` | resumo |
| Predição de nível (BIN-CT) | rotas 33,2% mais curtas | `ferrer2019bin` | resumo |

## Pendências

1. Obter o per capita municipal de Aracaju nas planilhas do SINISA (ano-base 2024). Se possível, buscar também a composição gravimétrica do PMGIRS de Aracaju.
2. Fonte nacional para a densidade do diesel (para obter kg CO₂/L) e um fator de emissão do MCTI para o Brasil.
3. Encontrar o tempo de serviço para contêiner de 240 L e coleta manual. Opções: o texto completo de `sonesson2000modelling` (via biblioteca institucional) ou um estudo brasileiro de tempos e movimentos.
4. Encontrar a velocidade média medida de caminhões de coleta em uma capital brasileira (dado operacional da EMSURB/Aracaju ou equivalente).
