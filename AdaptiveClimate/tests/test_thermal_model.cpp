#include "../components/adaptive_climate/thermal_model.h"
#include <cassert>
#include <chrono>
#include <iostream>
#include <limits>
using namespace esphome::adaptive_climate;

int main() {
  InputValue input;
  assert(!input.fresh(0, 900000));
  input.receive(20, UINT32_MAX - 100);
  assert(input.fresh(50, 200));
  assert(!input.fresh(500, 200));
  input.receive(NAN, 500);
  assert(!input.fresh(500, 200));

  Observer observer;
  Observation o{20, 10, 50, 50, true, false, false};
  observer.observe(o, 0);
  observer.observe(o, 300000);
  assert(observer.model.samples() == 1);
  o.window_open = true;
  observer.observe(o, 600000);
  o.window_open = false;
  observer.observe(o, 900000);
  assert(observer.model.samples() == 1);  // Cannot learn across open window.
  o.dhw = true;
  observer.observe(o, 1200000);
  o.dhw = false;
  observer.observe(o, 1500000);
  assert(observer.model.samples() == 1);
  observer.observe(o, 2500000);
  assert(observer.model.samples() == 1);  // Long gap starts a new baseline.
  o.room = NAN;
  observer.observe(o, 2800000);
  assert(!observer.ready());
  o.room = 20; o.valve = 101;
  assert(!o.valid());
  o.valve = 0;
  assert(ThermalModel::heat_proxy(20, 50, 0, true) == 0);
  assert(ThermalModel::heat_proxy(20, 50, 100, false) == 0);

  ThermalModel model;
  assert(!model.learn(20, 10, .5f, NAN, 5));
  assert(!model.learn(20, 10, .5f, 30, 5));
  assert(!model.learn(20, 10, .5f, 20, 0));
  // Independent known system with deterministic excitation. No claim of room calibration.
  float room = 20;
  for (int k = 0; k < 6000; ++k) {
    float outdoor = 10 + 5 * std::sin(k * .017f);
    float heat = (k / 17) % 2 ? .8f : .1f;
    float next = room + 5 * (.002f * (outdoor - room) + .08f * heat + .003f);
    assert(model.learn(room, outdoor, heat, next, 5));
    room = next;
  }
  assert(std::fabs(model.coefficient(0) - .002f) < .0002f);
  assert(std::fabs(model.coefficient(1) - .08f) < .002f);
  assert(std::fabs(model.coefficient(2) - .003f) < .002f);
  assert(model.rmse() < .01f);
  assert(std::isfinite(model.forecast(20, 10, .5f, 60)));
  assert(std::isnan(model.forecast(20, 10, .5f, 61)));
  assert(std::isnan(model.forecast(NAN, 10, .5f, 15)));
  for (int i = 0; i < 6; ++i) assert(!model.learn(20, 10, .5f, 30, 5));
  assert(model.samples() == 0);  // Consecutive large residuals force relearning.

  // Separate rooms have independent collection, coefficients and fault state.
  Observer room_a, room_b;
  Observation valid_room{20, 10, 50, 50, true, false, false};
  for (unsigned k = 0; k <= 30; ++k) room_a.observe(valid_room, k * 300000);
  assert(room_a.ready());
  assert(room_a.model.samples() == 30);
  assert(room_b.model.samples() == 0 && !room_b.ready());
  const float prediction = room_a.forecast(valid_room, 30);
  assert(std::isfinite(prediction));
  valid_room.window_open = true;
  room_b.observe(valid_room, 9000000);
  assert(room_a.ready() && room_a.model.samples() == 30);
  valid_room.window_open = false;
  assert(room_a.forecast(valid_room, 30) == prediction);
  room_a.suspend();
  assert(std::isnan(room_a.forecast(valid_room, 15)));

  auto start = std::chrono::steady_clock::now();
  volatile float result = 0;
  for (int k = 0; k < 100000; ++k) {
    model.learn(20, 10, .5f, 20.01f, 5);
    result = model.forecast(20, 10, .5f, 60);
  }
  auto us = std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now() - start).count();
  std::cout << "PASS: guards, rollover, suspension, numerical rejection, convergence, forecast bounds, change reset\n";
  std::cout << "Desktop sizeof(ThermalModel)=" << sizeof(ThermalModel) << " sizeof(Observer)=" << sizeof(Observer)
            << " mean learn+60min forecast us=" << us / 100000.0 << " (not ESP32 timing)\n";
  return result > -100 ? 0 : 1;
}
