#!/usr/bin/env python3
# Gera referencias.bib e biblioteca.csv a partir de uma única fonte de dados.
import csv, re, sys

OUT = "/home/jovinull/Workspace/IoT-Gestao-Residuos-Solidos-Urbanos/paper/references/"
ACESSO = "Acesso em: 14 nov. 2026"
DA = "2026-11-14"

E = []  # (key, type, fields(list of tuples), meta(dict))

def add(key, typ, fields, **meta):
    E.append((key, typ, fields, meta))

CR = "Crossref API (metadados) "
OA = "OpenAlex (resumo/OA) "

# ---------------------------------------------------------------- originais
add("anagnostopoulos2017challenges", "article", [
 ("author", "Anagnostopoulos, Theodoros and Zaslavsky, Arkady and Kolomvatsos, Kostas and Medvedev, Alexey and Amirian, Pouria and Morley, Jeremy and Hadjieftymiades, Stathes"),
 ("title", "Challenges and Opportunities of Waste Management in {IoT}-Enabled Smart Cities: A Survey"),
 ("journal", "IEEE Transactions on Sustainable Computing"), ("year", "2017"), ("volume", "2"), ("number", "3"),
 ("pages", "275--289"), ("doi", "10.1109/TSUSC.2017.2691049")],
 tipo="artigo de periódico (survey)", metodo="Revisão de modelos de gestão de resíduos habilitados por TIC/IoT",
 res="Discute forças e fraquezas de modelos de coleta IoT; base para novos frameworks (resumo).",
 lim="Survey de 2017; não cobre trabalhos recentes de otimização/predição.",
 rel="alta (contextualização; já usado no TCC)", txt="resumo",
 trecho="'we present a comprehensive and thorough survey of ICT-enabled waste management models' (resumo)",
 via=CR + "+ OpenAlex; versão aberta em figshare")

add("bouskela2016road", "book", [
 ("author", "Bouskela, Mauricio and Casseb, M{\\'a}rcia and Bassi, Silvia and De Luca, Cristina and Facchina, Marcelo"),
 ("title", "The Road toward Smart Cities: Migrating from Traditional City Management to the Smart City"),
 ("publisher", "Inter-American Development Bank"), ("year", "2016"), ("doi", "10.18235/0000377")],
 tipo="relatório institucional (BID)", metodo="Documento técnico sobre transição para gestão urbana inteligente",
 res="Não consultado em detalhe.", lim="Documento de política, sem avaliação experimental.",
 rel="baixa-média (contexto de cidades inteligentes)", txt="nao",
 trecho="—", via=CR + "(monograph, IDB)")

add("hoornweg2012waste", "book", [
 ("author", "Hoornweg, Daniel and Bhada-Tata, Perinaz"),
 ("title", "What a Waste: A Global Review of Solid Waste Management"),
 ("publisher", "World Bank"), ("address", "Washington, DC"), ("year", "2012"),
 ("doi", "10.1596/17388"), ("url", "https://hdl.handle.net/10986/17388")],
 tipo="relatório institucional (Banco Mundial)", metodo="Revisão global de dados de RSU",
 res="Não extraído nesta etapa.", lim="Dados de ~2010; preferir Kaza et al. (2018) para números atuais.",
 rel="média (contexto global)", txt="nao", trecho="—", via=CR)

add("hannan2011radio", "article", [
 ("author", "Hannan, M. A. and Arebey, Maher and Begum, R. A. and Basri, Hassan"),
 ("title", "Radio Frequency Identification ({RFID}) and communication technologies for solid waste bin and truck monitoring system"),
 ("journal", "Waste Management"), ("year", "2011"), ("volume", "31"), ("number", "12"),
 ("pages", "2406--2413"), ("doi", "10.1016/j.wasman.2011.07.022")],
 tipo="artigo de periódico", metodo="Integração RFID+GPS+GPRS+GIS+câmera para monitorar contêineres e caminhões",
 res="Sistema estável em testes de tempo real; GUI com estimativa de resíduos por imagem (resumo).",
 lim="Sem otimização de rotas nem comparação de políticas de coleta.",
 rel="média (monitoramento; já usado no TCC)", txt="resumo",
 trecho="'RFID, GPS, GPRS and GIS along with camera technologies have been integrated' (resumo)",
 via=CR + "+ Europe PMC (resumo)")

add("ipcc2023climate", "book", [
 ("author", "{IPCC}"),
 ("title", "Climate Change 2023: Synthesis Report. Contribution of Working Groups {I}, {II} and {III} to the Sixth Assessment Report of the Intergovernmental Panel on Climate Change"),
 ("publisher", "IPCC"), ("address", "Geneva"), ("year", "2023"),
 ("doi", "10.59327/IPCC/AR6-9789291691647"),
 ("note", "Core Writing Team, H. Lee e J. Romero (eds.)")],
 tipo="relatório científico (IPCC AR6 SYR)", metodo="Síntese de avaliação",
 res="SPM C.3.2: grandes contribuições de redução de emissões com custo < USD 20/tCO2-eq vêm, entre outras, da redução de emissões de metano (mineração de carvão, petróleo e gás, resíduos).",
 lim="Relatório genérico; para afirmações sobre setor de resíduos, citar seção específica (SPM C.3.2) ou o WGIII.",
 rel="média (motivação ambiental)", txt="sim (SPM)",
 trecho="'methane emissions reductions (coal mining, oil and gas, waste)' (SPM, parágrafo C.3.2; p. 34 do arquivo PDF da SPM)",
 via=CR + "+ PDF da SPM em ipcc.ch")

add("oliveira2018arquitetura", "article", [
 ("author", "de Oliveira, Samuel Silva and Kniess, Janine"),
 ("title", "Arquitetura Baseada em {Internet} das Coisas para Medi{\\c{c}}{\\~a}o e Monitoramento de Res{\\'\\i}duos"),
 ("journal", "Anais do Computer on the Beach"), ("year", "2018"), ("volume", "9"), ("pages", "130--139"),
 ("url", "https://periodicos.univali.br/index.php/acotb/article/view/12744")],
 tipo="artigo de evento (anais)", metodo="Arquitetura IoT em 3 camadas para medição de resíduos",
 res="Não extraído (fonte de figura no TCC).", lim="Protótipo; sem avaliação de roteirização.",
 rel="média (arquitetura de referência nacional)", txt="nao",
 trecho="—", via="Metadados citation_* da página Univali (OJS); DOI declarado 10.14210/cotb.v0n0.p130-139 NÃO resolve em doi.org (404)")

add("espressif2026esp32", "misc", [
 ("author", "{Espressif Systems}"), ("title", "{ESP32} Series Datasheet, Version 5.3"), ("year", "2026"),
 ("howpublished", "\\url{https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf}"),
 ("note", "Revis{\\~a}o v5.3, jul. 2026. " + ACESSO)],
 tipo="folha de dados (fabricante)", metodo="—", res="Wi-Fi 802.11 b/g/n; Deep-sleep 10 µA (p. Product Overview).",
 lim="Versão do documento muda; citar a versão consultada.", rel="média (hardware)", txt="sim",
 trecho="'Datasheet Version 5.3'; 'Power consumption in Deep-sleep mode is 10 µA'", via="PDF oficial Espressif")

add("elecfreakssdhcsr04", "misc", [
 ("author", "{Elecfreaks}"), ("title", "Ultrasonic Ranging Module {HC-SR04}"), ("year", "[s.d.]"),
 ("howpublished", "\\url{https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf}"),
 ("note", "Folha de dados sem data, hospedada pela SparkFun. " + ACESSO)],
 tipo="folha de dados (módulo)", metodo="—",
 res="Faixa 2–400 cm; precisão 'can reach to 3mm'; ângulo 15°; ciclo de medição > 60 ms; alvo ≥ 0,5 m² e plano.",
 lim="Documento não datado e sem condições de ensaio; superfícies irregulares de resíduos violam a condição de alvo plano.",
 rel="alta (modelo de ruído do sensor)", txt="sim",
 trecho="'provides 2cm - 400cm non-contact measurement function, the ranging accuracy can reach to 3mm'; 'the range of area is not less than 0.5 square meters and the plane requests as smooth as possible'",
 via="PDF (SparkFun CDN)")

add("drobotics2010dht11", "misc", [
 ("author", "{D-Robotics UK}"), ("title", "{DHT11} Humidity \\& Temperature Sensor"), ("year", "2010"),
 ("howpublished", "\\url{https://www.mouser.com/datasheet/2/758/DHT11-Technical-Data-Sheet-Translated-Version-1143054.pdf}"),
 ("note", "Tradu{\\c{c}}{\\~a}o da folha de dados do fabricante, datada de 30 jul. 2010. " + ACESSO)],
 tipo="folha de dados (tradução)", metodo="—",
 res="UR 20–90%, ±4%RH a 25 °C (máx. ±5%RH); temperatura 0–50 °C, ±1 °C típ. (máx. ±2 °C); amostragem ≥ 1 s.",
 lim="Tradução não oficial; Mouser bloqueou acesso automatizado — conteúdo conferido em cópia idêntica (D-Robotics, 30/07/2010) hospedada em cdn.hackaday.io.",
 rel="baixa-média (sensor auxiliar)", txt="sim",
 trecho="'DHT11 20-90%RH 0-50 ℃ ±5％RH ±2℃'; 'Sampling period at intervals should be no less than 1 second'",
 via="PDF D-Robotics (cópia em cdn.hackaday.io)")

# ---------------------------------------------------------------- pistas do autor
add("olawade2024smart", "article", [
 ("author", "Olawade, David B. and Fapohunda, Oluwaseun and Wada, Ojima Z. and Usman, Sunday O. and Ige, Abimbola O. and Ajisafe, Olawale and Oladapo, Bankole I."),
 ("title", "Smart waste management: A paradigm shift enabled by artificial intelligence"),
 ("journal", "Waste Management Bulletin"), ("year", "2024"), ("volume", "2"), ("number", "2"), ("pages", "244--263"),
 ("doi", "10.1016/j.wmb.2024.05.001")],
 tipo="artigo de revisão", metodo="Revisão narrativa sobre IA em coleta, triagem, reciclagem e monitoramento",
 res="Destaca necessidade de qualidade de dados, privacidade, custo e ética (resumo).",
 lim="Revisão narrativa, sem protocolo sistemático nem meta-análise.", rel="média", txt="resumo",
 trecho="'emphasizing the imperative for improved data quality, privacy measures, cost-effectiveness'", via=CR + "+ OpenAlex")

