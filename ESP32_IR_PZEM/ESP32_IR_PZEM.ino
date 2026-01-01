#define IR_LED_PIN 4

int tlacidlo_ohrevu;
bool stavOhrevu = false; // false = vypnuté, true = zapnuté

#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <Arduino.h>
#include <IRremote.hpp>
#include <PZEM004Tv30.h>

PZEM004Tv30 pzem(Serial2, 16, 17);

char auth[] = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l";
char ssid[] = "ESP";
char pass[] = "202PuskaS";

int currentPercent = 50;  

unsigned long lastOhrevCheck = 0;
unsigned long lastPowerAdjust = 0;
unsigned long lastPzemRead = 0;
const unsigned long ohrevInterval = 2000; 
const unsigned long powerAdjustInterval = 1000; 
const unsigned long pzemInterval = 5000; 

// --- Blynk write ---
void writeValue(int pin, float value){
  HTTPClient http;
  String urlWrite = "http://blynk.cloud/external/api/update?token=" + String(auth) + "&V" + String(pin) + "=" + String(value);
  http.begin(urlWrite);
  int httpCodeWrite = http.GET();
  http.end();
}

void writeValue(int pin, const char* text){
  HTTPClient http;
  String url = "http://blynk.cloud/external/api/update?token=" + String(auth) +
               "&V" + String(pin) + "=" + String(text);
  http.begin(url);
  http.GET();
  http.end();
}

// --- Blynk read ---
float readValue(int pin){
  HTTPClient http;
  String urlRead = "http://blynk.cloud/external/api/get?token=" + String(auth) + "&V" + String(pin);
  http.begin(urlRead);
  int httpCodeRead = http.GET();
  if (httpCodeRead == HTTP_CODE_OK) {
    String payload = http.getString();
    http.end();
    return payload.toFloat();
  } else {
    http.end();
    return currentPercent; 
  }
}

// --- IR ---
void sendIRCommand(uint16_t userCode, uint16_t dataCode) {
    Serial.printf("📡 IR: userCode=0x%X, dataCode=0x%X\n", userCode, dataCode);
    IrSender.sendNEC(userCode, dataCode, 0);
}

// --- zapnutie ohrevu ---
void zapnutieOhrevu() {
  int tlacidlo_ohrevu = readValue(20);
  int tlacidlo_play_stop = readValue(19); 

  if (tlacidlo_play_stop == 1) { 
    delay(500); 
    sendIRCommand(0xFE01, 0xE41B);
    writeValue(19, (float)0);
  }

  if (tlacidlo_ohrevu == 1 && !stavOhrevu) { 
    Serial.println("🔥 Zapínam ohrev");
    delay(5000); 
    sendIRCommand(0xFE01, 0xE41B); 
    stavOhrevu = true;
  } 
  else if (tlacidlo_ohrevu == 0 && stavOhrevu) { 
    Serial.println("🛑 Vypínam ohrev");
    sendIRCommand(0xFE01, 0xE41B); 
    stavOhrevu = false; 
  }
}

// --- výkon ---
void nastavenieOhrevu() {
  int sliderValue = readValue(7);
  adjustPowerLevel(sliderValue);
}

