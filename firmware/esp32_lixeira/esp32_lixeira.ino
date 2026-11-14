/*
 * esp32_lixeira.ino — firmware 2.x da lixeira inteligente (ESP32 DOIT DevKit V1).
 *
 * Mede o nível de resíduos com um HC-SR04 (rajada de N pulsos + mediana) e a
 * temperatura/umidade do ar com um DHT11, e publica via MQTT 3.1.1 seguindo o
 * contrato em docs/mqtt/contrato-mqtt.md:
 *
 *   {prefixo}/dispositivos/{id}/telemetria  (QoS 0, não retido)
 *   {prefixo}/dispositivos/{id}/estado      (retido; LWT "offline" QoS 1)
 *   {prefixo}/dispositivos/{id}/eventos     (QoS 0)
 *   {prefixo}/dispositivos/{id}/comandos    (assinado com QoS 1)
 *
 * Arquitetura (sem delay() no laço principal):
 *   loop() ─┬─ rede.processar()       máquina de estados Wi-Fi/MQTT + backoff
 *           ├─ tarefa de medição      a cada CFG_INTERVALO_MEDICAO_S: lê o DHT e
 *           │                         inicia a rajada ultrassônica
 *           ├─ ultrassom.processar()  dispara 1 pulso por vez (≥ 65 ms entre pulsos)
 *           ├─ fim da medição         ocupação, limiar com histerese, falhas de sensor
 *           ├─ tarefa de publicação   a cada "intervalo" s: telemetria da última medição
 *           └─ fila de eventos        publicada assim que houver conexão
 *
 * Antes de compilar: copie config.example.h para config.h e edite-o.
 */
#include <ArduinoJson.h>
#include <Preferences.h>
#include <WiFi.h>
#include <esp_system.h>
#include <esp_task_wdt.h>

#include "calculos.h"
#include "configuracao.h"
#include "rede.h"
#include "registro.h"
#include "sensores.h"

// ===========================================================================
// Agendador simples baseado em millis() (seguro contra o estouro de 49,7 dias)
// ===========================================================================
struct Tarefa {
  uint32_t periodo_ms;
  uint32_t ultima_ms;
  bool vencida(uint32_t agora) {
    if ((uint32_t)(agora - ultima_ms) < periodo_ms) return false;
    ultima_ms = agora;
    return true;
  }
};

// ===========================================================================
// Estado global
// ===========================================================================
namespace {

GerenciadorRede rede;
SensorUltrassonico ultrassom;
SensorAmbiente ambiente;
Preferences nvs;

// Tópicos montados em setup() a partir do prefixo e do id.
char topicoTelemetria[96];
char topicoEstado[96];
char topicoEventos[96];
char topicoComandos[96];
char payloadLwt[128];

uint32_t contadorBoot = 0;     // persistido na NVS
uint32_t seqTelemetria = 0;    // reinicia a cada boot (contrato)
uint32_t seqEventos = 0;       // sequência independente da telemetria
uint32_t intervaloPublicacao_s = CFG_INTERVALO_PUBLICACAO_S;
uint32_t telemetriasNaoEnviadas = 0;
bool ledLigado = false;

Tarefa tarefaMedicao{CFG_INTERVALO_MEDICAO_S * 1000UL, 0};
Tarefa tarefaPublicacao{CFG_INTERVALO_PUBLICACAO_S * 1000UL, 0};

// Última medição completa (instantâneo publicado na telemetria).
struct Medicao {
  bool existe = false;
  Carimbo carimbo{0, "uptime"};
  ResultadoUltrassom us;
  float ocupacaoPct = NAN;
  LeituraAmbiente amb;
} ultimaMedicao;

LeituraAmbiente leituraAmbienteEmCurso;  // DHT lido no início da medição corrente
Carimbo carimboEmCurso{0, "uptime"};
// Publica uma telemetria assim que houver medição e conexão (boot e cada reconexão).
bool publicarAssimQuePossivel = true;

// Detecção de eventos.
bool alertaAtivo = false;
uint32_t falhasUs = 0;
bool emFalhaUs = false;
#if CFG_HABILITAR_DHT
uint32_t falhasDht = 0;
bool emFalhaDht = false;
#endif

// Fila circular de eventos já serializados, aguardando conexão.
constexpr size_t kTamFilaEventos = 8;
constexpr size_t kTamEvento = 384;
char filaEventos[kTamFilaEventos][kTamEvento];
size_t filaInicio = 0, filaQtd = 0;

const char *kNvsNamespace = "lixeira";

}  // namespace

