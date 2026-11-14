/*
 * sensores.cpp — implementação dos sensores (HC-SR04 e DHT).
 */
#include "sensores.h"

#include <DHT.h>

#include "calculos.h"
#include "registro.h"

namespace {

// Distância máxima plausível: fundo da lixeira + margem, limitada ao alcance do sensor.
constexpr float kDistMaxPlausivel_cm =
    (CFG_DIST_SENSOR_FUNDO_CM + CFG_MARGEM_PLAUSIVEL_CM) < US_FAIXA_MAX_CM
        ? (CFG_DIST_SENSOR_FUNDO_CM + CFG_MARGEM_PLAUSIVEL_CM)
        : US_FAIXA_MAX_CM;

// Temperatura usada só para dimensionar o timeout do pulseIn (pior caso: ar
// frio => som mais lento => pulso mais longo).
constexpr float kTempPiorCaso_C = -20.0f;

// Folga somada ao timeout: atraso entre o fim do TRIG e a subida do ECHO
// (o módulo emite 8 ciclos de 40 kHz = 200 µs antes de levantar o ECHO).
constexpr uint32_t kFolgaTimeout_us = 2000;

#if CFG_HABILITAR_DHT
DHT dht(CFG_PINO_DHT, CFG_DHT_TIPO);
#endif

}  // namespace

// ---------------------------------------------------------------------------
// HC-SR04
// ---------------------------------------------------------------------------
void SensorUltrassonico::iniciar() {
  pinMode(CFG_PINO_TRIG, OUTPUT);
  digitalWrite(CFG_PINO_TRIG, LOW);
  pinMode(CFG_PINO_ECHO, INPUT);  // nível já reduzido para 3,3 V pelo divisor resistivo
  timeout_us_ = calc::distanciaParaDuracao_us(kDistMaxPlausivel_cm, kTempPiorCaso_C) + kFolgaTimeout_us;
  LOG_INFO("us", "TRIG=GPIO%d ECHO=GPIO%d, H=%.1f cm, faixa plausivel=[%.0f, %.0f] cm, timeout=%lu us",
           CFG_PINO_TRIG, CFG_PINO_ECHO, (double)ALTURA_UTIL_CM, (double)US_FAIXA_MIN_CM,
           (double)kDistMaxPlausivel_cm, (unsigned long)timeout_us_);
}

void SensorUltrassonico::comecarMedicao(float temperaturaC) {
  temperaturaC_ = temperaturaC;
  pulsosDisparados_ = 0;
  resultado_ = ResultadoUltrassom{};
  estado_ = Estado::Medindo;
  // Garante que o primeiro pulso saia na próxima chamada de processar().
  ultimoPulso_ms_ = millis() - CFG_US_INTERVALO_PULSOS_MS;
}

void SensorUltrassonico::processar(uint32_t agora_ms) {
  if (estado_ != Estado::Medindo) return;
  if ((uint32_t)(agora_ms - ultimoPulso_ms_) < CFG_US_INTERVALO_PULSOS_MS) return;
  ultimoPulso_ms_ = agora_ms;
  dispararPulso();
  if (pulsosDisparados_ >= CFG_US_PULSOS_POR_MEDICAO) finalizar();
}

void SensorUltrassonico::dispararPulso() {
  // Pulso de disparo de 10 µs (datasheet: "at least 10us high level").
  digitalWrite(CFG_PINO_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(CFG_PINO_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(CFG_PINO_TRIG, LOW);

  // pulseIn devolve 0 se o pulso não começar E terminar dentro do timeout.
  const unsigned long duracao_us = pulseIn(CFG_PINO_ECHO, HIGH, timeout_us_);
  ++pulsosDisparados_;

  if (duracao_us == 0) {
    ++resultado_.timeouts;
    LOG_DEPURA("us", "pulso %u: timeout", pulsosDisparados_);
    return;
  }
  const float d = calc::duracaoParaDistancia_cm((uint32_t)duracao_us, temperaturaC_);
  if (d < US_FAIXA_MIN_CM || d > kDistMaxPlausivel_cm) {
    ++resultado_.foraDaFaixa;
    LOG_DEPURA("us", "pulso %u: %lu us = %.1f cm (fora da faixa)", pulsosDisparados_, duracao_us, (double)d);
    return;
  }
  amostras_[resultado_.pulsosValidos++] = d;
  LOG_DEPURA("us", "pulso %u: %lu us = %.1f cm", pulsosDisparados_, duracao_us, (double)d);
}

void SensorUltrassonico::finalizar() {
  if (resultado_.pulsosValidos >= CFG_US_MIN_PULSOS_VALIDOS) {
    resultado_.valida = true;
    resultado_.distancia_cm = calc::mediana(amostras_, resultado_.pulsosValidos);
  } else {
    resultado_.valida = false;
    resultado_.distancia_cm = NAN;
  }
  estado_ = Estado::Concluido;
}

bool SensorUltrassonico::obterResultado(ResultadoUltrassom &saida) {
  if (estado_ != Estado::Concluido) return false;
  saida = resultado_;
  estado_ = Estado::Ocioso;
  return true;
}

// ---------------------------------------------------------------------------
// DHT11 / DHT22
// ---------------------------------------------------------------------------
void SensorAmbiente::iniciar() {
#if CFG_HABILITAR_DHT
  dht.begin();  // ausente no firmware original
  LOG_INFO("dht", "DHT tipo %d em GPIO%d", (int)CFG_DHT_TIPO, CFG_PINO_DHT);
#endif
}

LeituraAmbiente SensorAmbiente::ler() {
  LeituraAmbiente l;
#if CFG_HABILITAR_DHT
  // readTemperature() faz a leitura física (respeitando o intervalo mínimo de
  // 2 s da biblioteca); readHumidity() logo em seguida reaproveita o mesmo quadro.
  const float t = dht.readTemperature();
  const float h = dht.readHumidity();
  // Faixas físicas plausíveis (não as de especificação do DHT11, 0–50 °C e
  // 20–90 %RH, para não descartar leituras reais em condições extremas).
  l.temperaturaValida = !isnan(t) && t >= -40.0f && t <= 80.0f;
  l.umidadeValida = !isnan(h) && h >= 0.0f && h <= 100.0f;
  l.temperaturaC = l.temperaturaValida ? t : NAN;
  l.umidadePct = l.umidadeValida ? h : NAN;
  if (!l.temperaturaValida || !l.umidadeValida) {
    LOG_AVISO("dht", "leitura invalida (T=%.1f, UR=%.1f)", (double)t, (double)h);
  }
#endif
  return l;
}
