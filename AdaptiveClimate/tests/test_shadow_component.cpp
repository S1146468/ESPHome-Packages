#include "../components/adaptive_climate/adaptive_climate.h"
#include <cassert>
#include <iostream>
#ifdef NDEBUG
#error Regression tests require assertions enabled
#endif
using namespace esphome;
using namespace esphome::adaptive_climate;
struct Harness : AdaptiveClimate {
  sensor::Sensor inputs[4];binary_sensor::BinarySensor flags[3];
  text_sensor::TextSensor details,candidate,forecasts,cycle;
  Harness(bool shadow) {
    for(unsigned i=0;i<4;++i){set_input(i,&inputs[i]);set_input_policy(i,true,900000);}
    for(unsigned i=0;i<3;++i){set_flag(i,&flags[i]);flags[i].publish_state(false);}
    set_shadow_model(shadow);set_model_record(&details);set_shadow_record(&candidate);
    set_shadow_forecasts(&forecasts);set_cycle_record(&cycle);setup();
  }
  void receive(float room=20) {
    inputs[1].publish_state(10);inputs[2].publish_state(100);inputs[3].publish_state(60);inputs[0].publish_state(room);
  }
  unsigned n() const{return shadow_.model.samples();}
  float heat() const{return shadow_.heat_state();}
  void max_sequence(){cycle_sequence_=UINT64_MAX-2;}
};
int main(){
  test_clock=0;Harness on(true),off(false);
  on.receive();off.receive();on.flags[0].publish_state(true);off.flags[0].publish_state(true);
  for(unsigned i=0;i<30;++i){
    test_clock=i*300000ULL;on.loop();off.loop();on.update();off.update();
    assert(on.cycle.state==off.cycle.state); // candidate and telemetry cannot alter reference
    assert(on.details.state==off.details.state);
    assert(on.details.state.size()<256 && on.candidate.state.size()<256 && on.forecasts.state.size()<256);
  }
  assert(on.n()==0 && off.candidate.state.empty());
  // Same-value raw publication is eligible; cached heartbeat is not.
  on.inputs[0].publish_state(20);test_clock+=300000;on.inputs[0].publish_state(20);
  assert(on.n()==1);
  test_clock+=300000;on.inputs[0].filtered_heartbeat(20);on.loop();assert(on.n()==1);
  const float hot=on.heat();
  on.flags[0].publish_state(false);test_clock+=60000;on.loop();
  assert(on.heat()>0 && on.heat()<hot); // captures CH transition between polls
  const float before_dhw=on.heat();
  on.flags[2].publish_state(true);test_clock+=60000;on.loop();on.flags[2].publish_state(false);
  assert(on.heat()>0 && on.heat()<before_dhw);
  on.update();assert(on.forecasts.state.find("null")!=std::string::npos);
  on.max_sequence();test_clock=(1ULL<<32)+123;on.inputs[0].publish_state(NAN);on.update();
  assert(on.details.state.size()<256 && on.candidate.state.size()<256 && on.forecasts.state.size()<256);
  assert(on.details.state.find("18446744073709551614")!=std::string::npos);
  assert(on.forecasts.state.find("suspended")!=std::string::npos);
  std::cout<<"PASS optional telemetry, reference parity, raw/filtered callbacks, CH/DHW transitions, bounded 64bit records\n";
  std::cout<<on.details.state<<'\n'<<on.candidate.state<<'\n'<<on.forecasts.state<<'\n';
}
