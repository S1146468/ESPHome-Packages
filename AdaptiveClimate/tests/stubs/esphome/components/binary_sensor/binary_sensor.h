#pragma once
namespace esphome::binary_sensor {
struct BinarySensor {
  bool state = false, known = false;
  bool has_state() const { return known; }
  void publish_state(bool v) { state = v; known = true; }
};
}
