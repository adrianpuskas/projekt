#define IR_LED_PIN 4 //

//#define RELAY_OHREV 17  // Digitálny pin na riadenie ohrevu

int tlacidlo_ohrevu;
bool stavOhrevu = false; // false = vypnuté, true = zapnuté

#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <Arduino.h>
#include <IRremote.hpp>

char auth[] = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l";
char ssid[] = "ESP";
char pass[] = "202PuskaS";

int currentPercent = 50;  // Počiatočná hodnota výkonu

unsigned long lastOhrevCheck = 0;
unsigned long lastPowerAdjust = 0;
const unsigned long ohrevInterval = 2000; // 2 sekundy
const unsigned long powerAdjustInterval = 1000; // 1 sekunda

void writeValue(int pin, float value){
  Serial.printf("➡ Zapisujem do Blynk: V%d = %.2f\n", pin, value);
  HTTPClient http;
  String urlWrite = "http://blynk.cloud/external/api/update?token=" + String(auth) + "&V" + String(pin) + "=" + String(value);
  http.begin(urlWrite);
  int httpCodeWrite = http.GET();
  Serial.printf("📡 writeValue odpoveď: %d\n", httpCodeWrite);
  http.end();
}

float readValue(int pin){
  Serial.printf("⬅ Čítam z Blynk: V%d\n", pin);
  HTTPClient http;
  String urlRead = "http://blynk.cloud/external/api/get?token=" + String(auth) + "&V" + String(pin);
  http.begin(urlRead);
  int httpCodeRead = http.GET();
  Serial.printf("📡 readValue odpoveď: %d\n", httpCodeRead);
  if (httpCodeRead == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.printf("📥 Prijatá hodnota: %s\n", payload.c_str());
    http.end();
    return payload.toFloat();
  } else {
    http.end();
    return currentPercent; 
  }
}

void zapnutieOhrevu() {
  Serial.println("🔄 Spúšťam zapnutieOhrevu()");
  int tlacidlo_ohrevu = readValue(20);
  int tlacidlo_play_stop = readValue(19); 

  Serial.printf("📊 tlacidlo_ohrevu=%d, tlacidlo_play_stop=%d, stavOhrevu=%d\n", tlacidlo_ohrevu, tlacidlo_play_stop, stavOhrevu);

  if (tlacidlo_play_stop == 1) { 
    delay(500); 
    sendIRCommand(0xFE01, 0xE41B);
    writeValue(19,0);
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

void nastavenieOhrevu() {
  Serial.println("⚙ Spúšťam nastavenieOhrevu()");
  int sliderValue = readValue(7);
  Serial.printf("🎚 Nastavujem výkon na %d%%\n", sliderValue);
  adjustPowerLevel(sliderValue);
}

void sendIRCommand(uint16_t userCode, uint16_t dataCode) {
    Serial.printf("📡 Posielam IR príkaz: userCode=0x%X, dataCode=0x%X\n", userCode, dataCode);
    IrSender.sendNEC(userCode, dataCode, 0);
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

void setup() {
    Serial.begin(115200);
    Serial.println("🔌 Pripájam sa na WiFi...");
    WiFi.begin(ssid, pass);
    while (WiFi.status() != WL_CONNECTED) {
        Serial.print(".");
        delay(500);
    }
    Serial.println("\n✅ WiFi pripojené!");
    Serial.print("📶 IP adresa: ");
    Serial.println(WiFi.localIP());

    IrSender.begin(IR_LED_PIN);
    //pinMode(RELAY_OHREV, OUTPUT);
    //digitalWrite(RELAY_OHREV, HIGH);
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        Serial.println("❌ WiFi odpojené, reštartujem...");
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
}
