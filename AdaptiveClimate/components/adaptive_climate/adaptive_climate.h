#pragma once
#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "thermal_model.h"
#include "shadow_model.h"
#include "input_policy.h"
#include <string>

namespace esphome {
namespace adaptive_climate {
class AdaptiveClimate : public PollingComponent {
 public:
  AdaptiveClimate() : PollingComponent(300000) {}
  void set_input(unsigned i, sensor::Sensor *s) { inputs_[i] = s; }
  void set_flag(unsigned i, binary_sensor::BinarySensor *s) { flags_[i] = s; }
  void set_diagnostic(unsigned i, sensor::Sensor *s) { diagnostics_[i] = s; }
  void set_status(text_sensor::TextSensor *s) { status_ = s; }
  void set_cycle_record(text_sensor::TextSensor *s) { cycle_record_ = s; }
  void set_model_record(text_sensor::TextSensor *s) { model_record_ = s; }
  void set_shadow_model(bool enabled) { shadow_enabled_ = enabled; }
  void set_shadow_record(text_sensor::TextSensor *s) { shadow_record_ = s; }
  void set_shadow_forecasts(text_sensor::TextSensor *s) { shadow_forecasts_ = s; }
  void set_stale_after(uint32_t ms) { for (auto &v : values_) v.timeout = ms; }
  void set_input_policy(unsigned i, bool event_driven, uint32_t ms) {
    values_[i].event_driven = event_driven; values_[i].timeout = ms;
  }
  void set_availability(unsigned i, binary_sensor::BinarySensor *s) { availability_[i] = s; }
  void set_input_age(unsigned i, sensor::Sensor *s) { ages_[i] = s; }
  void set_input_status(text_sensor::TextSensor *s) { input_status_ = s; }
  void set_require_api_connection(bool value) { require_api_connection_ = value; }
  void set_valve_command_scale(float value) { valve_command_scale_ = value; }
  void setup() override;
  void loop() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }
 protected:
  const char *input_fault_(uint64_t now) const;
  InputState input_state_(unsigned i, uint64_t now) const;
  bool api_available_() const;
  void publish_inputs_(uint64_t now);
  void invalidate_(const char *reason);
  void publish_status_(const char *value);
  void publish_cycle_(uint64_t now, const char *outcome, const char *reason, const float *forecasts);
  void feed_shadow_(uint64_t now, bool room_publication);
  void publish_models_(uint64_t now);
  sensor::Sensor *inputs_[4]{};
  binary_sensor::BinarySensor *flags_[3]{};
  sensor::Sensor *diagnostics_[6]{};
  text_sensor::TextSensor *status_{nullptr};
  text_sensor::TextSensor *cycle_record_{nullptr};
  text_sensor::TextSensor *model_record_{nullptr}, *shadow_record_{nullptr}, *shadow_forecasts_{nullptr};
  bool shadow_enabled_{false};
  ShadowObserver shadow_;
  uint64_t cycle_sequence_{0};
  InputPolicy values_[4];
  sensor::Sensor *ages_[4]{};
  binary_sensor::BinarySensor *availability_[4]{};
  text_sensor::TextSensor *input_status_{nullptr};
  std::string last_input_status_;
  bool require_api_connection_{false};
  float valve_command_scale_{1.0f};
  Observer observer_;
  uint32_t last_guard_{0}, last_age_publish_{0};
  const char *last_status_{nullptr};
};
}  // namespace adaptive_climate
}  // namespace esphome