// ===========================================================================
// Utilidades
// ===========================================================================
static void aplicarLed(bool ligado) {
  ledLigado = ligado;
  digitalWrite(CFG_PINO_LED, (ligado == (CFG_LED_ATIVO_ALTO != 0)) ? HIGH : LOW);
}

static const char *motivoReinicio() {
  switch (esp_reset_reason()) {
    case ESP_RST_POWERON: return "energizacao";
    case ESP_RST_EXT: return "pino_externo";
    case ESP_RST_SW: return "software";
    case ESP_RST_PANIC: return "panico";
    case ESP_RST_INT_WDT: return "watchdog_interrupcao";
    case ESP_RST_TASK_WDT: return "watchdog_tarefa";
    case ESP_RST_WDT: return "watchdog";
    case ESP_RST_DEEPSLEEP: return "deep_sleep";
    case ESP_RST_BROWNOUT: return "subtensao";
    case ESP_RST_SDIO: return "sdio";
    default: return "desconhecido";
  }
}

// Serializa doc em buf; retorna false (e registra) se não couber.
static bool serializar(const JsonDocument &doc, char *buf, size_t tam) {
  const size_t necessario = measureJson(doc);
  if (necessario + 1 > tam) {
    LOG_ERRO("json", "documento de %u bytes nao cabe em %u", (unsigned)necessario, (unsigned)tam);
    return false;
  }
  serializeJson(doc, buf, tam);
  return true;
}

// ===========================================================================
// Eventos
// ===========================================================================
// Cria o cabeçalho comum de um evento. O chamador preenche doc["detalhe"].
static JsonDocument novoEvento(const char *tipo) {
  JsonDocument doc;
  const Carimbo c = carimboAgora();
  doc["v"] = ESQUEMA_VERSAO;
  doc["id"] = CFG_ID_DISPOSITIVO;
  doc["boot"] = contadorBoot;  // extensão compatível: permite deduplicar por (id, boot, seq)
  doc["seq"] = seqEventos++;
  doc["ts"] = c.ts;
  doc["ts_src"] = c.fonte;
  doc["tipo"] = tipo;
  return doc;
}

static void enfileirarEvento(const JsonDocument &doc) {
  if (filaQtd == kTamFilaEventos) {
    // Fila cheia: descarta o mais antigo (a lacuna em "seq" sinaliza a perda).
    LOG_AVISO("evento", "fila cheia; descartando evento mais antigo");
    filaInicio = (filaInicio + 1) % kTamFilaEventos;
    --filaQtd;
  }
  char *destino = filaEventos[(filaInicio + filaQtd) % kTamFilaEventos];
  if (!serializar(doc, destino, kTamEvento)) return;
  ++filaQtd;
  LOG_INFO("evento", "enfileirado: %s", destino);
}

static void descarregarEventos() {
  while (filaQtd > 0 && rede.mqttConectado()) {
    if (!rede.publicar(topicoEventos, filaEventos[filaInicio], false)) {
      LOG_AVISO("evento", "falha ao publicar; nova tentativa depois");
      return;
    }
    filaInicio = (filaInicio + 1) % kTamFilaEventos;
    --filaQtd;
  }
}

