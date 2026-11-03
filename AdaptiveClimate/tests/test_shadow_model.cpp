#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#define esphome frozen_esphome
#include "reference/thermal_model.h"
#undef esphome
#include "../components/adaptive_climate/shadow_model.h"
#include <cassert>
#include <chrono>
#include <iostream>
#include <limits>
#ifdef NDEBUG
#error Regression tests require assertions enabled
#endif
using namespace esphome::adaptive_climate;
namespace esphome::adaptive_climate {
struct ThermalModelTestAccess {
  static void extreme(ThermalModel &m) { m.theta_[0]=.02f; m.theta_[1]=.05f; m.theta_[2]=-.03f; }
};
struct ShadowModelTestAccess {
  static void corrupt(ShadowModel &m) { m.p_[1][1] = -1; }
  static void extreme(ShadowModel &m) { m.beta_[0] = .2f; m.beta_[2] = -.03f; }
  static void uncertain(ShadowModel &m) {
    for(unsigned i=0;i<3;++i)for(unsigned j=0;j<3;++j)m.p_[i][j]=i==j?.05f:0;
  }
};
}
int main() {
  // Instrumentation must preserve every original numerical operation, including
  // bound hits, invalid calls, resets, suspensions and uint32 clock rollover.
  ThermalModel instrumented;
  frozen_esphome::adaptive_climate::ThermalModel frozen;
  for (unsigned k = 0; k < 20000; ++k) {
    const float room = 20 + std::sin(k * .1f), out = 10 + std::cos(k * .03f);
    const float heat = (k / 19) % 2 ? .8f : 0;
    const float next = k % 97 < 7 ? room + 2 : room + .1f * std::sin(k * .3f);
    assert(instrumented.learn(room,out,heat,next,5) == frozen.learn(room,out,heat,next,5));
    assert(instrumented.samples() == frozen.samples());
    for (unsigned i=0;i<3;++i) assert(instrumented.coefficient(i) == frozen.coefficient(i));
    for (unsigned h : {15,30,60}) assert(instrumented.forecast(room,out,heat,h) == frozen.forecast(room,out,heat,h));
  }
  // Repeated plausible-rate model mismatch is distinct from a failed estimator.
  ThermalModel original;
  ShadowModel candidate;
  for (unsigned k=0;k<30;++k) {
    original.learn(20,10,.2f,20,5); candidate.learn(20,10,.2f,20,5);
  }
  const auto samples = candidate.samples();
  const float loss = candidate.coefficient(0);
  for (unsigned k=0;k<12;++k) {
    assert(!original.learn(20,10,.2f,22,5));
    assert(!candidate.learn(20,10,.2f,22,5));
  }
  assert(original.samples()==0 && original.trace().resets==2);
  assert(candidate.samples()==samples && candidate.trace().resets==0 && candidate.coefficient(0)==loss);
  assert(std::strcmp(candidate.forecast_status(),"recovering")==0);
  assert(!candidate.learn(NAN,10,.2f,20,5));
  assert(candidate.samples()==samples);
  for (unsigned k=0;k<3;++k) assert(candidate.learn(20,10,.2f,20,5));
  assert(candidate.trace().consecutive==0);
  ShadowModelTestAccess::corrupt(candidate);
  assert(!candidate.learn(20,10,.2f,20,5));
  assert(candidate.samples()==0 && candidate.trace().resets==1);
  assert(std::strcmp(candidate.trace().reset_reason,"numerical")==0);
  assert(candidate.learn(20,10,.2f,20,5));

  // Six residual rejections on held zero-change data, with a legal but extreme
  // coefficient vector, reproduce the baseline reset mechanism without guessing
  // Stijn's missing raw temperatures or historical coefficient vector.
  ShadowModel mismatch;
  ThermalModel reference_mismatch;
  ThermalModelTestAccess::extreme(reference_mismatch);
  ShadowModelTestAccess::extreme(mismatch);
  for (unsigned k=0;k<6;++k) {
    assert(!reference_mismatch.learn(21.4f,9.9f,0,21.4f,5));
    assert(std::strcmp(reference_mismatch.trace().reason,"residual")==0);
    assert(!mismatch.learn(21.4f,9.9f,0,21.4f,5));
    assert(std::strcmp(mismatch.trace().reason,"residual")==0);
  }
  assert(mismatch.trace().resets==0 && mismatch.coefficient(0)==.02f);
  assert(reference_mismatch.trace().resets==1 && reference_mismatch.coefficient(0)==.002f);
  // Nick's curve follows an a=.02, equilibrium=9.9 cooling solution.
  float t=17.1f;
  for(unsigned i=1;i<=60;++i){
    t += .02f*(9.9f-t);
    if(i==15)assert(std::fabs(t-15.217697f)<.0001f);
    if(i==30)assert(std::fabs(t-13.827486f)<.0001f);
    if(i==60)assert(std::fabs(t-12.042380f)<.0001f);
  }

  ShadowObserver observer;
  Observation o{20,10,100,60,true,false,false};
  observer.receive(o,0,true);
  for(unsigned k=1;k<=12;++k) observer.receive(o,k*300000ULL,false);
  assert(observer.model.samples()==0); // polls cannot manufacture observations
  observer.receive(o,3900000,true); // held >30 min -> new baseline
  observer.receive(o,4200000,true); // unchanged but new raw publication counts
  assert(observer.model.samples()==1);
  const float hot=observer.heat_state();
  o.heating=false;observer.receive(o,4200000,false);
  observer.receive(o,4500000,false);
  assert(observer.heat_state()>0 && observer.heat_state()<hot);
  const float residual_heat=observer.heat_state();
  o.dhw=true;observer.receive(o,4500000,false);
  o.dhw=false;observer.receive(o,4560000,false);
  assert(std::fabs(observer.heat_state()-residual_heat*std::exp(-.1f))<1.e-5f);
  const auto prior=observer.model.samples();
  observer.receive(o,4800000,true);
  assert(observer.model.samples()==prior); // no pair across DHW
  observer.receive(o,5100000,true);
  assert(observer.model.samples()==prior+1);
  assert(std::isnan(observer.forecast(7000000,60))); // unconfirmed origin
  observer.invalidate(7000000);
  observer.receive(o,7300000,true);
  assert(std::strcmp(observer.forecast_status(7300000),"radiator_settling")==0);

  ShadowModel off;
  for(unsigned k=0;k<10000;++k)off.learn(20,10,0,20,5);
  assert(!off.identified()); // loss/offset correlation and absent heat excitation
  assert(off.trace().resets==0);
  ShadowModel constraint;
  bool saturated=false;
  for(unsigned k=0;k<100;++k) {constraint.learn(20,20,0,19.3f,5);saturated|=constraint.trace().saturation!=0;}
  assert(saturated);
  assert(std::strcmp(constraint.forecast_status(),"constraint")==0);

  // Known physical system, broad independent forcing, > one simulated year.
  // Testing conditioning/convergence only; this is not historical validation.
  ShadowModel long_run;
  float room=20;
  auto start=std::chrono::steady_clock::now();
  for(unsigned k=0;k<120000;++k){
    const float outdoor=10+5*std::sin(k*.017f), heat=(k/17)%2?.8f:.1f;
    // Implicit midpoint is the same interval model, independently generated.
    const float next=(room+5*(.002f*(outdoor-room*.5f)+.08f*heat+.003f))/(1+.005f);
    long_run.learn(room,outdoor,heat,next,5); room=next;
  }
  assert(long_run.trace().resets==0 && long_run.samples()>119000 && long_run.identified());
  assert(std::fabs(long_run.coefficient(0)-.002f)<.0001f);
  assert(std::fabs(long_run.coefficient(1)-.08f)<.001f);
  assert(std::fabs(long_run.coefficient(2)-.003f)<.001f);
  ShadowObserver forecast;
  o={20,10,50,50,true,false,false};
  forecast.receive(o,0,true);forecast.receive(o,1800000,true);forecast.model=long_run;
  float width;
  assert(std::isfinite(forecast.forecast(1800000,60,&width)) && width<1);
  assert(std::isnan(forecast.forecast(1800000,61)));
  ShadowModelTestAccess::uncertain(forecast.model);
  assert(std::isnan(forecast.forecast(1800000,60,&width)) && width>1);
  const auto us=std::chrono::duration_cast<std::chrono::microseconds>(std::chrono::steady_clock::now()-start).count();
  std::cout<<"PASS reference parity, disturbance preservation, invalid/numerical recovery, event pairs, DHW residual heat, constraints, Nick curve, long operation\n";
  std::cout<<"sizeof(reference model/observer)="<<sizeof(frozen)<<'/'<<sizeof(frozen_esphome::adaptive_climate::Observer)
           <<" instrumented="<<sizeof(ThermalModel)<<'/'<<sizeof(Observer)
           <<" shadow="<<sizeof(ShadowModel)<<'/'<<sizeof(ShadowObserver)<<" desktop learn us="<<us/120000.0<<'\n';
}
