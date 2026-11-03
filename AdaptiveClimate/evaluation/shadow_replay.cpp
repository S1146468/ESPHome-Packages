// Task-specific replay of actual C++ learners. Input events and grid origins are
// distinct. Last two fields: raw room publication, evaluate origin (both 0/1).
#include "../components/adaptive_climate/shadow_model.h"
#include <array>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
using namespace esphome::adaptive_climate;
int main() {
  std::array<Observer,2> reference;
  std::array<ShadowObserver,2> shadow;
  std::array<uint64_t,2> last{};
  std::array<unsigned,2> ref_accepted{}, shadow_accepted{}, shadow_rejected{};
  std::string line;
  std::cout<<"room,time,ref_status,ref_n,ref_a,ref_b,ref_c,ref_reason,ref_resets,ref_sat,shadow_status,shadow_n,shadow_a,shadow_b,shadow_c,shadow_reason,shadow_resets,shadow_sat,ref15,ref30,ref60,shadow15,shadow30,shadow60,ref_attempts,ref_accepted,shadow_attempts,shadow_accepted,shadow_rejected\n"<<std::setprecision(9);
  while(std::getline(std::cin,line)) {
    std::istringstream in(line);std::string room,extra;uint64_t now;Observation o{};int ch,win,dhw,valid,pub,tick;
    if(!(in>>room>>now>>o.room>>o.outdoor>>o.valve>>o.supply>>ch>>win>>dhw>>valid>>pub>>tick)||(in>>extra)||
       (room!="stijn"&&room!="nick")||ch<0||ch>1||win<0||win>1||dhw<0||dhw>1||valid<0||valid>1||pub<0||pub>1||tick<0||tick>1)return 2;
    unsigned i=room=="stijn"?0:1;
    if(now<last[i])return 2;
    last[i]=now;o.heating=ch;o.window_open=win;o.dhw=dhw;
    auto &r=reference[i];auto &s=shadow[i];
    const auto attempts=s.model.trace().attempts;
    if(!valid){r.suspend();s.invalidate(now);}else{s.receive(o,now,pub);if(win||dhw)r.suspend();}
    if(s.model.trace().attempts!=attempts) {
      if(std::string(s.model.trace().reason)=="accepted")++shadow_accepted[i];else ++shadow_rejected[i];
    }
    if(!tick)continue;
    const auto ref_before=r.model.trace().attempts;
    const char *status=valid?r.observe(o,uint32_t(now)):"masked_input";
    if(r.model.trace().attempts!=ref_before&&std::string(r.model.trace().reason)=="accepted")++ref_accepted[i];
    std::cout<<room<<','<<now<<','<<status<<','<<r.model.samples();
    for(unsigned j=0;j<3;++j)std::cout<<','<<r.model.coefficient(j);
    std::cout<<','<<r.model.trace().reason<<','<<r.model.trace().resets<<','<<unsigned(r.model.trace().saturation)
             <<','<<s.forecast_status(now)<<','<<s.model.samples();
    for(unsigned j=0;j<3;++j)std::cout<<','<<s.model.coefficient(j);
    std::cout<<','<<s.model.trace().reason<<','<<s.model.trace().resets<<','<<unsigned(s.model.trace().saturation);
    for(unsigned h:{15,30,60})std::cout<<','<<r.forecast(o,h);
    for(unsigned h:{15,30,60})std::cout<<','<<s.forecast(now,h);
    std::cout<<','<<r.model.trace().attempts<<','<<ref_accepted[i]<<','<<s.model.trace().attempts<<','<<shadow_accepted[i]<<','<<shadow_rejected[i];
    std::cout<<'\n';
  }
}