// ===========================================================================
// Telemetria
// ===========================================================================
static void adicionarLeitura(JsonArray leituras, const char *tipo, bool valida, float valor, const char *unidade) {
  JsonObject l = leituras.add<JsonObject>();
  l["tipo"] = tipo;
  if (valida) {
    l["valor"] = calc::arred1(valor);
  } else {
    l["valor"] = nullptr;  // contrato: valor null quando valida = false
  }
  l["unidade"] = unidade;
  l["valida"] = valida;
}

static void publicarTelemetria() {
  if (!ultimaMedicao.existe) return;
  if (!rede.mqttConectado()) {
    ++telemetriasNaoEnviadas;
    LOG_AVISO("telem", "sem conexao MQTT; telemetria nao enviada (total=%lu)", (unsigned long)telemetriasNaoEnviadas);
    return;
  }
  JsonDocument doc;
  doc["v"] = ESQUEMA_VERSAO;
  doc["id"] = CFG_ID_DISPOSITIVO;
  doc["boot"] = contadorBoot;
  doc["seq"] = seqTelemetria;
  doc["ts"] = ultimaMedicao.carimbo.ts;  // instante da medição, não do envio
  doc["ts_src"] = ultimaMedicao.carimbo.fonte;
  JsonArray leituras = doc["leituras"].to<JsonArray>();
  const auto &m = ultimaMedicao;
  adicionarLeitura(leituras, "distancia", m.us.valida, m.us.distancia_cm, "cm");
  adicionarLeitura(leituras, "ocupacao", m.us.valida, m.ocupacaoPct, "%");
#if CFG_HABILITAR_DHT
  adicionarLeitura(leituras, "temperatura", m.amb.temperaturaValida, m.amb.temperaturaC, "degC");
  adicionarLeitura(leituras, "umidade", m.amb.umidadeValida, m.amb.umidadePct, "%RH");
#endif
  doc["rssi"] = WiFi.RSSI();

  char buf[CFG_MQTT_TAMANHO_BUFFER];
  if (!serializar(doc, buf, sizeof(buf))) return;
  if (rede.publicar(topicoTelemetria, buf, false)) {
    LOG_INFO("telem", "seq=%lu %s", (unsigned long)seqTelemetria, buf);
    ++seqTelemetria;  // só conta telemetrias efetivamente publicadas
  } else {
    ++telemetriasNaoEnviadas;
    LOG_AVISO("telem", "publish falhou");
  }
}

// ===========================================================================
// Medição e detecção de eventos
// ===========================================================================
static void iniciarMedicao() {
  if (ultrassom.ocupado()) {
    LOG_AVISO("medicao", "rajada anterior ainda em curso; ciclo ignorado");
    return;
  }
  carimboEmCurso = carimboAgora();
  leituraAmbienteEmCurso = ambiente.ler();
  float tempSom = CFG_US_TEMPERATURA_PADRAO_C;
#if CFG_US_COMPENSAR_TEMPERATURA
  if (leituraAmbienteEmCurso.temperaturaValida) tempSom = leituraAmbienteEmCurso.temperaturaC;
#endif
  ultrassom.comecarMedicao(tempSom);
}

// Atualiza o contador de falhas de um sensor e gera sensor_falha/sensor_recuperado.
static void avaliarSensor(const char *nome, bool valida, uint32_t &falhas, bool &emFalha, const char *motivo) {
  if (!valida) {
    ++falhas;
    if (!emFalha && falhas >= CFG_FALHAS_PARA_EVENTO) {
      emFalha = true;
      JsonDocument ev = novoEvento("sensor_falha");
      ev["detalhe"]["sensor"] = nome;
      ev["detalhe"]["falhas_consecutivas"] = falhas;
      ev["detalhe"]["motivo"] = motivo;
      enfileirarEvento(ev);
    }
    return;
  }
  if (emFalha) {
    JsonDocument ev = novoEvento("sensor_recuperado");
    ev["detalhe"]["sensor"] = nome;
    ev["detalhe"]["falhas_consecutivas"] = falhas;
    enfileirarEvento(ev);
  }
  emFalha = false;
  falhas = 0;
}

