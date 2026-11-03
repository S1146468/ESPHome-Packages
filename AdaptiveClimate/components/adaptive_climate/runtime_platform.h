#pragma once
#include <algorithm>
#include <cstdint>
#ifdef USE_ESP32
#include "esp_heap_caps.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#endif

namespace esphome::adaptive_climate {
inline uint32_t runtime_clock_us() {
#ifdef USE_ESP32
  return uint32_t(esp_timer_get_time());
#else
  return esphome::micros();
#endif
}
inline uint32_t runtime_boot_id() {
#ifdef USE_ESP32
  static const uint32_t boot = esp_random();
#else
  static const uint32_t boot = 1;  // deterministic host test, never a device ID
#endif
  return boot;
}
struct RuntimeMemory { uint32_t free, minimum, largest, stack; };
inline RuntimeMemory runtime_memory() {
#ifdef USE_ESP32
  constexpr uint32_t caps = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
  return {uint32_t(heap_caps_get_free_size(caps)), uint32_t(heap_caps_get_minimum_free_size(caps)),
          uint32_t(heap_caps_get_largest_free_block(caps)), uint32_t(uxTaskGetStackHighWaterMark(nullptr))};
#else
  return {0, 0, 0, 0};  // no fabricated hardware measurements on a host
#endif
}
class RuntimeScope {
 public:
  explicit RuntimeScope(uint32_t *maximum) : maximum_(maximum), start_(maximum ? runtime_clock_us() : 0) {}
  ~RuntimeScope() { if (maximum_) *maximum_ = std::max(*maximum_, uint32_t(runtime_clock_us() - start_)); }
 private:
  uint32_t *maximum_;
  uint32_t start_;
};
template<class F> auto runtime_sum(uint32_t *sum, F call) {
  if (!sum) return call();
  const uint32_t start = runtime_clock_us();
  auto result = call();
  *sum += uint32_t(runtime_clock_us() - start);
  return result;
}
}  // namespace esphome::adaptive_climate
