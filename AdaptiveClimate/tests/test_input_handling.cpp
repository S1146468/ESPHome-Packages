// Exercise the real component's setup/callback/loop/update code with a controlled clock.
#include "../components/adaptive_climate/adaptive_climate.h"
#include "esphome/components/api/api_server.h"
#include <cassert>
#include <iostream>
using namespace esphome;
using namespace esphome::adaptive_climate;

struct Harness : AdaptiveClimate {
  sensor::Sensor input[4], age[4], diagnostic[6];
  binary_sensor::BinarySensor flag[3], health;
  text_sensor::TextSensor status, freshness;
  Harness(bool event = true) {
    for (unsigned i = 0; i < 4; ++i) {
      set_input(i, &input[i]); set_input_age(i, &age[i]);
      set_input_policy(i, event, 900000);
    }
    for (unsigned i = 0; i < 3; ++i) { set_flag(i, &flag[i]); flag[i].publish_state(false); }
    for (unsigned i = 0; i < 6; ++i) set_diagnostic(i, &diagnostic[i]);
    set_status(&status); set_input_status(&freshness); setup();
  }
  void receive() {
    input[0].publish_state(21.6f); input[1].publish_state(21.6f);
    input[2].publish_state(0); input[3].publish_state(40);
  }
  uint32_t samples() const { return observer_.model.samples(); }
  float value(unsigned i) const { return values_[i].value; }
  uint64_t stamp(unsigned i) const { return values_[i].timestamp; }
};

int main() {
  test_clock = 0;
  Harness stijn, nick;
  assert(stijn.interval == 300000);
  stijn.update(); assert(stijn.samples() == 0);
  assert(stijn.status.state == "missing_or_stale_input");
  stijn.receive(); nick.receive(); stijn.update(); nick.update();
  for (int i = 1; i <= 12; ++i) {
    test_clock = i * 300000ULL;
    stijn.input[0].filtered_heartbeat(21.6f);
    stijn.loop(); stijn.update(); nick.loop(); nick.update();
  }
  assert(stijn.samples() == 12 && nick.samples() == 12);
  assert(stijn.stamp(0) == 0 && stijn.age[0].state == 3600);
  assert(stijn.freshness.state.find("room=held_unconfirmed") != std::string::npos);
  stijn.input[0].publish_state(21.7f);
  assert(stijn.value(0) == 21.7f && stijn.stamp(0) == test_clock);
  assert(nick.value(0) == 21.6f && nick.stamp(0) == 0);
  assert(stijn.freshness.state.find("room=recent_publication") != std::string::npos);
  stijn.input[0].publish_state(NAN); // HA unknown/unavailable becomes NaN.
  assert(stijn.status.state == "invalid_input");
  test_clock += 300000; stijn.update(); nick.update();
  assert(stijn.samples() == 12 && nick.samples() == 13);
  stijn.input[0].publish_state(21.6f); stijn.update();
  test_clock += 300000; stijn.update(); assert(stijn.samples() == 13);
  for (float bad : {INFINITY, -1.0f, 46.0f}) {
    stijn.input[0].publish_state(bad); assert(stijn.status.state == "invalid_input");
    stijn.update(); assert(stijn.samples() == 13);
  }
  stijn.receive(); stijn.set_availability(0, &stijn.health);
  stijn.update(); assert(stijn.status.state == "input_unavailable");
  stijn.health.publish_state(false); stijn.update(); assert(stijn.samples() == 13);
  stijn.health.publish_state(true); stijn.update();
  test_clock += 300000; stijn.update(); assert(stijn.samples() == 14);
  stijn.set_require_api_connection(true); api::server.subscribed = false;
  test_clock += 1000; stijn.loop(); assert(stijn.status.state == "api_disconnected");
  const auto stamp = stijn.stamp(0);
  stijn.update(); assert(stijn.samples() == 14);
  api::server.subscribed = true; stijn.update(); assert(stijn.stamp(0) == stamp);
  stijn.flag[1].publish_state(true); stijn.update(); assert(stijn.status.state == "window_open");
  stijn.flag[1].publish_state(false); stijn.flag[2].publish_state(true);
  stijn.update(); assert(stijn.status.state == "domestic_hot_water");
  assert(stijn.samples() == 14);

  test_clock = 0;
  Harness periodic(false); periodic.receive(); periodic.update();
  test_clock = 900000; periodic.loop();
  assert(periodic.freshness.state.find("expired") == std::string::npos);
  test_clock = 900001; periodic.update();
  assert(periodic.status.state == "missing_or_stale_input");
  assert(periodic.freshness.state.find("room=expired") != std::string::npos);
  periodic.input[0].filtered_heartbeat(21.6f); periodic.update();
  assert(periodic.stamp(0) == 0 && periodic.samples() == 0);
  periodic.set_input_policy(0, true, 60000); periodic.update();
  assert(periodic.freshness.state.find("room=held_unconfirmed") != std::string::npos);
  assert(periodic.freshness.state.find("outdoor=expired") != std::string::npos);
  test_clock = (1ULL << 32) + 1; periodic.update();
  assert(periodic.freshness.state.find("outdoor=expired") != std::string::npos);
  assert(periodic.age[0].state > 4000000);

  Harness scaled; scaled.set_valve_command_scale(100);
  scaled.input[2].publish_state(0.6f); assert(std::fabs(scaled.value(2) - 60) < 0.001f);
  // A held room alongside genuinely periodic other sources continues training.
  test_clock = 0;
  Harness mixed(false); mixed.set_input_policy(0, true, 900000);
  mixed.receive(); mixed.update();
  for (unsigned i = 1; i <= 12; ++i) {
    test_clock = i * 300000ULL;
    mixed.input[1].publish_state(21.6f);
    mixed.input[2].publish_state(0);
    mixed.input[3].publish_state(40);
    mixed.loop(); mixed.update();
  }
  assert(mixed.samples() == 12 && mixed.stamp(0) == 0);
  assert(mixed.freshness.state.find("room=held_unconfirmed; outdoor=recent_publication") == 0);
  // Cached frontend state without any raw publication must not start training.
  Harness cached;
  for (auto &s : cached.input) s.filtered_heartbeat(21.6f);
  cached.update(); assert(cached.samples() == 0 && cached.status.state == "missing_or_stale_input");
  std::cout << "PASS: stable hour, raw changes, invalid/unavailable, startup, strict expiry, independent rooms, health, API, protections, heartbeat, rollover, raw scale\n";
}