add("zoumpoulis2024smart", "article", [
 ("author", "Zoumpoulis, Panagiotis and Konstantinidis, Fotios K. and Tsimiklis, Georgios and Amditis, Angelos"),
 ("title", "Smart bins for enhanced resource recovery and sustainable urban waste practices in smart cities: A systematic literature review"),
 ("journal", "Cities"), ("year", "2024"), ("volume", "152"), ("pages", "105150"), ("doi", "10.1016/j.cities.2024.105150")],
 tipo="revisão sistemática", metodo="RSL com 79 artigos de >1400",
 res="Definição comum de smart bin (monitoramento de nível + conectividade IoT); falta de padronização em automação (resumo).",
 lim="Foco em lixeiras e separação de materiais, não em roteirização.", rel="alta (definição de smart bin)", txt="resumo",
 trecho="'waste disposal containers incorporating functionalities such as fill-level monitoring and IoT connectivity'", via=CR + "+ OpenAlex")

add("maciel2025impact", "article", [
 ("author", "Maciel, Rafael R. and de Souza, Adler Diniz and Almeida, Rodrigo M. A. and Leite, Jo{\\~a}o Paulo R. R."),
 ("title", "The Impact of {IoT}-Enabled Routing Optimization on Waste Collection Distance: A Systematic Review and Meta-Analysis"),
 ("journal", "Logistics"), ("year", "2025"), ("volume", "9"), ("number", "4"), ("pages", "161"), ("doi", "10.3390/logistics9040161")],
 tipo="revisão sistemática + meta-análise", metodo="PRISMA; 11 estudos, 21 amostras",
 res="Redução média combinada de 21,51% na distância; simulação −39,79% vs implantações reais −12,37%; sem diferença significativa entre algoritmos/variantes de VRP (resumo).",
 lim="Poucos estudos; heterogeneidade; só distância como desfecho.", rel="muito alta (ancoragem de ganhos esperados e viés de simulação)", txt="resumo",
 trecho="'reduces collection distance by a combined average of 21.51%'; 'simulation-based approaches reporting higher reductions (−39.79%) compared to real-world deployments (−12.37%)'",
 via=CR + "+ OpenAlex")

add("banks2019mqtt", "misc", [
 ("author", "Banks, Andrew and Briggs, Ed and Borgendale, Ken and Gupta, Rahul"),
 ("title", "{MQTT} Version 5.0"), ("year", "2019"),
 ("howpublished", "\\url{https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html}"),
 ("note", "OASIS Standard, 7 mar. 2019. " + ACESSO)],
 tipo="norma técnica (OASIS)", metodo="—", res="Especificação do protocolo MQTT 5.0.",
 lim="A implementação do projeto usa 3.1.1; citar 5.0 apenas ao discutir evolução/recursos.", rel="média", txt="sim (cabeçalho)",
 trecho="Editores e data na página da norma", via="docs.oasis-open.org (WebFetch)")

add("banks2014mqtt", "misc", [
 ("author", "Banks, Andrew and Gupta, Rahul"),
 ("title", "{MQTT} Version 3.1.1"), ("year", "2014"),
 ("howpublished", "\\url{https://docs.oasis-open.org/mqtt/mqtt/v3.1.1/os/mqtt-v3.1.1-os.html}"),
 ("note", "OASIS Standard, 29 out. 2014. " + ACESSO)],
 tipo="norma técnica (OASIS)", metodo="—",
 res="QoS 0/1/2 (seç. 4.3); Will Flag (3.1.2.5); Keep Alive (3.1.2.10).",
 lim="—", rel="alta (protocolo usado na implementação)", txt="sim",
 trecho="Citação recomendada: 'MQTT Version 3.1.1. Edited by Andrew Banks and Rahul Gupta. 29 October 2014. OASIS Standard.'",
 via="docs.oasis-open.org (WebFetch)")

add("sinirsdportal", "misc", [
 ("author", "{SINIR}"),
 ("title", "{SINIR+}: Sistema Nacional de Informa{\\c{c}}{\\~o}es sobre a Gest{\\~a}o de Res{\\'\\i}duos S{\\'o}lidos"),
 ("year", "[s.d.]"), ("howpublished", "\\url{https://sinir.gov.br/}"), ("note", "Portal do Governo Federal. " + ACESSO)],
 tipo="portal oficial", metodo="—", res="Portal de informações (planos, inventários, MTR, logística reversa).",
 lim="Portal; para números, citar relatórios específicos (SINISA).", rel="baixa-média", txt="sim (página inicial)",
 trecho="Título: 'SINIR+ | Sistema Nacional de Informações sobre a Gestão de Resíduos Sólidos'", via="curl da página oficial")

add("perron2025ortools", "misc", [
 ("author", "Perron, Laurent and Furnon, Vincent"), ("title", "{OR-Tools}"), ("year", "2025"),
 ("howpublished", "\\url{https://developers.google.com/optimization/}"),
 ("note", "Google. Vers{\\~a}o v9.12 (2025-02-17) conforme cita{\\c{c}}{\\~a}o recomendada; ajustar para a vers{\\~a}o usada. " + ACESSO)],
 tipo="software", metodo="—", res="Suíte de otimização combinatória (CP-SAT, MIP, roteamento).",
 lim="Atualizar versão (última release no GitHub: v9.15, jan. 2026; PyPI 9.15.6755).", rel="alta", txt="sim",
 trecho="Página oficial 'How to cite OR-Tools and its solvers'", via="developers.google.com/optimization/support/cite")

add("furnon2025ortools", "misc", [
 ("author", "Furnon, Vincent and Perron, Laurent"), ("title", "{OR-Tools} Routing Library"), ("year", "2025"),
 ("howpublished", "\\url{https://developers.google.com/optimization/routing/}"),
 ("note", "Google. Vers{\\~a}o v9.12 (2025-02-17) conforme cita{\\c{c}}{\\~a}o recomendada; ajustar para a vers{\\~a}o usada. " + ACESSO)],
 tipo="software", metodo="—",
 res="Resolve TSP, VRP, CVRP, VRPTW, VRP com recursos e com visitas descartáveis (penalidades); opções de busca local incluem GUIDED_LOCAL_SEARCH.",
 lim="Heurístico; sem garantia de otimalidade; resultados dependem de limite de tempo e semente.", rel="muito alta", txt="sim",
 trecho="Páginas 'Vehicle Routing' e 'Routing Options' (GREEDY_DESCENT, GUIDED_LOCAL_SEARCH, SIMULATED_ANNEALING)",
 via="developers.google.com (curl/WebFetch)")

# ---------------------------------------------------------------- coleta IoT / roteirização dinâmica
add("anagnostopoulos2015robust", "inproceedings", [
 ("author", "Anagnostopoulos, Theodoros and Zaslavsky, Arkady and Medvedev, Alexey"),
 ("title", "Robust waste collection exploiting cost efficiency of {IoT} potentiality in Smart Cities"),
 ("booktitle", "2015 International Conference on Recent Advances in Internet of Things (RIoT)"),
 ("publisher", "IEEE"), ("year", "2015"), ("pages", "1--6"), ("doi", "10.1109/RIOT.2015.7104901")],
 tipo="artigo de evento", metodo="Roteamento dinâmico robusto com frota heterogênea (LCT/HCT); dados sintéticos e reais de São Petersburgo",
 res="Inclusão de caminhões de alta capacidade reduz viagens ao destino e custo; modelos 'demonstram consistência e correção' (resumo).",
 lim="Avaliação qualitativa; sem comparação estatística com política fixa.", rel="alta (robustez a falhas de caminhão)", txt="resumo",
 trecho="'dynamic routing algorithm which is robust and copes when a truck is overloaded or damaged'", via=CR + "+ OpenAlex")

add("anagnostopoulos2015topk", "inproceedings", [
 ("author", "Anagnostopoulos, Theodoros and Zaslavsky, Arkady and Medvedev, Alexey and Khoruzhnicov, Sergei"),
 ("title", "Top-$k$ Query Based Dynamic Scheduling for {IoT}-enabled Smart City Waste Collection"),
 ("booktitle", "2015 16th IEEE International Conference on Mobile Data Management"),
 ("publisher", "IEEE"), ("year", "2015"), ("pages", "50--55"), ("doi", "10.1109/MDM.2015.25")],
 tipo="artigo de evento", metodo="Escalonamento dinâmico por consultas top-k sobre fluxos de sensores; app Android",
 res="Viabilidade demonstrada com dados sintéticos e reais (São Petersburgo) (resumo).",
 lim="Sem métricas quantitativas no resumo.", rel="média-alta (priorização)", txt="resumo",
 trecho="'top -- k query based dynamic scheduling model to address the challenges of near real-time scheduling driven by sensor data streams'",
 via=CR + "(grafia 'Zaslavsy' no Crossref; corrigido para Zaslavsky conforme demais registros) + OpenAlex")

add("ramos2018smart", "article", [
 ("author", "Ramos, T{\\^a}nia Rodrigues Pereira and de Morais, Carolina Soares and Barbosa-P{\\'o}voa, Ana Paula"),
 ("title", "The smart waste collection routing problem: Alternative operational management approaches"),
 ("journal", "Expert Systems with Applications"), ("year", "2018"), ("volume", "103"), ("pages", "146--158"),
 ("doi", "10.1016/j.eswa.2018.03.001")],
 tipo="artigo de periódico", metodo="Três abordagens operacionais de rotas dinâmicas com nível em tempo real; caso real",
 res="Melhorias significativas de lucro em relação à operação real (resumo).",
 lim="Ganhos não quantificados no resumo; texto completo (repositório ISCTE) bloqueado por proteção anti-bot.", rel="muito alta", txt="resumo",
 trecho="'significant profit improvements are observed when compared to the real operation'", via=CR + "+ Semantic Scholar (resumo)")

add("johansson2006effect", "article", [
 ("author", "Johansson, Ola M."),
 ("title", "The effect of dynamic scheduling and routing in a solid waste management system"),
 ("journal", "Waste Management"), ("year", "2006"), ("volume", "26"), ("number", "8"), ("pages", "875--885"),
 ("doi", "10.1016/j.wasman.2005.09.004")],
 tipo="artigo de periódico", metodo="Modelagem analítica + simulação de eventos discretos; 3300 contêineres com sensores (Malmö)",
 res="Políticas dinâmicas reduzem custos, distâncias e horas de trabalho versus rotas fixas; analítico e simulação coerentes (resumo).",
 lim="Contêineres de recicláveis; contexto sueco.", rel="muito alta (clássico de simulação de políticas)", txt="resumo",
 trecho="'dynamic scheduling and routing policies exist that have lower operating costs, shorter collection and hauling distances, and reduced labor hours compared to the static policy'",
 via=CR + "+ Europe PMC (resumo)")

