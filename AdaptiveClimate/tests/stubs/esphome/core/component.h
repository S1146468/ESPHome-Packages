#pragma once
#include <cstdint>
namespace esphome {
inline uint64_t test_clock = 0;
inline uint32_t millis() { return uint32_t(test_clock); }
inline uint64_t millis_64() { return test_clock; }
inline uint32_t test_micros_step = 0;
inline uint32_t test_micros_offset = 0;
inline uint32_t micros() { test_micros_offset += test_micros_step; return uint32_t(test_clock * 1000) + test_micros_offset; }
namespace setup_priority { constexpr float DATA = 600; }
class PollingComponent {
 public:
  explicit PollingComponent(uint32_t interval) : interval(interval) {}
  virtual void setup() {}
  virtual void loop() {}
  virtual void update() {}
  virtual void dump_config() {}
  virtual float get_setup_priority() const { return 0; }
  uint32_t interval;
};
}
