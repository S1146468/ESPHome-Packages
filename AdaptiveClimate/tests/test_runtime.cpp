#include "../components/adaptive_climate/adaptive_climate.h"
#include <cassert>
#include <iostream>
#include <limits>
#ifdef NDEBUG
#error Runtime tests require assertions enabled
#endif
using namespace esphome;
using namespace esphome::adaptive_climate;
struct Harness : AdaptiveClimate {
  sensor::Sensor inputs[4], writer;
  binary_sensor::BinarySensor flags[3];
  text_sensor::TextSensor cycle, details, forecasts, input, runtime;
  Harness(bool enabled) {
    for(unsigned i=0;i<4;++i){set_input(i,&inputs[i]);set_input_policy(i,true,900000);}
    for(unsigned i=0;i<3;++i){set_flag(i,&flags[i]);flags[i].publish_state(false);}
    set_shadow_model(true);set_cycle_record(&cycle);set_model_record(&details);set_shadow_forecasts(&forecasts);
    if(enabled){set_input_record(&input);set_runtime_record(&runtime);set_pid_tick_source(&inputs[0]);set_writer_tick_source(&writer);}
    setup();
  }
  void receive(){inputs[1].publish_state(10);inputs[2].publish_state(0);inputs[3].publish_state(40);inputs[0].publish_state(20);}
  void extreme(){cycle_sequence_=UINT64_MAX-2;runtime_.original_us=runtime_.shadow_feed_us=runtime_.shadow_forecast_us=runtime_.update_us=UINT32_MAX;}
  const RuntimeMonitor &stats()const{return runtime_;}
  uint64_t room_time()const{return values_[0].timestamp;}
};
int main(){
  GapProbe rollover;rollover.note(UINT32_MAX-100);rollover.note(99);assert(rollover.maximum==200);
  rollover.note(6000,5000);assert(rollover.late==1);
  RuntimeMonitor monitor;monitor.cycle(0);monitor.cycle(300123);assert(monitor.cycle_gap_ms==300123&&monitor.cycle_jitter_ms==123);
  test_clock=0;test_micros_step=11;Harness on(true),off(false);
  on.receive();off.receive();
  for(unsigned i=1;i<=30;++i){
    test_clock=i*300000ULL;on.inputs[0].filtered_heartbeat(20);off.inputs[0].filtered_heartbeat(20);
    on.writer.publish_state(50);off.writer.publish_state(50);on.loop();off.loop();on.update();off.update();
    assert(on.cycle.state==off.cycle.state && on.details.state==off.details.state && on.forecasts.state==off.forecasts.state);
    assert(on.room_time()==0 && off.room_time()==0); // filtered probes cannot refresh a raw receipt
    assert(on.input.state.size()<256&&on.runtime.state.size()<256);
  }
  assert(on.stats().original_us>0&&on.stats().shadow_feed_us>0&&on.stats().update_us>0);
  assert(on.stats().pid_input.maximum==300000 && on.stats().writer_target.maximum==300000);
  assert(off.runtime.state.empty()&&off.input.state.empty());
  assert(on.input.state.find("|4444|000|1")!=std::string::npos || on.input.state.find("|5544|000|1")!=std::string::npos || on.input.state.find("|5555|000|1")!=std::string::npos);
  on.extreme();test_clock=UINT64_MAX-2;on.update();
  assert(on.input.state.size()<256&&on.runtime.state.size()<256);
  assert(on.input.state.find("18446744073709551614")!=std::string::npos);
  assert(on.input.state.find("18446744073709551613")!=std::string::npos);
  std::cout<<"PASS optional runtime/input records, estimator parity, filtered probe isolation, timing, rollover and bounded states\n";
  std::cout<<on.input.state<<'\n'<<on.runtime.state<<'\n';
}
