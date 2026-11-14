# Protocolo experimental

Versão 1.0 — redigido em 14/11/2026, **antes** das rodadas definitivas.
Rodadas-piloto anteriores a este documento usaram somente as sementes 1 e 3
(para depuração e para medir o custo computacional). As rodadas definitivas
usam sementes disjuntas (1001–1030); as do piloto não entram em nenhuma
análise.

## 1. Natureza do estudo

Estudo experimental baseado em simulação estocástica de tempo discreto, com
números aleatórios comuns: em cada semente, todas as políticas recebem
exatamente a mesma demanda, as mesmas posições, o mesmo ruído de sensor e as
mesmas perdas de comunicação. As comparações são, portanto, **pareadas por
semente**. Nenhum resultado constitui medição de campo. Os resultados valem
para o modelo e os parâmetros descritos em `docs/parametros.md`.

## 2. Questões e hipóteses

| QP | Hipótese operacional (pré-especificada) | Experimento |
|---|---|---|
| QP1 | Dados de ocupação permitem coletar contêineres mais cheios (maior ocupação média na coleta e menos coletas abaixo de 50%) do que a coleta periódica fixa (A). | E1 |
| QP2 | H2a: C percorre menos km/dia que A. H2b: B transborda mais que A. H2c: D transborda menos que C, ao custo de mais km. | E1 |
| QP2/QP5 | H2d: para o mesmo nível de serviço (transbordamento ≤ 1% do volume gerado), as políticas com telemetria (C, D) exigem menos km/dia que A. | E2 |
| QP3 | H3a: perda de mensagens, interrupções, ruído e falhas de sensores pioram o transbordamento de B–D. H3b: a estimativa por taxa para dados desatualizados (*fallback*) reduz esse efeito. | E3 |
| QP4 | H4: a vantagem relativa de C/D sobre A depende da escala/densidade, da variabilidade da demanda e da capacidade da frota; sob mudança de regime de demanda, A degrada mais que C/D. | E1, E4 |
| QP5 | Discussão: condições em que os ganhos são pequenos ou negativos (baixa densidade, alta perda de dados, frota folgada). | E1–E4 |

As hipóteses são direcionais apenas para orientar a leitura; todos os testes
são bilaterais.

## 3. Cenário-base

* Malha viária dirigida de Aracaju-SE (OSM, limite municipal), contêineres
  em interseções sorteadas uniformemente; **posições hipotéticas**.
* Depósito/ponto de descarga hipotético em (−10,9260; −37,0985).
* 7 dias de aquecimento (descartados) + 28 dias avaliados (4 semanas).
* Passo de 15 min; planejamento às 06h; turno 07h–15h.
* Demais parâmetros: `wastesim/config.py` e `docs/parametros.md`.

## 4. Políticas

A (periódica com frequência por contêiner, rotas OR-Tools), B (limiar 75%,
vizinho mais próximo + 2-opt), B-OR (limiar 75%, OR-Tools), C (dinâmica:
obrigatórios ≥ 75%, opcionais ≥ 50%, prêmio 1 m/L, OR-Tools), D (preditiva:
como C com projeção por taxa; obrigatório se a projeção no fim do turno
seguinte ≥ 95%). Solver: OR-Tools com descida gulosa até o ótimo local
(determinístico). Todas as políticas usam a mesma frota, capacidade, jornada,
velocidade, tempos de serviço e a mesma regra de execução (desvio ao depósito
quando a carga excederia a capacidade).

## 5. Experimentos

