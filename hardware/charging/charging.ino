#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;

float batteryVoltage = 0.0;
float batteryPercent = 0.0;

void setup() {

  Serial.begin(115200);

  Wire.begin(21, 22);

  delay(100);

  if (!ina219.begin()) {

    Serial.println("INA219 not found!");

    while (1);
  }

  Serial.println("Battery Charging Monitor Started");
}

void loop() {

  batteryVoltage = ina219.getBusVoltage_V();

  // Simple Li-ion percentage estimation
  batteryPercent = ((batteryVoltage - 3.0) / (4.2 - 3.0)) * 100.0;

  // limit range
  if (batteryPercent > 100)
    batteryPercent = 100;

  if (batteryPercent < 0)
    batteryPercent = 0;

  Serial.print("Battery Voltage: ");
  Serial.print(batteryVoltage);
  Serial.println(" V");

  Serial.print("Estimated Charge: ");
  Serial.print(batteryPercent);
  Serial.println(" %");

  // Charging state
  if (batteryVoltage >= 4.18) {

    Serial.println("Battery Fully Charged");

  }
  else if (batteryVoltage >= 4.0) {

    Serial.println("Battery Near Full");

  }
  else if (batteryVoltage >= 3.7) {

    Serial.println("Charging Normally");

  }
  else {

    Serial.println("Battery Low / Charging");
  }

  Serial.println("------------------------");

  delay(1000);
}