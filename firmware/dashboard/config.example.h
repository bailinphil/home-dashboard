// Copy to config.h and fill in real values. config.h is gitignored.
#ifndef DASHBOARD_CONFIG_H_
#define DASHBOARD_CONFIG_H_

// Ordered list of networks to try (home, work, phone hotspot, ...).
#define STA_SSID_HOME   "your-ssid"
#define STA_PASS_HOME   "your-password"
#define STA_SSID_2      ""
#define STA_PASS_2      ""
#define STA_SSID_3      ""
#define STA_PASS_3      ""
#define STA_SSID_4      ""
#define STA_PASS_4      ""

// During bring-up this is the dev Mac on the LAN; in production it is
// http://ino.bailinphil.com (HTTP only, like kitchen-lights).
#define SERVER_BASE     "http://192.168.1.100:8080"
#define DEVICE_ID       "inkplate1"

#endif
