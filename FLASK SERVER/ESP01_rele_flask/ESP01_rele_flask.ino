#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>

const char *ssid = "ESP";
const char *password = "202PuskaS";
const char *serverIP = "192.168.3.84";
const int serverPort = 8000;
const String relayKey = "esp1_relay";

int premenna = 0;
int premenna1 = 0;
float prevFlask = 0.0;

// Definícia príkazov pre ovládanie relé
const byte rel1ON[] = {0xA0, 0x01, 0x01, 0xA2};  // Hex command to send to serial for open relay
const byte rel1OFF[] = {0xA0, 0x01, 0x00, 0xA1}; // Hex command to send to serial for close relay

void setup() {
  Serial.begin(9600);

  // Pripojenie na Wi-Fi sieť
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  delay(1000);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, restarting...");
    delay(2000);  // malá pauza na istotu
    ESP.restart();
  }

  float flaskValue = readFlaskValue(); // Čítanie hodnoty z Flask servera

  Serial.print("Current state from Flask: ");
  Serial.print(flaskValue);
  Serial.print(", premenna: ");
  Serial.print(premenna);
  Serial.print(", premenna1: ");
  Serial.println(premenna1);

  // Spracovanie chýb čítania (použi predchádzajúcu hodnotu)
  if (flaskValue == -1.0) flaskValue = prevFlask;

  // Aktualizuj prevFlask
  prevFlask = flaskValue;

  // Ovládanie relé na základe hodnoty z Flask
  if (flaskValue == 1 && premenna == 0) {
    sendRelayCommand(rel1ON);  // ON
    Serial.println("Zapínam");
    premenna = 1;
    premenna1 = 0;
  } else if (flaskValue == 1 && premenna == 1) {
    Serial.println("Zapnute, Cakam na zmenu");
  } else if (flaskValue == 0 && premenna1 == 0) {
    sendRelayCommand(rel1OFF);  // OFF
    Serial.println("Vypínam");
    premenna1 = 1;
    premenna = 0;
  } else if (flaskValue == 0 && premenna1 == 1) {
    Serial.println("Vypnute, Cakam na zmenu");
  } else {
    Serial.println("Error podmienok");
  }

  // Pomalšie kontrolovanie
  delay(2000);
}

void sendRelayCommand(const byte* cmd) {
  for (int i = 0; i < 8; i++) {
    Serial.write(cmd, 4);  // sizeof(rel1ON) = 4
    delay(1);  // Malý delay
  }
}

float readFlaskValue() {
  HTTPClient http;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + relayKey;
  WiFiClient client;
  http.begin(client, url);
  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Flask read success: " + payload);
    return payload.toFloat();
  } else {
    Serial.println("Flask read error: HTTP code " + String(httpCode));
    return -1.0;
  }
  http.end();
}

void writeFlaskValue(float value) {
  HTTPClient http;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/write";
  WiFiClient client;
  http.begin(client, url);
  http.addHeader("Content-Type", "application/json");
  String payload = "{\"key\":\"" + relayKey + "\",\"value\":" + String(value) + "}";
  int httpCode = http.POST(payload);
  if (httpCode == HTTP_CODE_OK) {
    Serial.println("Flask write success");
  } else {
    Serial.println("Flask write error: HTTP code " + String(httpCode));
  }
  http.end();
}