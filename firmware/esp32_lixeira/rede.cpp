/*
 * rede.cpp — implementação do gerenciador de conectividade.
 *
 * Diagrama de estados:
 *
 *   WifiIniciar ──> WifiAguardando ──(associado)──> MqttConectar ──(CONNACK ok)──> Operando
 *        ^               │ timeout                     │ falha                       │ queda Wi-Fi/MQTT
 *        │               v                             v                             v
 *        └─────────── Backoff <────────────────────────┴──────────── (registrarQueda)┘
 *
 * Nenhum estado usa delay(): o único trecho bloqueante é PubSubClient::connect()
 * (DNS + TCP + CONNACK), limitado por CFG_MQTT_TIMEOUT_SOCKET_S e pelo timeout
 * de conexão TCP do núcleo ESP32.
 */
#include "rede.h"

#include <WiFi.h>
#include <esp_random.h>
#include <time.h>

#ifdef CFG_MQTT_TLS
#include <WiFiClientSecure.h>
#endif

#include "calculos.h"
#include "registro.h"

namespace {
#ifdef CFG_MQTT_TLS
WiFiClientSecure clienteTcp;
#else
WiFiClient clienteTcp;
#endif

// 2023-11-14 00:00:00 UTC: qualquer horário anterior indica relógio não acertado.
constexpr time_t kEpocaMinimaValida = 1699920000;

const char *descreverEstadoMqtt(int s) {
  switch (s) {
    case MQTT_CONNECTION_TIMEOUT: return "timeout";
    case MQTT_CONNECTION_LOST: return "conexao perdida";
    case MQTT_CONNECT_FAILED: return "falha TCP";
    case MQTT_DISCONNECTED: return "desconectado";
    case MQTT_CONNECTED: return "conectado";
    case MQTT_CONNECT_BAD_PROTOCOL: return "protocolo recusado";
    case MQTT_CONNECT_BAD_CLIENT_ID: return "client id recusado";
    case MQTT_CONNECT_UNAVAILABLE: return "broker indisponivel";
    case MQTT_CONNECT_BAD_CREDENTIALS: return "credenciais invalidas";
    case MQTT_CONNECT_UNAUTHORIZED: return "nao autorizado";
    default: return "desconhecido";
  }
}
}  // namespace

// ---------------------------------------------------------------------------
// Relógio
// ---------------------------------------------------------------------------
bool relogioSincronizado() {
  return time(nullptr) >= kEpocaMinimaValida;
}

Carimbo carimboAgora() {
  if (relogioSincronizado()) return {(uint32_t)time(nullptr), "ntp"};
  return {(uint32_t)(millis() / 1000UL), "uptime"};
}

// ---------------------------------------------------------------------------
// Gerenciador de rede
// ---------------------------------------------------------------------------
void GerenciadorRede::iniciar(const char *clientId, const char *topicoEstado, const char *payloadLwt,
                              AoConectar aoConectar, AoReceber aoReceber) {
  clientId_ = clientId;
  topicoEstado_ = topicoEstado;
  payloadLwt_ = payloadLwt;
  aoConectar_ = aoConectar;

  WiFi.persistent(false);         // não grava SSID/senha na flash a cada begin()
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(false);   // a reconexão é feita por esta máquina de estados
  WiFi.setHostname(clientId);

#ifdef CFG_MQTT_TLS
#ifdef CFG_MQTT_CA_PEM
  clienteTcp.setCACert(CFG_MQTT_CA_PEM);
#else
  clienteTcp.setInsecure();
  LOG_AVISO("rede", "TLS SEM validacao de certificado (CFG_MQTT_TLS_INSEGURO) - apenas para testes!");
#endif
#endif

  mqtt_.setClient(clienteTcp);
  mqtt_.setServer(CFG_MQTT_HOST, CFG_MQTT_PORTA);
  mqtt_.setKeepAlive(CFG_MQTT_KEEPALIVE_S);
  mqtt_.setSocketTimeout(CFG_MQTT_TIMEOUT_SOCKET_S);
  if (!mqtt_.setBufferSize(CFG_MQTT_TAMANHO_BUFFER)) {
    LOG_ERRO("mqtt", "sem memoria para buffer de %d bytes", CFG_MQTT_TAMANHO_BUFFER);
  }
  mqtt_.setCallback(aoReceber);

  estado_ = Estado::WifiIniciar;
  quedaDesde_ms_ = millis();
}

void GerenciadorRede::agendarBackoff(uint32_t &contadorFalhas, Estado proximo, const char *motivo) {
  espera_ms_ = calc::esperaBackoff_ms(contadorFalhas, CFG_BACKOFF_BASE_MS, CFG_BACKOFF_MAX_MS, esp_random());
  if (contadorFalhas < 31) ++contadorFalhas;
  aposBackoff_ = proximo;
  marco_ms_ = millis();
  estado_ = Estado::Backoff;
  LOG_AVISO("rede", "%s; nova tentativa em %lu ms (falhas consecutivas=%lu)", motivo, (unsigned long)espera_ms_,
            (unsigned long)contadorFalhas);
}

void GerenciadorRede::registrarQueda(const char *causa) {
  causaUltimaQueda_ = causa;
  quedaDesde_ms_ = millis();
  tentativasDesdeQueda_ = 0;
}

