#pragma once
#include <cmath>
#include <functional>
#include <vector>
namespace esphome::sensor {
class Sensor {
 public:
  float state = NAN;
  std::vector<std::function<void(float)>> callbacks;
  std::vector<std::function<void(float)>> filtered_callbacks;
  void add_on_state_callback(std::function<void(float)> f) { filtered_callbacks.push_back(f); }
  void add_on_raw_state_callback(std::function<void(float)> f) { callbacks.push_back(f); }
  void publish_state(float value) { for (auto &f : callbacks) f(value); state = value; for (auto &f : filtered_callbacks) f(value); }
  // ESPHome filters send only to the frontend, not the raw callbacks.
  void filtered_heartbeat(float value) { state = value; for (auto &f : filtered_callbacks) f(value); }
};
}
