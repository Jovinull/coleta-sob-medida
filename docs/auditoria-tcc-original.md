# Auditoria do TCC original (artigo SBC, 2024)

Material auditado: `original/tcc-artigo-sbc-2024/` (preservado sem alterações;
SHA-256 em `original/SHA256SUMS`). PDF recompilado em 2026 para referência:
`original/pdf/tcc-2024-compilado-2026.pdf` (8 páginas). O projeto Overleaf
não pôde ser acessado nesta sessão (extensão do navegador desconectada); a
auditoria usa a cópia local, que corresponde ao projeto LaTeX do artigo.

Prioridade: **A** crítica (compromete a validade), **B** importante, **C** forma.

## 1. Problemas científicos e metodológicos

| # | Prioridade | Problema | Evidência no texto | Tratamento na versão 2026 |
|---|---|---|---|---|
| 1 | A | Afirma "revisões sistemáticas da literatura" sem protocolo, bases, critérios ou contagens | Resumo; Conclusão, §3 | Revisão narrativa declarada como tal; critérios de seleção explícitos; nenhuma alegação de revisão sistemática |
| 2 | A | Conclusões sobre otimização de rotas, redução de custos e eficiência sem nenhum experimento que as sustente | Resumo; Conclusão | Experimentos de simulação com 30 réplicas pareadas, IC 95% e testes com correção de Holm |
| 3 | A | Fórmula de "percentual de volume" mede espaço vazio: `percentMax = distância/Tmax·100` cresce quando a lixeira esvazia; sem limites físicos | Seção 3, equação; `MQTT.ino`, l. 80 | Ocupação = 100·(H − (d − off))/H, limitada a [0, 100], com validação de faixa (testes automatizados) |
| 4 | A | "Temperatura" publicada é o índice de calor | `MQTT.ino`, l. 129–134 | Firmware publica a temperatura do ar |
| 5 | A | Testes descritos qualitativamente ("leitura precisa", "leituras consistentes") sem números, repetições ou critério de aceitação | Seção 3.1 | Protótipo original registrado como evidência qualitativa; nova avaliação é quantitativa e por simulação |
| 6 | B | Afirmação de que o MQTT "garante a entrega" e "eficiência energética" sem distinguir níveis de QoS nem medir consumo | Seção 3 | Discussão por QoS; o firmware (PubSubClient) só publica com QoS 0; consumo não medido é declarado como tal |
| 7 | B | Broker público sem autenticação/TLS apresentado como escolha adequada | Seção 3 | Broker local isolado; requisitos de segurança para implantação discutidos separadamente |
| 8 | B | Ausência de problema de pesquisa, questões, hipóteses e métricas | Introdução | QP1–QP5, hipóteses pré-especificadas, métricas definidas |
| 9 | B | "Estudos de Caso" resume três trabalhos sem comparação crítica; um deles (Sruthi e Manjunath) não pôde ser verificado (ano 2010 implausível) | Seção 4 | Referência removida; tabela comparativa de trabalhos relacionados verificados |
| 10 | B | Citação inadequada: página da OPAS sobre dengue usada para sustentar contaminação de solo, água e ar | Seção 2, §2 | Substituída por fontes que sustentam a afirmação |
| 11 | B | DHT11 justificado como influenciando o "nível de enchimento" sem fundamento | Seção 3 | Papel do DHT11 restrito à compensação da velocidade do som e ao monitoramento ambiental |
| 12 | C | Adjetivação sem evidência ("crucial", "robusta", "significativo", "inovadora") | todo o texto | Linguagem descritiva e verificável |

## 2. Problemas de LaTeX e formatação

| # | Problema | Efeito |
|---|---|---|
| 13 | `inputenc` carregado duas vezes (`utf8` e `latin1`) | Erro "Option clash for package inputenc" |
| 14 | `\author`/`\address` comentados | Erro "Undefined control sequence" em `\maketitle`; aviso "No \author given" |
| 15 | Apóstrofo solto antes de `\section{Metodologia}` | Caractere "'" impresso no PDF |
| 16 | Datasheets com `year = {Year}` e `author = {Manufacturer}` | Citações "[Systems Year]", "[Manufacturer Yearb]" |
| 17 | Figura referenciada por número fixo ("Figura 2") em vez de `\ref` | Numeração frágil |
| 18 | Erros de digitação: "tambfoim", "descrito a metodologia", "incluindo e os", "subscriber" no título da figura | — |
| 19 | `babel` com opção `brazil` (obsoleta) | Aviso |

## 3. Referências (detalhe em `paper/references/auditoria_referencias_originais.md`)

1 correta, 8 corrigidas (autores incompletos ou corrompidos, anos ausentes,
DOI), 1 não verificável (removida) e 1 inadequada para a afirmação.

## 4. O que foi preservado

Tema (IoT e MQTT na gestão de RSU), arquitetura em três camadas como ponto de
partida, hardware (ESP32, HC-SR04, DHT11), autoria e instituição (IFS, campus
Lagarto), formato de artigo SBC. O protótipo físico e seus testes qualitativos
são relatados como trabalho anterior (2024), sem reinterpretação como
resultado quantitativo.