static void avaliarLimiar(float ocupacao) {
  if (!alertaAtivo && ocupacao >= CFG_LIMIAR_ALERTA_PCT) {
    alertaAtivo = true;
    JsonDocument ev = novoEvento("limiar_excedido");
    ev["detalhe"]["ocupacao"] = calc::arred1(ocupacao);
    ev["detalhe"]["limiar"] = calc::arred1(CFG_LIMIAR_ALERTA_PCT);
    enfileirarEvento(ev);
  } else if (alertaAtivo && ocupacao < CFG_LIMIAR_ALERTA_PCT - CFG_HISTERESE_PCT) {
    alertaAtivo = false;
    JsonDocument ev = novoEvento("limiar_normalizado");
    ev["detalhe"]["ocupacao"] = calc::arred1(ocupacao);
    ev["detalhe"]["limiar"] = calc::arred1(CFG_LIMIAR_ALERTA_PCT);
    ev["detalhe"]["histerese"] = calc::arred1(CFG_HISTERESE_PCT);
    enfileirarEvento(ev);
  }
}

static void concluirMedicao(const ResultadoUltrassom &us) {
  ultimaMedicao.existe = true;
  ultimaMedicao.carimbo = carimboEmCurso;
  ultimaMedicao.us = us;
  ultimaMedicao.amb = leituraAmbienteEmCurso;
  ultimaMedicao.ocupacaoPct =
      us.valida ? calc::ocupacao_pct(us.distancia_cm, CFG_OFFSET_MONTAGEM_CM, ALTURA_UTIL_CM) : NAN;

  if (us.valida) {
    LOG_INFO("medicao", "d=%.1f cm ocup=%.1f %% (%u/%u pulsos validos) T=%.1f UR=%.1f", (double)us.distancia_cm,
             (double)ultimaMedicao.ocupacaoPct, us.pulsosValidos, (unsigned)CFG_US_PULSOS_POR_MEDICAO,
             (double)ultimaMedicao.amb.temperaturaC, (double)ultimaMedicao.amb.umidadePct);
  } else {
    LOG_AVISO("medicao", "ultrassom invalido: %u validos, %u timeouts, %u fora da faixa", us.pulsosValidos,
              us.timeouts, us.foraDaFaixa);
  }

  avaliarSensor("ultrassonico", us.valida, falhasUs, emFalhaUs, us.timeouts >= us.foraDaFaixa ? "timeout" : "fora_da_faixa");
#if CFG_HABILITAR_DHT
  const bool dhtOk = ultimaMedicao.amb.temperaturaValida && ultimaMedicao.amb.umidadeValida;
  avaliarSensor("dht", dhtOk, falhasDht, emFalhaDht, "leitura_invalida");
#endif
  if (us.valida) avaliarLimiar(ultimaMedicao.ocupacaoPct);
}

// ===========================================================================
// MQTT: conexão e comandos
// ===========================================================================
static void aoConectarMqtt(bool primeiraConexao) {
  // Estado "online" retido (o PubSubClient só publica com QoS 0; o LWT usa QoS 1).
  JsonDocument doc;
  const Carimbo c = carimboAgora();
  doc["v"] = ESQUEMA_VERSAO;
  doc["id"] = CFG_ID_DISPOSITIVO;
  doc["estado"] = "online";
  doc["ts"] = c.ts;
  doc["ts_src"] = c.fonte;
  doc["fw"] = FW_VERSAO;
  char buf[192];
  if (serializar(doc, buf, sizeof(buf)) && rede.publicar(topicoEstado, buf, true)) {
    LOG_INFO("mqtt", "estado online publicado (retido)");
  }
  if (rede.assinar(topicoComandos, 1)) {
    LOG_INFO("mqtt", "assinado %s (QoS 1)", topicoComandos);
  } else {
    LOG_ERRO("mqtt", "falha ao assinar %s", topicoComandos);
  }
  publicarAssimQuePossivel = true;
  if (!primeiraConexao) {
    JsonDocument ev = novoEvento("reconexao");
    ev["detalhe"]["causa"] = rede.causaUltimaQueda();
    ev["detalhe"]["tentativas"] = rede.tentativasUltimaConexao();
    ev["detalhe"]["offline_s"] = rede.duracaoUltimaQueda_ms() / 1000UL;
    ev["detalhe"]["telemetrias_nao_enviadas"] = telemetriasNaoEnviadas;
    enfileirarEvento(ev);
  }
}

