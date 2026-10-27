#pragma once
namespace esphome::api {
struct APIServer {
  bool subscribed = true;
  bool is_connected_with_state_subscription() const { return subscribed; }
};
inline APIServer server;
inline APIServer *global_api_server = &server;
}
