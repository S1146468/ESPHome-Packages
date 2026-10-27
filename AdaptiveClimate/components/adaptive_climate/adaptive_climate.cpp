#include "adaptive_climate.h"
#include "esphome/core/log.h"
#include <cstring>

namespace esphome {
namespace adaptive_climate {
static const char *const TAG = "adaptive_climate";
void AdaptiveClimate::setup() {
  for (unsigned i = 0; i < 4; ++i) {
    // Register before HA subscriptions begin. Never assign a new timestamp to an
    // already cached state, or to a filter heartbeat repeating that cached state.
    inputs_[i]->add_on_raw_state_callback([this, i](float value) {
      values_[i].receive(value, millis());
      if (!std::isfinite(value)) invalidate_("invalid_input");
    });
  }
  publish_status_("waiting_for_inputs");
}
const char *AdaptiveClimate::input_fault_(uint32_t now) const {
  for (const auto &v : values_)
    if (!v.fresh(now, stale_after_)) return "missing_or_stale_input";
  for (auto *flag : flags_)
    if (!flag->has_state()) return "missing_operating_state";
  if (flags_[1]->state) return "window_open";
  if (flags_[2]->state) return "domestic_hot_water";
  Observation o{values_[0].value, values_[1].value, values_[2].value, values_[3].value,
                flags_[0]->state, flags_[1]->state, flags_[2]->state};
  return o.valid() ? nullptr : "invalid_input";
}
void AdaptiveClimate::publish_status_(const char *value) {
  if (last_status_ == nullptr || std::strcmp(last_status_, value) != 0) {
    if (status_) status_->publish_state(value);
    last_status_ = value;
  }
}
void AdaptiveClimate::invalidate_(const char *reason) {
  observer_.suspend();
  for (unsigned i = 0; i < 3; ++i)
    if (diagnostics_[i] && std::isfinite(diagnostics_[i]->state)) diagnostics_[i]->publish_state(NAN);
  publish_status_(reason);
}
void AdaptiveClimate::loop() {
  uint32_t now = millis();
  if (uint32_t(now - last_guard_) < 1000) return;
  last_guard_ = now;
  if (const char *reason = input_fault_(now)) invalidate_(reason);
}
void AdaptiveClimate::update() {
  uint32_t now = millis();
  if (const char *reason = input_fault_(now)) { invalidate_(reason); return; }
  Observation o{values_[0].value, values_[1].value, values_[2].value, values_[3].value,
                flags_[0]->state, flags_[1]->state, flags_[2]->state};
  publish_status_(observer_.observe(o, now));
  const unsigned horizons[3] = {15, 30, 60};
  for (unsigned i = 0; i < 3; ++i)
    if (diagnostics_[i]) diagnostics_[i]->publish_state(observer_.ready() ?
        observer_.forecast(o, horizons[i]) : NAN);
  if (diagnostics_[3]) diagnostics_[3]->publish_state(observer_.model.rmse());
  if (diagnostics_[4]) diagnostics_[4]->publish_state(observer_.model.samples());
  if (diagnostics_[5]) diagnostics_[5]->publish_state(observer_.model.heat_span());
}
void AdaptiveClimate::dump_config() {
  ESP_LOGCONFIG(TAG, "Observation-only thermal model; 5-minute updates; no actuator interfaces");
  ESP_LOGCONFIG(TAG, "Raw-input timeout: %u ms; model state: %u bytes", (unsigned) stale_after_, (unsigned) sizeof(Observer));
}
}  // namespace adaptive_climate
}  // namespace esphome
