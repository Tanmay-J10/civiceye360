/*
 * CivicEye 360 — Arduino UNO R4 Motor, Button & OLED Controller
 *
 * Wiring:
 *   L298N ENA (Left PWM)  -> Pin 6
 *   L298N ENB (Right PWM) -> Pin 5
 *   L298N IN1 / IN2       -> Pin 7 / Pin 8
 *   L298N IN3 / IN4       -> Pin 3 / Pin 4
 *   Start/Stop Button     -> Pin 2 to GND (internal pull-up)
 *   0.96" I2C OLED        -> SDA (A4), SCL (A5), VCC (5V), GND (GND)
 *   Common Ground         -> Arduino GND tied to L298N GND
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Pin Assignments
const int BUTTON_PIN = 2;
const int IN3 = 3;  // Right Dir 1
const int IN4 = 4;  // Right Dir 2
const int ENB = 5;  // Right Speed (PWM B)
const int ENA = 6;  // Left Speed (PWM A)
const int IN1 = 7;  // Left Dir 1
const int IN2 = 8;  // Left Dir 2

int cruiseSpeed = 200;
bool isRunning = false;
bool oledReady = false;
String piIp = "Waiting...";

// Push-button debounce state
unsigned long buttonLowSince = 0;
bool buttonHandled = false;

void updateOled(String l1, String l2, String l3, String l4) {
  if (!oledReady) return;
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);  display.println(l1);
  display.setCursor(0, 18); display.println(l2);
  display.setCursor(0, 34); display.println(l3);
  display.setCursor(0, 50); display.println(l4);
  display.display();
}

void showStandbyScreen() {
  updateOled("CIVICEYE 360 [READY]", "PI IP ADDRESS:", piIp, "PRESS BTN TO START");
}

void moveForward() {
  analogWrite(ENA, cruiseSpeed);
  analogWrite(ENB, cruiseSpeed);
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void moveBackward() {
  analogWrite(ENA, cruiseSpeed);
  analogWrite(ENB, cruiseSpeed);
  digitalWrite(IN1, LOW); digitalWrite(IN2, HIGH);
  digitalWrite(IN3, LOW); digitalWrite(IN4, HIGH);
}

void turnLeft() {
  analogWrite(ENA, cruiseSpeed);
  analogWrite(ENB, cruiseSpeed);
  digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
  digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
}

void turnRight() {
  analogWrite(ENA, cruiseSpeed);
  analogWrite(ENB, cruiseSpeed);
  digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
}

void stopMotors() {
  analogWrite(ENA, 0);
  analogWrite(ENB, 0);
  digitalWrite(IN1, LOW); digitalWrite(IN2, LOW);
  digitalWrite(IN3, LOW); digitalWrite(IN4, LOW);
}

void toggleRunState(bool startNow) {
  isRunning = startNow;
  if (isRunning) {
    Serial.println("START");
    updateOled("CIVICEYE 360 [ACTIVE]", "MODE: AUTO-PATROL", "MOTORS: FORWARD", "PRESS BTN TO STOP");
    moveForward();
  } else {
    Serial.println("STOP");
    stopMotors();
    showStandbyScreen();
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(50);
  Wire.begin();

  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(ENA, OUTPUT); pinMode(ENB, OUTPUT);
  pinMode(IN1, OUTPUT); pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT); pinMode(IN4, OUTPUT);
  stopMotors();

  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C) || display.begin(SSD1306_SWITCHCAPVCC, 0x3D)) {
    oledReady = true;
    showStandbyScreen();
  } else {
    Serial.println("ERR:OLED_NOT_FOUND");
  }
}

void loop() {
  // 1. Debounced Push-Button Start / Stop Toggle (50ms active LOW)
  if (digitalRead(BUTTON_PIN) == LOW) {
    if (buttonLowSince == 0) buttonLowSince = millis();
    if (!buttonHandled && (millis() - buttonLowSince >= 50)) {
      buttonHandled = true;
      toggleRunState(!isRunning);
    }
  } else {
    buttonLowSince = 0;
    buttonHandled = false;
  }

  // 2. Serial Commands from Raspberry Pi 5
  if (Serial.available() > 0) {
    String msg = Serial.readStringUntil('\n');
    msg.trim();

    if (msg.startsWith("IP:")) {
      piIp = msg.substring(3);
      if (!isRunning) showStandbyScreen();
    }
    else if (msg == "START") {
      toggleRunState(true);
    }
    else if (msg == "STOP" || msg == "S") {
      toggleRunState(false);
    }
    else if (msg == "TEST") {
      updateOled("CIVICEYE 360 [TEST]", "MOTOR CHECK...", "FORWARD 1.5s", "STAND CLEAR");
      moveForward();
      delay(1500);
      stopMotors();
      showStandbyScreen();
    }
    else if (msg == "F" && isRunning) {
      moveForward();
      updateOled("CIVICEYE 360 [ACTIVE]", "MODE: AUTO-PATROL", "SCANNING ROAD...", "PRESS BTN TO STOP");
    }
    else if (msg == "B") {
      moveBackward();
    }
    else if (msg == "L") {
      turnLeft();
    }
    else if (msg == "R") {
      turnRight();
    }
    else if (msg.startsWith("ALERT:")) {
      // Format: ALERT:HAZARD|ACTION|COST
      stopMotors();
      int p1 = msg.indexOf('|');
      int p2 = msg.indexOf('|', p1 + 1);
      if (p1 > 6 && p2 > p1) {
        updateOled(
          "! DEFECT DETECTED !",
          msg.substring(6, p1),
          msg.substring(p1 + 1, p2),
          "EST: Rs. " + msg.substring(p2 + 1)
        );
      }
    }
  }
}
