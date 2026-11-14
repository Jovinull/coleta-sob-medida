/*
 * rede.h — Wi-Fi + MQTT com máquina de estados não bloqueante, backoff
 * exponencial com jitter (limitado), Last Will retido e relógio (NTP/uptime).
 */
#pragma once
#include <Arduino.h>
#include <PubSubClient.h>

#include "configuracao.h"

// Origem do carimbo de tempo, conforme o contrato ("ntp" ou "uptime").
struct Carimbo {
  uint32_t ts;        // segundos desde a época Unix (ntp) ou desde o boot (uptime)
  const char *fonte;  // "ntp" | "uptime"
};

// true quando o relógio do sistema já foi acertado via SNTP.
bool relogioSincronizado();
Carimbo carimboAgora();

class GerenciadorRede {
 public:
  using AoConectar = void (*)(bool primeiraConexao);
  using AoReceber = void (*)(char *topico, uint8_t *payload, unsigned int tamanho);

  // topicoEstado/lwt devem permanecer válidos durante toda a execução.
  void iniciar(const char *clientId, const char *topicoEstado, const char *payloadLwt, AoConectar aoConectar,
               AoReceber aoReceber);
  void processar(uint32_t agora_ms);

  bool mqttConectado() { return estado_ == Estado::Operando && mqtt_.connected(); }
  bool publicar(const char *topico, const char *payload, bool retido = false);
  bool assinar(const char *topico, uint8_t qos);

  // Dados da última reconexão (para o evento "reconexao").
  uint32_t tentativasUltimaConexao() const { return tentativasUltimaConexao_; }
  uint32_t duracaoUltimaQueda_ms() const { return duracaoUltimaQueda_ms_; }
  const char *causaUltimaQueda() const { return causaUltimaQueda_; }

 private:
  enum class Estado : uint8_t { WifiIniciar, WifiAguardando, MqttConectar, Operando, Backoff };

  PubSubClient mqtt_;
  Estado estado_ = Estado::WifiIniciar;
  Estado aposBackoff_ = Estado::WifiIniciar;
  uint32_t marco_ms_ = 0;    // início do estado atual (timeout/backoff)
  uint32_t espera_ms_ = 0;   // duração do backoff corrente
  uint32_t falhasWifi_ = 0;  // falhas consecutivas (expoente do backoff)
  uint32_t falhasMqtt_ = 0;
  uint32_t tentativasDesdeQueda_ = 0;
  uint32_t quedaDesde_ms_ = 0;
  bool jaConectou_ = false;
  bool ntpConfigurado_ = false;
  uint32_t tentativasUltimaConexao_ = 0;
  uint32_t duracaoUltimaQueda_ms_ = 0;
  const char *causaUltimaQueda_ = "boot";

  const char *clientId_ = nullptr;
  const char *topicoEstado_ = nullptr;
  const char *payloadLwt_ = nullptr;
  AoConectar aoConectar_ = nullptr;

  void agendarBackoff(uint32_t &contadorFalhas, Estado proximo, const char *motivo);
  void registrarQueda(const char *causa);
  bool conectarMqtt();
};
