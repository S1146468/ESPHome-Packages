#pragma once
#include <Arduino.h>
#include <SPI.h>
#include <SD.h>

static bool g_sd_mounted = false;

static bool sd_try_mount(int cs, int sck, int miso, int mosi, uint32_t hz) {
  pinMode(cs, OUTPUT);
  digitalWrite(cs, HIGH);        // CS idle high
  SPI.end();                     // clean slate
  SPI.begin(sck, miso, mosi, cs);
  if ( SD.begin(cs, SPI, hz) ) {
    g_sd_mounted = true;
    ESP_LOGI("sd", "Mounted at %lu Hz", (unsigned long)hz);
    ESP_LOGI("sd", "Type=%d Size=%llu MB", (int)SD.cardType(), (unsigned long long)(SD.cardSize() / (1024ULL*1024ULL)));
    return true;
  }
  return false;
}

inline bool sd_mount_any(int cs, int sck, int miso, int mosi) {
  if (g_sd_mounted) return true;
  const uint32_t speeds[] = { 8000000UL, 4000000UL, 1000000UL, 400000UL };
  for (auto hz : speeds) {
    if (sd_try_mount(cs, sck, miso, mosi, hz)) return true;
    ESP_LOGW("sd", "SD.begin failed at %lu Hz", (unsigned long)hz);
    delay(50);
  }
  ESP_LOGE("sd", "Failed to mount SD");
  return false;
}

inline void sd_list_dir(const char* path) {
  if (!g_sd_mounted) { ESP_LOGE("sd","Not mounted"); return; }
  File root = SD.open(path);
  if (!root) { ESP_LOGE("sd","Open failed: %s", path); return; }
  if (!root.isDirectory()) { ESP_LOGE("sd","Not a dir: %s", path); root.close(); return; }
  for (File f = root.openNextFile(); f; f = root.openNextFile()) {
    ESP_LOGI("sd","%s %s (%u bytes)", f.isDirectory() ? "DIR " : "FILE", f.name(), (unsigned)f.size());
  }
  root.close();
}
