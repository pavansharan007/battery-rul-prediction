#include <math.h>

#include "XGBoost_Optimized_split.h"

void setup() {
  Serial.begin(115200);


  double discharge_capacity_ah = 536.7198 / 1000.0;

  double x[5] = {
    discharge_capacity_ah, // input[0] discharge_capacity (Ah)
    3.6860,                // input[1] avg_voltage (V)
    3.0000,                // input[2] end_voltage (V)
    6504.0,                // input[3] discharge_time (s)
    1744.0                 // input[4] cv_charge_time (s)
  };

  double rul_cycles = score(x);
  Serial.println("Predicted RUL (cycles): ");
  Serial.println(rul_cycles, 6);
}

void loop() {}