/*
 * registro.h — log na Serial com níveis (ERRO, AVISO, INFO, DEPURA).
 *
 * Uso: LOG_INFO("rede", "conectado, IP=%s", ip);
 * Formato da linha: "[   12.345] I rede: conectado, IP=..."
 * O nível é definido por CFG_NIVEL_LOG; chamadas acima do nível são removidas
 * pelo pré-processador (custo zero).
 */
#pragma once
#include <Arduino.h>
#include "configuracao.h"

#define NIVEL_LOG_ERRO   1
#define NIVEL_LOG_AVISO  2
#define NIVEL_LOG_INFO   3
#define NIVEL_LOG_DEPURA 4

#define LOG_IMPL_(letra, modulo, fmt, ...)                                        \
  Serial.printf("[%5lu.%03lu] %c %s: " fmt "\n", (unsigned long)(millis() / 1000), \
                (unsigned long)(millis() % 1000), letra, modulo, ##__VA_ARGS__)

#if CFG_NIVEL_LOG >= NIVEL_LOG_ERRO
#define LOG_ERRO(modulo, fmt, ...) LOG_IMPL_('E', modulo, fmt, ##__VA_ARGS__)
#else
#define LOG_ERRO(modulo, fmt, ...) do {} while (0)
#endif

#if CFG_NIVEL_LOG >= NIVEL_LOG_AVISO
#define LOG_AVISO(modulo, fmt, ...) LOG_IMPL_('W', modulo, fmt, ##__VA_ARGS__)
#else
#define LOG_AVISO(modulo, fmt, ...) do {} while (0)
#endif

#if CFG_NIVEL_LOG >= NIVEL_LOG_INFO
#define LOG_INFO(modulo, fmt, ...) LOG_IMPL_('I', modulo, fmt, ##__VA_ARGS__)
#else
#define LOG_INFO(modulo, fmt, ...) do {} while (0)
#endif

#if CFG_NIVEL_LOG >= NIVEL_LOG_DEPURA
#define LOG_DEPURA(modulo, fmt, ...) LOG_IMPL_('D', modulo, fmt, ##__VA_ARGS__)
#else
#define LOG_DEPURA(modulo, fmt, ...) do {} while (0)
#endif
