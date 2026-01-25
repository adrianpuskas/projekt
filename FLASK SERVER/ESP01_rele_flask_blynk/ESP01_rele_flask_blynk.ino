#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <ESP8266HTTPClient.h>

const char *ssid = "iHome";
const char *password = "202PuskaS";
const char *blynkAuth = "Gurl2O0DoNv46y8iKKJmNTx1w15NLJ7l";
const char *serverIP = "192.168.3.84";
const int serverPort = 8000;
const String relayKey = "esp1_relay";

int premenna = 0;
int premenna1 = 0;
float prevBlynk = 0.0;
float prevFlask = 0.0;

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
  delay(1000);
  writeValue(20, 0);
  writeFlaskValue(0);
  prevBlynk = 0.0;
  prevFlask = 0.0;
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, restarting...");
    delay(2000);  // malá pauza na istotu
    ESP.restart();
  }

  float blynkValue = readValue(20); // Čítanie hodnoty z pinu č. 20 na Blynk
  float flaskValue = readFlaskValue(); // Čítanie hodnoty z Flask servera

  Serial.print("Current states: pinValue from Blynk: ");
  Serial.print(blynkValue);
  Serial.print(", from Flask: ");
  Serial.print(flaskValue);
  Serial.print(", premenna: ");
  Serial.print(premenna);
  Serial.print(", premenna1: ");
  Serial.println(premenna1);

  // Spracovanie chýb čítania (použi predchádzajúcu hodnotu)
  if (blynkValue == -1.0) blynkValue = prevBlynk;
  if (flaskValue == -1.0) flaskValue = prevFlask;

  // Detekcia zmeny a synchronizácia
  if (blynkValue != prevBlynk) {
    // Zmena na Blynk, synchronizuj na Flask
    writeFlaskValue(blynkValue);
    prevBlynk = blynkValue;
    prevFlask = blynkValue;
    Serial.println("Synchronizácia: Blynk -> Flask");
  } else if (flaskValue != prevFlask) {
    // Zmena na Flask, synchronizuj na Blynk
    writeValue(20, flaskValue);
    prevFlask = flaskValue;
    prevBlynk = flaskValue;
    Serial.println("Synchronizácia: Flask -> Blynk");
  }

  // Efektívna hodnota (použi blynkValue, pretože sú synchronizované)
  float pinValue = blynkValue;

  // Ovládanie relé na základe hodnoty
  if (pinValue == 1 && premenna == 0) {
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.write(rel1ON, sizeof(rel1ON));
    Serial.write(rel1ON, sizeof(rel1ON)); 
    Serial.println("Zapínam");
    premenna = 1;
    premenna1 = 0;
  } else if (pinValue == 1 && premenna == 1) {
    Serial.println("Zapnute, Cakam na zmenu");
  } else if (pinValue == 0 && premenna1 == 0) {
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.write(rel1OFF, sizeof(rel1OFF)); 
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.write(rel1OFF, sizeof(rel1OFF));
    Serial.println("Vypínam");
    premenna1 = 1;
    premenna = 0;
  } else if (pinValue == 0 && premenna1 == 1) {
    Serial.println("Vypnute, Cakam na zmenu");
  } else {
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
    Serial.println("Blynk read success: " + payload);
    return payload.toFloat(); // Prevod reťazca na desatinné číslo
  } else {
    Serial.println("Blynk read error: HTTP code " + String(httpCodeRead));
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

  if (httpCodeWrite == HTTP_CODE_OK) {
    Serial.println("Blynk write success");
  } else {
    Serial.println("Blynk write error: HTTP code " + String(httpCodeWrite));
  }

  // Ukončenie HTTP klienta pre zápis hodnoty
  http.end();
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