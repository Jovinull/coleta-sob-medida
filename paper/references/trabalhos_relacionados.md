# Trabalhos relacionados: comparação crítica

Base: resumos verificados (OpenAlex, Europe PMC e Semantic Scholar) e, quando indicado, o texto completo. "n.i." significa não informado no material lido. Nada aqui foi inferido além do que consta no resumo ou no texto lido; quando uma célula depende só do resumo, isso está implícito. Data: 14/11/2026.

| Trabalho | Sensoriamento | Comunicação | Simulação | Otimização | Avaliação | Limitações |
|---|---|---|---|---|---|---|
| Johansson (2006) `johansson2006effect` | Sensores de nível em 3.300 contêineres de recicláveis (Malmö) | Sem fio (tipo n.i.) | Modelo analítico + simulação de eventos discretos | Políticas dinâmicas de escalonamento e roteirização vs rotas fixas | Custo, distância e horas de trabalho; modelos coerentes com a experiência dos operadores | Recicláveis; contexto sueco; sem falhas de sensor |
| Faccio, Persona e Zanin (2011) `faccio2011waste` | Sensores volumétricos, RFID, GPS | GPRS | Sim (validação por simulação) | VRP multiobjetivo com dados em tempo real | Distância, nº de veículos, impacto ambiental; viabilidade econômica (cidade italiana, ~100 mil hab.) | Números não constam no resumo |
| Mes, Schutten e Pérez Rivera (2014) `mes2014inventory` | Contêineres subterrâneos com sensores | n.i. | Simulação + aprendizado ótimo para ajuste de parâmetros | Heurística antecipatória (roteamento de inventário reverso) | Até −40% de custo (caso holandês) | Depende do ajuste; contêineres subterrâneos |
| Anagnostopoulos et al. (2015) `anagnostopoulos2015robust` | Dados de sensores (sintéticos + reais) | n.i. | Avaliação com dados de São Petersburgo | Roteamento dinâmico robusto, frota heterogênea | "Consistência e correção" | Falha considerada só do **caminhão**; avaliação qualitativa |
| Gutierrez et al. (2015) `gutierrez2015smart` | Protótipo IoT de volume | Internet / rede municipal | Cenário com dados abertos (Copenhague) | Otimização em grafos + GIS | Comparação com coleta setorial, incluindo fatores econômicos | Cenário simulado; números não no resumo |
| Akhtar et al. (2017) `akhtar2017backtracking` | Smart bins (nível) | n.i. | Cenários de 4 dias | CVRP + BSA modificado + limiar (TWL) | TWL ótimo de 70–75%; −36,8% distância; −50% combustível | Horizonte curto; sem teste estatístico declarado |
| Ramos, Morais e Barbosa-Póvoa (2018) `ramos2018smart` | Níveis em tempo real | n.i. | Caso real | Três abordagens operacionais de rotas dinâmicas | Lucro vs operação real ("melhorias significativas") | Ganho não quantificado no resumo |
| Lozano et al. (2018) `lozano2018smart` | Peso, volume e temperatura (nó próprio) | LoRa/LoRaWAN | Caso em Salamanca (rural) | Rotas dinâmicas | Plataforma + app do motorista | Contexto rural; comunicação diferente da nossa |
| Ferrer e Alba (2019) `ferrer2019bin` | Histórico de nível + previsões | n.i. | Caso real (cidade espanhola) | Rotas a partir de previsão (ML) | −20% de distância por contêiner; rotas 33,2% mais curtas | Um caso; comparação com rota da empresa |
| Hannan et al. (2020) `hannan2020waste` | Nível em tempo real | n.i. | Cenários fixos vs variáveis | MILP (FRO vs VRO) | +26,08% de eficiência; −44,44% de custo; −17,60% de CO₂ (limiar 70%) | Sem incerteza de sensor/comunicação |
| Barth et al. (2023) `barth2023data` | 98 contêineres com sensores (campo, Suíça) | n.i. | Sim: trade-off custo × qualidade de serviço | Planejamento por nível; "digital process twin" | Economias sem perda de qualidade de serviço | Contexto suíço; uso do termo "gêmeo digital" a confrontar com Kritzinger et al. |
| Brouwer et al. (2023) `brouwer2023comparison` | Ultrassônico vs observação visual dos motoristas | n.i. | Modelo preditivo (processos gaussianos) | Decisão de coleta via previsão | Trade-off nº de coletas × nº de transbordos | Uma empresa (Portugal); foco no monitoramento |
| Priyadarshi et al. (2023) `priyadarshi2023dynamic` | Smart bins (valores em tempo real) | n.i. | Ambiente multiagente (Chandigarh) | PL por agente-caminhão | Mais resíduo em menos distância; mais contêineres cobertos | Números não no resumo; contexto indiano |
| Hussain et al. (2024) `hussain2024smart` | Ultrassônico e peso | Wi-Fi, celular etc. (discutidos) | Simulação multiagente | Roteamento preditivo; gatilhos de coleta | Comparação de modelos de gestão | Resumo lido parcialmente |
| Cárdenas-León et al. (2024) `cardenasleon2024urban` | Monitoramento em tempo real + participação cidadã | n.i. | Simulação de geração | Rotas otimizadas; dashboard | Avaliação qualitativa por stakeholders | Sem métricas operacionais no resumo |
| Iosif et al. (2026) `iosif2026optimizing` | Sensores de nível reais (Kozani) + dados sintéticos | Backend de aquisição (protocolo n.i.) | Simulação para contêineres sem sensor | ML de curto prazo + VRP dinâmico | "Potencial" demonstrado | Artigo curto; sem análise de falhas |
| Maciel et al. (2025) `maciel2025impact` (meta-análise) | — | — | 11 estudos / 21 amostras | — | −21,51% de distância; simulação −39,79% vs real −12,37% | Só distância; poucos estudos |