add("mes2014inventory", "article", [
 ("author", "Mes, Martijn and Schutten, Marco and Rivera, Arturo P{\\'e}rez"),
 ("title", "Inventory routing for dynamic waste collection"),
 ("journal", "Waste Management"), ("year", "2014"), ("volume", "34"), ("number", "9"), ("pages", "1564--1576"),
 ("doi", "10.1016/j.wasman.2014.05.011")],
 tipo="artigo de periódico", metodo="Problema de roteamento de inventário reverso; heurística antecipatória ajustada por aprendizado ótimo + simulação",
 res="Economias de custo de até 40% ao otimizar parâmetros (caso holandês) (resumo).",
 lim="Contêineres subterrâneos; dependência do ajuste de parâmetros.", rel="muito alta (política preditiva/antecipatória)", txt="resumo",
 trecho="'costs savings up to 40% are possible by optimizing the parameters'", via=CR + "+ Europe PMC (resumo)")

add("faccio2011waste", "article", [
 ("author", "Faccio, Maurizio and Persona, Alessandro and Zanin, Giorgia"),
 ("title", "Waste collection multi objective model with real time traceability data"),
 ("journal", "Waste Management"), ("year", "2011"), ("volume", "31"), ("number", "12"), ("pages", "2391--2405"),
 ("doi", "10.1016/j.wasman.2011.07.005")],
 tipo="artigo de periódico", metodo="Modelo de roteirização multiobjetivo com dados de rastreabilidade (sensores volumétricos, RFID, GPRS, GPS); cidade italiana ~100 mil hab.",
 res="Modelo testado e validado por simulação; estudo de viabilidade econômica (resumo).",
 lim="Ganhos numéricos não constam no resumo.", rel="alta", txt="resumo",
 trecho="'knowing the real time data of each vehicle and the real time replenishment level at each bin makes it possible to decide... what bin should be emptied'",
 via=CR + "+ Europe PMC (resumo)")

add("gutierrez2015smart", "article", [
 ("author", "Gutierrez, Jose M. and Jensen, Michael and Henius, Morten and Riaz, Tahir"),
 ("title", "Smart Waste Collection System Based on Location Intelligence"),
 ("journal", "Procedia Computer Science"), ("year", "2015"), ("volume", "61"), ("pages", "120--127"),
 ("doi", "10.1016/j.procs.2015.09.170")],
 tipo="artigo de evento (Procedia)", metodo="Protótipo IoT de volume + GIS + otimização em grafos; cenário com dados abertos de Copenhague",
 res="Compara com coleta setorial tradicional incluindo fatores econômicos (resumo).",
 lim="Cenário simulado; detalhes de ganho não no resumo.", rel="alta", txt="resumo",
 trecho="'Experiments are carried out to investigate the benefits of such a system, in comparison to a traditional sectorial waste collection'", via=CR + "+ OpenAlex")

add("akhtar2017backtracking", "article", [
 ("author", "Akhtar, Mahmuda and Hannan, M. A. and Begum, R. A. and Basri, Hassan and Scavino, Edgar"),
 ("title", "Backtracking search algorithm in {CVRP} models for efficient solid waste collection and route optimization"),
 ("journal", "Waste Management"), ("year", "2017"), ("volume", "61"), ("pages", "117--128"),
 ("doi", "10.1016/j.wasman.2017.01.022")],
 tipo="artigo de periódico", metodo="CVRP com BSA modificado e limiar de nível (TWL)",
 res="TWL ótimo entre 70% e 75%; −36,80% distância coletando 91,40% do resíduo; −50% combustível, −44,68% CO2 (4 dias) (resumo).",
 lim="Horizonte curto (4 dias); comparação sem teste estatístico declarado no resumo.", rel="muito alta (política por limiar)", txt="resumo",
 trecho="'The optimal TWL was found to be between 70% and 75%'; '36.80% distance reduction for 91.40% of the total waste collection'",
 via=CR + "+ Europe PMC (resumo)")

add("hannan2020waste", "article", [
 ("author", "Hannan, M. A. and Begum, R. A. and Al-Shetwi, Ali Q. and Ker, P. J. and Al Mamun, M. A. and Hussain, Aini and Basri, Hassan and Mahlia, T. M. I."),
 ("title", "Waste collection route optimisation model for linking cost saving and emission reduction to achieve sustainable development goals"),
 ("journal", "Sustainable Cities and Society"), ("year", "2020"), ("volume", "62"), ("pages", "102393"),
 ("doi", "10.1016/j.scs.2020.102393")],
 tipo="artigo de periódico", metodo="MILP com roteirização fixa (dados estáticos) vs variável (tempo real)",
 res="VRO com limiar 70%: +26,08% eficiência, 44,44% economia de custo e −17,60% emissões (resumo).",
 lim="Ganhos dependem do limiar; sem análise de falhas de sensor.", rel="muito alta", txt="resumo",
 trecho="'VRO improved the collection efficiency by 26.08 % when the minimum filled-up level for collection was 70 %'", via=CR + "+ Semantic Scholar (resumo)")

