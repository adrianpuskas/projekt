#include <ESP8266WiFi.h>
#include <PZEM004Tv30.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

#if !defined(PZEM_RX_PIN) && !defined(PZEM_TX_PIN)
#define PZEM_RX_PIN 0
#define PZEM_TX_PIN 2
#endif

SoftwareSerial pzemSWSerial(PZEM_RX_PIN, PZEM_TX_PIN);

#define NUM_PZEMS 3
PZEM004Tv30 pzems[NUM_PZEMS];

char ssid[] = "ESP";
char pass[] = "202PuskaS";

// Lokálny server
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;
const String resetKey = "PZEM_reset_energy";

unsigned long lastPZEMTime = 0;
unsigned long lastResetCheckTime = 0;
const unsigned long pzemInterval = 5000;  // Interval pre čítanie PZEM (5 sekúnd)
const unsigned long resetCheckInterval = 2000;  // Interval pre kontrolu resetu (2 sekundy)

double celkovaSpotreba = 0.0;

// Funkcia na odoslanie hodnoty na lokálny server
void sendToLocalServer(const String& key, float value) {
  if (WiFi.status() != WL_CONNECTED) return;

  WiFiClient client;
  HTTPClient http;

  String url = "http://";
  url += serverIP;
  url += ":";
  url += serverPort;
  url += "/write";

  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"key\":\"" + key + "\",\"value\":" + String(value, 3) + "}";

  int httpCode = http.POST(payload);
  if (httpCode > 0) {
    Serial.printf("%s = %.3f odoslané, HTTP: %d\n", key.c_str(), value, httpCode);
  } else {
    Serial.printf("Chyba odosielania %s: %d\n", key.c_str(), httpCode);
  }
  http.end();
}

// Funkcia na čítanie hodnoty z lokálneho servera
float readFromLocalServer(const String& key) {
  if (WiFi.status() != WL_CONNECTED) return -1.0;

  WiFiClient client;
  HTTPClient http;

  String url = "http://";
  url += serverIP;
  url += ":";
  url += serverPort;
  url += "/get/" + key;

  http.begin(client, url);
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Čítanie z Flask úspešné: " + payload);
    return payload.toFloat();
  } else {
    Serial.println("Chyba čítania z Flask: HTTP kód " + String(httpCode));
    return -1.0;
  }
  http.end();
}

// Funkcia na reset energie
void resetPZEMEnergy() {
  for (int i = 0; i < NUM_PZEMS; i++) {
    pzems[i].resetEnergy();
  }
  celkovaSpotreba = 0.0;

  // Odoslať resetované hodnoty na lokálny server
  sendToLocalServer("PZEM_L1_energy", 0.0);
  sendToLocalServer("PZEM_L2_energy", 0.0);
  sendToLocalServer("PZEM_L3_energy", 0.0);
  sendToLocalServer("PZEM_total_energy", 0.0);

  // Nastaviť reset kľúč späť na 0 na serveri
  sendToLocalServer(resetKey, 0.0);
}

void PZEMs() {
  float totalPower = 0.0;
  float totalEnergy = 0.0;

  for (int i = 0; i < NUM_PZEMS; i++) {
    float voltage = pzems[i].voltage();
    float current = pzems[i].current();
    float power = pzems[i].power();
    float energy = pzems[i].energy();
    float frequency = pzems[i].frequency();
    float pf = pzems[i].pf();

    String phase = "PZEM_L" + String(i + 1);

    if (!isnan(voltage)) sendToLocalServer(phase + "_voltage", voltage);
    if (!isnan(current)) sendToLocalServer(phase + "_current", current);
    if (!isnan(power)) {
      sendToLocalServer(phase + "_power", power);
      totalPower += power;
    }
    if (!isnan(energy)) {
      sendToLocalServer(phase + "_energy", energy);
      totalEnergy += energy;
    }
    if (!isnan(frequency)) sendToLocalServer(phase + "_freq", frequency);
    if (!isnan(pf)) sendToLocalServer(phase + "_pf", pf);
  }

  // Celkové hodnoty
  sendToLocalServer("PZEM_total_power", totalPower);
  sendToLocalServer("PZEM_total_energy", totalEnergy);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, pass);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi pripojené: " + WiFi.localIP().toString());

  for (int i = 0; i < NUM_PZEMS; i++) {
    pzems[i] = PZEM004Tv30(pzemSWSerial, 0x10 + i);
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    ESP.restart();
  }

  unsigned long currentMillis = millis();

  // Čítanie PZEM hodnôt každých 5 sekúnd
  if (currentMillis - lastPZEMTime >= pzemInterval) {
    lastPZEMTime = currentMillis;
    PZEMs();
  }

  // Kontrola reset tlačidla každých 2 sekundy
  if (currentMillis - lastResetCheckTime >= resetCheckInterval) {
    lastResetCheckTime = currentMillis;
    float resetValue = readFromLocalServer(resetKey);
    if (resetValue == 1.0) {
      Serial.println("Reset požiadavka prijatá, vykonávam reset...");
      resetPZEMEnergy();
    } else if (resetValue == -1.0) {
      Serial.println("Chyba pri čítaní reset hodnoty, preskakujem...");
    }
  }
}