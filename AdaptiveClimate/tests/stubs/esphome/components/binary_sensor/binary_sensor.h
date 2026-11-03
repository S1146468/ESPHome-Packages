#pragma once
#include <functional>
#include <vector>
namespace esphome::binary_sensor {
struct BinarySensor {
  bool state = false, known = false;
  std::vector<std::function<void(bool)>> callbacks;
  void add_on_state_callback(std::function<void(bool)> f) { callbacks.push_back(f); }
  bool has_state() const { return known; }
  void publish_state(bool v) { state = v; known = true; for (auto &f : callbacks) f(v); }
};
}
