#pragma once
#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "thermal_model.h"

namespace esphome {
namespace adaptive_climate {
class AdaptiveClimate : public PollingComponent {
 public:
  AdaptiveClimate() : PollingComponent(300000) {}
  void set_input(unsigned i, sensor::Sensor *s) { inputs_[i] = s; }
  void set_flag(unsigned i, binary_sensor::BinarySensor *s) { flags_[i] = s; }
  void set_diagnostic(unsigned i, sensor::Sensor *s) { diagnostics_[i] = s; }
  void set_status(text_sensor::TextSensor *s) { status_ = s; }
  void set_stale_after(uint32_t ms) { stale_after_ = ms; }
  void setup() override;
  void loop() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }
 protected:
  const char *input_fault_(uint32_t now) const;
  void invalidate_(const char *reason);
  void publish_status_(const char *value);
  sensor::Sensor *inputs_[4]{};
  binary_sensor::BinarySensor *flags_[3]{};
  sensor::Sensor *diagnostics_[6]{};
  text_sensor::TextSensor *status_{nullptr};
  InputValue values_[4];
  Observer observer_;
  uint32_t stale_after_{900000}, last_guard_{0};
  const char *last_status_{nullptr};
};
}  // namespace adaptive_climate
}  // namespace esphome
