// === BLYNK NASTAVENIA – MUSIA BYŤ NA ZAČIATKU ===
#define BLYNK_TEMPLATE_ID "TMPLblK60Pj-"
#define BLYNK_TEMPLATE_NAME "Zavlaha"
#define BLYNK_AUTH_TOKEN "NhAZeqig1jKjzGuVcYmdnAH_zzIWd3pL"

#define BLYNK_PRINT Serial

#include <ESP8266WiFi.h>
#include <BlynkSimpleEsp8266.h>
#include <DHT.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

// === Wi-Fi ===
const char* ssid = "ESP";
const char* pass = "202PuskaS";

// === LOKÁLNY SERVER ===
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

// === DHT21 ===
#define DHTPIN 2
#define DHTTYPE DHT21
DHT dht(DHTPIN, DHTTYPE);

// === Premenné a timer ===
char auth[] = BLYNK_AUTH_TOKEN;
BlynkTimer timer;
double senzorTeploty;
int senzorVlhkostiVzuchu;

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
  http.setTimeout(10000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Connection", "close");
  http.addHeader("User-Agent", "ESP8266-DHT21");

  String payload = "{\"key\":\"" + key + "\",\"value\":" + String(value, 1) + "}";

  int httpCode = http.POST(payload);
  Serial.printf("%s odoslané, HTTP kód: %d\n", key.c_str(), httpCode);

  http.end();
}

void DHTsenzor() {
  senzorVlhkostiVzuchu = dht.readHumidity();
  senzorTeploty = dht.readTemperature();

  if (isnan(senzorVlhkostiVzuchu) || isnan(senzorTeploty)) {
    Serial.println(F("Chyba čítania DHT senzora!"));
    return;
  }

  Serial.print(F("Teplota vonku: "));
  Serial.print(senzorTeploty, 2);
  Serial.print(F("°C   Vlhkosť: "));
  Serial.print(senzorVlhkostiVzuchu);
  Serial.println(F("%"));

  // Blynk
  Blynk.virtualWrite(V56, senzorTeploty);
  Blynk.virtualWrite(V58, senzorVlhkostiVzuchu);

  // Lokálny server
  sendToLocalServer("outdoor_temp", senzorTeploty);
  sendToLocalServer("outdoor_humidity", (float)senzorVlhkostiVzuchu);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println();
  Serial.println("=== ŠTART ESP01 s DHT21 ===");

  // Wi-Fi
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);
  Serial.print("Pripájam sa na Wi-Fi ");
  Serial.print(ssid);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("Pripojené! IP ESP01: ");
  Serial.println(WiFi.localIP());

  // Test spojenia na lokálny server
  Serial.print("Testujem spojenie na server ");
  Serial.print(serverIP);
  Serial.print(":");
  Serial.print(serverPort);
  Serial.print(" ... ");
  WiFiClient testClient;
  if (testClient.connect(serverIP, serverPort)) {
    Serial.println("ÚSPEŠNÉ!");
    testClient.stop();
  } else {
    Serial.println("ZLYHALO!");
  }

  // Blynk
  Blynk.config(auth);
  Blynk.connect();
  if (Blynk.connected()) {
    Serial.println("Blynk pripojený");
  } else {
    Serial.println("Blynk sa nepodarilo pripojiť (pokračujem bez neho)");
  }

  dht.begin();
  timer.setInterval(5000L, DHTsenzor);

  Serial.println("Systém ready!");
}

void loop() {
  Blynk.run();
  timer.run();
}