void adjustPowerLevel(int targetPercent) {
    if (stavOhrevu) {
    Serial.printf("⚡ Aktuálny výkon: %d%%, cieľ: %d%%\n", currentPercent, targetPercent);

      if (targetPercent == 100) {
          sendIRCommand(0xFE01, 0xF807);
          currentPercent = 100;
          return;
      } else if (targetPercent == 75) {
          sendIRCommand(0xFE01, 0xF50A);
          currentPercent = 75;
          return;
      } else if (targetPercent == 50) {
          sendIRCommand(0xFE01, 0xFB04);
          currentPercent = 50;
          return;
      } else if (targetPercent == 25) {
          sendIRCommand(0xFE01, 0xFD02);
          currentPercent = 25;
          return;
      }
      
      while (currentPercent != targetPercent) {
          Serial.printf("🔄 Úprava výkonu: %d%% -> %d%%\n", currentPercent, targetPercent);
          if ((currentPercent > targetPercent && (currentPercent - 1) % 25 != 0) ||
              (currentPercent < targetPercent && (currentPercent + 1) % 25 != 0)) {
              sendIRCommand(0xFE01, currentPercent > targetPercent ? 0xE11E : 0xE31C);
              currentPercent += (currentPercent > targetPercent) ? -1 : 1;
          } else {
              if (currentPercent > targetPercent) {
                  if (currentPercent > 75) {
                      sendIRCommand(0xFE01, 0xF50A);
                      currentPercent = 75;
                  } else if (currentPercent > 50) {
                      sendIRCommand(0xFE01, 0xFB04);
                      currentPercent = 50;
                  } else if (currentPercent > 25) {
                      sendIRCommand(0xFE01, 0xFD02);
                      currentPercent = 25;
                  }
              } else {
                  if (currentPercent < 25) {
                      sendIRCommand(0xFE01, 0xFD02);
                      currentPercent = 25;
                  } else if (currentPercent < 50) {
                      sendIRCommand(0xFE01, 0xFB04);
                      currentPercent = 50;
                  } else if (currentPercent < 75) {
                      sendIRCommand(0xFE01, 0xF50A);
                      currentPercent = 75;
                  } else if (currentPercent < 100) {
                      sendIRCommand(0xFE01, 0xF807);
                      currentPercent = 100;
                  }
              }
          }
          delay(500);
      }
    }
    else {
      Serial.printf("❌ OHREV VYPNUTÝ");
    }
}

int pzemErrorCount = 0;
int pzemOkCount = 0;

void readPzem(){
  float voltage = pzem.voltage();
  float current = pzem.current();
  float power = pzem.power();
  float energy = pzem.energy();

  if ((isnan(voltage) || isnan(current) || isnan(power)) || power < 50) {
    pzemErrorCount++;
    pzemOkCount = 0; // reset
    Serial.printf("⚠️ PZEM error %d/3\n", pzemErrorCount);

    if (pzemErrorCount >= 3) {  // až po 3 neúspechoch
      Serial.println("❌ PZEM nekomunikuje → OFF");
      stavOhrevu = false;
      pzemErrorCount = 0; // reset
    }
    return;
  } else {
    pzemOkCount++;
    pzemErrorCount = 0;
    Serial.printf("✅ PZEM OK %d/3\n", pzemOkCount);

    if (pzemOkCount >= 3) { // až po 3 úspechoch
      stavOhrevu = true;
      pzemOkCount = 0; // reset
    }
  }

  char dataPzem[200];
  snprintf(dataPzem, sizeof(dataPzem),
    "Voltage: %.1f V\r\n"
    "Current: %.2f A\r\n"
    "Power: %.1f W\r\n"
    "Energy: %.3f kWh\r\n",
    voltage, current, power, energy
  );

  Serial.print(dataPzem);
  writeValue(10, dataPzem);
}


// --- setup/loop ---
void setup() {
    Serial.begin(115200);
    WiFi.begin(ssid, pass);
    while (WiFi.status() != WL_CONNECTED) { delay(500); }
    Serial.println("✅ WiFi pripojené");

    IrSender.begin(IR_LED_PIN);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        delay(2000); 
        ESP.restart();
    }

    unsigned long currentMillis = millis();

    if (currentMillis - lastOhrevCheck >= ohrevInterval) {
        zapnutieOhrevu();
        lastOhrevCheck = currentMillis;
    }

    if (currentMillis - lastPowerAdjust >= powerAdjustInterval) {
        nastavenieOhrevu();
        lastPowerAdjust = currentMillis;
    }

    if (currentMillis - lastPzemRead >= pzemInterval) {
        readPzem();
        lastPzemRead = currentMillis;
    }
}