bool GerenciadorRede::conectarMqtt() {
  const char *usuario = (sizeof(CFG_MQTT_USUARIO) > 1) ? CFG_MQTT_USUARIO : nullptr;
  const char *senha = (sizeof(CFG_MQTT_SENHA) > 1) ? CFG_MQTT_SENHA : nullptr;
  ++tentativasDesdeQueda_;
  LOG_INFO("mqtt", "conectando a %s:%d como '%s'%s", CFG_MQTT_HOST, CFG_MQTT_PORTA, clientId_,
           usuario ? " (com autenticacao)" : "");
  // Last Will: retido, QoS 1, no tópico de estado (contrato MQTT). cleanSession = true.
  const bool ok = mqtt_.connect(clientId_, usuario, senha, topicoEstado_, 1, true, payloadLwt_, true);
  if (!ok) {
    LOG_AVISO("mqtt", "falha na conexao: rc=%d (%s)", mqtt_.state(), descreverEstadoMqtt(mqtt_.state()));
  }
  return ok;
}

void GerenciadorRede::processar(uint32_t agora_ms) {
  switch (estado_) {
    case Estado::WifiIniciar:
      LOG_INFO("wifi", "associando a rede '%s'", CFG_WIFI_SSID);  // a senha nunca é registrada
      WiFi.disconnect();
      WiFi.begin(CFG_WIFI_SSID, CFG_WIFI_SENHA);
      marco_ms_ = agora_ms;
      estado_ = Estado::WifiAguardando;
      break;

    case Estado::WifiAguardando:
      if (WiFi.status() == WL_CONNECTED) {
        LOG_INFO("wifi", "conectado: IP=%s RSSI=%d dBm", WiFi.localIP().toString().c_str(), WiFi.RSSI());
        falhasWifi_ = 0;
        if (!ntpConfigurado_) {
          // UTC (offset 0): o contrato exige ts em segundos Unix UTC.
          configTime(0, 0, CFG_NTP_SERVIDOR_1, CFG_NTP_SERVIDOR_2);
          ntpConfigurado_ = true;
        }
        estado_ = Estado::MqttConectar;
      } else if ((uint32_t)(agora_ms - marco_ms_) >= CFG_WIFI_TIMEOUT_CONEXAO_MS) {
        WiFi.disconnect();
        agendarBackoff(falhasWifi_, Estado::WifiIniciar, "Wi-Fi nao associou no tempo limite");
      }
      break;

    case Estado::MqttConectar:
      if (WiFi.status() != WL_CONNECTED) {
        estado_ = Estado::WifiIniciar;
        break;
      }
      if (conectarMqtt()) {
        falhasMqtt_ = 0;
        tentativasUltimaConexao_ = tentativasDesdeQueda_;
        duracaoUltimaQueda_ms_ = millis() - quedaDesde_ms_;
        estado_ = Estado::Operando;
        LOG_INFO("mqtt", "conectado apos %lu tentativa(s), %lu ms offline", (unsigned long)tentativasUltimaConexao_,
                 (unsigned long)duracaoUltimaQueda_ms_);
        const bool primeira = !jaConectou_;
        jaConectou_ = true;
        if (aoConectar_) aoConectar_(primeira);
      } else {
        agendarBackoff(falhasMqtt_, Estado::MqttConectar, "MQTT indisponivel");
      }
      break;

    case Estado::Operando:
      if (WiFi.status() != WL_CONNECTED) {
        LOG_AVISO("wifi", "conexao Wi-Fi perdida");
        registrarQueda("wifi");
        // Fecha só o socket: mqtt_.disconnect() enviaria DISCONNECT, e um
        // DISCONNECT "limpo" faz o broker descartar o Last Will.
        clienteTcp.stop();
        agendarBackoff(falhasWifi_, Estado::WifiIniciar, "reassociando Wi-Fi");
      } else if (!mqtt_.loop()) {  // loop() devolve false se a sessão MQTT caiu
        LOG_AVISO("mqtt", "sessao MQTT perdida: rc=%d (%s)", mqtt_.state(), descreverEstadoMqtt(mqtt_.state()));
        registrarQueda("mqtt");
        // Mesmo a primeira retentativa passa pelo backoff com jitter, para que
        // muitas lixeiras não reconectem todas no mesmo instante após uma
        // queda do broker.
        agendarBackoff(falhasMqtt_, Estado::MqttConectar, "reconectando ao broker");
      }
      break;

    case Estado::Backoff:
      if ((uint32_t)(agora_ms - marco_ms_) >= espera_ms_) estado_ = aposBackoff_;
      break;
  }
}

bool GerenciadorRede::publicar(const char *topico, const char *payload, bool retido) {
  if (!mqttConectado()) return false;
  const size_t n = strlen(payload);
  // PubSubClient descarta silenciosamente mensagens maiores que o buffer.
  if (n + strlen(topico) + 8 > mqtt_.getBufferSize()) {
    LOG_ERRO("mqtt", "mensagem de %u bytes excede o buffer (%u)", (unsigned)n, (unsigned)mqtt_.getBufferSize());
    return false;
  }
  return mqtt_.publish(topico, (const uint8_t *)payload, n, retido);
}

bool GerenciadorRede::assinar(const char *topico, uint8_t qos) {
  return mqttConectado() && mqtt_.subscribe(topico, qos);
}