## Lacuna proposta

Os trabalhos acima mostram ganhos operacionais consistentes quando a coleta passa a ser guiada por dados de nível. As abordagens incluem limiares (Akhtar et al., 2017; Hannan et al., 2020), roteirização dinâmica (Johansson, 2006; Ramos et al., 2018) e predição (Mes et al., 2014; Ferrer e Alba, 2019; Iosif et al., 2026). Ao mesmo tempo, a meta-análise de Maciel et al. (2025) indica que estudos de simulação tendem a relatar reduções bem maiores que as implantações reais.

Nos resumos e textos consultados, três aspectos aparecem pouco e raramente juntos:

1. a modelagem explícita de imperfeições do sensoriamento e da comunicação, como perda de mensagens, leituras espúrias do ultrassônico e nós offline. Anagnostopoulos et al. (2015) tratam falhas de caminhão, não de sensores;
2. a comparação **pareada** de políticas fixa, por limiar, dinâmica e preditiva sob as mesmas restrições de serviço, com números aleatórios comuns, réplicas e testes estatísticos não paramétricos com correção para comparações múltiplas;
3. a disponibilização de uma plataforma aberta e reprodutível que inclua a telemetria MQTT, e não apenas o otimizador.

Um trabalho como o nosso pode contribuir de forma incremental nessa interseção: uma plataforma aberta de simulação, parametrizada com dados oficiais brasileiros (SINISA, IBGE, IBAM) para o contexto de Aracaju, com telemetria MQTT, injeção controlada de falhas e comparação estatística pareada das quatro políticas. Isso ajudaria a estimar quanto do ganho reportado em simulações resiste a falhas realistas.

Essa formulação não pretende originalidade absoluta. A busca não foi uma revisão sistemática, e trabalhos com componentes semelhantes (por exemplo, Hussain et al., 2024; Barth et al., 2023; Iosif et al., 2026) devem ser lidos na íntegra antes de afirmar a lacuna no texto final.

## Sobre o termo "gêmeo digital"

Kritzinger et al. (2018), pelo resumo, distinguem três níveis por grau de integração de dados: *Digital Model*, *Digital Shadow* e *Digital Twin*. Uma plataforma em que dados (reais ou simulados) fluem do "físico" para o modelo, mas as decisões de rota não são aplicadas automaticamente a um sistema físico, tende a se enquadrar como **modelo digital** ou, com telemetria real automática, como **sombra digital**, e não como gêmeo digital.

Recomenda-se usar "plataforma de simulação" ou "modelo/sombra digital" e reservar "gêmeo digital" apenas se houver fluxo bidirecional automático com um sistema físico real. Antes de citar as definições operacionais exatas, é preciso confirmá-las no texto completo de Kritzinger et al. (2018), que não foi acessado. Note que Barth et al. (2023) e Cárdenas-León et al. (2024) usam o termo de modo mais amplo.