static void aplicarIntervalo(uint32_t segundos, bool persistir) {
  intervaloPublicacao_s = segundos;
  tarefaPublicacao.periodo_ms = segundos * 1000UL;
  if (persistir) nvs.putUInt("intervalo", segundos);
}

// Chamado de dentro de PubSubClient::loop(). O payload aponta para o buffer
// interno do cliente: é interpretado aqui e as respostas vão para a fila de
// eventos (publicadas depois, fora do callback).
static void aoReceberMqtt(char *topico, uint8_t *payload, unsigned int tamanho) {
  if (strcmp(topico, topicoComandos) != 0) return;
  JsonDocument doc;
  const DeserializationError erro = deserializeJson(doc, payload, tamanho);
  if (erro) {
    LOG_AVISO("cmd", "JSON invalido (%s)", erro.c_str());
    return;
  }
  const char *cmd = doc["cmd"] | "";
  LOG_INFO("cmd", "recebido: %s", cmd);

  if (strcmp(cmd, "intervalo") == 0) {
    if (!doc["valor"].is<uint32_t>()) {
      LOG_AVISO("cmd", "intervalo: 'valor' deve ser inteiro (segundos)");
      return;
    }
    const uint32_t v = doc["valor"].as<uint32_t>();
    if (v < CFG_INTERVALO_MEDICAO_S || v > 86400UL) {
      LOG_AVISO("cmd", "intervalo %lu s fora da faixa [%lu, 86400]", (unsigned long)v,
                (unsigned long)CFG_INTERVALO_MEDICAO_S);
      return;
    }
    aplicarIntervalo(v, true);
    LOG_INFO("cmd", "intervalo de publicacao = %lu s (salvo na NVS)", (unsigned long)v);
  } else if (strcmp(cmd, "led") == 0) {
    if (!doc["valor"].is<bool>()) {
      LOG_AVISO("cmd", "led: 'valor' deve ser booleano");
      return;
    }
    aplicarLed(doc["valor"].as<bool>());
    LOG_INFO("cmd", "LED %s", ledLigado ? "ligado" : "desligado");
  } else if (strcmp(cmd, "ping") == 0) {
    JsonDocument ev = novoEvento("pong");
    ev["detalhe"]["uptime_s"] = millis() / 1000UL;
    ev["detalhe"]["rssi"] = WiFi.RSSI();
    ev["detalhe"]["heap_livre"] = ESP.getFreeHeap();
    ev["detalhe"]["intervalo_s"] = intervaloPublicacao_s;
    ev["detalhe"]["led"] = ledLigado;
    ev["detalhe"]["fw"] = FW_VERSAO;
    enfileirarEvento(ev);
  } else {
    LOG_AVISO("cmd", "comando desconhecido: '%s'", cmd);
  }
}

// ===========================================================================
// Watchdog
// ===========================================================================
static void configurarWatchdog() {
  esp_task_wdt_config_t cfg = {};
  cfg.timeout_ms = CFG_WATCHDOG_S * 1000UL;
  cfg.idle_core_mask = 1U << 0;  // mantém a supervisão da tarefa ociosa do núcleo 0
  cfg.trigger_panic = true;
  esp_err_t r = esp_task_wdt_reconfigure(&cfg);
  if (r == ESP_ERR_INVALID_STATE) r = esp_task_wdt_init(&cfg);  // TWDT não iniciado pelo núcleo
  if (r == ESP_OK) r = esp_task_wdt_add(nullptr);                // supervisiona a tarefa de loop()
  if (r != ESP_OK) LOG_AVISO("wdt", "watchdog nao configurado (erro %d)", (int)r);
}

