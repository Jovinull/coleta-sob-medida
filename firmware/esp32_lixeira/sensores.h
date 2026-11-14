/*
 * sensores.h — leitura do HC-SR04 (rajada + mediana, não bloqueante) e do DHT.
 */
#pragma once
#include <Arduino.h>
#include "configuracao.h"

// Resultado consolidado de uma medição ultrassônica (rajada de N pulsos).
struct ResultadoUltrassom {
  bool valida = false;
  float distancia_cm = NAN;  // mediana dos pulsos válidos (já compensada pela temperatura)
  uint8_t pulsosValidos = 0;
  uint8_t timeouts = 0;      // pulseIn() devolveu 0 (sem eco dentro do tempo limite)
  uint8_t foraDaFaixa = 0;   // eco recebido, mas fora de [2 cm, fundo + margem]
};

// Máquina de estados da rajada: cada chamada de processar() dispara no máximo
// UM pulso (bloqueio máximo = timeout do pulseIn, alguns ms), respeitando o
// intervalo mínimo entre pulsos recomendado pelo datasheet.
class SensorUltrassonico {
 public:
  void iniciar();
  // Começa uma nova rajada; temperaturaC é usada na compensação da velocidade do som.
  void comecarMedicao(float temperaturaC);
  void processar(uint32_t agora_ms);
  bool ocupado() const { return estado_ == Estado::Medindo; }
  // Retorna true UMA vez quando a rajada termina e copia o resultado.
  bool obterResultado(ResultadoUltrassom &saida);

 private:
  enum class Estado : uint8_t { Ocioso, Medindo, Concluido };
  Estado estado_ = Estado::Ocioso;
  float temperaturaC_ = CFG_US_TEMPERATURA_PADRAO_C;
  uint32_t timeout_us_ = 0;
  uint32_t ultimoPulso_ms_ = 0;
  uint8_t pulsosDisparados_ = 0;
  float amostras_[CFG_US_PULSOS_POR_MEDICAO] = {};
  ResultadoUltrassom resultado_;

  void dispararPulso();
  void finalizar();
};

// Leitura de temperatura do ar e umidade relativa.
struct LeituraAmbiente {
  bool temperaturaValida = false;
  bool umidadeValida = false;
  float temperaturaC = NAN;
  float umidadePct = NAN;
};

class SensorAmbiente {
 public:
  void iniciar();  // chama dht.begin()
  LeituraAmbiente ler();
};
