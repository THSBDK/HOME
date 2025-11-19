# Prototype wiring and initial ESPhome sketch
- [Prototype wiring and initial ESPhome sketch](#prototype-wiring-and-initial-esphome-sketch)
  - [Wiring (I2C)](#wiring-i2c)
  - [Minimal ESPhome yaml sketch (ESP32, I2C)](#minimal-esphome-yaml-sketch-esp32-i2c)
  - [Testing tips](#testing-tips)
  - [where we at](#where-we-at)
    - [🔍 What Your YAML Is Doing](#-what-your-yaml-is-doing)
  - [pn532\_i2c block](#pn532_i2c-block)
  - [ble\_presence sensors](#ble_presence-sensors)
  - [ble\_rssi sensors](#ble_rssi-sensors)
  - [bluetooth\_proxy](#bluetooth_proxy)
  - [🧪 Next Step: InfluxDB Logging](#-next-step-influxdb-logging)



This file contains wiring guidance for connecting a PN532 NFC module to an ESP32 (I2C) and a minimal Arduino sketch to read NFC tag/phone UIDs using the Adafruit PN532 library.

## Wiring (I2C)

- PN532 VCC -> ESP32 3.3V
- PN532 GND -> ESP32 GND
- PN532 SDA -> ESP32 SDA (usually GPIO 21)
- PN532 SCL -> ESP32 SCL (usually GPIO 22)

Notes:
- Use the PN532 module's I2C mode (some breakout boards require soldering pads to select I2C).
- Confirm voltage compatibility; most PN532 modules accept 3.3V. If yours expects 5V, use level shifting for SDA/SCL.

## Minimal ESPhome yaml sketch (ESP32, I2C)

Paste this into the Arduino IDE. It initializes the PN532 over I2C and prints detected UID values to Serial.

```
esphome:
  name: hybridpresencenode
  friendly_name: Hybrid Presence Node

esp32:
  board: esp32dev
  framework:
    type: esp-idf

wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    ssid: "Fallback Hotspot"
    password: "fallback123"

# Enable API for HA integration
api:
  encryption:
    key: "qfxBuAHxWbY1ealIqsMYENNwRsyNUsK/DeocAuqlaDM="
logger:

ota:
  - platform: esphome
    password: "da457302e6274cbb6ccd5d86a4ab1831"

# MQTT (optional if you want direct MQTT publishing in addition to HA API)
#mqtt:
#  broker: !secret mqtt_broker
#  username: !secret mqtt_user
#  password: !secret mqtt_pass

# --- Bluetooth Proxy ---
esp32_ble_tracker:

# --- PN532 NFC Reader ---
i2c:
  sda: 21
  scl: 22
  scan: true
  frequency: 100kHz

pn532_i2c:
  update_interval: 1s
  on_tag:
    then:
      - lambda: |-
          std::string uid_str;
          for (auto b : tag.get_uid()) {
            char hex[4];
            sprintf(hex, "%02X-", b);
            uid_str += hex;
          }
          uid_str.pop_back();  // remove trailing dash
          ESP_LOGI("nfc", "🎯 Tag UID: %s", uid_str.c_str());

binary_sensor:
  - platform: pn532
    uid: "04-92-C4-CB-4C-59-80"   # iPhone NFC tag UID
    name: "Thomas iPhone NFC"
  - platform: pn532
    uid: "04-52-EB-CB-4C-59-80"      # Android NFC tag UID
    name: "Thomas Android NFC"
# Example BLE presence (replace with MACs or beacon UUIDs if static)
  - platform: ble_presence
    #mac_address: "AA:BB:CC:DD:EE:FF"   # Example Android MAC
    irk: "36d882e492530f80d17db3d6fb43b062"
    name: "Android BLE Presence"
  - platform: ble_presence
    #mac_address: "11:22:33:44:55:66"   # Example iPhone MAC (if static)
    irk: "40e9be44eeb0c24aa3d64bb9367607cf"
    name: "iPhone BLE Presence"

sensor:
  - platform: ble_rssi
    irk: "36d882e492530f80d17db3d6fb43b062"
    name: "Android BLE Presence"
  - platform: ble_rssi
    irk: "40e9be44eeb0c24aa3d64bb9367607cf"
    name: "iPhone BLE Presence"

# Optional LED feedback
#output:
#  - platform: gpio
#    pin: GPIO2
#    id: status_led
#
#light:
#  - platform: binary
#    name: "Presence Status LED"
#    output: status_led


```

## Testing tips

- Test with multiple phones and orientations — detection distance varies.
- If detection is flaky, increase PN532 antenna area in the 3D model or adjust placement.
- Use Serial prints to observe timing; add retries and debounce before declaring presence/absence.


## where we at
✅ NFC tag detection via PN532 (with live UID logging in the console)

✅ BLE proxy so Home Assistant can use this ESP32 as a remote antenna

✅ BLE presence detection using IRKs (so your iPhone and Android are tracked even with randomized MACs)

✅ BLE RSSI sensors so you can log signal strength and later use it for proximity analytics

### 🔍 What Your YAML Is Doing
## pn532_i2c block

Polls the PN532 every second (update_interval: 1s)

Logs any tag UID it sees (ESP_LOGI("nfc", ...))

Exposes binary sensors for your iPhone and Android NFC tags

## ble_presence sensors

Use IRKs instead of MACs, so they resolve your phones even with rotating addresses

Report on/off presence states into Home Assistant

## ble_rssi sensors

Track signal strength for each phone

Useful for distance/proximity estimation or logging into InfluxDB

## bluetooth_proxy

Lets Home Assistant’s Private BLE Device integration use this ESP32 as a remote scanner


## 🧪 Next Step: InfluxDB Logging
Since you’ve installed the InfluxDB add-on in Home Assistant, you don’t need ESPHome to push data directly. Instead:

In Home Assistant, go to Settings → Devices & Services → InfluxDB

Configure which entities to log (e.g., all binary_sensor.thomas_iphone_nfc, binary_sensor.thomas_android_nfc, binary_sensor.android_ble_presence, sensor.android_ble_presence_rssi, etc.)

InfluxDB will automatically store every state change with timestamps

Grafana can then query those metrics for dashboards (e.g., “phone docked sessions,” “BLE signal strength over time”)

🔧 Suggested Refinements
Give unique names to your RSSI sensors (e.g., "Android BLE RSSI" vs "Android BLE Presence") so HA doesn’t confuse them.

Add device_class: presence to your BLE binary sensors for better UI integration.

If you want to fuse NFC + BLE into a high-confidence presence sensor, you can do that with a template binary sensor or in Home Assistant itself.