# Prototype wiring and initial Arduino sketch

This file contains wiring guidance for connecting a PN532 NFC module to an ESP32 (I2C) and a minimal Arduino sketch to read NFC tag/phone UIDs using the Adafruit PN532 library.

## Wiring (I2C)

- PN532 VCC -> ESP32 3.3V
- PN532 GND -> ESP32 GND
- PN532 SDA -> ESP32 SDA (usually GPIO 21)
- PN532 SCL -> ESP32 SCL (usually GPIO 22)

Notes:
- Use the PN532 module's I2C mode (some breakout boards require soldering pads to select I2C).
- Confirm voltage compatibility; most PN532 modules accept 3.3V. If yours expects 5V, use level shifting for SDA/SCL.

## Libraries

- Adafruit PN532: install via Library Manager (Adafruit PN532)
- Wire (built-in)

## Minimal Arduino sketch (ESP32, I2C)

Paste this into the Arduino IDE. It initializes the PN532 over I2C and prints detected UID values to Serial.

```cpp
#include <Wire.h>
#include <Adafruit_PN532.h>

// Use I2C
#define PN532_SDA 21
#define PN532_SCL 22

Adafruit_PN532 nfc(PN532_SDA, PN532_SCL);

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10);
  Serial.println("PN532 + ESP32 - UID reader (I2C)");

  Wire.begin(PN532_SDA, PN532_SCL);
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("Didn't find PN532, check wiring");
    while (1) delay(1000);
  }

  Serial.print("Found PN532, firmware ver: 0x");
  Serial.println(versiondata, HEX);

  // Configure board to read RFID tags
  nfc.SAMConfig();
  Serial.println("Waiting for an NFC tag (or phone)...");
}

void loop() {
  boolean success;
  uint8_t uid[7];
  uint8_t uidLength;

  // Wait for an ISO14443A tag (Mifare, phones with NFC)
  success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 1000);

  if (success) {
    Serial.print("UID detected: ");
    for (uint8_t i = 0; i < uidLength; i++) {
      Serial.print(uid[i], HEX);
      if (i < uidLength - 1) Serial.print(":");
    }
    Serial.println();
    delay(500); // simple debounce
  }
}
```

## Testing tips

- Test with multiple phones and orientations — detection distance varies.
- If detection is flaky, increase PN532 antenna area in the 3D model or adjust placement.
- Use Serial prints to observe timing; add retries and debounce before declaring presence/absence.

## Next steps

- Add presence/absence logic with debouncing and event timestamps.
- Optionally add Wi-Fi + MQTT or a tiny web API for remote monitoring.
