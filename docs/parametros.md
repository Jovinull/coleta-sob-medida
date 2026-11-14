# Parâmetros do simulador e sua natureza

Legenda da coluna **Natureza**: **P** dado público observado; **G** dado
geográfico real; **L** valor extraído da literatura; **H** hipótese de cenário
(sem calibração empírica; objeto de análise de sensibilidade quando
relevante); **S** inteiramente sintético. Chaves bibliográficas:
`paper/references/referencias.bib`; localização exata dos valores:
`paper/references/parametros.md`.

| Parâmetro | Valor-base | Natureza | Fonte / justificativa |
|---|---|---|---|
| Malha viária | Aracaju-SE, limite municipal (relação OSM 303928); 45.011 nós, 86.410 arcos dirigidos | G | Extrato Geofabrik `nordeste-261113.osm.pbf` (MD5 verificado), © colaboradores OSM, ODbL |
| Posição dos contêineres | interseções sorteadas | S | Hipotético; não representa equipamentos reais |
| Depósito / descarga | nó mais próximo de (−10,9260; −37,0985) | H | Hipotético |
| População de Aracaju | 602.757 hab. | P | `ibge2022censo` (contexto, não entra no modelo) |
| Geração domiciliar per capita | 0,88 kg/hab·dia | P | `brasil2025sinisa`, Nordeste, IRS1005 |
| Densidade aparente (solto) | 230 kg/m³ | L | `monteiro2001manual` |
| Volume do contêiner | 1.100 L | L | `monteiro2001manual` (contêiner de 4 rodas) |
| Geometria | prismática; sensor a 110 cm do fundo; zona morta 10 cm; H = 100 cm | H | Simplificação declarada |
| Taxa média diária por perfil | residencial 300; comercial 380; institucional 260 L/dia | H | Com 0,88 kg/hab·dia e 230 kg/m³ (3,8 L/hab·dia), 300 L/dia ≈ 78 hab. atendidos por contêiner |
| Mistura de perfis | 60% / 25% / 15% | H | — |
| Heterogeneidade entre contêineres | lognormal, CV 0,35 | H | — |
| Variação diária / intradiária | Gama, CV 0,25 / 1,0 | H | — |
| Perfis semanais e horários | ver `wastesim/demand.py` | H | Formas plausíveis, não calibradas |
| Eventos de descarte volumoso | 1 a cada 30 dias por contêiner; 15–45% de V | H | — |
| Ruído do sensor | σ = 1,5 cm | H | O datasheet declara "até 3 mm" em condição ideal (`elecfreakssdhcsr04`); resíduos violam a condição de alvo liso |
| Irregularidade da superfície | semi-normal, σ = 3 cm (viés de superestimação) | H | Primeiro eco no cone de 15° (`elecfreakssdhcsr04`) |
| Leituras inválidas / espúrias | 1% / 0,5% | H | — |
| Indisponibilidade temporária | MTBF 60 dias, MTTR 12 h | H | — |
| Faixa válida do HC-SR04 | 2–400 cm | L | `elecfreakssdhcsr04` |
| Período de medição | 60 min | H | Variado em E3 |
| Perda de mensagens | 1% | H | Variado em E3 |
| Atraso | lognormal, mediana 0,5 s; 0,2% com 1–6 h | H | — |
| Duplicação | 0,2% | H | — |
| Capacidade do caminhão | 26.000 L soltos (≈ 6 t) | L+H | 15 m³ (`monteiro2001manual`) × 400 kg/m³ (limite superior compactado, `epa2016volume`) ÷ 230 kg/m³ |
| Tempo de atendimento | 60 s | L+H | 41,95 s medidos (`carlos2019influence`) + posicionamento |
| Tempo de descarga | 15 min | L | `monteiro2001manual` (exemplo) |
| Velocidade média | 20 km/h | H | Variada em E4 (15 e 30 km/h) |
| Turno | 8 h (07h–15h) | H | — |
| Frota | ⌈Σμ / (0,7·Q)⌉ veículos | H | Dimensionamento comum a todas as políticas |
| Limiares (B–D) | 75% obrigatório; 50% opcional; 95% crítico (D) | H | Faixa 70–75% citada em `akhtar2017backtracking` (resumo); varridos em E2 |
| Prêmio dos opcionais | 1 m de rota por litro | H | Varrido indiretamente em E2 |
| Dados desatualizados | > 24 h | H | — |
| Fator de consumo (somente discussão) | 1,26 L/km | L (resumo) | `nguyen2010fuel`; contexto canadense, não usado nas métricas principais |
