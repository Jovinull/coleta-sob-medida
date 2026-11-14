/*
 * calculos.h — funções puras (sem dependência de hardware) usadas pelo firmware.
 *
 * Mantidas isoladas para poderem ser testadas no computador hospedeiro com um
 * compilador C++ comum (não dependem de Arduino.h).
 */
#pragma once
#include <math.h>
#include <stdint.h>

namespace calc {

// Velocidade do som no ar seco em função da temperatura (°C), em m/s.
// Aproximação linear usual: c = 331,3 + 0,606·T (válida perto de 0–40 °C).
inline float velocidadeSom_m_s(float temperaturaC) {
  return 331.3f + 0.606f * temperaturaC;
}

// Converte a largura do pulso de eco (µs, ida e volta) em distância (cm).
// d = t · c / 2, com c em cm/µs = c[m/s] · 1e-4.
inline float duracaoParaDistancia_cm(uint32_t duracao_us, float temperaturaC) {
  return (float)duracao_us * velocidadeSom_m_s(temperaturaC) * 1e-4f / 2.0f;
}

// Converte distância (cm) em largura de pulso esperada (µs).
inline uint32_t distanciaParaDuracao_us(float distancia_cm, float temperaturaC) {
  return (uint32_t)(2.0f * distancia_cm / (velocidadeSom_m_s(temperaturaC) * 1e-4f));
}

// Ocupação da lixeira (%), conforme o contrato MQTT:
//   d_corr = d − offset;  ocupação = 100 · (H − d_corr) / H,  limitada a [0, 100].
// d: distância medida sensor→superfície dos resíduos; offset: deslocamento de
// montagem (sensor→linha de 100 %); H: altura útil (linha de 100 %→fundo).
inline float ocupacao_pct(float distancia_cm, float offset_cm, float alturaUtil_cm) {
  if (!(alturaUtil_cm > 0.0f)) return NAN;
  const float dCorr = distancia_cm - offset_cm;
  float ocup = 100.0f * (alturaUtil_cm - dCorr) / alturaUtil_cm;
  if (ocup < 0.0f) ocup = 0.0f;      // leitura abaixo do fundo (tolerância/ruído)
  if (ocup > 100.0f) ocup = 100.0f;  // resíduos acima da linha de 100 % (transbordo)
  return ocup;
}

// Mediana de n valores. ATENÇÃO: ordena o vetor no lugar (insertion sort; n pequeno).
inline float mediana(float *v, int n) {
  if (n <= 0) return NAN;
  for (int i = 1; i < n; ++i) {
    const float x = v[i];
    int j = i - 1;
    while (j >= 0 && v[j] > x) {
      v[j + 1] = v[j];
      --j;
    }
    v[j + 1] = x;
  }
  return (n % 2) ? v[n / 2] : 0.5f * (v[n / 2 - 1] + v[n / 2]);
}

// Espera do backoff exponencial com "equal jitter":
//   e = min(max, base · 2^tentativa);  retorna e/2 + aleatorio % (e/2 + 1).
inline uint32_t esperaBackoff_ms(uint32_t tentativa, uint32_t base_ms, uint32_t max_ms, uint32_t aleatorio) {
  uint32_t e = base_ms;
  for (uint32_t i = 0; i < tentativa && e < max_ms; ++i) e = (e > max_ms / 2) ? max_ms : e * 2;
  if (e > max_ms) e = max_ms;
  const uint32_t metade = e / 2;
  return metade + (aleatorio % (metade + 1));
}

// Arredonda para 1 casa decimal (em double, para o ArduinoJson imprimir "31.2"
// em vez de "31.20000076").
inline double arred1(float x) {
  return round((double)x * 10.0) / 10.0;
}

}  // namespace calc
