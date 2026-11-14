/*
 * configuracao.h — inclui config.h (local, não versionado) e deriva constantes.
 *
 * Todos os módulos incluem ESTE arquivo, nunca config.h diretamente, para que
 * as verificações de consistência abaixo sejam aplicadas em um só lugar.
 */
#pragma once

#if __has_include("config.h")
#include "config.h"
#else
#error "Arquivo config.h ausente: copie config.example.h para config.h e edite-o."
#endif

// Versão do firmware publicada no tópico de estado (campo "fw").
#define FW_VERSAO "2.0.0"
// Versão do esquema de mensagens (campo "v" do contrato MQTT).
#define ESQUEMA_VERSAO 1

// Altura útil da lixeira (contrato: H = distância sensor→fundo − deslocamento).
#define ALTURA_UTIL_CM (CFG_DIST_SENSOR_FUNDO_CM - CFG_OFFSET_MONTAGEM_CM)

// Faixa nominal do HC-SR04 segundo o datasheet (2 cm a 400 cm).
#define US_FAIXA_MIN_CM 2.0f
#define US_FAIXA_MAX_CM 400.0f

static_assert(ALTURA_UTIL_CM > 0.0f, "CFG_DIST_SENSOR_FUNDO_CM deve ser maior que CFG_OFFSET_MONTAGEM_CM");
static_assert(CFG_OFFSET_MONTAGEM_CM >= 0.0f, "CFG_OFFSET_MONTAGEM_CM não pode ser negativo");
static_assert(CFG_DIST_SENSOR_FUNDO_CM <= US_FAIXA_MAX_CM, "lixeira maior que o alcance do HC-SR04 (400 cm)");
static_assert(CFG_US_PULSOS_POR_MEDICAO >= 1 && CFG_US_PULSOS_POR_MEDICAO <= 15, "CFG_US_PULSOS_POR_MEDICAO fora de [1,15]");
static_assert(CFG_US_MIN_PULSOS_VALIDOS >= 1 && CFG_US_MIN_PULSOS_VALIDOS <= CFG_US_PULSOS_POR_MEDICAO,
              "CFG_US_MIN_PULSOS_VALIDOS deve estar em [1, CFG_US_PULSOS_POR_MEDICAO]");
static_assert(CFG_US_INTERVALO_PULSOS_MS >= 60, "o datasheet do HC-SR04 recomenda ciclo de medição > 60 ms");
static_assert(CFG_INTERVALO_MEDICAO_S >= 2, "DHT: a biblioteca Adafruit impõe intervalo mínimo de 2 s entre leituras");
static_assert(CFG_INTERVALO_PUBLICACAO_S >= CFG_INTERVALO_MEDICAO_S, "publicação não pode ser mais frequente que a medição");
static_assert(CFG_HISTERESE_PCT >= 0.0f && CFG_HISTERESE_PCT < CFG_LIMIAR_ALERTA_PCT, "histerese inválida");
static_assert(CFG_BACKOFF_BASE_MS > 0 && CFG_BACKOFF_MAX_MS >= CFG_BACKOFF_BASE_MS, "backoff inválido");
static_assert(CFG_MQTT_TAMANHO_BUFFER >= 512, "buffer MQTT pequeno demais para a telemetria");

#if defined(CFG_MQTT_TLS) && !defined(CFG_MQTT_CA_PEM) && !defined(CFG_MQTT_TLS_INSEGURO)
#error "CFG_MQTT_TLS exige CFG_MQTT_CA_PEM (ou, só para testes, CFG_MQTT_TLS_INSEGURO)."
#endif
