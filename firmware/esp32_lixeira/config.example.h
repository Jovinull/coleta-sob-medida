/*
 * config.example.h — modelo de configuração do firmware da lixeira (ESP32).
 *
 * COMO USAR
 *   1. Copie este arquivo para "config.h" na mesma pasta:
 *        cp config.example.h config.h
 *   2. Edite config.h com os dados da sua rede, broker e lixeira.
 *   3. config.h está no .gitignore: NUNCA versione credenciais.
 *
 * Todos os parâmetros têm prefixo CFG_. Valores de tempo indicam a unidade no
 * nome (_MS = milissegundos, _S = segundos). Distâncias em centímetros.
 */
#pragma once

// ---------------------------------------------------------------------------
// Identificação do dispositivo e tópicos (ver docs/mqtt/contrato-mqtt.md)
// ---------------------------------------------------------------------------
// Identificador ASCII sem '/', '+' ou '#'. Padrão sugerido: LX-[0-9]{4}.
// Também é usado como client ID MQTT, portanto deve ser ÚNICO no broker.
#define CFG_ID_DISPOSITIVO "LX-0001"
// Prefixo dos tópicos: {prefixo}/dispositivos/{id}/{telemetria|estado|eventos|comandos}
#define CFG_PREFIXO_TOPICO "residuos"

// ---------------------------------------------------------------------------
// Wi-Fi
// ---------------------------------------------------------------------------
#define CFG_WIFI_SSID  "COLOQUE_O_SSID_AQUI"
#define CFG_WIFI_SENHA "COLOQUE_A_SENHA_AQUI"
// Tempo máximo de uma tentativa de associação antes de aplicar o backoff.
#define CFG_WIFI_TIMEOUT_CONEXAO_MS 20000UL

// ---------------------------------------------------------------------------
// Broker MQTT (MQTT 3.1.1 via PubSubClient)
// ---------------------------------------------------------------------------
// Para o Mosquitto local (docker compose): IP da máquina que roda o Docker na
// mesma rede do ESP32 (não use "localhost": para o ESP32, localhost é ele mesmo).
#define CFG_MQTT_HOST "192.168.0.10"
#define CFG_MQTT_PORTA 1883
// Deixe "" para conexão sem autenticação (somente em laboratório).
#define CFG_MQTT_USUARIO ""
#define CFG_MQTT_SENHA   ""
#define CFG_MQTT_KEEPALIVE_S 30
// Tempo máximo de espera de resposta do broker (CONNACK etc.), em segundos.
#define CFG_MQTT_TIMEOUT_SOCKET_S 5
// Tamanho do buffer do PubSubClient (cabeçalho + tópico + payload).
// A telemetria ocupa ~350 B; 1024 deixa folga para eventos e comandos.
#define CFG_MQTT_TAMANHO_BUFFER 1024

// --- TLS (opcional) --------------------------------------------------------
// Descomente CFG_MQTT_TLS para usar WiFiClientSecure (troque a porta p/ 8883).
// #define CFG_MQTT_TLS 1
// Certificado da CA que assinou o certificado do broker (formato PEM).
// #define CFG_MQTT_CA_PEM R"PEM(
// -----BEGIN CERTIFICATE-----
// ...
// -----END CERTIFICATE-----
// )PEM"
// SOMENTE PARA TESTES: aceita qualquer certificado (sem validação; vulnerável
// a ataque man-in-the-middle). Usado apenas se CFG_MQTT_CA_PEM não definido.
// #define CFG_MQTT_TLS_INSEGURO 1

// ---------------------------------------------------------------------------
// Reconexão (Wi-Fi e MQTT): backoff exponencial com jitter
// ---------------------------------------------------------------------------
// espera_n = min(MAX, BASE * 2^n); aguarda-se um valor aleatório em
// [espera_n/2, espera_n] ("equal jitter").
#define CFG_BACKOFF_BASE_MS 1000UL
#define CFG_BACKOFF_MAX_MS  60000UL

// ---------------------------------------------------------------------------
// Relógio (NTP)
// ---------------------------------------------------------------------------
#define CFG_NTP_SERVIDOR_1 "pool.ntp.org"
#define CFG_NTP_SERVIDOR_2 "time.google.com"
// ts é sempre publicado em UTC (segundos desde a época Unix).

