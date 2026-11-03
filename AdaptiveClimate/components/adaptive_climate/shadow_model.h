#pragma once
#include "thermal_model.h"
#include <cstring>

namespace esphome::adaptive_climate {

// Experimental only. Units: minutes, Celsius, normalized heat proxy.
// beta = [10 * heat loss, heating gain, constant gain], all Celsius/minute.
// Priors are deliberately weak physical assumptions, not room calibration.
class ShadowModel {
 public:
  ShadowModel() { initialize_(); }
  const LearningTrace &trace() const { return trace_; }
  uint32_t samples() const { return samples_; }
  float coefficient(unsigned i) const { return i < 3 ? beta_[i] / (i == 0 ? 10.f : 1.f) : NAN; }
  float rmse() const { return std::sqrt(mse_); }  // rate residual, C/min
  bool learn(float room, float outdoor_mean, float heat_mean, float next_room, float minutes) {
    ++trace_.attempts;
    trace_.reason = "invalid";
    trace_.saturation = 0;
    trace_.change = trace_.predicted = trace_.residual = NAN;
    trace_.heat = heat_mean;
    if (!std::isfinite(room) || !std::isfinite(next_room) || !std::isfinite(outdoor_mean) ||
        !std::isfinite(heat_mean) || !std::isfinite(minutes) || minutes < 1 || minutes > 30 ||
        room < 0 || room > 45 || next_room < 0 || next_room > 45 ||
        outdoor_mean < -40 || outdoor_mean > 50 || heat_mean < 0 || heat_mean > 1.5f) {
      inliers_ = 0; return false;
    }
    if (!healthy_()) return numerical_failure_();
    const float x[3] = {(outdoor_mean - (room + next_room) * .5f) / 10.f, heat_mean, 1.f};
    const float change = next_room - room;
    float predicted = 0;
    for (unsigned i = 0; i < 3; ++i) predicted += beta_[i] * x[i] * minutes;
    const float residual = change - predicted;
    trace_.change = change; trace_.predicted = predicted; trace_.residual = residual;
    // Same hard disturbance limits as the reference. No threshold relaxation.
    if (std::fabs(change) / minutes > .15f || std::fabs(residual) > 1.f)
      return reject_(std::fabs(change) / minutes > .15f ? "rate" : "residual");

    // Forget only in identified operation. Held polls never call learn().
    const float forgetting = identified() ? std::pow(.999f, minutes / 5.f) : 1.f;
    float prior[3][3], px[3] = {}, gain[3], next[3][3] = {}, trial[3];
    // Quantization/publication uncertainty floor, plus Huber downweighting.
    const float weight = std::min(1.f, .2f / std::max(.2f, std::fabs(residual)));
    const float noise = std::pow(.1f / minutes / weight, 2.f);
    float denom = noise;
    for (unsigned i = 0; i < 3; ++i) {
      for (unsigned j = 0; j < 3; ++j) { prior[i][j] = p_[i][j] / forgetting; px[i] += prior[i][j] * x[j]; }
      denom += x[i] * px[i];
    }
    if (!std::isfinite(denom) || denom <= 0) return numerical_failure_();
    const float low[3] = {0, 0, -.03f}, high[3] = {.2f, .3f, .03f};
    trace_.saturation = 0;
    for (unsigned i = 0; i < 3; ++i) {
      gain[i] = px[i] / denom;
      trial[i] = beta_[i] + gain[i] * residual / minutes;
      if (!std::isfinite(trial[i])) return numerical_failure_();
      if (trial[i] <= low[i] || trial[i] >= high[i]) trace_.saturation |= 1U << i;
    }
    // Reject the whole constrained step: clipping theta while contracting the
    // unconstrained covariance manufactures confidence in the wrong solution.
    if (trace_.saturation) return reject_("constraint");
    float a[3][3], ap[3][3] = {};
    for (unsigned i = 0; i < 3; ++i)
      for (unsigned j = 0; j < 3; ++j) a[i][j] = (i == j ? 1.f : 0.f) - gain[i] * x[j];
    for (unsigned i = 0; i < 3; ++i)
      for (unsigned j = 0; j < 3; ++j)
        for (unsigned k = 0; k < 3; ++k) ap[i][j] += a[i][k] * prior[k][j];
    for (unsigned i = 0; i < 3; ++i)
      for (unsigned j = 0; j < 3; ++j) {
        next[i][j] = noise * gain[i] * gain[j];
        for (unsigned k = 0; k < 3; ++k) next[i][j] += ap[i][k] * a[j][k];
      }
    for (unsigned i = 0; i < 3; ++i) {
      beta_[i] = trial[i];
      for (unsigned j = 0; j < 3; ++j) {
        p_[i][j] = (next[i][j] + next[j][i]) * .5f;
        // Bounded exponentially weighted excitation information.
        info_[i][j] = .995f * info_[i][j] + x[i] * x[j];
      }
    }
    if (!healthy_()) return numerical_failure_();
    const float rate_residual = residual / minutes;
    mse_ = samples_ ? .95f * mse_ + .05f * rate_residual * rate_residual : rate_residual * rate_residual;
    if (samples_ < 1000000000U) ++samples_;
    trace_.reason = "accepted"; trace_.consecutive = 0;
    if (inliers_ < 3) ++inliers_;
    return true;
  }
  bool identified() const {
    // A heat range alone cannot distinguish correlated loss and offset.
    const float product = info_[0][0] * info_[1][1] * info_[2][2];
    const float det = info_[0][0] * (info_[1][1] * info_[2][2] - info_[1][2] * info_[2][1]) -
        info_[0][1] * (info_[1][0] * info_[2][2] - info_[1][2] * info_[2][0]) +
        info_[0][2] * (info_[1][0] * info_[2][1] - info_[1][1] * info_[2][0]);
    return samples_ >= 24 && product > 1.e-6f && det / product > 1.e-4f;
  }
  const char *forecast_status() const {
    if (trace_.saturation) return "constraint";
    if (inliers_ < 3) return "recovering";
    if (!identified()) return "unidentified";
    return "conditional_unvalidated";
  }
  float step(float room, float outdoor, float heat) const {
    return room + coefficient(0) * (outdoor - room) + beta_[1] * heat + beta_[2];
  }
  float variance(const float *sensitivity, unsigned horizon) const {
    float variance = .01f + (std::isfinite(mse_) ? mse_ : .0004f) * horizon * 5.f;
    for (unsigned i = 0; i < 3; ++i)
      for (unsigned j = 0; j < 3; ++j) variance += sensitivity[i] * p_[i][j] * sensitivity[j];
    return variance;
  }
 private:
  friend struct ShadowModelTestAccess;
  void initialize_() {
    beta_[0] = .02f; beta_[1] = .05f; beta_[2] = 0;
    const float prior[3] = {.0004f, .0025f, .0001f};
    for (unsigned i = 0; i < 3; ++i)
      for (unsigned j = 0; j < 3; ++j) { p_[i][j] = i == j ? prior[i] : 0; info_[i][j] = 0; }
    samples_ = 0; inliers_ = 0; mse_ = NAN;
  }
  bool healthy_() const {
    // Cholesky checks all pivots, symmetry and finiteness, not just a positive
    // RLS denominator. Small fixed matrices keep this deterministic on ESP32.
    float l[3][3] = {};
    for (unsigned i = 0; i < 3; ++i) {
      if (!std::isfinite(beta_[i])) return false;
      for (unsigned j = 0; j <= i; ++j) {
        if (!std::isfinite(p_[i][j]) || std::fabs(p_[i][j] - p_[j][i]) > 1.e-6f) return false;
        float v = p_[i][j];
        for (unsigned k = 0; k < j; ++k) v -= l[i][k] * l[j][k];
        if (i == j) { if (!(v > 0) || v > .1f) return false; l[i][j] = std::sqrt(v); }
        else l[i][j] = v / l[j][j];
      }
    }
    return true;
  }
  bool numerical_failure_() {
    ++trace_.resets; trace_.reason = trace_.reset_reason = "numerical";
    trace_.consecutive = 0; trace_.saturation = 0; initialize_(); return false;
  }
  bool reject_(const char *reason) {
    trace_.reason = reason; inliers_ = 0;
    if (trace_.consecutive < 255) ++trace_.consecutive;
    // One bounded uncertainty restoration per rejection run. Preserve theta
    // and sample history; persistent mismatch stays unavailable, not trusted.
    if (trace_.consecutive == 6) {
      const float inflation[3] = {.0004f, .0025f, .0001f};
      for (unsigned i = 0; i < 3; ++i) p_[i][i] = std::max(p_[i][i], inflation[i]);
    }
    return false;
  }
  float beta_[3], p_[3][3], info_[3][3], mse_;
  uint32_t samples_{0};
  uint8_t inliers_{0};
  LearningTrace trace_;
};

// Feed every observed input/flag transition. Only actual raw room publications
// can close a training pair. A publication is not proof of a physical reading.
class ShadowObserver {
 public:
  ShadowModel model;
  void invalidate(uint64_t now) {
    advance_(now); baseline_ = valid_ = false; settled_at_ = now + 1800000ULL;
    status_ = "input_gap";
  }
  void receive(const Observation &o, uint64_t now, bool room_publication) {
    advance_(now);
    if (!o.valid()) { invalidate(now); return; }
    if (!valid_) {
      heat_ = ThermalModel::heat_proxy(o.room, o.supply, o.valve, o.heating && !o.dhw);
      settled_at_ = now + 1800000ULL;
    }
    current_ = o; time_ = now; valid_ = true;
    if (o.window_open || o.dhw) { baseline_ = false; status_ = o.dhw ? "dhw" : "window"; return; }
    if (!room_publication) return;
    last_publication_ = now; seen_publication_ = true;
    if (baseline_) {
      const float minutes = (now - pair_time_) / 60000.f;
      if (minutes < 1) return;  // Accumulate, do not generate sub-minute pairs.
      if (minutes <= 30 && pair_time_ >= settled_at_) {
        const bool accepted = model.learn(pair_room_, outdoor_integral_ / minutes,
                                         heat_integral_ / minutes, o.room, minutes);
        status_ = accepted ? "publication_pair" : model.trace().reason;
      } else status_ = minutes > 30 ? "publication_gap" : "radiator_settling";
    } else status_ = "baseline";
    pair_room_ = o.room; pair_time_ = now; baseline_ = true;
    heat_integral_ = outdoor_integral_ = 0;
  }
  const char *status() const { return status_; }
  float heat_state() const { return heat_; }
  const char *forecast_status(uint64_t now) const {
    if (!valid_ || current_.window_open || current_.dhw) return "suspended";
    if (!seen_publication_ || now - last_publication_ > 900000ULL) return "held_origin";
    if (now < settled_at_) return "radiator_settling";
    return model.forecast_status();
  }
  float forecast(uint64_t now, unsigned minutes, float *half_width = nullptr) const {
    if (half_width) *half_width = NAN;
    if (minutes > 60 || std::strcmp(forecast_status(now), "conditional_unvalidated") != 0) return NAN;
    float room = current_.room, heat = heat_, sensitivity[3] = {};
    const float drive = drive_();
    for (unsigned i = 0; i < minutes; ++i) {
      const float decay = std::exp(-1.f / 10.f);
      const float mean_heat = drive + (heat - drive) * 10.f * (1.f - decay);
      heat = drive + (heat - drive) * decay;
      const float x[3] = {(current_.outdoor - room) / 10.f, mean_heat, 1.f};
      for (unsigned j = 0; j < 3; ++j)
        sensitivity[j] = (1.f - model.coefficient(0)) * sensitivity[j] + x[j];
      room = model.step(room, current_.outdoor, mean_heat);
    }
    const float variance = model.variance(sensitivity, minutes);
    const float width = variance >= 0 ? 1.96f * std::sqrt(variance) : NAN;
    if (half_width) *half_width = width;
    // Provisional visibility gate, not calibrated coverage or trajectory clipping.
    if (!std::isfinite(room) || !std::isfinite(width) || width > 1.f || room < -10 || room > 50) return NAN;
    return room;
  }
 private:
  float drive_() const {
    return ThermalModel::heat_proxy(current_.room, current_.supply, current_.valve,
                                   current_.heating && !current_.dhw);
  }
  void advance_(uint64_t now) {
    if (!valid_ || now <= time_) return;
    const float minutes = (now - time_) / 60000.f;
    const float drive = drive_(), decay = std::exp(-minutes / 10.f);
    if (baseline_) {
      heat_integral_ += drive * minutes + (heat_ - drive) * 10.f * (1.f - decay);
      outdoor_integral_ += current_.outdoor * minutes;
    }
    heat_ = drive + (heat_ - drive) * decay; time_ = now;
    // Bound accumulation during indefinitely held publications.
    if (baseline_ && now - pair_time_ > 1800000ULL) {
      baseline_ = false; heat_integral_ = outdoor_integral_ = 0; status_ = "publication_gap";
    }
  }
  Observation current_{};
  uint64_t time_{0}, pair_time_{0}, last_publication_{0}, settled_at_{0};
  float heat_{0}, heat_integral_{0}, outdoor_integral_{0}, pair_room_{0};
  bool valid_{false}, baseline_{false}, seen_publication_{false};
  const char *status_{"baseline"};
};
}  // namespace esphome::adaptive_climate
