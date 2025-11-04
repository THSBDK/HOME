# Phonestand with ESP32 and NFC (PN532)

Project to design and 3D-print a phone stand that detects when a phone is placed on it. Detection will use a PN532 NFC/RFID module and an ESP32 microcontroller. Firmware will be developed in the Arduino IDE. The goal is to reliably detect phone presence, log events, and optionally expose a small web UI or MQTT updates.

## Goals

- 3D-print a clean, stable phone stand that can house the PN532 and ESP32.
- Implement firmware in Arduino IDE for the ESP32 to read PN532 presence events.
- Provide basic connectivity: serial logging, optional Wi-Fi + MQTT or tiny web UI for status.
- Document assembly, wiring, and testing procedures.

## Todo (project-level)

- [ ] Design 3D-print model for the phone stand (STL file).
	- [ ] Ensure space/slots for PN532 module and ESP32 board
	- [ ] Add cable routing and mounting points for sensors
- [ ] Select hardware parts and order components
	- ESP32 board (suggested: WROOM/WROVER variant)
	- PN532 NFC module (I2C or SPI variant)
	- Wires, female headers, optional enclosure parts
- [ ] Wire up prototype on breadboard and validate PN532 communication
	- Confirm pinout, I2C/SPI mode, and power requirements
- [ ] Implement firmware (Arduino IDE)
	- [ ] Basic PN532 driver test (read UID)
	- [ ] Phone-detection logic (presence/absence debouncing)
	- [ ] Add logging over Serial
	- [ ] Optional: Wi‑Fi + MQTT publish or tiny web endpoint
- [ ] Create test plan and verify detection reliability with multiple phone models
- [ ] 3D-print prototypes and iterate fit/finish
- [ ] Final wiring and enclosure assembly
- [ ] Document assembly, flashing steps, and troubleshooting in this README

## Minimal contract

- Inputs: NFC field from phones (PN532), power (5V/3.3V), optional Wi-Fi credentials for reporting.
- Outputs: Serial logs, optional MQTT messages or HTTP endpoint indicating presence/absence.
- Success criteria: Phone presence reliably detected >95% across tested phone models; stable behavior after power cycles.

## Notes

- PN532 often detects phones using NFC polling; results vary by phone model and orientation — test early.
- Use logic-level converters if needed and confirm PN532 voltage compatibility with your chosen ESP32 board.

Generated: 4. november 2025
