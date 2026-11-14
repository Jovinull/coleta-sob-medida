# Contrato de mensagens MQTT — versão 1 do esquema

Este documento é a referência única para o firmware ESP32 (`firmware/`), para os
dispositivos virtuais do simulador (`wastesim/`) e para o serviço de ingestão.

## Versão do protocolo

* **MQTT 3.1.1** (OASIS Standard, 2014) em todos os componentes.
  * O firmware usa `PubSubClient`, que implementa apenas MQTT 3.1/3.1.1 e só
    publica com QoS 0 (assina com QoS 0 ou 1).
  * O simulador e a ingestão usam `paho-mqtt` 2.x configurado com
    `protocol=MQTTv311`, para manter a paridade com o firmware.
  * O broker é o Eclipse Mosquitto 2.0.x, que também aceita MQTT 5.0; recursos
    exclusivos do 5.0 (propriedades, *message expiry*, *topic alias*) **não** são
    usados.

## Tópicos

Prefixo padrão: `residuos` (configurável). `{id}` segue o padrão `LX-[0-9]{4}`
ou outro identificador ASCII sem `/`, `+` ou `#`.

| Tópico | Direção | QoS | Retido | Conteúdo |
|---|---|---|---|---|
| `residuos/dispositivos/{id}/telemetria` | dispositivo → plataforma | 0 (firmware) / 1 (simulador) | não | leituras periódicas |
| `residuos/dispositivos/{id}/estado` | dispositivo → plataforma | 1 | **sim** | `online`/`offline`; também usado como *Last Will* |
| `residuos/dispositivos/{id}/eventos` | dispositivo → plataforma | 0/1 | não | alertas e eventos discretos |
| `residuos/dispositivos/{id}/comandos` | plataforma → dispositivo | 1 | não | comandos remotos |

Assinatura da ingestão: `residuos/dispositivos/+/telemetria`,
`residuos/dispositivos/+/estado`, `residuos/dispositivos/+/eventos`.

## Payloads (JSON, UTF-8)

Campos comuns: `v` (versão do esquema, inteiro, = 1), `id` (identificador do
dispositivo), `ts` (instante da medição em segundos desde a época Unix, UTC),
`ts_src` (`"ntp"`, `"sim"` ou `"uptime"` — indica a origem do relógio).

### Telemetria

```json
{
  "v": 1,
  "id": "LX-0007",
  "boot": 4,
  "seq": 1532,
  "ts": 1731580000,
  "ts_src": "ntp",
  "leituras": [
    {"tipo": "distancia",   "valor": 31.2, "unidade": "cm",   "valida": true},
    {"tipo": "ocupacao",    "valor": 37.6, "unidade": "%",    "valida": true},
    {"tipo": "temperatura", "valor": 28.0, "unidade": "degC", "valida": true},
    {"tipo": "umidade",     "valor": 70.0, "unidade": "%RH",  "valida": true}
  ],
  "rssi": -61
}
```

* `boot`: contador de inicializações do dispositivo, persistido em memória
  não volátil (NVS no ESP32). Junto com `seq`, identifica unicamente a mensagem.
* `seq`: inteiro sem sinal, incrementado a cada telemetria publicada desde o
  último boot; volta a 0 após reinicialização.
* `valida = false` quando a leitura falhou (tempo esgotado do eco, NaN do DHT,
  valor fora da faixa física). Nesse caso `valor` é `null`.
* `ocupacao` é derivada da distância: `100 × (H − d) / H`, limitada a [0, 100],
  com `H` = altura útil configurada (distância sensor → fundo menos o
  deslocamento de montagem). Ver `docs/modelo-sensor.md`.
* `temperatura` é a temperatura do ar medida pelo DHT11 (**não** o índice de
  calor).
* Leituras opcionais podem ser omitidas (ex.: dispositivos sem DHT11).

### Estado (retido)

```json
{"v": 1, "id": "LX-0007", "estado": "online", "ts": 1731580000, "fw": "2.0.0"}
```

*Last Will and Testament* registrado na conexão, no mesmo tópico, retido, QoS 1:

```json
{"v": 1, "id": "LX-0007", "estado": "offline", "motivo": "lwt"}
```

### Eventos

```json
{"v": 1, "id": "LX-0007", "seq": 12, "ts": 1731580000,
 "tipo": "limiar_excedido", "detalhe": {"ocupacao": 81.3, "limiar": 80}}
```

Tipos definidos: `reinicio`, `limiar_excedido`, `limiar_normalizado`,
`sensor_falha`, `sensor_recuperado`, `reconexao`. `seq` de eventos é uma
sequência independente da telemetria.

### Comandos

```json
{"cmd": "intervalo", "valor": 300}
{"cmd": "led", "valor": true}
{"cmd": "ping"}
```

O dispositivo responde a `ping` com um evento `pong`.

## Regras de ingestão

1. Rejeitar (e contar) mensagens com JSON inválido, `v` desconhecido, `id`
   divergente do tópico ou campos obrigatórios ausentes.
2. Deduplicar por `(id, boot, seq)`; mensagens repetidas são contadas, não
   reaplicadas.
3. Mensagens fora de ordem (`ts` anterior ao último estado aplicado) são
   armazenadas no histórico mas não sobrescrevem o estado corrente.
4. O estado de um dispositivo é considerado **desatualizado** quando não há
   telemetria válida há mais de `k` períodos nominais (padrão `k = 3`).
