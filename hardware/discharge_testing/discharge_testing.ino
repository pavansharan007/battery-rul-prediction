#include <Wire.h>
#include <Adafruit_INA219.h>

Adafruit_INA219 ina219;

float used_mAh = 0.0;

unsigned long previousMillis = 0;

void setup() {

  Serial.begin(115200);

  Wire.begin(21,22);

  if (!ina219.begin()) {

    Serial.println("INA219 not found!");

    while(1);
  }

  previousMillis = millis();
}

void loop() {

  unsigned long currentMillis = millis();

  float elapsedHours = (currentMillis - previousMillis) / 3600000.0;

  previousMillis = currentMillis;

  float voltage = ina219.getBusVoltage_V();

  float current_mA = ina219.getCurrent_mA();

  // accumulate used capacity
  used_mAh += current_mA * elapsedHours;

  // remaining battery estimate
  float batteryCapacity = 2000.0;

  float remaining_mAh = batteryCapacity - used_mAh;

  float percentage = (remaining_mAh / batteryCapacity) * 100.0;

  if (percentage < 0)
    percentage = 0;

  Serial.print("Voltage: ");
  Serial.print(voltage);
  Serial.println(" V");

  Serial.print("Current: ");
  Serial.print(current_mA);
  Serial.println(" mA");

  Serial.print("Used Capacity: ");
  Serial.print(used_mAh);
  Serial.println(" mAh");

  Serial.print("Remaining Capacity: ");
  Serial.print(remaining_mAh);
  Serial.println(" mAh");

  Serial.print("Battery Percentage: ");
  Serial.print(percentage);
  Serial.println(" %");

  Serial.println("----------------------");

  delay(1000);
}