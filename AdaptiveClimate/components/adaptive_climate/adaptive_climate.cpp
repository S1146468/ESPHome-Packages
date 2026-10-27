#include "adaptive_climate.h"
#include "esphome/core/log.h"
#include <cstring>
#ifdef USE_API
#include "esphome/components/api/api_server.h"
#endif

namespace esphome {
namespace adaptive_climate {
static const char *const TAG = "adaptive_climate";
void AdaptiveClimate::setup() {
  for (unsigned i = 0; i < 4; ++i) {
    // Register before HA subscriptions begin. Never assign a new timestamp to an
    // already cached state, or to a filter heartbeat repeating that cached state.
    inputs_[i]->add_on_raw_state_callback([this, i](float value) {
      const uint64_t now = millis_64();
      values_[i].receive(i == 2 ? value * valve_command_scale_ : value, now);
      if (const char *reason = input_fault_(now)) invalidate_(reason);
      publish_inputs_(now);
    });
  }
  publish_status_("waiting_for_inputs");
}
bool AdaptiveClimate::api_available_() const {
  if (!require_api_connection_) return true;
#ifdef USE_API
  return api::global_api_server != nullptr && api::global_api_server->is_connected_with_state_subscription();
#else
  return false;
#endif
}
InputState AdaptiveClimate::input_state_(unsigned i, uint64_t now) const {
  const float low[4] = {0, -40, 0, 0}, high[4] = {45, 50, 100, 100};
  auto *health = availability_[i];
  return values_[i].state(now, low[i], high[i], health == nullptr || (health->has_state() && health->state));
}
const char *AdaptiveClimate::input_fault_(uint64_t now) const {
  if (!api_available_()) return "api_disconnected";
  for (unsigned i = 0; i < 4; ++i) {
    auto state = input_state_(i, now);
    if (state == InputState::INVALID) return "invalid_input";
    if (state == InputState::UNAVAILABLE) return "input_unavailable";
    if (!usable(state)) return "missing_or_stale_input";
  }
  for (auto *flag : flags_)
    if (!flag->has_state()) return "missing_operating_state";
  if (flags_[1]->state) return "window_open";
  if (flags_[2]->state) return "domestic_hot_water";
  Observation o{values_[0].value, values_[1].value, values_[2].value, values_[3].value,
                flags_[0]->state, flags_[1]->state, flags_[2]->state};
  return o.valid() ? nullptr : "invalid_input";
}
void AdaptiveClimate::publish_inputs_(uint64_t now) {
  const char *names[4] = {"room", "outdoor", "valve", "supply"};
  std::string state = api_available_() ? "" : "api_disconnected; ";
  for (unsigned i = 0; i < 4; ++i) {
    if (i) state += "; ";
    state += names[i]; state += "="; state += input_state_name(input_state_(i, now));
  }
  if (state != last_input_status_) {
    if (input_status_) input_status_->publish_state(state);
    last_input_status_ = state;
  }
  // Ages also refresh while learning is suspended; never refresh receipt timestamps.
  if (uint32_t(now - last_age_publish_) >= 10000) {
    last_age_publish_ = uint32_t(now);
    for (unsigned i = 0; i < 4; ++i)
      if (ages_[i]) ages_[i]->publish_state(values_[i].age_seconds(now));
  }
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
  const uint64_t clock = millis_64();
  publish_inputs_(clock);
  if (const char *reason = input_fault_(clock)) invalidate_(reason);
}
void AdaptiveClimate::update() {
  uint64_t now = millis_64();
  publish_inputs_(now);
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
  for (unsigned i = 0; i < 4; ++i)
    ESP_LOGCONFIG(TAG, "Input %u: %s, recent-publication deadline %u ms", i,
                  values_[i].event_driven ? "event_driven" : "strict", (unsigned) values_[i].timeout);
}
}  // namespace adaptive_climate
}  // namespace esphome
