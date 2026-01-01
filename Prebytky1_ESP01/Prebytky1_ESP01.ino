#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>

const char *ssid = "ESP";
const char *password = "202PuskaS";
const char *blynkAuth = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l";

int premenna = 0;
int premenna1 = 0;

// Definícia príkazov pre ovládanie relé
const byte rel1ON[] = {0xA0, 0x01, 0x01, 0xA2};  //Hex command to send to serial for open relay
const byte rel1OFF[] = {0xA0, 0x01, 0x00, 0xA1}; //Hex command to send to serial for close relay

void setup() {
  Serial.begin(9600);

  // Pripojenie na Wi-Fi sieť
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }
  Serial.println("Connected to WiFi");
  delay (1000);
  writeValue(20, 0);
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, restarting...");
    delay(2000);  // malá pauza na istotu
    ESP.restart();
  }

  float pinValue = readValue(20); // Čítanie hodnoty z pinu č. 20

  // Ovládanie relé na základe hodnoty prečítanej z pinu č. 20
  if (pinValue == 1 & premenna == 0) {
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.write(rel1ON, sizeof(rel1ON));
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.println("Zapínam");
    premenna = 1;
    premenna1 = 0;
  } 
  if (pinValue == 1 & premenna == 1) {
    Serial.println("Zapnute, Cakam na zmenu");
  }

  if (pinValue == 0 & premenna1 == 0) {
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.write(rel1OFF, sizeof(rel1OFF)); 
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.println("Vypínam");
    premenna1 = 1;
    premenna = 0;
    }
  if (pinValue == 0 & premenna1 == 1) {
    Serial.println("Vypnute, Cakam na zmenu");
  } 
  
  else {
    Serial.println("Error podmienok");
  }

  // Pomalšie kontrolovanie
  delay(2000);
}

float readValue(int pin) {
  // Inicializácia HTTP klienta
  HTTPClient http;

  // Konštrukcia URL pre čítanie hodnoty zo servera Blynk
  String urlRead = "http://blynk.cloud/external/api/get?token=" + String(blynkAuth) + "&V" + String(pin);

  // Volanie URL pre čítanie hodnoty
  WiFiClient client;
  http.begin(client, urlRead);
  int httpCodeRead = http.GET();

  if (httpCodeRead == HTTP_CODE_OK) {
    String payload = http.getString();
    return payload.toFloat(); // Prevod reťazca na desatinné číslo
  } else {
    Serial.println("Error reading value from pin " + String(pin) + ": " + String(httpCodeRead));
    return -1.0; // Vrátime -1.0 v prípade chyby
  }

  // Ukončenie HTTP klienta pre čítanie hodnoty
  http.end();
}

void writeValue(int pin, float value) {
  // Inicializácia HTTP klienta
  HTTPClient http;

  // Konštrukcia URL pre zápis hodnoty na server Blynk
  String urlWrite = "http://blynk.cloud/external/api/update?token=" + String(blynkAuth) + "&V" + String(pin) + "=" + String(value);

  // Volanie URL pre zápis hodnoty
  WiFiClient client;
  http.begin(client, urlWrite);
  int httpCodeWrite = http.GET();

  if (httpCodeWrite != HTTP_CODE_OK) {
    Serial.println("Error uploading value to pin " + String(pin) + ": " + String(httpCodeWrite));
  }

  // Ukončenie HTTP klienta pre zápis hodnoty
  http.end();
}