#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>

namespace esphome::adaptive_climate {
// Read-only counters, independent of both estimators. Millisecond gap probes
// describe observed callbacks, not PID execution or OpenTherm telegram deadlines.
struct GapProbe {
  uint32_t previous{0}, maximum{0}, late{0};
  bool seen{false};
  void note(uint32_t now, uint32_t expected = 0) {
    if (seen) {
      const uint32_t gap = now - previous;
      maximum = std::max(maximum, gap);
      if (expected && gap > expected + 250 && late < UINT32_MAX) ++late;
    }
    previous = now; seen = true;
  }
};
struct RuntimeMonitor {
  uint32_t original_us{0}, shadow_feed_us{0}, shadow_forecast_us{0}, update_us{0};
  uint32_t cycle_gap_ms{0}, cycle_jitter_ms{0};
  uint64_t previous_cycle_ms{0};
  bool cycle_seen{false};
  GapProbe loop, pid_input, writer_target;
  void cycle(uint64_t now) {
    if (cycle_seen) {
      const auto gap = std::min<uint64_t>(now - previous_cycle_ms, UINT32_MAX);
      cycle_gap_ms = uint32_t(gap);
      const uint32_t error = cycle_gap_ms > 300000 ? cycle_gap_ms - 300000 : 300000 - cycle_gap_ms;
      cycle_jitter_ms = std::max(cycle_jitter_ms, error);
    }
    previous_cycle_ms = now; cycle_seen = true;
  }
};
}  // namespace esphome::adaptive_climate
