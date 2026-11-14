# Auditoria do firmware original (`original/MQTT.ino`, TCC 2024)

Objeto: `original/MQTT.ino` (167 linhas; SHA-256 em `original/SHA256SUMS`), para
DOIT ESP32 DevKit V1 (módulo ESP32-WROOM-32), HC-SR04 (TRIG = GPIO14,
ECHO = GPIO12), DHT11 (GPIO4), LED (GPIO2) e PubSubClient.

Método:

1. Leitura linha a linha do código.
2. Leitura do código-fonte das bibliotecas e do núcleo nas versões da
   compilação (núcleo `esp32:esp32` 3.3.12, DHT sensor library 1.4.7,
   PubSubClient 2.8) e das duas bibliotecas "Ultrasonic" candidatas.
3. Compilação real de uma cópia do original, com as credenciais trocadas por
   `"REMOVIDO"`, contra cada uma das duas bibliotecas "Ultrasonic".
4. Conferência dos datasheets: cada fonte citada foi baixada e lida (seção
   [Fontes](#fontes)).

Cada item abaixo foi **confirmado no código ou na documentação** antes de entrar
na tabela. A seção [Suspeitas verificadas e descartadas](#suspeitas-verificadas-e-descartadas-ou-rebaixadas)
traz o que foi investigado mas não se confirmou como defeito (ou se confirmou
com gravidade menor).

Legenda de gravidade: **C** = crítica (segurança ou dano ao hardware),
**A** = alta (dado errado ou falha funcional), **M** = média
(confiabilidade/robustez), **B** = baixa (qualidade/manutenção).

> As credenciais Wi-Fi do original são citadas aqui apenas como "credenciais
> Wi-Fi em texto claro"; os valores não são reproduzidos.

## Tabela de defeitos

| # | Linhas | Defeito | Evidência | Impacto | Correção (firmware 2.x) | G |
|---|---|---|---|---|---|---|
| 1 | 7–8 (e `original/readme.md` 26–27) | Credenciais Wi-Fi em texto claro no código-fonte e no README | Atribuição literal de `ssid`/`password`. O mesmo par aparece no README e em commits antigos do histórico Git, ou seja, já foi publicado. | Qualquer leitor do repositório público obtém acesso à rede. Reescrever o histórico não desfaz a exposição. | As credenciais ficam em `config.h`, que está no `.gitignore`; o repositório só traz `config.example.h` com marcadores. **Trocar a senha da rede antiga.** | C |
| 2 | 10, 65, 146 | Broker público (`broker.hivemq.com`) na porta 1883, sem TLS e sem autenticação | `client.setServer(mqtt_server, 1883)` e `client.connect(clientId)` sem usuário/senha. A HiveMQ descreve o broker como público e compartilhado, "not intended for private or production data" [HIVEMQ]. | Telemetria legível por qualquer pessoa e em texto claro na rede. Qualquer pessoa pode publicar dados falsos ou comandos (ver #3). | Broker próprio (Mosquitto) com host, porta, usuário e senha configuráveis. TLS opcional (`CFG_MQTT_TLS` + CA em PEM, `WiFiClientSecure`). | C |
| 3 | 67, 89–117 | Comandos sem autenticação: um único caractere (`'L'`/`'l'`) em tópico público | O callback testa só `payload[0]`. O tópico `jovino/publisher` fica no broker público. | Qualquer cliente da internet aciona o LED (e qualquer atuador futuro). Também não há como distinguir comando de lixo. | Comandos JSON (`{"cmd":...}`) validados com ArduinoJson em `{prefixo}/dispositivos/{id}/comandos`, num broker com ACL. | A |
| 4 | 62, 67, 84, 107, 115, 126, 134 | Espaço de tópicos fixo, pessoal e sem identificador de dispositivo | Tópicos literais `jovino/sommm`, `jovino/umidade`, `jovino/temperatura`, `jovino/led`, `jovino/publisher`. | Só um dispositivo por broker. Com mais de um, os dados se misturam e a plataforma não sabe qual lixeira enviou o quê. O original não segue o contrato. | Tópicos `{prefixo}/dispositivos/{id}/…` montados a partir de `CFG_PREFIXO_TOPICO` e `CFG_ID_DISPOSITIVO` (contrato MQTT). | A |
| 5 | 37–38, 138–148 | `dht.begin()` nunca é chamado | `setup()` não chama `dht.begin()`. Na biblioteca Adafruit 1.4.7, `begin(usec=55)` define `pullTime = 55` µs e `_lastreadtime` [DHT-LIB]. Sem `begin()`, `pullTime` fica 0 (objeto global zerado), e `read()` pula a espera de *pull-up* entre o sinal de início e a resposta do sensor (o datasheet prevê 20–40 µs [DHT11-DS]). | Leituras intermitentes ou NaN, conforme o sensor ou módulo. O defeito não aparece em compilação. | `SensorAmbiente::iniciar()` chama `dht.begin()`. | A |
| 6 | 28, 103, 111, 142 | LED configurado como entrada mas acionado como saída | `pinMode(pin_led, INPUT)`, depois `digitalWrite(pin_led, HIGH/LOW)`. No núcleo 3.3.12, `digitalWrite` só chama `gpio_set_level()` [AR-ESP32 `esp32-hal-gpio.c`], que não liga o *driver* de saída de um pino em modo entrada. | O LED não acende (o comando "L" não tem efeito físico), mas o firmware publica "O LED está aceso". | `pinMode(CFG_PINO_LED, OUTPUT)` e estado inicial definido. | A |
| 7 | 33, 80 | A "porcentagem" publicada é proporcional ao **espaço vazio** e não tem limite | `percentMax = (distancia / Tmax) * 100`. A distância cresce quando a lixeira esvazia: vazia ≈ 100 %, cheia ≈ 0 %. Nada limita o valor a [0, 100], e não há desconto da montagem do sensor (*offset*). `Tmax = 50` está fixo no código. | O indicador publicado é o inverso da ocupação. Alertas e rotas feitos com ele ficam invertidos. Valores > 100 % aparecem (ver #9). | `ocupacao = 100·(H − d_corr)/H` com `d_corr = d − offset` e `H = dist_fundo − offset`, limitada a [0, 100]. Geometria em `config.h`. A distância bruta também é publicada. | A |
| 8 | 128–134 | Índice de calor publicado como "temperatura" | `hic = dht.computeHeatIndex(temperatura, umidade, false)` vai para `jovino/temperatura`. | O valor publicado não é a temperatura do ar: com UR alta e T > ~27 °C, o índice de calor fica bem acima de T. A série histórica do TCC tem esse viés. | Publica-se `readTemperature()` (ar) como `temperatura` em `degC`, como manda o contrato. | A |
| 9 | 25, 77 | Sem tratamento de *timeout* do eco: o *timeout* vira uma distância válida | A API `Ultrasonic(trig, echo)` + `Ranging(CM)` é a da biblioteca **JRodrigoTech/Ultrasonic-HC-SR04** (baseada na da ITead) [JR-LIB]. Lá, o *timeout* padrão é 3000 µs e, quando `pulseIn()` devolve 0, `Timing()` faz `duration = Time_out` e `Ranging()` devolve `3000/29/2 = 51` cm. O alcance útil também fica limitado a ~51 cm. | Eco perdido (superfície inclinada, absorção, sensor desconectado) aparece como "51 cm" e é publicado como 102 % (pela fórmula de #7). O dado inválido fica indistinguível do válido. | `pulseIn(…, timeout)` com *timeout* calculado a partir da geometria. Retorno 0 = pulso descartado. Faixa de validade [2 cm, fundo + margem]. Mediana de 5 pulsos com mínimo de 3 válidos. Sem quórum, `valida=false` e `valor=null`. | A |
| 10 | 3, 25, 77 | Dependência "Ultrasonic" ambígua e não documentada | A biblioteca "Ultrasonic" do Library Manager é a de Erick Simões (3.0.0, API `read()`/`distanceRead()`, sem `Ranging`) [ES-LIB]. Compilando o original contra ela: `error: 'class Ultrasonic' has no member named 'Ranging'`. Contra a JRodrigoTech (commit `2164ab4`), compila. Nenhuma tag da biblioteca de Erick Simões (v0.1 a 3.0.0) tem `Ranging`. | O projeto não é reprodutível: quem instala a biblioteca "óbvia" não consegue compilar. | Sem biblioteca de ultrassom: `pulseIn()` do núcleo, com todas as versões fixadas (ver README). | M |
| 11 | 122–134 | Sem tratamento de NaN do DHT | O retorno de `readHumidity()` e `readTemperature()` não é testado. `sprintf("%f", NAN)` gera `"nan"`, que é publicado. | O consumidor recebe a string "nan" como medida. Não há como sinalizar falha do sensor. | `isnan()` + faixa física. Leitura inválida vira `valida=false` e `valor=null`. Eventos `sensor_falha`/`sensor_recuperado` após N falhas seguidas. | A |
| 12 | 49–51 | Laço bloqueante e sem *timeout* na conexão Wi-Fi | `while (WiFi.status() != WL_CONNECTED) delay(500);` | Com a rede indisponível no boot, o dispositivo trava para sempre em `setup()` e não mede nem registra nada. | Máquina de estados não bloqueante com *timeout* de associação (`CFG_WIFI_TIMEOUT_CONEXAO_MS`) e backoff. | M |
| 13 | 58–73 | Reconexão MQTT bloqueante, a intervalo fixo, sem backoff e sem tratar queda do Wi-Fi | `while (!client.connected()) { …; delay(5000); }`. Se o Wi-Fi cair, `reconnect()` repete `connect()` a cada 5 s para sempre, sem reassociar. | O laço principal para enquanto o broker estiver fora: sem medições, sem `client.loop()`. Muitas lixeiras religando juntas tentam reconectar em sincronia (*thundering herd*). | Estados WifiIniciar → WifiAguardando → MqttConectar → Operando, com backoff exponencial (base 1 s, teto 60 s) e *jitter* aleatório (`esp_random()`). | M |
| 14 | 151–163 | Publica antes de verificar a conexão; o retorno de `publish()` é ignorado | `loop()` chama `ultrassonico()` e `umidade_temp()` (que publicam) **antes** de `if (!client.connected()) reconnect();`. Na primeira volta do `loop()` o cliente nunca conectou. `client.publish()` devolve `false` sem aviso. | A primeira leitura de cada boot e as leituras feitas durante quedas se perdem sem registro. | Só se publica com a sessão MQTT ativa. As falhas são contadas (`telemetrias_nao_enviadas`, informado no evento `reconexao`). Eventos esperam numa fila até haver conexão. | M |
| 15 | 53–54, 61–62 | `randomSeed(micros())` piora o RNG; o *client ID* muda a cada conexão | No núcleo 3.3.12, `random()` usa o RNG de hardware (`esp_random()`) **até** alguém chamar `randomSeed()`, que passa para o `rand()` de software [AR-ESP32 `WMath.cpp`]. O sufixo de 16 bits (`random(0xffff)`) muda a cada `reconnect()` e tem chance de colisão. | Identidade MQTT instável (o broker não associa sessões ao dispositivo). Pior aleatoriedade sem nenhum ganho. | *Client ID* = `CFG_ID_DISPOSITIVO` (estável e único). *Jitter* gerado por `esp_random()`. | B |
| 16 | 22, 141 | ECHO em GPIO12 (MTDI), pino de *strapping* da tensão da flash | O datasheet do ESP32 lista o MTDI como *strapping* do LDO interno (VDD_SDIO): MTDI = 1 no reset alimenta VDD_SDIO pelo LDO de **1,8 V**; o padrão é *pull-down* (0 → 3,3 V) [ESP32-DS §3, Tab. 3-1, §3.2] [ESPTOOL-FV]. O ESP32-WROOM-32 da DevKit V1 tem flash de **3,3 V** [WROOM32-DS Tab. 15]. | Se o ECHO estiver em nível alto no instante do reset, a flash recebe 1,8 V e o boot falha. Isso acontece num reset por software, *watchdog*, botão EN ou queda breve de tensão no meio de um pulso, já que o HC-SR04 tem alimentação própria. O original mede sem parar (~0,6 s por ciclo), o que aumenta a exposição. Risco **médio**: no *power-on* simultâneo o ECHO fica baixo, e o *pull-down* do divisor resistivo (#17) ajuda. | ECHO movido para **GPIO27** (sem função de *strapping*, vizinho de GPIO14 no conector). A alternativa de gravar o eFuse `set-flash-voltage 3.3V` é irreversível e não foi adotada. | M |
| 17 | 22–23 (hardware) | ECHO do HC-SR04 (5 V) ligado direto a um GPIO de 3,3 V | O HC-SR04 trabalha a 5 V e tem saída "TTL" [HCSR04-DS]: com 5 V de alimentação, o ECHO chega a ~5 V. Pelo ESP32-DS, Tab. 5-3, a entrada de um GPIO aceita no máximo V_IH = VDD + 0,3 V (≈ 3,6 V), e a Tab. 5-1 limita a alimentação a 3,6 V. Nem o código nem o README original mencionam divisor ou conversor de nível. | 5 V passa da tensão máxima de entrada: há estresse dos diodos de proteção e risco de degradação ou dano permanente ao GPIO. | Divisor 1 kΩ (série) / 2 kΩ (para GND): V = 5 × 2/3 ≈ 3,33 V, acima de V_IH,min = 0,75 × 3,3 = 2,475 V. Alternativas: conversor de nível ou HC-SR04P alimentado a 3,3 V (ver README). | C |
| 18 | 36–38 (hardware) | DHT11: alimentação e *pull-up* não especificados | O datasheet pede alimentação de 3–5,5 V e *pull-up* de 5 kΩ para cabos < 20 m [DHT11-DS]. Com *pull-up* ligado a 5 V, a linha de dados também chega a 5 V num GPIO de 3,3 V (mesmo problema do #17). | Risco elétrico análogo ao #17. Sem *pull-up* externo, só resta o interno (fraco), e as leituras ficam instáveis. | DHT11 alimentado em **3,3 V**, com *pull-up* de 4,7–10 kΩ para 3,3 V (módulos de 3 pinos costumam já trazer o resistor). Documentado no README. | M |
| 19 | 151–166, 120–135 | Leitura do DHT abaixo do intervalo mínimo; valores em cache publicados como novos | O laço dura ~0,6 s (`delay(100)` + `delay(500)` + leituras). O DHT11 exige ≥ 1 s entre leituras [DHT11-DS]. A biblioteca impõe 2 s (`MIN_INTERVAL 2000`) e, antes disso, devolve o último quadro lido [DHT-LIB `read()`]. | 3 de cada 4 publicações de umidade e temperatura repetem o quadro anterior, mas saem como medições novas, o que distorce estatísticas. | Medição a cada `CFG_INTERVALO_MEDICAO_S` (padrão 10 s; `static_assert` ≥ 2 s). | M |
| 20 | 84, 126, 134, 166 | Taxa de publicação excessiva e fixa | 3 mensagens por volta de ~0,6 s, ≈ 5 msg/s, sem intervalo configurável. | Consumo de energia e de dados desnecessário para um nível de lixeira que muda em horas. Carga extra no broker. | Telemetria única em JSON a cada 60 s (padrão), ajustável pelo comando `intervalo` e salva na NVS. | M |
| 21 | 83, 125, 133 | Payload texto `"%f"`, sem esquema, unidade, carimbo de tempo, validade ou sequência | `sprintf(msg, "%f", …)` publica só o número, com 6 casas decimais. | A plataforma não sabe quando a medida foi feita, de que dispositivo veio ou se é válida. Não dá para deduplicar nem detectar perdas. | JSON do contrato com `v`, `id`, `boot` (NVS), `seq`, `ts`/`ts_src` (NTP ou uptime), `leituras[]` com `unidade` e `valida`, e `rssi`. | A |
| 22 | — (ausência) | Sem *Last Will*, sem tópico de estado | `connect(clientId)` sem *will*. | A plataforma não distingue "lixeira vazia e quieta" de "lixeira desligada ou sem rede". | LWT retido, QoS 1, `{"estado":"offline","motivo":"lwt"}`. Ao conectar, publica `online` retido. Na queda do Wi-Fi só o socket é fechado: um DISCONNECT limpo anularia o LWT. | A |
| 23 | 89–99, 138 | `Serial` usado sem `Serial.begin()` | `setup()` não inicializa a serial, mas o callback chama `Serial.print`. | Nada aparece no monitor serial, e a depuração em campo fica impossível. | `Serial.begin(CFG_SERIAL_BAUD)` e log com níveis (`registro.h`). | B |
| 24 | 95, 102, 110 | Acesso a `payload[0]` sem checar `length`; comparação com sinal misturado | `for (int i = 0; i < length; i++)` com `length` sem sinal. `payload[0]` é lido mesmo com `length == 0`. | Mensagem vazia (comum ao limpar um tópico retido) lê dado residual do buffer. | `deserializeJson(doc, payload, tamanho)` com tratamento de erro. | B |
| 25 | 77, 80 | Resolução de 1 cm e velocidade do som fixa | `Ranging()` divide inteiros (`duration/29/2`), equivalente a c ≈ 345 m/s fixo, sem compensação de temperatura [JR-LIB]. | Com `Tmax = 50` cm, cada cm vale 2 % do indicador. De 10 °C a 40 °C, c varia ≈ 5 %. | Distância em `float` com c = 331,3 + 0,606·T, usando T do DHT quando válida (`CFG_US_COMPENSAR_TEMPERATURA`). | B |
| 26 | 31, 16, 33 | Variáveis mortas e constantes fixas | `tempo` e `lastMsg` não são usadas. `Tmax` é uma variável global mutável e não está documentada. | Manutenção mais difícil. | Toda a configuração fica em `config.h` (`CFG_*`), com verificações `static_assert` em `configuracao.h`. | B |
| 27 | — (ausência) | Sem *watchdog*, sem contador de boots, sem diagnóstico de reinício | Não há chamadas `esp_task_wdt_*`, NVS ou `esp_reset_reason()`. | Travamentos em campo passam despercebidos e os reinícios não são visíveis para a plataforma. | TWDT de 30 s em `loop()`. Contador de boots na NVS. Evento `reinicio` com o motivo do reset. | M |

## Suspeitas verificadas e descartadas (ou rebaixadas)

| Suspeita | Verificação | Conclusão |
|---|---|---|
| *Overflow* de `sprintf("%f")` no buffer de 50 bytes (l. 18–19, 83, 125, 133) | O maior `float` finito formatado com `"%f"` tem 47 caracteres (`-340282346638528859811704183484516925440.000000`), 48 com o terminador. NaN e infinito viram `"nan"` e `"inf"`. As distâncias da biblioteca são ≤ 51 cm. | **Sem *overflow* possível** com esses dados. Fica só a má prática (sem limite de tamanho, buffer global dividido com o callback, 6 casas decimais sem significado), incorporada ao item 21. |
| Ciclo de medição do HC-SR04 < 60 ms | O datasheet recomenda ciclo > 60 ms [HCSR04-DS]. O original mede a cada ~0,6 s. | Não é defeito. O firmware novo espaça os pulsos da rajada em 65 ms (`static_assert` ≥ 60 ms). |
| LED em GPIO2 (pino de *strapping* do modo de boot) | GPIO2 tem *pull-down* padrão e participa da seleção do modo de boot [ESP32-DS Tab. 3-1]. Na DevKit V1 o LED azul da placa já fica nesse pino, e o circuito do LED não força nível alto no reset. | Aceitável, e mantido. Não ligar ali nada que force nível alto no reset. |
| GPIO14 (TRIG) | É o MTMS (JTAG) [IDF-GPIO: "GPIO12-15 are usually used for inline debug"], mas **não** é *strapping* [ESP32-DS §3]. | Mantido. Só impede depuração JTAG simultânea. |
| Biblioteca "Ultrasonic" de Erick Simões | Na versão 3.0.0, um *timeout* devolve ≈ `20000/28/2 = 357` cm, e há um `delay(30)` dentro de `timing()` [ES-LIB]. | Não é a biblioteca usada pelo original (ver #10), mas teria o mesmo problema de *timeout* virar distância. |

## Fontes

Todas baixadas e conferidas em 2026-11-14.

- **[ESP32-DS]** Espressif, *ESP32 Series Datasheet*, v5.3. §3 "Boot
  Configurations" (Tab. 3-1, §3.2 "Internal LDO (VDD_SDIO) Voltage Control"),
  Tab. 5-1 "Absolute Maximum Ratings", Tab. 5-3 "DC Characteristics".
  <https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf>
- **[WROOM32-DS]** Espressif, *ESP32-WROOM-32 Datasheet*, v3.8: flash SPI de
  4 MB, Tab. 15 (flash de 3,3 V), §3.2.
  <https://www.espressif.com/sites/default/files/documentation/esp32-wroom-32_datasheet_en.pdf>
- **[ESPTOOL-FV]** Espressif, *esptool: espefuse set-flash-voltage* (MTDI alto
  no reset → regulador em 1,8 V).
  <https://docs.espressif.com/projects/esptool/en/latest/esp32/espefuse/set-flash-voltage-cmd.html>
- **[IDF-GPIO]** Espressif, *ESP-IDF Programming Guide — GPIO (ESP32)*.
  <https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/peripherals/gpio.html>
- **[HCSR04-DS]** ElecFreaks, *Ultrasonic Ranging Module HC-SR04* (5 V, 2 cm a
  4 m, 15°, TRIG ≥ 10 µs, µs/58 = cm, ciclo > 60 ms).
  <https://cdn.sparkfun.com/datasheets/Sensors/Proximity/HCSR04.pdf>
- **[DHT11-DS]** D-Robotics, *DHT11 Humidity & Temperature Sensor* (tradução
  do datasheet Aosong, 2010): 3–5,5 V, *pull-up* de 5 kΩ, amostragem ≥ 1 s,
  0–50 °C ± 2 °C, 20–90 %RH ± 5 %RH.
  <https://www.circuitbasics.com/wp-content/uploads/2015/11/DHT11-Datasheet.pdf>
- **[JR-LIB]** J. Rodrigo, *Ultrasonic-HC-SR04* (commit `2164ab4`),
  `Ultrasonic/Ultrasonic.cpp`. <https://github.com/JRodrigoTech/Ultrasonic-HC-SR04>
- **[ES-LIB]** E. Simões, *Ultrasonic* 3.0.0 (Arduino Library Manager).
  <https://github.com/ErickSimoes/Ultrasonic>
- **[DHT-LIB]** Adafruit, *DHT sensor library* 1.4.7, `DHT.cpp`/`DHT.h`.
  <https://github.com/adafruit/DHT-sensor-library>
- **[AR-ESP32]** Espressif, *arduino-esp32* 3.3.12, `cores/esp32/WMath.cpp`,
  `esp32-hal-gpio.c`, `wiring_pulse.c`. <https://github.com/espressif/arduino-esp32>
- **[HIVEMQ]** HiveMQ, *Public MQTT Broker*.
  <https://www.hivemq.com/mqtt/public-mqtt-broker/>