// ---------------------------------------------------------------------------
// Pinos (DOIT ESP32 DevKit V1). Ver mapa de pinos em firmware/README.md.
// ---------------------------------------------------------------------------
#define CFG_PINO_TRIG 14   // saída para o TRIG do HC-SR04 (3,3 V é aceito como nível alto)
#define CFG_PINO_ECHO 27   // entrada do ECHO (via divisor 1 kΩ/2 kΩ!). Era GPIO12 (strapping) no original.
#define CFG_PINO_DHT  4    // dados do DHT11 (pull-up de 4,7–10 kΩ para 3,3 V)
#define CFG_PINO_LED  2    // LED azul da placa DevKit V1
#define CFG_LED_ATIVO_ALTO 1

// ---------------------------------------------------------------------------
// Sensor de temperatura/umidade
// ---------------------------------------------------------------------------
#define CFG_HABILITAR_DHT 1
// DHT11 no hardware real; use DHT22 na simulação Wokwi (não há DHT11 no Wokwi).
#define CFG_DHT_TIPO DHT11

// ---------------------------------------------------------------------------
// Geometria da lixeira e sensor ultrassônico
// ---------------------------------------------------------------------------
// Distância medida do sensor até o FUNDO da lixeira vazia.
#define CFG_DIST_SENSOR_FUNDO_CM 60.0f
// Deslocamento de montagem: distância do sensor até a linha de "100 % cheio"
// (borda útil). Deve ser >= 2 cm (zona morta do HC-SR04).
#define CFG_OFFSET_MONTAGEM_CM 5.0f
// Altura útil H = CFG_DIST_SENSOR_FUNDO_CM - CFG_OFFSET_MONTAGEM_CM (calculada no código).
// Margem acima do fundo aceita como leitura plausível (reflexões, tolerância).
#define CFG_MARGEM_PLAUSIVEL_CM 10.0f
// Número de pulsos por medição (mediana) e mínimo de pulsos válidos.
#define CFG_US_PULSOS_POR_MEDICAO 5
#define CFG_US_MIN_PULSOS_VALIDOS 3
// Intervalo entre pulsos consecutivos (datasheet sugere ciclo > 60 ms).
#define CFG_US_INTERVALO_PULSOS_MS 65
// Compensação da velocidade do som pela temperatura do DHT: c = 331,3 + 0,606·T.
#define CFG_US_COMPENSAR_TEMPERATURA 1
// Temperatura usada quando o DHT está ausente/inválido.
#define CFG_US_TEMPERATURA_PADRAO_C 25.0f

// ---------------------------------------------------------------------------
// Alerta de ocupação com histerese
// ---------------------------------------------------------------------------
// limiar_excedido quando ocupação >= LIMIAR; limiar_normalizado quando
// ocupação < LIMIAR - HISTERESE.
#define CFG_LIMIAR_ALERTA_PCT 80.0f
#define CFG_HISTERESE_PCT     5.0f

// ---------------------------------------------------------------------------
// Falha de sensor: nº de medições inválidas consecutivas para gerar sensor_falha
// ---------------------------------------------------------------------------
#define CFG_FALHAS_PARA_EVENTO 3

// ---------------------------------------------------------------------------
// Intervalos
// ---------------------------------------------------------------------------
// Medição (sensores). Mínimo 2 s por causa do DHT (biblioteca Adafruit).
#define CFG_INTERVALO_MEDICAO_S 10UL
// Publicação de telemetria (padrão). Alterável pelo comando "intervalo";
// o valor recebido é persistido na NVS. Faixa aceita: [MEDICAO, 86400] s.
#define CFG_INTERVALO_PUBLICACAO_S 60UL

// ---------------------------------------------------------------------------
// Diversos
// ---------------------------------------------------------------------------
// Nível de log na Serial: 0 = nada, 1 = erro, 2 = aviso, 3 = info, 4 = depuração.
#define CFG_NIVEL_LOG 3
#define CFG_SERIAL_BAUD 115200
// Watchdog da tarefa loop(): reinicia o ESP32 se loop() travar por esse tempo.
#define CFG_WATCHDOG_S 30
