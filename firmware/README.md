# Firmware da lixeira inteligente — ESP32 (versão 2.0.0)

Reescrita do firmware do TCC (`original/MQTT.ino`) que corrige os defeitos
listados em [`AUDITORIA.md`](AUDITORIA.md) e segue o contrato
[`docs/mqtt/contrato-mqtt.md`](../docs/mqtt/contrato-mqtt.md) (MQTT 3.1.1,
esquema `v = 1`).

> **Segurança:** o firmware original e o `original/readme.md` publicaram
> **credenciais Wi-Fi em texto claro** num repositório público, e elas também
> estão no histórico do Git. **Troque a senha dessa rede.** Apagar o arquivo ou
> reescrever o histórico não desfaz a exposição. No firmware novo, as
> credenciais ficam só em `config.h`, que está no `.gitignore`.

## Situação da verificação

| Verificação | Situação |
|---|---|
| Compilação real (arduino-cli, FQBN `esp32:esp32:esp32doit-devkit-v1`, `--warnings all`) | **Feita, sem erros e sem avisos** em 4 variantes de `config.h`: padrão, TLS com CA, sem DHT com log de depuração, Wokwi/DHT22. Log completo em [`build/compile-log.txt`](build/compile-log.txt). |
| Uso de recursos (variante padrão) | Flash: **941 910 B de 1 310 720 B (71 %)**. RAM estática: **51 284 B de 327 680 B (15 %)**. Variante com TLS: 1 031 802 B (78 %) de flash e 51 828 B de RAM. |
| Funções puras (`calculos.h`: ocupação, mediana, velocidade do som, backoff) | Testadas no computador hospedeiro com g++ (asserções), todas passaram. O teste ficou fora do repositório. |
| Execução em hardware real | **Não realizada** (não havia placa disponível neste ambiente). |
| Simulação Wokwi | **Não executada.** O `wokwi-cli` exige `WOKWI_CLI_TOKEN`, que não temos. Os arquivos em `wokwi/` estão prontos para uso, mas não foram rodados. |
| Teste contra o Mosquitto local | **Não realizado** (depende do hardware ou do simulador). Procedimento na seção [Teste com o Mosquitto local](#teste-com-o-mosquitto-local). |

## Estrutura

```
firmware/
├── AUDITORIA.md              auditoria do firmware original (defeitos, evidências, fontes)
├── README.md                 este arquivo
├── build/compile-log.txt     log da compilação (versões, avisos, flash/RAM)
├── esp32_lixeira/            sketch Arduino
│   ├── esp32_lixeira.ino     agendador, telemetria, eventos, comandos, NVS, watchdog
│   ├── config.example.h      modelo de configuração (copiar para config.h)
│   ├── configuracao.h        inclui config.h, deriva constantes, static_asserts
│   ├── calculos.h            funções puras (ocupação, mediana, c(T), backoff)
│   ├── sensores.h/.cpp       HC-SR04 (rajada + mediana, não bloqueante) e DHT
│   ├── rede.h/.cpp           máquina de estados Wi-Fi/MQTT, LWT, NTP
│   ├── registro.h            log serial com níveis
│   └── .gitignore            ignora config.h
└── wokwi/                    diagram.json + wokwi.toml (simulação; não executada)
```

## Hardware

| Qtde | Componente | Observação |
|---|---|---|
| 1 | DOIT ESP32 DevKit V1 (30 pinos, ESP32-WROOM-32) | Lógica de 3,3 V; flash de 3,3 V |
| 1 | HC-SR04 | Alimentação de 5 V; o ECHO sai em ~5 V (ver divisor). Alternativa: **HC-SR04P** (3–5,5 V) alimentado a 3,3 V, sem divisor |
| 1 | DHT11 (módulo de 3 pinos ou sensor de 4 pinos) | Alimentar em **3,3 V** |
| 1 | Resistor de 1 kΩ | Divisor do ECHO (série) |
| 1 | Resistor de 2 kΩ (ou 2 × 1 kΩ em série) | Divisor do ECHO (para GND) |
| 1 | Resistor de 10 kΩ (4,7–10 kΩ) | *Pull-up* do DHT11 para 3,3 V. Dispensável se o módulo já tiver |
| — | Fonte de 5 V (USB) e cabos | GND comum a todos os componentes |

### Mapa de pinos

| Sinal | GPIO | Rótulo na DevKit V1 | Direção | Observação |
|---|---|---|---|---|
| HC-SR04 TRIG | 14 | D14 | saída | 3,3 V basta como nível alto TTL para o TRIG. GPIO14 é MTMS (JTAG), mas não é *strapping* |
| HC-SR04 ECHO | **27** | D27 | entrada | **Via divisor resistivo.** No original era o GPIO12 (ver abaixo) |
| DHT11 DATA | 4 | D4 | bidirecional | *Pull-up* para 3,3 V |
| LED | 2 | D2 (LED azul da placa) | saída | GPIO2 é *strapping* do modo de boot. O LED da placa não força nível alto no reset |

**Por que GPIO27, e não o GPIO12 do original.** O GPIO12 (MTDI) é pino de
*strapping*: se estiver em nível alto no reset, o ESP32 alimenta a flash pelo
LDO de 1,8 V. A flash do ESP32-WROOM-32 é de 3,3 V, e o resultado é falha de
boot (ESP32 Series Datasheet §3.2, ESP32-WROOM-32 Datasheet Tab. 15). Se o
ESP32 reiniciar no meio de um pulso de eco, o ECHO estará alto. O GPIO27 não
tem função de *strapping*, fica no conector ao lado do D14 (ordem
D12–D14–D27) e não está entre os pinos de flash (6–11) nem entre os somente
entrada (34–39). Outras opções livres: 25, 26, 32, 33.

### Conversão de nível do ECHO (5 V → 3,3 V)

O datasheet do ESP32 (Tab. 5-3) limita a entrada dos GPIOs a
V_IH,max = VDD + 0,3 V ≈ **3,6 V**. Com o HC-SR04 alimentado a 5 V, o ECHO
fica em ~5 V e passa desse limite. Use o divisor:

```
HC-SR04 ECHO ──[ R1 = 1 kΩ ]──┬──> GPIO27
                              │
                         [ R2 = 2 kΩ ]
                              │
                             GND
```

V_GPIO = 5 V × R2 / (R1 + R2) = 5 × 2/3 ≈ **3,33 V**, abaixo de 3,6 V e acima
de V_IH,min = 0,75 × 3,3 V ≈ 2,48 V. A corrente é de 5 V / 3 kΩ ≈ 1,7 mA. O R2
também mantém o pino em nível baixo enquanto o sensor está desconectado.
Alternativas: 2,2 kΩ / 3,3 kΩ (≈ 3,0 V), um conversor de nível bidirecional
(BSS138) ou o HC-SR04P alimentado a 3,3 V.

### Ligações

| De | Para | Observação |
|---|---|---|
| HC-SR04 VCC | VIN (5 V do USB) | |
| HC-SR04 GND | GND | |
| HC-SR04 TRIG | D14 | ligação direta |
| HC-SR04 ECHO | R1 (1 kΩ) → D27; D27 → R2 (2 kΩ) → GND | **obrigatório** com o HC-SR04 de 5 V |
| DHT11 VCC | 3V3 | **não** ligue a 5 V: o *pull-up* levaria a linha de dados a 5 V |
| DHT11 DATA | D4, com 10 kΩ entre D4 e 3V3 | datasheet: *pull-up* de 5 kΩ para cabos < 20 m |
| DHT11 GND | GND | |
| LED | já está na placa (D2) | um LED externo exige resistor de 220–330 Ω |

## Compilação (arduino-cli, versões fixadas)

Versões usadas e verificadas:

| Item | Versão |
|---|---|
| arduino-cli | 1.5.1 (binário oficial `arduino-cli_1.5.1_Linux_64bit.tar.gz`; SHA-256 conferido com `1.5.1-checksums.txt`) |
| Núcleo `esp32:esp32` (Espressif) | 3.3.12 (ESP-IDF 5.5.5) |
| PubSubClient (Nick O'Leary) | 2.8.0 |
| ArduinoJson (Benoît Blanchon) | 7.4.3 |
| DHT sensor library (Adafruit) | 1.4.7 |
| Adafruit Unified Sensor | 1.1.15 |

```bash
# 1. arduino-cli 1.5.1
curl -LO https://github.com/arduino/arduino-cli/releases/download/v1.5.1/arduino-cli_1.5.1_Linux_64bit.tar.gz
curl -LO https://github.com/arduino/arduino-cli/releases/download/v1.5.1/1.5.1-checksums.txt
grep Linux_64bit.tar.gz 1.5.1-checksums.txt | sha256sum -c -
tar xzf arduino-cli_1.5.1_Linux_64bit.tar.gz arduino-cli

# 2. núcleo ESP32 e bibliotecas
./arduino-cli config init
./arduino-cli config add board_manager.additional_urls \
  https://espressif.github.io/arduino-esp32/package_esp32_index.json
./arduino-cli core update-index
./arduino-cli core install esp32:esp32@3.3.12
./arduino-cli lib install "PubSubClient@2.8.0" "ArduinoJson@7.4.3" \
  "DHT sensor library@1.4.7" "Adafruit Unified Sensor@1.1.15"

# 3. configuração e compilação
cp firmware/esp32_lixeira/config.example.h firmware/esp32_lixeira/config.h
#    (edite config.h)
./arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 --warnings all \
  firmware/esp32_lixeira

# 4. gravação (porta pode variar: /dev/ttyUSB0, /dev/ttyACM0, COM3...)
./arduino-cli upload --fqbn esp32:esp32:esp32doit-devkit-v1 -p /dev/ttyUSB0 firmware/esp32_lixeira
./arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200
```

O pacote `esp32:esp32@3.3.12` instala toolchains e bibliotecas de **todos** os
chips (ESP32, S2, S3, C3, C5, C6, H2, P4) e precisa de vários GB de disco.
Neste ambiente, o `/tmp` não tinha espaço para isso. A instalação usou então
uma cópia local do índice oficial com o mesmo núcleo 3.3.12, mas com
`toolsDependencies` reduzidas ao necessário para o ESP32 clássico (`esp-x32`,
`esp32-libs`, `esptool_py`, `mkspiffs`, `mklittlefs`, `xtensa-esp-elf-gdb`). Os
arquivos baixados e seus checksums são os do índice oficial. Numa máquina
comum, use os comandos acima sem modificações.

## Configuração (`config.h`)

Copie `config.example.h` para `config.h` e ajuste:

| Grupo | Parâmetros | Padrão |
|---|---|---|
| Identidade | `CFG_ID_DISPOSITIVO` (também é o *client ID* MQTT, deve ser único), `CFG_PREFIXO_TOPICO` | `LX-0001`, `residuos` |
| Wi-Fi | `CFG_WIFI_SSID`, `CFG_WIFI_SENHA`, `CFG_WIFI_TIMEOUT_CONEXAO_MS` | marcadores, 20 s |
| Broker | `CFG_MQTT_HOST`, `CFG_MQTT_PORTA`, `CFG_MQTT_USUARIO`, `CFG_MQTT_SENHA` (vazio = sem autenticação), `CFG_MQTT_KEEPALIVE_S`, `CFG_MQTT_TIMEOUT_SOCKET_S`, `CFG_MQTT_TAMANHO_BUFFER` | `192.168.0.10:1883`, 30 s, 5 s, 1024 B |
| TLS (opcional) | `CFG_MQTT_TLS`, `CFG_MQTT_CA_PEM` (CA em PEM) ou, só em teste, `CFG_MQTT_TLS_INSEGURO` | desligado |
| Reconexão | `CFG_BACKOFF_BASE_MS`, `CFG_BACKOFF_MAX_MS` | 1 s, 60 s |
| NTP | `CFG_NTP_SERVIDOR_1/2` | `pool.ntp.org`, `time.google.com` |
| Pinos | `CFG_PINO_TRIG/ECHO/DHT/LED`, `CFG_LED_ATIVO_ALTO` | 14 / 27 / 4 / 2 |
| DHT | `CFG_HABILITAR_DHT`, `CFG_DHT_TIPO` (`DHT11`; `DHT22` no Wokwi) | 1, DHT11 |
| Geometria | `CFG_DIST_SENSOR_FUNDO_CM` (sensor → fundo vazio), `CFG_OFFSET_MONTAGEM_CM` (sensor → linha de 100 %, ≥ 2 cm), `CFG_MARGEM_PLAUSIVEL_CM` | 60, 5, 10 cm, o que dá **H = 55 cm** |
| Ultrassom | `CFG_US_PULSOS_POR_MEDICAO`, `CFG_US_MIN_PULSOS_VALIDOS`, `CFG_US_INTERVALO_PULSOS_MS`, `CFG_US_COMPENSAR_TEMPERATURA`, `CFG_US_TEMPERATURA_PADRAO_C` | 5, 3, 65 ms, 1, 25 °C |
| Alerta | `CFG_LIMIAR_ALERTA_PCT`, `CFG_HISTERESE_PCT` | 80 %, 5 % |
| Falha de sensor | `CFG_FALHAS_PARA_EVENTO` | 3 medições seguidas |
| Intervalos | `CFG_INTERVALO_MEDICAO_S` (≥ 2 s), `CFG_INTERVALO_PUBLICACAO_S` | 10 s, 60 s |
| Diversos | `CFG_NIVEL_LOG` (0–4), `CFG_SERIAL_BAUD`, `CFG_WATCHDOG_S` | 3 (info), 115200, 30 s |

Combinações inválidas, como offset ≥ distância ao fundo, intervalo de pulsos
< 60 ms, medição < 2 s ou TLS sem CA, param a compilação (`static_assert` e
`#error` em `configuracao.h`).

**Calibração da geometria.** Com a lixeira vazia e o sensor montado, meça a
distância do sensor ao fundo (ou leia o campo `distancia` da telemetria) e
grave em `CFG_DIST_SENSOR_FUNDO_CM`. `CFG_OFFSET_MONTAGEM_CM` é a distância do
sensor até o nível que se quer considerar 100 % (abaixo da tampa e fora da
zona morta de 2 cm).

## Funcionamento

### Medição

- A cada `CFG_INTERVALO_MEDICAO_S`, o firmware lê o DHT. Leituras NaN ou fora
  da faixa física (−40 a 80 °C, 0 a 100 %RH) ficam inválidas.
- Em seguida dispara uma **rajada de 5 pulsos** do HC-SR04, com 65 ms entre
  pulsos e um pulso por volta do `loop()`, sem bloquear a rede.
- Cada pulso usa `pulseIn()` com *timeout* calculado a partir da geometria:
  (fundo + margem) a −20 °C + 2 ms, ou ≈ 6,4 ms no padrão. Pulsos com
  *timeout* (retorno 0) ou com distância fora de [2 cm, fundo + margem] são
  descartados.
- Com ≥ 3 pulsos válidos, a distância é a **mediana** dos válidos. Caso
  contrário, a leitura fica `valida: false` e `valor: null`.
- Compensação de temperatura: d = t · c / 2, com **c = 331,3 + 0,606·T** m/s e
  T do DHT (25 °C se o DHT estiver inválido). Entre 10 °C e 40 °C, c varia
  ≈ 5 %. Em 55 cm de altura útil, isso dá ≈ 3 cm, ou seja, ≈ 5 pontos de
  ocupação.
- Ocupação: d_corr = d − offset e ocupação = 100·(H − d_corr)/H, limitada a
  [0, 100].

### Agendamento e conectividade

- Tudo roda no `loop()` com `millis()` (agendador seguro contra o estouro do
  contador), sem `delay()`. Medição e transmissão são tarefas separadas, e a
  telemetria publica a **última medição completa**, com o `ts` do instante da
  medição.
- Máquina de estados Wi-Fi → MQTT → operando. Cada falha agenda nova tentativa
  com **backoff exponencial com *jitter***: espera = U[e/2, e], e = min(60 s,
  1 s·2ⁿ). O único trecho bloqueante é o `connect()` do PubSubClient (DNS +
  TCP + CONNACK), limitado pelos *timeouts* configurados.
- O *watchdog* de tarefa (30 s) reinicia o ESP32 se o `loop()` travar.
- NTP via `configTime()` em UTC: `ts_src` = `"ntp"` depois da sincronização e
  `"uptime"` antes dela (nesse caso, `ts` = segundos desde o boot).
- NVS (`Preferences`, namespace `lixeira`): contador `boot`, incrementado a
  cada inicialização, e o `intervalo` de publicação recebido por comando.

### Tópicos e mensagens (contrato v1)

| Tópico | Conteúdo | QoS / retido |
|---|---|---|
| `residuos/dispositivos/{id}/telemetria` | `{v,id,boot,seq,ts,ts_src,leituras[distancia,ocupacao,temperatura,umidade],rssi}` | 0 / não |
| `residuos/dispositivos/{id}/estado` | ao conectar: `{v,id,estado:"online",ts,ts_src,fw:"2.0.0"}`; LWT: `{v,id,estado:"offline",motivo:"lwt"}` | online: 0 / **sim**; LWT: **1** / **sim** |
| `residuos/dispositivos/{id}/eventos` | `{v,id,boot,seq,ts,ts_src,tipo,detalhe}` | 0 / não |
| `residuos/dispositivos/{id}/comandos` (assinado) | `{"cmd":"intervalo","valor":300}`, `{"cmd":"led","valor":true}`, `{"cmd":"ping"}` | assinatura QoS 1 |

Detalhes:

- `seq` da telemetria começa em 0 a cada boot e só avança quando a publicação
  dá certo. Os eventos têm `seq` próprio. Ao lado de `boot`, o `seq` permite
  deduplicar por `(id, boot, seq)`.
- Eventos: `reinicio` (motivo do reset, boot, fw); `limiar_excedido`
  (ocupação ≥ 80 %); `limiar_normalizado` (ocupação < 80 − 5 = 75 %);
  `sensor_falha` e `sensor_recuperado` (`sensor` = `ultrassonico` ou `dht`,
  após 3 medições inválidas seguidas); `reconexao` (causa, tentativas,
  `offline_s`, `telemetrias_nao_enviadas`); `pong` (uptime, rssi, heap,
  intervalo, led, fw).
- Os eventos esperam numa fila de 8 posições até haver conexão. Com a fila
  cheia, o mais antigo é descartado, e a lacuna em `seq` mostra a perda.
- `intervalo` aceita inteiros em [`CFG_INTERVALO_MEDICAO_S`, 86400] s e grava
  o valor na NVS. Comandos inválidos são registrados na serial e ignorados.
- Logo após o boot e após cada reconexão, uma telemetria sai sem esperar o
  intervalo inteiro.
- Na queda do Wi-Fi, só o socket é fechado (sem DISCONNECT), para que o broker
  publique o LWT.

Diferenças em relação ao texto do contrato, todas compatíveis com as regras de
ingestão:

1. O `online` retido sai com **QoS 0**: o PubSubClient só publica com QoS 0,
   como o próprio contrato registra. O LWT usa QoS 1, que o PubSubClient
   aceita no CONNECT.
2. `ts_src`, um dos campos comuns do contrato, também é enviado em `estado` e
   `eventos`.
3. `boot` também é enviado nos eventos, para deduplicação.

O contrato cita `docs/modelo-sensor.md`, que ainda não existe no repositório.

## Teste com o Mosquitto local

O serviço `mosquitto` do `docker compose`, em criação por outro integrante,
escuta em `localhost:1883` **na máquina hospedeira**. Para o ESP32, `localhost`
é o próprio ESP32. Em `config.h`, use o **IP da máquina hospedeira na rede
local** (`ip -4 addr` ou `hostname -I`) e libere a porta 1883 no firewall
(ex.: `sudo firewall-cmd --add-port=1883/tcp` no Fedora).

```bash
# 1. sobe o broker
docker compose up -d mosquitto

# 2. acompanha tudo o que as lixeiras publicam (-v mostra o tópico)
docker compose exec mosquitto mosquitto_sub -h localhost -t 'residuos/#' -v
#   (com autenticação: acrescente -u <usuario> -P <senha>)

# 3. grava e abre o monitor serial (nível 4 em CFG_NIVEL_LOG mostra cada pulso)
arduino-cli upload ... && arduino-cli monitor -p /dev/ttyUSB0 -c baudrate=115200

# 4. comandos
docker compose exec mosquitto mosquitto_pub -h localhost -q 1 \
  -t residuos/dispositivos/LX-0001/comandos -m '{"cmd":"ping"}'
docker compose exec mosquitto mosquitto_pub -h localhost -q 1 \
  -t residuos/dispositivos/LX-0001/comandos -m '{"cmd":"led","valor":true}'
docker compose exec mosquitto mosquitto_pub -h localhost -q 1 \
  -t residuos/dispositivos/LX-0001/comandos -m '{"cmd":"intervalo","valor":30}'
```

O que conferir:

1. Logo após o boot: `estado` = `online` (retido), evento `reinicio` e
   telemetria com `seq` 0.
2. Mão ou objeto a < 16 cm do sensor (com H = 55 cm e offset = 5 cm, isso
   passa de 80 %): evento `limiar_excedido`. Ao afastar: `limiar_normalizado`.
3. DHT ou ECHO desconectados por mais de 3 medições: `sensor_falha`, com as
   leituras `valida: false` e `valor: null`. Ao religar: `sensor_recuperado`.
4. `docker compose stop mosquitto` e depois `start`: o evento `reconexao`
   aparece com o número de tentativas, e a serial mostra os intervalos
   crescentes do backoff.
5. Tirar o ESP32 da tomada: depois de ~1,5 × keepalive (≈ 45 s), o broker
   publica o LWT `offline` retido.

## Simulação no Wokwi (não executada)

`wokwi/diagram.json` monta uma DevKit V1 (`wokwi-esp32-devkit-v1`), um HC-SR04
(TRIG = D14, ECHO = D27, distância inicial de 40 cm), um **DHT22** em D4 e um
LED externo em D2.

- **O Wokwi não tem DHT11**: o catálogo tem `wokwi-dht22`, e a página
  `wokwi-dht11` não existe (conferido em docs.wokwi.com). Na simulação, use
  `#define CFG_DHT_TIPO DHT22`. A biblioteca Adafruit trata os dois modelos e
  só muda a decodificação. A documentação do Wokwi avisa que, no ESP32, a
  biblioteca "DHT sensor library for ESPx" pode funcionar melhor que outras.
  Se as leituras falharem no simulador, o problema é do modelo simulado, não
  do hardware real.
- O divisor do ECHO **não** está no diagrama: o Wokwi simula níveis lógicos e
  não tensões. No hardware real, ele é obrigatório.
- Rede: no Wokwi, o SSID é `Wokwi-GUEST`, sem senha. O broker local só é
  alcançável pelo *Private IoT Gateway* (recurso pago), com
  `CFG_MQTT_HOST "host.wokwi.internal"`. O gateway público só faz conexões de
  saída para a internet e não deve levar dados sensíveis.

Passos (exigem conta e token Wokwi, que não temos):

```bash
cp firmware/esp32_lixeira/config.example.h firmware/esp32_lixeira/config.h
# em config.h: CFG_DHT_TIPO DHT22, SSID "Wokwi-GUEST", senha "", host do broker
arduino-cli compile --fqbn esp32:esp32:esp32doit-devkit-v1 \
  --output-dir firmware/wokwi/build firmware/esp32_lixeira
WOKWI_CLI_TOKEN=... wokwi-cli firmware/wokwi     # ou VS Code: "Wokwi: Start Simulator"
```

A variante de `config.h` para o Wokwi **foi compilada** (está no log), mas a
simulação não foi executada.

## Limitações conhecidas

- **HC-SR04 dentro de uma lixeira.** O feixe tem ~15° (datasheet), e
  superfícies irregulares, inclinadas ou macias (sacos plásticos, tecidos)
  espalham ou absorvem o eco. O datasheet pede alvo plano de ≥ 0,5 m². O
  resultado são ecos perdidos (tratados como inválidos) ou reflexões nas
  paredes, que encurtam a distância lida. Em lixeiras estreitas, o cone atinge
  as paredes: a 55 cm, o raio do cone de 15° chega a ≈ 7 cm. A mediana da
  rajada filtra picos isolados, mas não corrige um viés sistemático. A
  ocupação mede **um ponto** da superfície, não o volume.
- **Zona morta e montagem.** Leituras abaixo de 2 cm são descartadas. Se o
  offset estiver mal calibrado, resíduos acima da linha de 100 % aparecem como
  100 %.
- **Condensação e sujeira.** Umidade alta e resíduos orgânicos podem condensar
  água ou depositar sujeira nos transdutores, o que atenua o sinal e gera
  falsos ecos. O evento `sensor_falha` ajuda a detectar isso, mas a prevenção
  é mecânica (proteção, inclinação).
- **Velocidade do som.** A compensação usa a temperatura do DHT11 (± 2 °C,
  segundo o datasheet), medida fora do caminho acústico. 2 °C de erro dão
  ≈ 0,35 % na distância. A umidade e o gradiente térmico dentro da lixeira não
  são compensados.
- **`pulseIn()` em software.** A medição conta ciclos de CPU. Interrupções do
  Wi-Fi durante o pulso podem alongá-lo em alguns µs (≈ mm), e a mediana reduz
  esse efeito. Para maior exatidão, use RMT ou MCPWM *capture*.
- **DHT11.** Resolução de 1 °C e 1 %RH. Especificado para 0–50 °C e 20–90 %RH.
  Lento (constante de tempo de 6–30 s).
- **Telemetria em QoS 0, sem armazenamento local.** O que é medido durante uma
  queda não é reenviado: a perda aparece em `telemetrias_nao_enviadas` e como
  lacuna de `ts`. A fila guarda só eventos (8 posições, em RAM, perdidos se o
  dispositivo reiniciar).
- **Limiar após reinício.** O estado do alerta não é salvo. Se a lixeira já
  estiver cheia no boot, `limiar_excedido` é emitido de novo, e a plataforma
  deve tratá-lo como idempotente.
- **Bloqueio no `connect()`.** DNS + TCP + CONNACK podem bloquear o `loop()`
  por alguns segundos quando o broker está inacessível. Nesse intervalo, a
  rajada ultrassônica atrasa, mas o *watchdog* (30 s) não dispara.
- **Sem OTA, *deep sleep* nem criptografia da NVS/flash.** Para operação com
  bateria, o próximo passo seria *deep sleep* entre medições.
