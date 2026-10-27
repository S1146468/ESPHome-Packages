#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>

namespace esphome {
namespace adaptive_climate {

// Three-parameter empirical model. Minutes and degrees Celsius throughout.
// No actuator interfaces or dynamically sized storage.
class ThermalModel {
 public:
  ThermalModel() { reset(); }
  void reset() {
    theta_[0] = 0.002f; theta_[1] = 0.05f; theta_[2] = 0.0f;
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j) p_[i][j] = i == j ? 10.0f : 0.0f;
    samples_ = 0; mse_ = NAN; heat_min_ = 1.0f; heat_max_ = 0.0f;
    failures_ = 0;
  }
  static float heat_proxy(float room, float supply, float valve, bool heating) {
    return heating ? std::clamp(valve / 100.0f, 0.0f, 1.0f) *
                         std::clamp((supply - room) / 50.0f, 0.0f, 1.5f) : 0.0f;
  }
  bool learn(float room, float outdoor, float heat, float next_room, float minutes) {
    if (!std::isfinite(room) || !std::isfinite(outdoor) || !std::isfinite(heat) ||
        !std::isfinite(next_room) || !std::isfinite(minutes) || minutes < 1.0f ||
        minutes > 10.0f || heat < 0.0f || heat > 1.5f) return false;
    const float change = next_room - room;
    const float x[3] = {minutes * (outdoor - room), minutes * heat, minutes};
    float predicted = 0;
    for (int i = 0; i < 3; ++i) predicted += theta_[i] * x[i];
    const float residual = change - predicted;
    // Reject disturbances rather than teaching the model an implausible heat gain.
    if (std::fabs(change) / minutes > 0.15f || std::fabs(residual) > 1.0f) {
      if (++failures_ >= 6) reset();
      return false;
    }
    failures_ = 0;
    const float forgetting = 0.999f;
    float prior[3][3], px[3] = {}, gain[3], denom = 1.0f;
    for (int i = 0; i < 3; ++i) {
      for (int j = 0; j < 3; ++j) { prior[i][j] = p_[i][j] / forgetting; px[i] += prior[i][j] * x[j]; }
      denom += x[i] * px[i];
    }
    if (!std::isfinite(denom) || denom <= 0) { reset(); return false; }
    for (int i = 0; i < 3; ++i) gain[i] = px[i] / denom;
    // Joseph covariance update: (I-Kx) P (I-Kx)' + KK'.
    float a[3][3], ap[3][3] = {}, next[3][3] = {};
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j) a[i][j] = (i == j ? 1.0f : 0.0f) - gain[i] * x[j];
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j)
        for (int k = 0; k < 3; ++k) ap[i][j] += a[i][k] * prior[k][j];
    for (int i = 0; i < 3; ++i)
      for (int j = 0; j < 3; ++j) {
        next[i][j] = gain[i] * gain[j];
        for (int k = 0; k < 3; ++k) next[i][j] += ap[i][k] * a[j][k];
        if (!std::isfinite(next[i][j]) || std::fabs(next[i][j]) > 10000) { reset(); return false; }
      }
    const float lower[3] = {0.0f, 0.0f, -0.03f};
    const float upper[3] = {0.02f, 0.30f, 0.03f};
    for (int i = 0; i < 3; ++i) {
      theta_[i] = std::clamp(theta_[i] + gain[i] * residual, lower[i], upper[i]);
      for (int j = 0; j < 3; ++j) p_[i][j] = (next[i][j] + next[j][i]) * 0.5f;
    }
    mse_ = samples_ ? 0.95f * mse_ + 0.05f * residual * residual : residual * residual;
    if (samples_ < 1000000000U) ++samples_;
    heat_min_ = std::min(heat_min_, heat); heat_max_ = std::max(heat_max_, heat);
    return true;
  }
  float forecast(float room, float outdoor, float heat, unsigned minutes) const {
    if (!std::isfinite(room) || !std::isfinite(outdoor) || !std::isfinite(heat) || minutes > 60) return NAN;
    // Explicit constant-input scenario, not a forecast of future boiler operation.
    for (unsigned i = 0; i < minutes; ++i) {
      room += theta_[0] * (outdoor - room) + theta_[1] * heat + theta_[2];
      if (!std::isfinite(room) || room < -10 || room > 50) return NAN;
    }
    return room;
  }
  uint32_t samples() const { return samples_; }
  float rmse() const { return std::sqrt(mse_); }
  float heat_span() const { return std::max(0.0f, heat_max_ - heat_min_); }
  float coefficient(unsigned i) const { return i < 3 ? theta_[i] : NAN; }

 private:
  float theta_[3], p_[3][3], mse_, heat_min_, heat_max_;
  uint32_t samples_;
  uint8_t failures_;
};

