#include "../components/adaptive_climate/adaptive_climate.h"
#include <cassert>
#include <iostream>
#include <limits>
using namespace esphome;
using namespace esphome::adaptive_climate;
struct Harness : AdaptiveClimate {
  sensor::Sensor inputs[4], forecasts[3];
  binary_sensor::BinarySensor flags[3];
  text_sensor::TextSensor record;
  Harness(bool enabled) {
    for (unsigned i=0;i<4;++i) { set_input(i,&inputs[i]);set_input_policy(i,true,900000); }
    for (unsigned i=0;i<3;++i) { set_flag(i,&flags[i]);flags[i].publish_state(false);set_diagnostic(i,&forecasts[i]); }
    if(enabled)set_cycle_record(&record);
    setup();
  }
  void receive() { inputs[0].publish_state(20);inputs[1].publish_state(10);inputs[2].publish_state(0);inputs[3].publish_state(40); }
  unsigned samples() const {return observer_.model.samples();}
  void large_sequence(){cycle_sequence_=UINT64_MAX-2;}
};
int main(){
  test_clock=0;Harness enabled(true),disabled(false),other(true);
  enabled.update();assert(enabled.record.state.find("\"o\":\"suspended\"")!=std::string::npos);
  assert(enabled.record.state.find("\"f\":[null,null,null]")!=std::string::npos);
  enabled.receive();disabled.receive();other.receive();enabled.update();disabled.update();other.update();
  assert(enabled.record.state.find("\"o\":\"baseline\"")!=std::string::npos);
  for(unsigned i=1;i<=30;++i){
    test_clock=i*300000ULL;enabled.update();disabled.update();
    assert(enabled.samples()==disabled.samples());
    for(unsigned j=0;j<3;++j) assert((std::isnan(enabled.forecasts[j].state)&&std::isnan(disabled.forecasts[j].state)) || enabled.forecasts[j].state==disabled.forecasts[j].state);
  }
  assert(enabled.record.state.find("\"o\":\"accepted\"")!=std::string::npos);
  assert(enabled.record.state.find("\"n\":30")!=std::string::npos);
  assert(other.samples()==0);
  assert(disabled.record.state.empty());
  std::cout<<enabled.record.state<<'\n';
  test_clock+=300000;enabled.inputs[0].publish_state(30);enabled.update();
  assert(enabled.record.state.find("\"o\":\"rejected\"")!=std::string::npos);
  assert(enabled.record.state.find("disturbance_rejected")!=std::string::npos);
  assert(enabled.record.state.find("\"n\":30")!=std::string::npos);
  assert(enabled.record.state.find("\"f\":[null,null,null]")!=std::string::npos);
  enabled.flags[1].publish_state(true);enabled.update();
  assert(enabled.record.state.find("window_open")!=std::string::npos);
  assert(enabled.record.state.find("\"f\":[null,null,null]")!=std::string::npos);
  enabled.flags[1].publish_state(false);enabled.flags[2].publish_state(true);enabled.large_sequence();
  test_clock=(1ULL<<32)+123;enabled.update();
  assert(enabled.record.state.find("4294967419")!=std::string::npos);
  assert(enabled.record.state.find("18446744073709551614")!=std::string::npos);
  assert(enabled.record.state.size()<256);
  std::cout<<enabled.record.state<<'\n';
}
