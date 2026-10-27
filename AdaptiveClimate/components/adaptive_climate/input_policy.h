#pragma once
#include <cmath>
#include <cstdint>

namespace esphome::adaptive_climate {

enum class InputState { MISSING, INVALID, UNAVAILABLE, EXPIRED, RECENT, HELD };

// Receipt age measures raw publications, not physical measurement time.
// A 64-bit clock prevents a long-held value becoming recent at millis rollover.
struct InputPolicy {
  bool event_driven{false};
  uint32_t timeout{900000};
  float value{NAN};
  uint64_t timestamp{0};
  bool seen{false};
  void receive(float v, uint64_t now) { value = v; timestamp = now; seen = true; }
  float age_seconds(uint64_t now) const { return seen ? (now - timestamp) / 1000.0f : NAN; }
  InputState state(uint64_t now, float low, float high, bool available = true) const {
    if (!available) return InputState::UNAVAILABLE;
    if (!seen) return InputState::MISSING;
    if (!std::isfinite(value) || value < low || value > high) return InputState::INVALID;
    if (now - timestamp <= timeout) return InputState::RECENT;
    return event_driven ? InputState::HELD : InputState::EXPIRED;
  }
};

inline bool usable(InputState state) { return state == InputState::RECENT || state == InputState::HELD; }
inline const char *input_state_name(InputState state) {
  switch (state) {
    case InputState::MISSING: return "missing";
    case InputState::INVALID: return "invalid_or_unavailable";
    case InputState::UNAVAILABLE: return "health_unavailable";
    case InputState::EXPIRED: return "expired";
    case InputState::RECENT: return "recent_publication";
    default: return "held_unconfirmed";
  }
}
}  // namespace esphome::adaptive_climate