struct Observation {
  float room, outdoor, valve, supply;
  bool heating, window_open, dhw;
  bool valid() const {
    return std::isfinite(room) && room >= 0 && room <= 45 &&
           std::isfinite(outdoor) && outdoor >= -40 && outdoor <= 50 &&
           std::isfinite(valve) && valve >= 0 && valve <= 100 &&
           std::isfinite(supply) && supply >= 0 && supply <= 100;
  }
};

// Callback timestamps use unsigned subtraction, including across millis rollover.
struct InputValue {
  float value{NAN};
  uint32_t timestamp{0};
  bool seen{false};
  void receive(float v, uint32_t now) { value = v; timestamp = now; seen = true; }
  bool fresh(uint32_t now, uint32_t timeout) const {
    return seen && std::isfinite(value) && uint32_t(now - timestamp) <= timeout;
  }
};

class Observer {
 public:
  ThermalModel model;
  void suspend() { previous_valid_ = false; ready_ = false; heat_state_ = 0; }
  const char *observe(const Observation &o, uint32_t now) {
    ready_ = false;
    if (!o.valid()) { suspend(); return "invalid_input"; }
    if (o.window_open || o.dhw) { suspend(); return o.window_open ? "window_open" : "domestic_hot_water"; }
    const float heat = ThermalModel::heat_proxy(o.room, o.supply, o.valve, o.heating);
    if (!previous_valid_) { heat_state_ = heat; baseline_(o, heat, now); return "collecting_data"; }
    const uint32_t elapsed = now - previous_time_;
    if (elapsed < 240000) return "collecting_data";
    if (elapsed > 450000) { heat_state_ = heat; baseline_(o, heat, now); return "timing_gap"; }
    const float minutes = elapsed / 60000.0f;
    const float decay = std::exp(-minutes / 10.0f);
    // Fixed, provisional ten-minute radiator lag. Previous input is held over
    // the interval; faster valve/boiler changes are not reconstructed here.
    const float mean_heat = previous_heat_ + (heat_state_ - previous_heat_) * 10.0f * (1.0f - decay) / minutes;
    heat_state_ = previous_heat_ + (heat_state_ - previous_heat_) * decay;
    bool accepted = model.learn(previous_room_, previous_outdoor_, mean_heat, o.room, minutes);
    baseline_(o, heat, now);
    if (!accepted) return "disturbance_rejected";
    ready_ = model.samples() >= 24;
    return !ready_ ? "collecting_data" : (model.heat_span() < 0.1f ? "low_excitation" : "learning_unvalidated");
  }
  bool ready() const { return ready_; }
  float forecast(const Observation &o, unsigned minutes) const {
    if (!ready_ || !o.valid() || minutes > 60 || o.window_open || o.dhw) return NAN;
    float room = o.room, heat = heat_state_;
    const float drive = ThermalModel::heat_proxy(o.room, o.supply, o.valve, o.heating);
    for (unsigned i = 0; i < minutes; ++i) {
      heat = drive + (heat - drive) * 0.904837418f;
      room = model.forecast(room, o.outdoor, heat, 1);
      if (!std::isfinite(room)) return NAN;
    }
    return room;
  }
 private:
  void baseline_(const Observation &o, float heat, uint32_t now) {
    previous_room_ = o.room; previous_outdoor_ = o.outdoor; previous_heat_ = heat;
    previous_time_ = now; previous_valid_ = true;
  }
  float previous_room_{0}, previous_outdoor_{0}, previous_heat_{0};
  float heat_state_{0};
  uint32_t previous_time_{0};
  bool previous_valid_{false}, ready_{false};
};

}  // namespace adaptive_climate
}  // namespace esphome