| Id | Objetivo | Fatores | Políticas | Sementes |
|---|---|---|---|---|
| E1 | Comparação principal e escala | N ∈ {20, 100, 500} | A, B, B-OR, C, D | 30 |
| E2 | Fronteira distância × serviço | parâmetro de agressividade de cada política (5–7 níveis), N = 100 | A, B-OR, C, D | 20 |
| E3 | Robustez da telemetria | perda {0; 0,05; 0,2; 0,5}; interrupções regionais (48 h, 50% dos dispositivos, 1 episódio/semana); ruído {0; base; 3×; 6×}; falha permanente {10%; 30%}; sensores congelados 10%; período de amostragem {15 min; 1 h; 6 h; 24 h}; *fallback* ligado/desligado sob falha de 30% | A (referência), B-OR, C, D | 30 |
| E4 | Sensibilidade operacional | intensidade de demanda {0,7; 1,3}; alta variabilidade; mudança de regime (+60% em 30% dos contêineres a partir do dia 14); frota reduzida (utilização-alvo 0,95); layout agrupado; velocidade {15; 30} km/h | A, B-OR, C, D | 30 |
| E5 | Sensibilidade ao solver | descida gulosa vs GLS (5 s) | A, C, D (N = 500) | 10 |
| E6 | Integração MQTT real | broker Mosquitto local, 100 dispositivos virtuais, QoS 0/1, reinício do broker | — | — |

Fatores de E3 e E4 são variados um de cada vez em torno do cenário-base
(N = 100), para isolar efeitos com custo computacional controlado; interações
não são estimadas (limitação declarada).

## 6. Métricas

Primárias: **km/dia** (custo) e **transbordamento (% do volume gerado)**
(falha de serviço). Secundárias: visitas/dia; km por m³ coletado; eventos de
transbordamento; horas de contêiner cheio por contêiner·dia; ocupação média
na coleta; % de coletas com ocupação < 50% ("coleta prematura"); espera
média entre cruzar 80% e ser coletado (h); utilização da capacidade dos
veículos; viagens extras de descarga; visitas planejadas não realizadas;
obrigatórios descartados pelo planejador; tempo do otimizador; disponibilidade
de telemetria (leituras válidas entregues / leituras programadas); erro
absoluto médio da previsão de 24 h (D) versus persistência.

Verificação embutida: balanço de volume (gerado = coletado + transbordado +
Δestoque) com resíduo numérico ≈ 0 em toda execução.

## 7. Análise estatística

1. Descritivas por condição: média, desvio-padrão, mediana, IQR.
2. Para cada comparação pré-definida (B, B-OR, C, D vs A; D vs C; C vs B-OR)
   e cada métrica primária: diferença pareada por semente; IC 95% da
   diferença média por *bootstrap* percentil (10.000 reamostragens, semente
   fixa); teste de postos sinalizados de Wilcoxon bilateral; correção de
   Holm dentro de cada família (experimento × métrica); tamanho de efeito por
   correlação bisserial de postos pareada e diferença relativa (%).
3. E2: fronteiras médias (km/dia × transbordamento) com IC 95% em ambos os
   eixos; km/dia necessário para transbordamento ≤ 1%, interpolado
   linearmente por semente e comparado de forma pareada.
4. Ausência de significância não é interpretada como equivalência.
5. Nenhum resultado é removido; execuções com falha são registradas.

## 8. Ameaças à validade (antecipadas)

Interna: parâmetros de demanda e perfis horários/semanais são hipóteses;
solver heurístico; passo de 15 min. Construto: transbordamento modelado como
volume recusado; "coleta prematura" depende do limiar de 50%. Externa:
posições de contêineres e depósito hipotéticos; velocidade constante, sem
trânsito; uma viagem planejada por veículo e turno (com desvios de descarga).
Conclusão: comparações múltiplas (Holm), pareamento por semente.

## Emenda 1 (14/11/2026)

Após revisão independente do código, durante as rodadas: política A passou a
usar a taxa média verdadeira com descartes volumosos (todas as execuções de A
refeitas); E2 com níveis adicionais (θ = 0,3 e 0,4 para B-OR e C; θ = 1,0 para
D); E4 "frota reduzida" = 1 veículo; E5 com descida gulosa sem truncamento
(30 s). Detalhes e itens não corrigidos: `docs/desvios-protocolo.md`.
