// Offline only. Compile against the unchanged production observer implementation.
#include "../components/adaptive_climate/thermal_model.h"
#include <iostream>
#include <sstream>
#include <string>
#include <iomanip>
#include <array>
using namespace esphome::adaptive_climate;

int main() {
  std::array<Observer, 2> observers;
  std::array<uint64_t, 2> last{};
  std::array<bool, 2> seen{};
  std::string line;
  std::cout << "room,elapsed_ms,status,samples,loss,gain,offset,forecast15,forecast30,forecast60\n";
  std::cout << std::setprecision(9);
  unsigned line_number = 0;
  while (std::getline(std::cin, line)) {
    ++line_number;
    if (line.empty() || line[0] == '#') continue;
    std::istringstream input(line);
    std::string room, extra;
    uint64_t time;
    Observation o{};
    int heating, window, dhw, valid;
    if (!(input >> room >> time >> o.room >> o.outdoor >> o.valve >> o.supply >>
          heating >> window >> dhw >> valid) || (input >> extra) ||
        (room != "stijn" && room != "nick") ||
        (heating != 0 && heating != 1) || (window != 0 && window != 1) ||
        (dhw != 0 && dhw != 1) || (valid != 0 && valid != 1)) {
      std::cerr << "Invalid replay row " << line_number << '\n'; return 2;
    }
    unsigned index = room == "stijn" ? 0 : 1;
    if (seen[index] && (time <= last[index] || time-last[index] > UINT32_MAX)) {
      std::cerr << "Nonmonotonic/ambiguous clock\n"; return 2;
    }
    last[index] = time; seen[index] = true;
    o.heating = heating; o.window_open = window; o.dhw = dhw;
    auto &observer = observers[index];
    const char *status;
    if (!valid) { observer.suspend(); status = "masked_input"; }
    else status = observer.observe(o, static_cast<uint32_t>(time));
    std::cout << room << ',' << time << ',' << status << ',' << observer.model.samples();
    for (unsigned i = 0; i < 3; ++i) std::cout << ',' << observer.model.coefficient(i);
    for (unsigned horizon : {15, 30, 60}) std::cout << ',' << observer.forecast(o, horizon);
    std::cout << '\n';
  }
}