add("jorge2022hybrid", "article", [
 ("author", "Jorge, Diana and Pais Antunes, Ant{\\'o}nio and Rodrigues Pereira Ramos, T{\\^a}nia and Barbosa-P{\\'o}voa, Ana Paula"),
 ("title", "A hybrid metaheuristic for smart waste collection problems with workload concerns"),
 ("journal", "Computers \\& Operations Research"), ("year", "2022"), ("volume", "137"), ("pages", "105518"),
 ("doi", "10.1016/j.cor.2021.105518")],
 tipo="artigo de periódico", metodo="Metaheurística híbrida para coleta inteligente com equilíbrio de carga de trabalho",
 res="Não consultado (resumo indisponível nas APIs).", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("kim2025clustered", "article", [
 ("author", "Kim, Jungmin and Manna, Apurba and Roy, Arindam and Moon, Ilkyeong"),
 ("title", "Clustered vehicle routing problem for waste collection with smart operational management approaches"),
 ("journal", "International Transactions in Operational Research"), ("year", "2025"), ("volume", "32"), ("number", "2"),
 ("pages", "863--887"), ("doi", "10.1111/itor.13282")],
 tipo="artigo de periódico", metodo="CluVRP com ACO + k-means; duas abordagens operacionais com smart bins",
 res="Mostra potencial de sistema inteligente em larga escala (resumo).",
 lim="Resumo sem números.", rel="média-alta", txt="resumo",
 trecho="'combined ant colony optimization with a k-means clustering algorithm to solve the clustered vehicle routing problem'", via=CR + "+ OpenAlex (publicado online 2023)")

add("bouleft2023dynamic", "article", [
 ("author", "Bouleft, Yousra and Elhilali Alaoui, Ahmed"),
 ("title", "Dynamic Multi-Compartment Vehicle Routing Problem for Smart Waste Collection"),
 ("journal", "Applied System Innovation"), ("year", "2023"), ("volume", "6"), ("number", "1"), ("pages", "30"),
 ("doi", "10.3390/asi6010030")],
 tipo="artigo de periódico", metodo="DM-CVRP; PLI + algoritmo genético híbrido; penalidade por transbordo",
 res="Efetividade verificada em experimentos numéricos (resumo).", lim="Instâncias de teste; sem falhas de sensor.",
 rel="média-alta (penalidade de overflow)", txt="resumo",
 trecho="'minimize the total cost, which are the transportation costs and the penalty costs caused by exceeding the bin capacity'", via=CR + "+ OpenAlex")

add("priyadarshi2023dynamic", "article", [
 ("author", "Priyadarshi, Marut and Maratha, Meet and Anish, Mohammad and Kumar, Vaibhav"),
 ("title", "Dynamic routing for efficient waste collection in resource constrained societies"),
 ("journal", "Scientific Reports"), ("year", "2023"), ("volume", "13"), ("number", "1"), ("pages", "2365"),
 ("doi", "10.1038/s41598-023-29593-x")],
 tipo="artigo de periódico", metodo="Multiagente; PL maximizando resíduo coletado e minimizando distância; Chandigarh (Índia)",
 res="Melhor desempenho em resíduo coletado/distância e contêineres atendidos vs cenário existente (resumo).",
 lim="Contexto de país em desenvolvimento; números não no resumo.", rel="alta (contexto de recursos limitados, próximo ao Brasil)", txt="resumo",
 trecho="'significantly better performance in terms of waste collected in less distance and total bins covered'", via=CR + "+ OpenAlex")

add("hussain2024smart", "article", [
 ("author", "Hussain, Iftikhar and Elomri, Adel and Kerbache, Laoucine and El Omri, Abdelfatteh"),
 ("title", "Smart city solutions: Comparative analysis of waste management models in {IoT}-enabled environments using multiagent simulation"),
 ("journal", "Sustainable Cities and Society"), ("year", "2024"), ("volume", "103"), ("pages", "105247"),
 ("doi", "10.1016/j.scs.2024.105247")],
 tipo="artigo de periódico", metodo="Simulação multiagente de sistema IoT (geração, monitoramento, gatilhos, roteamento preditivo)",
 res="Compara modelos de gestão; descreve sensores ultrassônicos/peso e tecnologias de comunicação (resumo parcial).",
 lim="Resumo lido parcialmente (truncado); números não verificados.", rel="muito alta (simulação comparativa de políticas)", txt="resumo",
 trecho="'multiagent simulation-based framework for understanding and assessing the dynamics of an IoT-enabled smart waste management system'",
 via=CR + "(Crossref traz prefixo 'Dr.' nos nomes; removido) + OpenAlex")

add("ghahramani2022iot", "article", [
 ("author", "Ghahramani, Mohammadhossein and Zhou, MengChu and Molter, Anna and Pilla, Francesco"),
 ("title", "{IoT}-Based Route Recommendation for an Intelligent Waste Management System"),
 ("journal", "IEEE Internet of Things Journal"), ("year", "2022"), ("volume", "9"), ("number", "14"), ("pages", "11883--11892"),
 ("doi", "10.1109/JIOT.2021.3132126")],
 tipo="artigo de periódico", metodo="Recomendação de rotas por métodos de IA com status e coordenadas dos contêineres",
 res="Comparação entre métodos de IA (resumo, sem números).", lim="—", rel="média", txt="resumo",
 trecho="'multiple-level decision-making process in which bins’ status and coordinates are taken into account'", via=CR + "+ OpenAlex")

add("lozano2018smart", "article", [
 ("author", "Lozano, {\\'A}lvaro and Caridad, Javier and De Paz, Juan Francisco and Villarrubia Gonz{\\'a}lez, Gabriel and Bajo, Javier"),
 ("title", "Smart Waste Collection System with Low Consumption {LoRaWAN} Nodes and Route Optimization"),
 ("journal", "Sensors"), ("year", "2018"), ("volume", "18"), ("number", "5"), ("pages", "1465"), ("doi", "10.3390/s18051465")],
 tipo="artigo de periódico", metodo="Nó LoRa de baixo consumo (peso, volume, temperatura) + módulo de rotas dinâmicas; Salamanca (rural)",
 res="Plataforma com alertas e rotas dinâmicas (resumo).", lim="Contexto rural; LoRa (não MQTT/Wi-Fi).", rel="alta (hardware+rotas)", txt="resumo",
 trecho="'measurements of the weight, filling volume and temperature of a waste container'", via=CR + "+ OpenAlex")

add("iosif2026optimizing", "inproceedings", [
 ("author", "Iosif, Panteleimon and Karantoumanis, Emmanouil and Sarigiannidis, Panagiotis and Ploskas, Nikolaos"),
 ("title", "Optimizing Waste Collection Routes Using {IoT} Sensors, Predictive Simulation, and {VRP} Techniques: A Case Study in {Kozani}, {Greece}"),
 ("booktitle", "Proceedings of the 29th Pan-Hellenic Conference on Progress in Computing and Informatics"),
 ("publisher", "ACM"), ("year", "2026"), ("pages", "7--12"), ("doi", "10.1145/3829216.3829275")],
 tipo="artigo de evento", metodo="Sensores reais + dados sintéticos simulados para contêineres sem sensor; ML prevê nível; VRP dinâmico",
 res="Demonstra potencial de gestão preditiva escalável (resumo, sem números).", lim="Artigo curto; sem análise de falhas.",
 rel="muito alta (trabalho mais próximo do nosso)", txt="resumo",
 trecho="'To extend smart monitoring to bins lacking sensors, we generate synthetic data via simulations based on the collected measurements'", via=CR + "+ OpenAlex")

add("barth2023data", "article", [
 ("author", "Barth, Linard and Schweiger, Lukas and Benedech, Rodolfo and Ehrat, Matthias"),
 ("title", "From data to value in smart waste management: Optimizing solid waste collection with a digital twin-based decision support system"),
 ("journal", "Decision Analytics Journal"), ("year", "2023"), ("volume", "9"), ("pages", "100347"), ("doi", "10.1016/j.dajour.2023.100347")],
 tipo="artigo de periódico", metodo="Estudo de campo com 98 contêineres com sensores; simulação do trade-off custo × qualidade; 'digital process twin'",
 res="Economias substanciais possíveis sem comprometer a qualidade de serviço (resumo).",
 lim="Município suíço; números não extraídos.", rel="muito alta (trade-off custo/serviço e uso do termo digital twin)", txt="resumo",
 trecho="'substantial cost savings are possible without a service quality compromise'; 'We also introduce a digital process twin'", via=CR + "+ OpenAlex")

add("cardenasleon2024urban", "article", [
 ("author", "C{\\'a}rdenas-Le{\\'o}n, Iv{\\'a}n and Koeva, Mila and Nourian, Pirouz and Davey, Calayde"),
 ("title", "Urban digital twin-based solution using geospatial information for solid waste management"),
 ("journal", "Sustainable Cities and Society"), ("year", "2024"), ("volume", "115"), ("pages", "105798"), ("doi", "10.1016/j.scs.2024.105798")],
 tipo="artigo de periódico", metodo="Protótipo de gêmeo digital urbano: monitoramento, simulação de geração, rotas otimizadas, dashboard; África do Sul",
 res="Stakeholders valorizaram dashboard; desempenho depende de capacidade computacional (resumo).",
 lim="Avaliação qualitativa por stakeholders.", rel="alta (terminologia digital twin em RSU)", txt="resumo",
 trecho="'Urban Digital Twin (UDT) prototype... integrating real-time monitoring, citizen participation, waste generation simulations, optimized collection routes'", via=CR + "+ OpenAlex")

add("prata2025improvements", "article", [
 ("author", "Prata, Jo{\\~a}o and Sim{\\~o}es, Carla L. and Simoes, Ricardo"),
 ("title", "Improvements to Municipal Solid Waste Collection Systems Using Real-Time Monitoring"),
 ("journal", "Sustainability"), ("year", "2025"), ("volume", "17"), ("number", "4"), ("pages", "1405"), ("doi", "10.3390/su17041405")],
 tipo="artigo de periódico (estudo de caso)", metodo="Monitoramento em tempo real (RFID, GIS) na LIPOR, Portugal",
 res="Melhorias de eficiência, custo e participação; agendamento por nível de enchimento (resumo).",
 lim="Estudo de caso descritivo.", rel="média-alta (evidência de implantação real)", txt="resumo",
 trecho="'Key innovations included optimized scheduling based on container filling levels'", via=CR + "+ OpenAlex")

# ---------------------------------------------------------------- predição
add("ferrer2019bin", "article", [
 ("author", "Ferrer, Javier and Alba, Enrique"),
 ("title", "{BIN-CT}: Urban waste collection based on predicting the container fill level"),
 ("journal", "Biosystems"), ("year", "2019"), ("volume", "186"), ("pages", "103962"), ("doi", "10.1016/j.biosystems.2019.04.006")],
 tipo="artigo de periódico", metodo="Software livre; aprendizado de máquina prevê nível; planejamento de rotas; cidade espanhola",
 res="Reduz 20% a distância por contêiner coletado e gera rotas 33,2% mais curtas que as da empresa (resumo).",
 lim="Um caso; comparação com operação real.", rel="muito alta (política preditiva)", txt="resumo (texto completo arXiv disponível)",
 trecho="'reduces the distance traveled to collect a container by 20%, and generates routes 33.2% shorter'", via=CR + "+ Semantic Scholar; arXiv:1807.01603")

add("rutqvist2020automated", "article", [
 ("author", "Rutqvist, David and Kleyko, Denis and Blomstedt, Fredrik"),
 ("title", "An Automated Machine Learning Approach for Smart Waste Management Systems"),
 ("journal", "IEEE Transactions on Industrial Informatics"), ("year", "2020"), ("volume", "16"), ("number", "1"), ("pages", "384--392"),
 ("doi", "10.1109/TII.2019.2915572")],
 tipo="artigo de periódico", metodo="AutoML para detectar esvaziamento de contêineres a partir de medições de nível",
 res="Acurácia/recall de 86,8%/47,9% (modelo manual) para 99,1%/98,2% (Random Forest) (resumo).",
 lim="Contêineres de recicláveis; foco em detecção, não roteirização.", rel="alta (qualidade de dados de sensor)", txt="resumo",
 trecho="'improving the classification accuracy and recall... from 86.8% and 47.9% to 99.1% and 98.2%'", via=CR + "+ OpenAlex")

add("abbasi2016forecasting", "article", [
 ("author", "Abbasi, Maryam and El Hanandeh, Ali"),
 ("title", "Forecasting municipal solid waste generation using artificial intelligence modelling approaches"),
 ("journal", "Waste Management"), ("year", "2016"), ("volume", "56"), ("pages", "13--22"), ("doi", "10.1016/j.wasman.2016.05.018")],
 tipo="artigo de periódico", metodo="SVM, ANFIS, ANN e kNN para geração mensal (Logan, Austrália)",
 res="ANFIS melhor nos picos; kNN nas médias mensais (resumo).", lim="Escala mensal/municipal, não por contêiner.",
 rel="média", txt="resumo", trecho="'ANFIS system produced the most accurate forecasts of the peaks while kNN was successful in predicting the monthly averages'",
 via=CR + "+ Europe PMC")

add("rodriguezlopez2021prediction", "article", [
 ("author", "Rodr{\\'\\i}guez L{\\'o}pez, Juana Carmen and Rodr{\\'\\i}guez-Garc{\\'\\i}a, M. Inmaculada and Moscoso L{\\'o}pez, Jos{\\'e} Antonio and Ru{\\'\\i}z Aguilar, Juan Jes{\\'u}s and Alc{\\'a}ntara P{\\'e}rez, Jos{\\'e} Manuel and Turias Dom{\\'\\i}nguez, Ignacio J."),
 ("title", "Prediction of container filling for the selective waste collection in {Algeciras} ({Spain})"),
 ("journal", "Transportation Research Procedia"), ("year", "2021"), ("volume", "58"), ("pages", "583--590"), ("doi", "10.1016/j.trpro.2021.11.077")],
 tipo="artigo de evento (Procedia)", metodo="Classificação por ML do enchimento de contêineres de papelão com dados históricos",
 res="Melhoria média de 26% em sensibilidade e 67% em especificidade (resumo).", lim="Uma fração (papelão).", rel="média-alta", txt="resumo",
 trecho="'improvement average rate of 26% in sensitivity performance index and 67% in specificity'", via=CR + "+ OpenAlex")

add("fokker2023short", "article", [
 ("author", "Fokker, Elisabeth and Koch, Thomas and Dugundji, Elenna R."),
 ("title", "Short-term time series forecasting for multi-site municipal solid waste management"),
 ("journal", "Procedia Computer Science"), ("year", "2023"), ("volume", "220"), ("pages", "170--179"), ("doi", "10.1016/j.procs.2023.03.024")],
 tipo="artigo de evento (Procedia)", metodo="Seasonal naïve, ETSX e regressão quantílica; 3640 contêineres com sensores ultrassônicos (Países Baixos)",
 res="ETSX melhor em 74% dos casos (RMSE); mau tempo reduz descarte (resumo).", lim="Clima/contexto europeu.",
 rel="alta (baseline sazonal ingênuo para política preditiva)", txt="resumo",
 trecho="'the ETSX model is the outperforming model for 74% of the time'", via=CR + "+ OpenAlex")

add("brouwer2023comparison", "article", [
 ("author", "Brouwer, Yoeri and Barbosa-P{\\'o}voa, Ana Paula and Antunes, Ant{\\'o}nio Pais and Rodrigues Pereira Ramos, T{\\^a}nia"),
 ("title", "Comparison of different waste bin monitoring approaches: An exploratory study"),
 ("journal", "Waste Management \\& Research"), ("year", "2023"), ("volume", "41"), ("number", "10"), ("pages", "1570--1583"),
 ("doi", "10.1177/0734242X231160691")],
 tipo="artigo de periódico", metodo="Sensores ultrassônicos vs observação visual de motoristas; modelo preditivo por processos gaussianos",
 res="Observações visuais + modelo preditivo reduzem coletas e transbordos consideravelmente (resumo).",
 lim="Uma empresa portuguesa.", rel="muito alta (qualidade/limitações do sensor ultrassônico; trade-off coletas × overflow)", txt="resumo",
 trecho="'trade-off analysis of the number of collections versus the number of overflows for each monitoring approach'", via=CR + "+ OpenAlex")

# ---------------------------------------------------------------- revisões
add("sosunova2022iot", "article", [
 ("author", "Sosunova, Inna and Porras, Jari"),
 ("title", "{IoT}-Enabled Smart Waste Management Systems for Smart Cities: A Systematic Review"),
 ("journal", "IEEE Access"), ("year", "2022"), ("volume", "10"), ("pages", "73326--73363"), ("doi", "10.1109/ACCESS.2022.3188308")],
 tipo="revisão sistemática", metodo="RSL com 173 estudos primários (de 3732)",
 res="Mapeia sensores, atuadores, stakeholders, dados trocados e lacunas (resumo).", lim="—", rel="muito alta", txt="resumo",
 trecho="'This study consists of 173 primary studies selected... from the 3,732 initially retrieved'", via=CR + "+ OpenAlex")

add("fang2023artificial", "article", [
 ("author", "Fang, Bingbing and Yu, Jiacheng and Chen, Zhonghao and Osman, Ahmed I. and Farghali, Mohamed and Ihara, Ikko and Hamza, Essam H. and Rooney, David W. and Yap, Pow-Seng"),
 ("title", "Artificial intelligence for waste management in smart cities: a review"),
 ("journal", "Environmental Chemistry Letters"), ("year", "2023"), ("volume", "21"), ("number", "4"), ("pages", "1959--1989"),
 ("doi", "10.1007/s10311-023-01604-3")],
 tipo="artigo de revisão", metodo="Revisão sobre IA em gestão de resíduos", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("esmaeilian2018future", "article", [
 ("author", "Esmaeilian, Behzad and Wang, Ben and Lewis, Kemper and Duarte, Fabio and Ratti, Carlo and Behdad, Sara"),
 ("title", "The future of waste management in smart and sustainable cities: A review and concept paper"),
 ("journal", "Waste Management"), ("year", "2018"), ("volume", "81"), ("pages", "177--195"), ("doi", "10.1016/j.wasman.2018.09.047")],
 tipo="revisão + artigo conceitual", metodo="Revisão integrativa", res="Propõe framework com infraestrutura sensorizada para coleta 'on-time' (resumo).",
 lim="Conceitual.", rel="média", txt="resumo", trecho="'an intelligent sensor-based infrastructure for proper upstream waste separation and on-time collection'", via=CR + "+ Europe PMC")

add("hess2024waste", "article", [
 ("author", "Hess, Christina and Dragomir, Alina G. and Doerner, Karl F. and Vigo, Daniele"),
 ("title", "Waste collection routing: a survey on problems and methods"),
 ("journal", "Central European Journal of Operations Research"), ("year", "2024"), ("volume", "32"), ("number", "2"), ("pages", "399--434"),
 ("doi", "10.1007/s10100-023-00892-y")],
 tipo="survey", metodo="Revisão de problemas de roteirização em coleta (nó, arco, location-routing)",
 res="Identifica características: instalações intermediárias, demanda incerta, pessoal, sustentabilidade (resumo).",
 lim="—", rel="muito alta (enquadramento OR)", txt="resumo", trecho="'uncertain demand, personnel planning aspects, alternative collection systems'", via=CR + "+ OpenAlex (OA)")

add("han2015waste", "article", [
 ("author", "Han, Hui and Ponce Cueto, Eva"),
 ("title", "Waste Collection Vehicle Routing Problem: Literature Review"),
 ("journal", "Promet -- Traffic \\& Transportation"), ("year", "2015"), ("volume", "27"), ("number", "4"), ("pages", "345--358"),
 ("doi", "10.7307/ptt.v27i4.1616")],
 tipo="revisão", metodo="Revisão de WCVRP", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("belien2014municipal", "article", [
 ("author", "Beli{\\\"e}n, Jeroen and De Boeck, Liesje and Van Ackere, Jonas"),
 ("title", "Municipal Solid Waste Collection and Management Problems: A Literature Review"),
 ("journal", "Transportation Science"), ("year", "2014"), ("volume", "48"), ("number", "1"), ("pages", "78--102"),
 ("doi", "10.1287/trsc.1120.0448")],
 tipo="revisão", metodo="Revisão de problemas de coleta e gestão de RSU", res="Não extraído.", lim="—", rel="média-alta", txt="nao", trecho="—", via=CR)

add("vishnu2022sensor", "article", [
 ("author", "Vishnu, S. and Ramson, S. R. Jino and Rukmini, M. S. S. and Abu-Mahfouz, Adnan M."),
 ("title", "Sensor-Based Solid Waste Handling Systems: A Survey"),
 ("journal", "Sensors"), ("year", "2022"), ("volume", "22"), ("number", "6"), ("pages", "2340"), ("doi", "10.3390/s22062340")],
 tipo="survey", metodo="Revisão RFID, RSSF e IoT em gestão de resíduos", res="Aponta LoRaWAN como protocolo preferido para lixeiras urbanas (resumo).",
 lim="—", rel="alta (justificar escolha Wi-Fi/MQTT vs LoRaWAN)", txt="resumo",
 trecho="'LoRaWAN is identified as the preferred communication protocol for the automation of solid waste handling systems in urban areas'", via=CR + "+ OpenAlex")

add("mamun2015integrated", "article", [
 ("author", "Abdulla Al Mamun, Md. and Hannan, Mahammad A. and Hussain, Aini and Basri, Hassan"),
 ("title", "Integrated Sensing Systems and Algorithms for Solid Waste Bin State Management Automation"),
 ("journal", "IEEE Sensors Journal"), ("year", "2015"), ("volume", "15"), ("number", "1"), ("pages", "561--567"),
 ("doi", "10.1109/JSEN.2014.2351452")],
 tipo="artigo de periódico", metodo="Sistema integrado de sensoriamento de estado de contêiner", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("kaza2018what", "book", [
 ("author", "Kaza, Silpa and Yao, Lisa C. and Bhada-Tata, Perinaz and Van Woerden, Frank and Levine, Daniel"),
 ("title", "What a Waste 2.0: A Global Snapshot of Solid Waste Management to 2050"),
 ("publisher", "World Bank"), ("address", "Washington, DC"), ("year", "2018"), ("doi", "10.1596/978-1-4648-1329-0")],
 tipo="relatório institucional", metodo="Compilação global de dados de RSU", res="Não extraído nesta etapa.", lim="—",
 rel="média (substitui/atualiza Hoornweg 2012)", txt="nao", trecho="—",
 via=CR + "+ OpenAlex (ambos listam 5 autores, incluindo Levine, Daniel; a capa pode listá-lo como colaborador — conferir antes de usar)")

# ---------------------------------------------------------------- comunicação / MQTT
add("thangavel2014performance", "inproceedings", [
 ("author", "Thangavel, Dinesh and Ma, Xiaoping and Valera, Alvin and Tan, Hwee-Xian and Tan, Colin Keng-Yan"),
 ("title", "Performance evaluation of {MQTT} and {CoAP} via a common middleware"),
 ("booktitle", "2014 IEEE Ninth International Conference on Intelligent Sensors, Sensor Networks and Information Processing (ISSNIP)"),
 ("publisher", "IEEE"), ("year", "2014"), ("pages", "1--6"), ("doi", "10.1109/ISSNIP.2014.6827678")],
 tipo="artigo de evento", metodo="Avaliação de desempenho MQTT vs CoAP", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("naik2017choice", "inproceedings", [
 ("author", "Naik, Nitin"),
 ("title", "Choice of effective messaging protocols for {IoT} systems: {MQTT}, {CoAP}, {AMQP} and {HTTP}"),
 ("booktitle", "2017 IEEE International Systems Engineering Symposium (ISSE)"),
 ("publisher", "IEEE"), ("year", "2017"), ("pages", "1--7"), ("doi", "10.1109/SysEng.2017.8088251")],
 tipo="artigo de evento", metodo="Comparação qualitativa de protocolos", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("mishra2020use", "article", [
 ("author", "Mishra, Biswajeeban and Kertesz, Attila"),
 ("title", "The Use of {MQTT} in {M2M} and {IoT} Systems: A Survey"),
 ("journal", "IEEE Access"), ("year", "2020"), ("volume", "8"), ("pages", "201071--201086"), ("doi", "10.1109/ACCESS.2020.3035849")],
 tipo="survey", metodo="Revisão do uso de MQTT", res="Não extraído.", lim="—", rel="alta", txt="nao", trecho="—", via=CR)

add("seoane2021performance", "article", [
 ("author", "Seoane, Victor and Garcia-Rubio, Carlos and Almenares, Florina and Campo, Celeste"),
 ("title", "Performance evaluation of {CoAP} and {MQTT} with security support for {IoT} environments"),
 ("journal", "Computer Networks"), ("year", "2021"), ("volume", "197"), ("pages", "108338"), ("doi", "10.1016/j.comnet.2021.108338")],
 tipo="artigo de periódico", metodo="Avaliação de banda e CPU de CoAP e MQTT com segurança sob condições de rede diversas",
 res="Análise focada em banda e CPU como proxy de consumo (resumo, sem números).", lim="—", rel="média-alta (custo de TLS)", txt="resumo",
 trecho="'determine their feasibility to operate under constrained devices taking into account security support and diverse network conditions'", via=CR + "+ OpenAlex")

add("domingues2024dimensioning", "article", [
 ("author", "Domingues, Marco and Faria, Jos{\\'e} N. and Portugal, David"),
 ("title", "Dimensioning payload size for fast retransmission of {MQTT} packets in the wake of network disconnections"),
 ("journal", "EURASIP Journal on Wireless Communications and Networking"), ("year", "2024"), ("volume", "2024"), ("number", "1"), ("pages", "2"),
 ("doi", "10.1186/s13638-023-02327-3")],
 tipo="artigo de periódico", metodo="Mecanismo de retransmissão de dados perdidos via MQTT após desconexão",
 res="Determina tamanho máximo de payload para recuperar dados minimizando tempo (resumo).", lim="Caso de saúde digital.",
 rel="alta (falhas de comunicação e buffering no nó)", txt="resumo",
 trecho="'retransmission mechanism to allow sensor nodes to relay missing data via MQTT to a local server when it reconnects'", via=CR + "+ OpenAlex")

add("andy2017attack", "inproceedings", [
 ("author", "Andy, Syaiful and Rahardjo, Budi and Hanindhito, Bagus"),
 ("title", "Attack scenarios and security analysis of {MQTT} communication protocol in {IoT} system"),
 ("booktitle", "2017 4th International Conference on Electrical Engineering, Computer Science and Informatics (EECSI)"),
 ("publisher", "IEEE"), ("year", "2017"), ("pages", "1--6"), ("doi", "10.1109/EECSI.2017.8239179")],
 tipo="artigo de evento", metodo="Cenários de ataque ao MQTT", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

add("vaccari2020slowite", "article", [
 ("author", "Vaccari, Ivan and Aiello, Maurizio and Cambiaso, Enrico"),
 ("title", "{SlowITe}, a Novel Denial of Service Attack Affecting {MQTT}"),
 ("journal", "Sensors"), ("year", "2020"), ("volume", "20"), ("number", "10"), ("pages", "2932"), ("doi", "10.3390/s20102932")],
 tipo="artigo de periódico", metodo="Ataque DoS de baixa taxa explorando configuração do servidor pelo cliente",
 res="Ataque bem-sucedido contra serviços MQTT reais, em texto claro e cifrado (resumo).", lim="—", rel="média (segurança)", txt="resumo",
 trecho="'Results show that the attack is successful... with limited attack resources'", via=CR + "+ OpenAlex")

add("light2017mosquitto", "article", [
 ("author", "Light, Roger A."),
 ("title", "Mosquitto: server and client implementation of the {MQTT} protocol"),
 ("journal", "Journal of Open Source Software"), ("year", "2017"), ("volume", "2"), ("number", "13"), ("pages", "265"),
 ("doi", "10.21105/joss.00265")],
 tipo="artigo de software", metodo="—", res="Broker/cliente MQTT de código aberto.", lim="Citar apenas se Mosquitto for usado.",
 rel="condicional", txt="nao", trecho="—", via=CR)

add("baldo2021multi", "article", [
 ("author", "Baldo, David and Mecocci, Alessandro and Parrino, Stefano and Peruzzi, Giacomo and Pozzebon, Alessandro"),
 ("title", "A Multi-Layer {LoRaWAN} Infrastructure for Smart Waste Management"),
 ("journal", "Sensors"), ("year", "2021"), ("volume", "21"), ("number", "8"), ("pages", "2600"), ("doi", "10.3390/s21082600")],
 tipo="artigo de periódico", metodo="Infraestrutura LoRaWAN multicamadas com edge computing; testes em laboratório e campo",
 res="TRL 3 alcançado (resumo).", lim="Foco em comunicação.", rel="média", txt="resumo",
 trecho="'This study has enhanced the readiness level of the proposed technology to Technology Readiness Level (TRL) 3'", via=CR + "+ OpenAlex")

# ---------------------------------------------------------------- VRP clássicos
add("dantzig1959truck", "article", [
 ("author", "Dantzig, G. B. and Ramser, J. H."), ("title", "The Truck Dispatching Problem"),
 ("journal", "Management Science"), ("year", "1959"), ("volume", "6"), ("number", "1"), ("pages", "80--91"), ("doi", "10.1287/mnsc.6.1.80")],
 tipo="artigo clássico", metodo="Formulação original do VRP", res="—", lim="—", rel="alta (fundamentação)", txt="nao", trecho="—", via=CR)
add("clarke1964scheduling", "article", [
 ("author", "Clarke, G. and Wright, J. W."), ("title", "Scheduling of Vehicles from a Central Depot to a Number of Delivery Points"),
 ("journal", "Operations Research"), ("year", "1964"), ("volume", "12"), ("number", "4"), ("pages", "568--581"), ("doi", "10.1287/opre.12.4.568")],
 tipo="artigo clássico", metodo="Heurística de economias (savings)", res="—", lim="—", rel="alta (heurística construtiva; disponível no OR-Tools como SAVINGS)", txt="nao", trecho="—", via=CR)
add("toth2014vehicle", "book", [
 ("editor", "Toth, Paolo and Vigo, Daniele"), ("title", "Vehicle Routing: Problems, Methods, and Applications"),
 ("edition", "2"), ("publisher", "Society for Industrial and Applied Mathematics"), ("year", "2014"), ("doi", "10.1137/1.9781611973594")],
 tipo="livro (editado)", metodo="—", res="—", lim="—", rel="alta", txt="nao", trecho="—", via=CR + "(edited-book; editores Toth e Vigo)")
add("voudouris1999guided", "article", [
 ("author", "Voudouris, Christos and Tsang, Edward"), ("title", "Guided local search and its application to the traveling salesman problem"),
 ("journal", "European Journal of Operational Research"), ("year", "1999"), ("volume", "113"), ("number", "2"), ("pages", "469--499"),
 ("doi", "10.1016/S0377-2217(98)00099-X")],
 tipo="artigo clássico", metodo="Metaheurística Guided Local Search", res="—", lim="—", rel="alta (GLS usada no OR-Tools)", txt="nao", trecho="—", via=CR)

# ---------------------------------------------------------------- gêmeo digital
add("kritzinger2018digital", "article", [
 ("author", "Kritzinger, Werner and Karner, Matthias and Traar, Georg and Henjes, Jan and Sihn, Wilfried"),
 ("title", "Digital Twin in manufacturing: A categorical literature review and classification"),
 ("journal", "IFAC-PapersOnLine"), ("year", "2018"), ("volume", "51"), ("number", "11"), ("pages", "1016--1022"), ("doi", "10.1016/j.ifacol.2018.08.474")],
 tipo="artigo de evento (IFAC)", metodo="Revisão categórica; classifica por nível de integração de dados",
 res="Distingue Digital Model, Digital Shadow e Digital Twin; literatura sobre DT (nível mais alto) é escassa (resumo).",
 lim="Texto completo não acessado (ScienceDirect 403; repositório Fraunhofer com anti-bot): definições operacionais (fluxos manuais/automáticos) precisam ser conferidas no PDF antes de citar.",
 rel="muito alta (decidir terminologia 'gêmeo digital')", txt="resumo",
 trecho="'it is distinct between Digital Model (DM), Digital Shadow (DS) and Digital Twin'", via=CR + "+ OpenAlex")
add("grieves2017digital", "incollection", [
 ("author", "Grieves, Michael and Vickers, John"),
 ("title", "Digital Twin: Mitigating Unpredictable, Undesirable Emergent Behavior in Complex Systems"),
 ("booktitle", "Transdisciplinary Perspectives on Complex Systems"), ("publisher", "Springer International Publishing"),
 ("year", "2017"), ("pages", "85--113"), ("doi", "10.1007/978-3-319-38756-7_4")],
 tipo="capítulo de livro", metodo="Conceitual", res="—", lim="Não consultado.", rel="alta (origem do conceito)", txt="nao", trecho="—", via=CR)
add("jones2020characterising", "article", [
 ("author", "Jones, David and Snider, Chris and Nassehi, Aydin and Yon, Jason and Hicks, Ben"),
 ("title", "Characterising the Digital Twin: A systematic literature review"),
 ("journal", "CIRP Journal of Manufacturing Science and Technology"), ("year", "2020"), ("volume", "29"), ("pages", "36--52"),
 ("doi", "10.1016/j.cirpj.2020.02.002")],
 tipo="revisão sistemática", metodo="—", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)
add("tao2019digital", "article", [
 ("author", "Tao, Fei and Zhang, He and Liu, Ang and Nee, A. Y. C."), ("title", "Digital Twin in Industry: State-of-the-Art"),
 ("journal", "IEEE Transactions on Industrial Informatics"), ("year", "2019"), ("volume", "15"), ("number", "4"), ("pages", "2405--2415"),
 ("doi", "10.1109/TII.2018.2873186")],
 tipo="revisão", metodo="—", res="Não extraído.", lim="—", rel="média", txt="nao", trecho="—", via=CR)

# ---------------------------------------------------------------- simulação e estatística
add("law2024simulation", "book", [
 ("author", "Law, Averill M."), ("title", "Simulation Modeling and Analysis"), ("edition", "6"),
 ("publisher", "McGraw Hill"), ("year", "2024"), ("note", "ISBN 978-1-264-26824-5")],
 tipo="livro", metodo="—", res="—", lim="Não consultado; usar capítulos de análise de saída e CRN.", rel="muito alta", txt="nao", trecho="—",
 via="Página da editora (mheducation.com): 6ª ed., © 2024, ISBN-13 9781264268245")
add("sargent2013verification", "article", [
 ("author", "Sargent, R. G."), ("title", "Verification and validation of simulation models"),
 ("journal", "Journal of Simulation"), ("year", "2013"), ("volume", "7"), ("number", "1"), ("pages", "12--24"), ("doi", "10.1057/jos.2012.20")],
 tipo="artigo de periódico", metodo="Revisão metodológica de V&V",
 res="Define validade conceitual, verificação, validade operacional e de dados; propõe procedimento recomendado (resumo).",
 lim="—", rel="muito alta", txt="resumo", trecho="'Conceptual model validity, model verification, operational validity, and data validity are discussed'", via=CR + "+ OpenAlex")
add("glasserman1992some", "article", [
 ("author", "Glasserman, Paul and Yao, David D."), ("title", "Some Guidelines and Guarantees for Common Random Numbers"),
 ("journal", "Management Science"), ("year", "1992"), ("volume", "38"), ("number", "6"), ("pages", "884--908"), ("doi", "10.1287/mnsc.38.6.884")],
 tipo="artigo de periódico", metodo="Teoria de números aleatórios comuns (CRN)", res="Não extraído.", lim="—", rel="alta (comparação pareada de políticas)", txt="nao", trecho="—", via=CR)
add("wilcoxon1945individual", "article", [
 ("author", "Wilcoxon, Frank"), ("title", "Individual Comparisons by Ranking Methods"),
 ("journal", "Biometrics Bulletin"), ("year", "1945"), ("volume", "1"), ("number", "6"), ("pages", "80--83"), ("doi", "10.2307/3001968")],
 tipo="artigo clássico", metodo="Teste de postos sinalizados", res="—", lim="—", rel="alta", txt="nao", trecho="—",
 via=CR + "(Crossref/OpenAlex informam só a página inicial 80; intervalo 80–83 corroborado por índice bibliográfico secundário)")
add("holm1979simple", "article", [
 ("author", "Holm, Sture"), ("title", "A Simple Sequentially Rejective Multiple Test Procedure"),
 ("journal", "Scandinavian Journal of Statistics"), ("year", "1979"), ("volume", "6"), ("number", "2"), ("pages", "65--70"),
 ("url", "https://www.jstor.org/stable/4615733")],
 tipo="artigo clássico", metodo="Correção de Holm para comparações múltiplas", res="—", lim="—", rel="alta", txt="nao", trecho="—",
 via="OpenAlex + registro JSTOR (DOI 10.2307/4615733 listado no OpenAlex NÃO resolve em doi.org; omitido)")
add("efron1979bootstrap", "article", [
 ("author", "Efron, B."), ("title", "Bootstrap Methods: Another Look at the Jackknife"),
 ("journal", "The Annals of Statistics"), ("year", "1979"), ("volume", "7"), ("number", "1"), ("pages", "1--26"), ("doi", "10.1214/aos/1176344552")],
 tipo="artigo clássico", metodo="Bootstrap", res="—", lim="—", rel="alta", txt="nao", trecho="—", via=CR)
add("efron1993introduction", "book", [
 ("author", "Efron, Bradley and Tibshirani, Robert J."), ("title", "An Introduction to the Bootstrap"),
 ("publisher", "Springer US"), ("year", "1993"), ("doi", "10.1007/978-1-4899-4541-9")],
 tipo="livro", metodo="—", res="—", lim="Edição original Chapman & Hall; registro Crossref aponta Springer US.", rel="alta (IC bootstrap)", txt="nao", trecho="—", via=CR)
add("sandve2013ten", "article", [
 ("author", "Sandve, Geir Kjetil and Nekrutenko, Anton and Taylor, James and Hovig, Eivind"), ("title", "Ten Simple Rules for Reproducible Computational Research"),
 ("journal", "PLoS Computational Biology"), ("year", "2013"), ("volume", "9"), ("number", "10"), ("pages", "e1003285"), ("doi", "10.1371/journal.pcbi.1003285")],
 tipo="artigo de periódico", metodo="Diretrizes", res="—", lim="—", rel="alta (reprodutibilidade)", txt="nao", trecho="—", via=CR)
add("peng2011reproducible", "article", [
 ("author", "Peng, Roger D."), ("title", "Reproducible Research in Computational Science"),
 ("journal", "Science"), ("year", "2011"), ("volume", "334"), ("number", "6060"), ("pages", "1226--1227"), ("doi", "10.1126/science.1213847")],
 tipo="artigo de periódico", metodo="Perspectiva", res="—", lim="—", rel="média-alta", txt="nao", trecho="—", via=CR)

# ---------------------------------------------------------------- parâmetros operacionais
add("sonesson2000modelling", "article", [
 ("author", "Sonesson, Ulf"), ("title", "Modelling of waste collection -- a general approach to calculate fuel consumption and time"),
 ("journal", "Waste Management \\& Research"), ("year", "2000"), ("volume", "18"), ("number", "2"), ("pages", "115--123"), ("doi", "10.1177/0734242X0001800203")],
 tipo="artigo de periódico", metodo="Modelo de tempo e energia na coleta com compactadores; dados suecos",
 res="Desvio de 5–14% (energia) e 10–24% (tempo) frente ao real em 4 áreas (resumo).",
 lim="Valores padrão por parada não acessíveis (paywall).", rel="alta (modelo de tempo/combustível)", txt="resumo",
 trecho="'between 5 and 14% deviation for energy consumption and between 10 and 24% deviation for time consumption'", via=CR + "+ OpenAlex")
add("nguyen2010fuel", "article", [
 ("author", "Nguyen, Thuy T. T. and Wilson, Bruce G."), ("title", "Fuel consumption estimation for kerbside municipal solid waste ({MSW}) collection activities"),
 ("journal", "Waste Management \\& Research"), ("year", "2010"), ("volume", "28"), ("number", "4"), ("pages", "289--297"), ("doi", "10.1177/0734242X09337656")],
 tipo="artigo de periódico", metodo="GPS + registros de combustível de caminhões de coleta (Canadá)",
 res="Compactador normal ≈ 1,26 L diesel/km e co-coleta ≈ 1,8 L/km dentro da área de coleta; >60% do combustível diário gasto coletando (resumo).",
 lim="Contexto canadense; frota específica.", rel="alta (parâmetro de combustível)", txt="resumo",
 trecho="'The co-collection and the normal garbage packer consumed approximately 1.8 L and 1.26 L of diesel per km'", via=CR + "+ Europe PMC")
add("carlos2019influence", "article", [
 ("author", "Carlos, Mar and Gallardo, Antonio and Edo-Alc{\\'o}n, Natalia and Abaso, Juan Ram{\\'o}n"),
 ("title", "Influence of the Municipal Solid Waste Collection System on the Time Spent at a Collection Point: A Case Study"),
 ("journal", "Sustainability"), ("year", "2019"), ("volume", "11"), ("number", "22"), ("pages", "6481"), ("doi", "10.3390/su11226481")],
 tipo="artigo de periódico (estudo de campo)", metodo="Medição de tempo em ponto de coleta em 6 sistemas (Burriana, Espanha)",
 res="Carregamento traseiro, contêiner de 1,1 m³: média 41,95 s por ponto (1 contêiner, sem transbordo), 79,00 s com transbordo, 73,53 s (2 contêineres); valor agregado 40,34 s para S1/S2/S4-1b (Tab. 2 e 4); caminhão traseiro de 16 m³ com equipe de 3 (Tab. 1).",
 lim="Cidade pequena e tranquila; Espanha.", rel="muito alta (tempo de serviço por contêiner)", txt="sim",
 trecho="Tabela 2 ('Tcpa not Overflowed (s)'), Tabela 4 ('Tcp per type of MSW collection system')",
 via=CR + "+ PDF (CC BY) no repositório Universitat Jaume I (hdl 10234/185518)")
add("monteiro2001manual", "book", [
 ("author", "Monteiro, Jos{\\'e} Henrique Penido and Figueiredo, Carlos Eug{\\^e}nio Moutinho and Magalh{\\~a}es, Ant{\\^o}nio Fernando and de Melo, Marco Ant{\\^o}nio Fran{\\c{c}}a and de Brito, Jo{\\~a}o Carlos Xavier and de Almeida, Tarqu{\\'\\i}nio Prisco Fernandes and Mansur, Gilson Leite"),
 ("title", "Manual de Gerenciamento Integrado de Res{\\'\\i}duos S{\\'o}lidos"),
 ("publisher", "IBAM"), ("address", "Rio de Janeiro"), ("year", "2001"),
 ("note", "Coordena{\\c{c}}{\\~a}o t{\\'e}cnica: Victor Zular Zveibil. Patroc{\\'\\i}nio: SEDU/PR")],
 tipo="manual técnico (IBAM/SEDU-PR)", metodo="Manual técnico",
 res="Peso específico aparente do lixo domiciliar 230 kg/m³ (p. 35); contêineres 120/240/360 L e 760/1.100 L (p. 49); compactadores traseiros de 6, 10, 12, 15 e 19 m³ (p. 72); taxa de compactação ≥ 3:1 (p. 71); exemplo: 4 km/h em coleta, 40 km/h em transferência, 5,5 t/viagem em compactador de 12 m³ (Tab. 1, p. 17–18).",
 lim="2001; valores 'na ausência de dados mais precisos'; exemplo de cidade hipotética.", rel="muito alta (parâmetros brasileiros)", txt="sim",
 trecho="'podem-se utilizar os valores de 230kg/m3 para o peso específico do lixo domiciliar' (p. 35); 'capacidade volumétrica útil de 6, 10, 12, 15 e 19m³' (p. 72)",
 via="PDF (ficha catalográfica conferida); cópia obtida em unijales.edu.br — recomenda-se citar com indicação de que é publicação IBAM/SEDU")
add("epa2016volume", "misc", [
 ("author", "{U.S. Environmental Protection Agency}"), ("title", "Volume-to-Weight Conversion Factors"), ("year", "2016"),
 ("howpublished", "\\url{https://www.epa.gov/sites/production/files/2016-04/documents/volume_to_weight_conversion_factors_memorandum_04192016_508fnl.pdf}"),
 ("note", "Office of Resource Conservation and Recovery, abr. 2016. " + ACESSO)],
 tipo="documento técnico governamental (EUA)", metodo="Compilação de fatores",
 res="RSU misto (residencial, institucional, comercial): não compactado 250–300 lb/yd³; compactado 400–700 lb/yd³ (p. 5; fonte primária: Caterpillar Performance Handbook, 40ª ed.).",
 lim="Contexto dos EUA; fonte secundária.", rel="alta (faixa de densidade)", txt="sim",
 trecho="'Mixed MSW - Residential, Institutional, Commercial — Uncompacted cubic yard 250-300; Compacted cubic yard 400-700' (p. 5)", via="PDF oficial EPA")
add("ipcc2006guidelines", "misc", [
 ("author", "{IPCC}"), ("title", "2006 {IPCC} Guidelines for National Greenhouse Gas Inventories. Volume 2: Energy"), ("year", "2006"),
 ("howpublished", "\\url{https://www.ipcc-nggip.iges.or.jp/public/2006gl/vol2.html}"),
 ("note", "Eggleston, H. S.; Buendia, L.; Miwa, K.; Ngara, T.; Tanabe, K. (eds.). IGES, Jap{\\~a}o. Cap. 1 (Tab. 1.2) e Cap. 3, Mobile Combustion (Tab. 3.2.1). " + ACESSO)],
 tipo="diretriz metodológica (IPCC)", metodo="—",
 res="Fator padrão de CO2 para gasóleo/diesel no transporte rodoviário: 74.100 kg/TJ (intervalo 72.600–74.800) (Tab. 3.2.1, p. 3.16); PCI padrão do diesel 43,0 TJ/Gg (Tab. 1.2).",
 lim="Conversão para kg CO2/L exige densidade do diesel (fonte nacional, ex.: ANP/MCTI) — não verificada aqui.",
 rel="alta (emissões)", txt="sim", trecho="'Gas/ Diesel Oil 74 100 72 600 74 800' (Tab. 3.2.1)",
 via="PDFs oficiais ipcc-nggip.iges.or.jp (citação conforme capa do volume)")

# ---------------------------------------------------------------- contexto brasileiro oficial
add("brasil2010lei", "misc", [
 ("author", "Brasil"),
 ("title", "Lei n{\\textordmasculine}~12.305, de 2 de agosto de 2010. Institui a Pol{\\'\\i}tica Nacional de Res{\\'\\i}duos S{\\'o}lidos; altera a Lei n{\\textordmasculine}~9.605, de 12 de fevereiro de 1998; e d{\\'a} outras provid{\\^e}ncias"),
 ("year", "2010"), ("howpublished", "\\url{https://www.planalto.gov.br/ccivil_03/_ato2007-2010/2010/lei/l12305.htm}"),
 ("note", "Di{\\'a}rio Oficial da Uni{\\~a}o. " + ACESSO)],
 tipo="legislação", metodo="—", res="Art. 3º, X e XI (gerenciamento/gestão integrada); art. 9º (ordem de prioridade).", lim="—",
 rel="alta", txt="sim", trecho="Art. 9º: 'não geração, redução, reutilização, reciclagem, tratamento dos resíduos sólidos e disposição final ambientalmente adequada dos rejeitos'",
 via="planalto.gov.br (WebFetch)")
add("brasil2020lei", "misc", [
 ("author", "Brasil"),
 ("title", "Lei n{\\textordmasculine}~14.026, de 15 de julho de 2020. Atualiza o marco legal do saneamento b{\\'a}sico"),
 ("year", "2020"), ("howpublished", "\\url{https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14026.htm}"),
 ("note", "Di{\\'a}rio Oficial da Uni{\\~a}o. " + ACESSO)],
 tipo="legislação", metodo="—", res="Art. 11 altera a Lei 12.305/2010 (nova redação do art. 54, prazos de disposição final).", lim="—",
 rel="média-alta", txt="sim (ementa e art. 54)", trecho="'Atualiza o marco legal do saneamento básico e altera a Lei nº 9.984...'", via="planalto.gov.br (WebFetch)")
add("brasil2025sinisa", "misc", [
 ("author", "{Brasil. Minist{\\'e}rio das Cidades}"),
 ("title", "Relat{\\'o}rio dos Servi{\\c{c}}os de Limpeza Urbana e Manejo de Res{\\'\\i}duos S{\\'o}lidos: {SINISA} 2025, ano de refer{\\^e}ncia 2024"),
 ("year", "2025"), ("howpublished", "\\url{https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa/RELATORIO_SINISA_RESIDUOS_SOLIDOS_2025.pdf}"),
 ("note", "Secretaria Nacional de Saneamento Ambiental. Bras{\\'\\i}lia, dez. 2025. " + ACESSO)],
 tipo="relatório oficial", metodo="Coleta de dados SINISA junto a municípios/prestadores",
 res="RSU coletado per capita (IRS1004): 1,14 kg/hab.dia (Brasil), 1,21 (Nordeste) (p. 25); RDO (IRS1005): 0,84 Brasil, 0,88 Nordeste (p. 26); massa total estimada 88,1 Mt/ano.",
 lim="Massa coletada (não gerada); IRS1005 e IRS1006 não somam IRS1004.", rel="muito alta (parâmetro de geração)", txt="sim",
 trecho="'1,14 (kg/hab.dia) quantidade de resíduos sólidos urbanos coletada por habitante' (p. 25); 'Nordeste 0,88 kg/hab.dia' (IRS1005, p. 26)",
 via="PDF oficial gov.br (pdftotext)")
add("brasil2025sinisa2024", "misc", [
 ("author", "{Brasil. Minist{\\'e}rio das Cidades}"),
 ("title", "Relat{\\'o}rio dos Servi{\\c{c}}os de Limpeza Urbana e Manejo de Res{\\'\\i}duos S{\\'o}lidos: {SINISA} 2024, ano de refer{\\^e}ncia 2023"),
 ("year", "2025"), ("howpublished", "\\url{https://www.gov.br/cidades/pt-br/acesso-a-informacao/acoes-e-programas/saneamento/sinisa/resultados-sinisa/RELATORIO_SINISA_RESIDUOS_SOLIDOS_2024.pdf}"),
 ("note", "Secretaria Nacional de Saneamento Ambiental. Bras{\\'\\i}lia, mar. 2025. " + ACESSO)],
 tipo="relatório oficial", metodo="Idem", res="IRS1004: 1,04 kg/hab.dia (Brasil), 1,14 (Nordeste) (p. 23); IRS1005: 0,81 Brasil, 0,84 Nordeste (p. 24).",
 lim="Edição anterior; usar para análise de sensibilidade.", rel="alta", txt="sim", trecho="'1,04 (kg/hab.dia)' (p. 23)", via="PDF oficial gov.br")
add("abrema2026panorama", "misc", [
 ("author", "{ABREMA}"), ("title", "Panorama of Solid Waste in Brazil 2025"), ("year", "2026"),
 ("howpublished", "\\url{https://www.abrema.org.br/wp-content/uploads/2026/03/Panorama2025_ABREMA_EN.pdf}"),
 ("note", "Associa{\\c{c}}{\\~a}o Brasileira de Res{\\'\\i}duos e Meio Ambiente. Edi{\\c{c}}{\\~a}o em ingl{\\^e}s do Panorama dos Res{\\'\\i}duos S{\\'o}lidos no Brasil 2025 (ano-base 2024). " + ACESSO)],
 tipo="relatório setorial", metodo="Estimativas por projeção de séries históricas e indicadores socioeconômicos (metodologia publicada à parte)",
 res="Geração per capita 2024: 1,051 kg/hab/dia (Brasil), 0,967 (Nordeste); 81,6 Mt/ano (Seç. 3.1, p. 20, e Fig. 3.3, p. 22, da edição em inglês; p. 22 e 24 do arquivo PDF).",
 lim="Estimativa (não medição); entidade setorial; diverge do SINISA (massa coletada).", rel="alta", txt="sim",
 trecho="'each inhabitant generating, on average, 1.051 kg of MSW per day' (p. 20); Fig. 3.3 'Northeast 0.959 [2023] / 0.967 [2024]'",
 via="PDF oficial abrema.org.br (versão EN; PDF PT não localizado em acesso aberto)")
add("ibge2022censo", "misc", [
 ("author", "{IBGE}"),
 ("title", "Censo Demogr{\\'a}fico 2022: Tabela 4709 -- Popula{\\c{c}}{\\~a}o residente, varia{\\c{c}}{\\~a}o absoluta de popula{\\c{c}}{\\~a}o residente e taxa de crescimento geom{\\'e}trico"),
 ("year", "2022"), ("howpublished", "\\url{https://sidra.ibge.gov.br/tabela/4709}"),
 ("note", "Sistema IBGE de Recupera{\\c{c}}{\\~a}o Autom{\\'a}tica (SIDRA). Aracaju (SE), c{\\'o}digo 2800308. " + ACESSO)],
 tipo="dados oficiais", metodo="Censo", res="Aracaju: 602.757 pessoas residentes (2022).", lim="—", rel="alta", txt="sim (consulta à API)",
 trecho="API SIDRA agregado 4709, variável 93, N6[2800308] → '602757'", via="servicodados.ibge.gov.br (API v3)")

# ---------------------------------------------------------------- utilitários geográficos (condicionais)
add("boeing2017osmnx", "article", [
 ("author", "Boeing, Geoff"), ("title", "{OSMnx}: New methods for acquiring, constructing, analyzing, and visualizing complex street networks"),
 ("journal", "Computers, Environment and Urban Systems"), ("year", "2017"), ("volume", "65"), ("pages", "126--139"), ("doi", "10.1016/j.compenvurbsys.2017.05.004")],
 tipo="artigo de software", metodo="—", res="—", lim="Citar só se OSMnx for usado.", rel="condicional", txt="nao", trecho="—", via=CR)
add("haklay2008openstreetmap", "article", [
 ("author", "Haklay, M. and Weber, P."), ("title", "{OpenStreetMap}: User-Generated Street Maps"),
 ("journal", "IEEE Pervasive Computing"), ("year", "2008"), ("volume", "7"), ("number", "4"), ("pages", "12--18"), ("doi", "10.1109/MPRV.2008.80")],
 tipo="artigo de periódico", metodo="—", res="—", lim="Citar só se dados OSM forem usados.", rel="condicional", txt="nao", trecho="—", via=CR)


# ================================================================= escrita
LATEX = [("{\\'a}","á"),("{\\'e}","é"),("{\\'o}","ó"),("{\\'u}","ú"),("{\\'\\i}","í"),("{\\~a}","ã"),("{\\~o}","õ"),
         ("{\\^a}","â"),("{\\^e}","ê"),("{\\^o}","ô"),("{\\c{c}}","ç"),("{\\'A}","Á"),('{\\"e}',"ë"),
         ("{\\textordmasculine}","º"),("\\&","&"),("--","–"),("~"," "),("$k$","k")]
def plain(s):
    for a,b in LATEX: s = s.replace(a,b)
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    return s.replace("{","").replace("}","")

def bib():
    out = ["% referencias.bib -- gerado em 2026-11-14; todos os metadados conferidos (ver biblioteca.csv, coluna verificado_via)",
           "% Entradas web/oficiais usam @misc + howpublished + note com data de acesso.", ""]
    for key, typ, fields, meta in E:
        out.append("@%s{%s," % (typ, key))
        for k, v in fields:
            out.append("  %s = {%s}," % (k, v))
        out[-1] = out[-1].rstrip(",")
        out.append("}\n")
    return "\n".join(out)

def csvrows():
    rows = []
    for key, typ, fields, meta in E:
        f = dict(fields)
        aut = plain(f.get("author", f.get("editor", "")) ).replace(" and ", "; ")
        veic = plain(f.get("journal") or f.get("booktitle") or f.get("publisher") or "")
        url = plain(f.get("url", "") or f.get("howpublished", ""))
        if not url and f.get("doi"): url = "https://doi.org/" + f["doi"]
        rows.append([key, aut, plain(f["title"]), f.get("year",""), veic, f.get("doi",""), url, DA,
                     meta["tipo"], meta["metodo"], meta["res"], meta["lim"], meta["rel"], meta["txt"], meta["trecho"], meta["via"]])
    return rows

if __name__ == "__main__":
    keys = [e[0] for e in E]
    assert len(keys) == len(set(keys)), "chave duplicada"
    for k in keys: assert re.fullmatch(r"[a-z0-9]+", k), k
    open(OUT + "referencias.bib", "w", encoding="utf-8").write(bib())
    with open(OUT + "biblioteca.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_ALL)
        w.writerow(["id","autores","titulo","ano","veiculo","doi","url","data_acesso","tipo_fonte","metodo","resultados_reportados","limitacoes","relevancia","texto_completo_consultado","trechos_que_fundamentam","verificado_via"])
        w.writerows(csvrows())
    print(len(E), "entradas")
