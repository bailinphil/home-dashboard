// Home dashboard thin client, bring-up stage 1.
// WiFi -> GET /v1/active manifest -> GET image PNG -> drawPngFromBuffer
// -> full refresh -> deep sleep for next_refresh_s.
// All progress and errors go to Serial (115200).

#include <Inkplate.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "config.h"

Inkplate display;

struct WiFiCred { const char *ssid; const char *pass; };
const WiFiCred kNetworks[] = {
    {STA_SSID_HOME, STA_PASS_HOME},
    {STA_SSID_2,    STA_PASS_2},
    {STA_SSID_3,    STA_PASS_3},
    {STA_SSID_4,    STA_PASS_4},
};
const size_t kNumNetworks = sizeof(kNetworks) / sizeof(kNetworks[0]);

bool connectWiFi() {
    for (size_t i = 0; i < kNumNetworks; i++) {
        if (strlen(kNetworks[i].ssid) == 0) continue;
        Serial.printf("[wifi] trying %s\n", kNetworks[i].ssid);
        WiFi.begin(kNetworks[i].ssid, kNetworks[i].pass);
        uint32_t start = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
            delay(250);
        }
        if (WiFi.status() == WL_CONNECTED) {
            Serial.printf("[wifi] connected to %s, ip=%s rssi=%d\n",
                          kNetworks[i].ssid, WiFi.localIP().toString().c_str(),
                          WiFi.RSSI());
            return true;
        }
        Serial.printf("[wifi] failed on %s (status %d)\n",
                      kNetworks[i].ssid, WiFi.status());
        WiFi.disconnect(true);
    }
    return false;
}

bool httpGet(const char *url, uint8_t **buf, size_t *len) {
    HTTPClient http;
    http.setTimeout(30000);
    if (!http.begin(url)) return false;
    int code = http.GET();
    if (code != HTTP_CODE_OK) {
        Serial.printf("[http] GET %s -> %d\n", url, code);
        http.end();
        return false;
    }
    int total = http.getSize();
    WiFiClient *stream = http.getStreamPtr();
    size_t cap = total > 0 ? total : 2 * 1024 * 1024;
    *buf = (uint8_t *)ps_malloc(cap);
    if (!*buf) { http.end(); return false; }
    size_t n = 0;
    while (http.connected() && (total < 0 || n < (size_t)total)) {
        size_t avail = stream->available();
        if (avail) {
            if (n + avail > cap) {
                cap = n + avail + 65536;
                *buf = (uint8_t *)ps_realloc(*buf, cap);
            }
            n += stream->readBytes(*buf + n, avail);
        } else if (total < 0) {
            delay(1);
        } else {
            delay(1);
        }
    }
    http.end();
    *len = n;
    return true;
}

void setup() {
    Serial.begin(115200);
    uint32_t t0 = millis();
    display.begin();

    double vbat = display.readBattery();
    Serial.printf("[boot] battery %.2fV\n", vbat);

    if (!connectWiFi()) {
        Serial.println("[fail] no wifi");
        esp_deep_sleep(300ull * 1000000ull);   // retry in 5 min
    }

    char url[256];
    snprintf(url, sizeof(url), "%s/v1/active?device=%s&battery=%.2f",
             SERVER_BASE, DEVICE_ID, vbat);

    uint8_t *manifest = nullptr;
    size_t manifestLen = 0;
    if (!httpGet(url, &manifest, &manifestLen)) {
        Serial.println("[fail] manifest");
        esp_deep_sleep(300ull * 1000000ull);
    }

    JsonDocument doc;
    if (deserializeJson(doc, manifest, manifestLen)) {
        Serial.println("[fail] manifest json");
        esp_deep_sleep(300ull * 1000000ull);
    }
    const char *imageUrl = doc["image_url"];
    long nextRefresh = doc["next_refresh_s"] | 3600L;
    bool fullRefresh = doc["full_refresh"] | true;
    int regionCount = doc["regions"].isNull() ? -1 : doc["regions"].size();
    Serial.printf("[manifest] regions=%d full=%d next=%lds img=%s\n",
                  regionCount, fullRefresh, nextRefresh, imageUrl);

    if (regionCount == 0) {
        Serial.println("[skip] image unchanged; sleeping");
        esp_deep_sleep((uint64_t)nextRefresh * 1000000ull);
    }

    snprintf(url, sizeof(url), "%s%s", SERVER_BASE, imageUrl);
    uint8_t *png = nullptr;
    size_t pngLen = 0;
    if (!httpGet(url, &png, &pngLen)) {
        Serial.println("[fail] image download");
        esp_deep_sleep(300ull * 1000000ull);
    }
    Serial.printf("[image] %u bytes in %ums\n", (unsigned)pngLen,
                  (unsigned)(millis() - t0));

    if (!display.image.drawPngFromBuffer(png, pngLen, 0, 0, false, false)) {
        Serial.println("[fail] png decode");
        esp_deep_sleep(300ull * 1000000ull);
    }
    free(png);

    uint32_t tDraw = millis();
    display.display();
    Serial.printf("[display] refreshed in %ums (total %ums)\n",
                  (unsigned)(millis() - tDraw), (unsigned)(millis() - t0));

    // TODO: POST /v1/devices/<id>/telemetry
    Serial.printf("[sleep] %lds\n", nextRefresh);
    esp_deep_sleep((uint64_t)nextRefresh * 1000000ull);
}

void loop() {}
