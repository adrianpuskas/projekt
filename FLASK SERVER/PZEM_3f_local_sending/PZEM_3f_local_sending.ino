#define BLYNK_TEMPLATE_ID "TMPLUV2L_lh7"
#define BLYNK_TEMPLATE_NAME "FVE"
#define BLYNK_AUTH_TOKEN "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l"

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
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

char auth[] = BLYNK_AUTH_TOKEN;
char ssid[] = "ESP";
char pass[] = "202PuskaS";

// Lokálny server
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

BlynkTimer timer;

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

// Reset energie cez Blynk tlačidlo
BLYNK_WRITE(V11) {
  if (param.asInt() == 1) {
    for (int i = 0; i < NUM_PZEMS; i++) {
      pzems[i].resetEnergy();
    }
    celkovaSpotreba = 0.0;

    // Odoslať resetované hodnoty aj na lokálny server
    sendToLocalServer("PZEM_L1_energy", 0.0);
    sendToLocalServer("PZEM_L2_energy", 0.0);
    sendToLocalServer("PZEM_L3_energy", 0.0);
    sendToLocalServer("PZEM_total_energy", 0.0);
  }
  Blynk.virtualWrite(V11, 0);
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

    // Blynk (ponechané pre kompatibilitu)
    if (!(isnan(voltage) && isnan(current) && isnan(power) && isnan(energy) && isnan(frequency) && isnan(pf))) {
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 0), voltage);
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 1), current);
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 2), power);
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 3), energy);
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 4), frequency);
      Blynk.virtualWrite(V0 + (10 * (i + 3) + 5), pf);
    }
  }

  // Celkové hodnoty
  sendToLocalServer("PZEM_total_power", totalPower);
  sendToLocalServer("PZEM_total_energy", totalEnergy);

  Blynk.virtualWrite(V12, totalEnergy);
}

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, pass);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi pripojené: " + WiFi.localIP().toString());

  Blynk.config(auth);
  Blynk.connect();

  for (int i = 0; i < NUM_PZEMS; i++) {
    pzems[i] = PZEM004Tv30(pzemSWSerial, 0x10 + i);
  }

  timer.setInterval(5000L, PZEMs);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    ESP.restart();
  }
  Blynk.run();
  timer.run();
}