// ===========================================================================
// setup() / loop()
// ===========================================================================
void setup() {
  Serial.begin(CFG_SERIAL_BAUD);
  pinMode(CFG_PINO_LED, OUTPUT);  // no original o LED era configurado como INPUT
  aplicarLed(false);

  // Contador de boots e intervalo persistidos na NVS.
  nvs.begin(kNvsNamespace, false);
  contadorBoot = nvs.getUInt("boot", 0) + 1;
  nvs.putUInt("boot", contadorBoot);
  const uint32_t intervaloSalvo = nvs.getUInt("intervalo", CFG_INTERVALO_PUBLICACAO_S);
  aplicarIntervalo((intervaloSalvo >= CFG_INTERVALO_MEDICAO_S && intervaloSalvo <= 86400UL)
                       ? intervaloSalvo
                       : CFG_INTERVALO_PUBLICACAO_S,
                   false);

  LOG_INFO("boot", "firmware %s, id=%s, boot=%lu, motivo=%s, intervalo=%lu s", FW_VERSAO, CFG_ID_DISPOSITIVO,
           (unsigned long)contadorBoot, motivoReinicio(), (unsigned long)intervaloPublicacao_s);

  snprintf(topicoTelemetria, sizeof(topicoTelemetria), "%s/dispositivos/%s/telemetria", CFG_PREFIXO_TOPICO, CFG_ID_DISPOSITIVO);
  snprintf(topicoEstado, sizeof(topicoEstado), "%s/dispositivos/%s/estado", CFG_PREFIXO_TOPICO, CFG_ID_DISPOSITIVO);
  snprintf(topicoEventos, sizeof(topicoEventos), "%s/dispositivos/%s/eventos", CFG_PREFIXO_TOPICO, CFG_ID_DISPOSITIVO);
  snprintf(topicoComandos, sizeof(topicoComandos), "%s/dispositivos/%s/comandos", CFG_PREFIXO_TOPICO, CFG_ID_DISPOSITIVO);
  snprintf(payloadLwt, sizeof(payloadLwt), "{\"v\":%d,\"id\":\"%s\",\"estado\":\"offline\",\"motivo\":\"lwt\"}",
           ESQUEMA_VERSAO, CFG_ID_DISPOSITIVO);

  ultrassom.iniciar();
  ambiente.iniciar();

  // Evento de reinício: fica na fila até a primeira conexão.
  {
    JsonDocument ev = novoEvento("reinicio");
    ev["detalhe"]["motivo"] = motivoReinicio();
    ev["detalhe"]["boot"] = contadorBoot;
    ev["detalhe"]["fw"] = FW_VERSAO;
    enfileirarEvento(ev);
  }

  rede.iniciar(CFG_ID_DISPOSITIVO, topicoEstado, payloadLwt, aoConectarMqtt, aoReceberMqtt);
  configurarWatchdog();

  // Primeira medição ~2 s após o boot: o datasheet do DHT11 pede ao menos 1 s
  // após a energização antes do primeiro comando.
  tarefaMedicao.ultima_ms = millis() - tarefaMedicao.periodo_ms + 2000UL;
}

void loop() {
  esp_task_wdt_reset();
  const uint32_t agora = millis();

  rede.processar(agora);

  if (tarefaMedicao.vencida(agora)) iniciarMedicao();
  ultrassom.processar(agora);
  ResultadoUltrassom us;
  if (ultrassom.obterResultado(us)) concluirMedicao(us);

  if (publicarAssimQuePossivel && ultimaMedicao.existe && rede.mqttConectado()) {
    // Primeira telemetria após boot/reconexão sem esperar um intervalo inteiro.
    publicarAssimQuePossivel = false;
    tarefaPublicacao.ultima_ms = agora;
    publicarTelemetria();
  } else if (tarefaPublicacao.vencida(agora)) {
    publicarTelemetria();
  }
  descarregarEventos();
}
