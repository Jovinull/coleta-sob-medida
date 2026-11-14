# Desvios e emendas ao protocolo experimental

Registro das alterações feitas depois do início das rodadas definitivas, com
motivo e efeito. Nenhum resultado foi apagado: os registros substituídos estão
em `experiments/raw/superseded/`.

## Emenda 1 — 14/11/2026, após revisão independente do código

Uma revisão do código feita por um revisor que não participou da implementação
(agente de IA separado, com acesso somente de leitura) apontou quatro problemas
que afetariam conclusões. As rodadas foram interrompidas (E1 e E2 completos; E3
com 873 de 1.860 execuções; E4 e E5 não iniciados) e as correções abaixo foram
aplicadas antes de retomar.

| # | Problema | Correção | Efeito sobre os dados |
|---|---|---|---|
| 1 | Política A usava a taxa média **sem** os descartes volumosos (≈ 3,5% do volume no cenário-base), contrariando a premissa documentada de "histórico perfeito" e desfavorecendo A | A passa a usar `mu_total_l_day` (taxa média + valor esperado dos eventos) | **Todas** as execuções de A (E1, E2, E3) foram refeitas; as anteriores estão em `superseded/*_politicaA_v1.jsonl`. As demais políticas não usam essa grandeza e seus resultados não mudam |
| 2 | E2: a grade de limiares não fazia todas as políticas atravessarem 1% e 2% de transbordamento; a interpolação ficava restrita a um subconjunto não aleatório de sementes | Níveis adicionais: θ = 0,3 e 0,4 para B-OR e C; θ = 1,0 para D | +100 execuções no E2 |
| 3 | E4 "frota reduzida" (utilização-alvo 0,95) produzia a mesma frota da base (2 veículos), ou seja, condição idêntica à base | Frota fixada em 1 veículo | E4 ainda não havia sido executado |
| 4 | E5: o limite de 5 s seria aplicado também à descida gulosa, truncando-a | Descida gulosa com salvaguarda de 30 s (igual ao E1); GLS com 5 s | E5 ainda não havia sido executado |

Itens menores apontados e **não** corrigidos no código (documentados como limitações):
- a semente do sorteio de fases de amostragem consome números aleatórios de forma
  diferente quando o período é de 15 min, o que enfraquece (mas não enviesa) o
  pareamento dessa condição com a base no E3;
- B e C estimam a carga dos veículos pelo nível observado no planejamento, e não
  pelo nível esperado na hora da visita, o que gera mais desvios de descarga para
  essas políticas (efeito contra B e C);
- a métrica de espera (80% → coleta) considera apenas episódios encerrados por
  coleta; episódios censurados no fim do horizonte não entram;
- a disponibilidade de telemetria conta leituras válidas entregues, inclusive as
  que chegam atrasadas e são descartadas como fora de ordem;
- a taxa *a priori* da ingestão é inicializada com a mediana verdadeira das taxas
  (efeito restrito ao aquecimento, que é descartado);
- `route_h_mean` subestima a duração de rotas encerradas por inviabilidade de
  recurso (métrica não usada no artigo);
- o transbordamento dentro de um passo é contado antes da coleta no mesmo passo
  (artefato da resolução de 15 min).

Além disso, as famílias de Holm do E3 foram unificadas por métrica, como previsto
no protocolo (antes estavam divididas em "degradação" e "contra A"), e a
comparação B-OR × B foi mantida no E1 como comparação adicional à lista
pré-especificada.

## Ocorrências durante a execução (14/11/2026)

- **E5 interrompido.** O processo do E5 recebeu um sinal de término (SIGTERM, de
  origem não identificada) após 54 das 60 execuções. As 6 restantes foram
  executadas ao retomar pelo *checkpoint* (`experiments/raw/E5.jsonl`), com a
  máquina ociosa. Como a GLS é limitada por tempo de relógio, as execuções GLS
  dependem da carga da máquina; isso já excluía o E5/GLS da verificação de
  reprodutibilidade.
- **E6/T2: equivalência lote × *live*.** A comparação pré-especificada (lote
  com canal ideal × modo *live* com broker real) **não** resultou em métricas
  idênticas (89 × 90 visitas; 4 × 3 transbordamentos em 6 dias). A causa foi
  isolada: o contrato MQTT arredonda distância e ocupação a 0,1 cm / 0,1 %, e o
  lote usa precisão total; uma decisão de limiar mudou. Foi acrescentada ao
  simulador a opção `quantize_payload` (padrão desligado; não afeta E1–E5) e uma
  segunda comparação (lote com o mesmo arredondamento × *live*), que resultou
  idêntica nas cinco métricas. O teste T2 foi reexecutado isoladamente depois
  dessa alteração (campo `rerun_at` em `experiments/results/E6_mqtt.json`); os
  demais testes do E6 são da execução original. O resultado negativo da
  comparação original é relatado no artigo.
