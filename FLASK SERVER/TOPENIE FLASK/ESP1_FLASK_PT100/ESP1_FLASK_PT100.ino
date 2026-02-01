#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>
//#include <OneWire.h>
//#include <DallasTemperature.h>
#include <Adafruit_MAX31865.h>
#include <HTTPClient.h>

char ssid[] = "ESP";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

// === LOKÁLNY SERVER ===
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

#define RELAY_PUMP 5   // Digitálny pin na riadenie čerpadla
#define RELAY_VALVE 17  // Digitálny pin na riadenie elektroventilu TUV
#define RELAY_VALVE_RADIATOR 27   // Digitálny pin na riadenie elektroventila radiatorov

// definicie pre PT100 senzory
#define MAXCLK   18
#define MAXMISO  19
#define MAXMOSI  23

#define CS_TUV       22   // Zelena
#define CS_KOTOL     21   // Žltá
#define CS_DYMOVOD   16   // Hnedá

#define RREF_TUV      410.0
#define RREF_KOTOL    430.0
#define RREF_DYMOVOD  415.0

#define RNOMINAL  100.0

Adafruit_MAX31865 pt100_tuv(CS_TUV, MAXMOSI, MAXMISO, MAXCLK);
Adafruit_MAX31865 pt100_kotol(CS_KOTOL, MAXMOSI, MAXMISO, MAXCLK);
Adafruit_MAX31865 pt100_dymovod(CS_DYMOVOD, MAXMOSI, MAXMISO, MAXCLK);


float teplota_tuv;
float teplota_kotla;
float teplota_dymovod;

float topenie_rezim = 0;
float topenie_wifiStatus = 0;

float ovladanie_rele_cerpadlo = 0;
float ovladanie_rele_tuv = 0;
float ovladanie_rele_radiatory = 0;

float teplota_vypnutie_cerpadla_kotol_pod = 0;
float teplota_zapnutie_cerpadla_kotol_nad = 0;
float teplota_ovladanie_cerpadla_dymovod = 0;

float nastavenie_teplota_pozadovana_tuv = 0;
float nastavenie_teplota_tolerancia_tuv = 0;

float nastavenie_teplota_kotla_pracovna_radiatory = 0;
float nastavenie_teplota_kotla_pracovna_tuv = 0;

float ovladanie_priorita_topenie = 0;

// Premenné pre timery a stav
bool serverAvailable = false;
unsigned long lastSensorTime = 0;
const unsigned long sensorInterval = 2000;  // Interval pre sendSensor alebo default
unsigned long lastWatchTime = 0;
const unsigned long watchInterval = 000;  // Interval pre watch
unsigned long lastSlowWatchTime = 0;  // Nový timer pre menej časté watch
const unsigned long slowWatchInterval = 10000;  // Interval pre menej časté watch (10 sekúnd)
unsigned long lastCheckTime = 0;
const unsigned long checkIntervalWhenDown = 5000;  // Interval pre kontrolu obnovy servera

unsigned long lastWifiReconnectTime = 0;  // Nový timer pre reconnect WiFi
const unsigned long wifiReconnectInterval = 10000;  // Skús reconnect každých 10 sekúnd

 // Uchováva čas pre zapnutie ventilu 
unsigned long cas_zapnutia_eletroventilu = 0; // Uchováva čas pre zapnutie ventilu
bool eletroventil_tuv_vypnuty = false; // Sledovanie stavu ventilu
bool relay_cerpadlo = false; // sledovanie stavu cerpadla

// Zapisovanie do local servera
//zapisovanie v tvare : sendToLocalServer("KEY - NA AKU POZICIU VPINS", zapisovana_hodnota);
int sendToLocalServer(const String& key, float value) {
  if (WiFi.status() != WL_CONNECTED) return -1;

  WiFiClient client;
  HTTPClient http;

  String url = String("http://") + serverIP + ":" + String(serverPort) + "/write";

  http.begin(client, url);
  http.setTimeout(10000);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("Connection", "close");
  http.addHeader("User-Agent", "ESP32-Sensor");

  String payload = "{\"key\":\"" + key + "\",\"value\":" + String(value, 1) + "}";

  int httpCode = http.POST(payload);
  Serial.printf("%s odoslané, HTTP kód: %d\n", key.c_str(), httpCode);

  http.end();
  return httpCode;
}


// citanie z local servera .. 
// priklad citania :
// float premennaESP = readFromLocalServer("key vo Flask serveri");

WiFiClient client;
HTTPClient http;

float readFromLocalServer(const String& readKey) {
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/" + readKey;
  http.begin(client, url);
  int httpCode = http.GET();
  float result = -999.0;

  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.println("Flask read success: " + payload);
    result = payload.toFloat();
  } else {
    Serial.println("Flask read error: HTTP code " + String(httpCode));
  }
  http.end();
  return result;
}

// Funkcia na overenie dostupnosti servera
bool isServerAvailable() {
  WiFiClient client;
  HTTPClient http;
  String url = "http://" + String(serverIP) + ":" + String(serverPort) + "/get/wifiStatus";  // Používame existujúci endpoint na test
  http.begin(client, url);
  int httpCode = http.GET();
  http.end();
  return (httpCode > 0);  // Ak > 0, server odpovedal (aj keby to bol error code ako 404)
}

// Funkcia na citanie hodnot z flask servera
void watchFlaskValue(const String& key, float& localVar, void (*callback)(float)) {
    float newValue = readFromLocalServer(key);

    if (newValue < -900) return; // chyba čítania

    if (newValue != localVar) {
        localVar = newValue;
        callback(newValue);
    }
}

// Flask citanie manual/auto
void cb_topenie_rezim(float value) {
    topenie_rezim = (int)value;
    Serial.printf("Režim zmenený na: %d\n", (int)topenie_rezim);
}

// Flask citanie čerpadlo
void cb_rele_cerpadlo(float value) {
    if ((int)topenie_rezim == 1) { // manuál
        ovladanie_rele_cerpadlo = value;

        if (value == 1) {
            digitalWrite(RELAY_PUMP, LOW);   // zapnuté
            relay_cerpadlo = true;
        } else {
            digitalWrite(RELAY_PUMP, HIGH);  // vypnuté
            relay_cerpadlo = false;
        }
    } else {
        Serial.println("Čerpadlo sa nedá ovládať v automatickom režime");
    }
}

// Flask citanie ventil TUV
void cb_rele_tuv(float value) {
    if ((int)topenie_rezim == 1) {
        ovladanie_rele_tuv = value;
        digitalWrite(RELAY_VALVE, value == 0 ? LOW : HIGH);
    } else {
        Serial.println("TUV ventil sa nedá ovládať v automatickom režime");
    }
}

// Flask citanie ventil RELAY_VALVE_RADIATOR
void cb_rele_radiatory(float value) {
    if ((int)topenie_rezim == 1) {
        ovladanie_rele_radiatory = value;
        digitalWrite(RELAY_VALVE_RADIATOR, value == 0 ? LOW : HIGH);
    } else {
        Serial.println("Radiátory sa nedajú ovládať v automatickom režime");
    }
}

// Flask citanie nastavena teplota dymovodu
void cb_teplota_ovladanie_cerpadla_dymovod(float value) {
    teplota_ovladanie_cerpadla_dymovod = value;
}

// Flask citanie priorita topenia
void cb_priorita_topenie(float value) {
    ovladanie_priorita_topenie = (int)value;
}

// Flask citanie wifi status
void cb_wifiStatus(float value) {
    topenie_wifiStatus = (int)value;
    Serial.printf("WiFi status: %d\n", (int)topenie_wifiStatus);
}

// Nastavena tolerancia TUV
void cb_tolerancia_tuv(float value) {
    nastavenie_teplota_tolerancia_tuv = value;
}

// Flask citanie - nastavena teplota vody
void cb_teplota_pozadovana_tuv(float value) {
    nastavenie_teplota_pozadovana_tuv = value;
}

// Flask citanie - Vypnutie cerpadla teplota kotla pod...
void cb_teplota_vypnutie(float value) {
    teplota_vypnutie_cerpadla_kotol_pod = value;
}



void updateOvladacichPrepinacov() {
  if ((int)topenie_rezim == 0) { // Len v automatickom režime
    // Pre RELAY_PUMP
    sendToLocalServer("ovladanie_rele_cerpadlo", digitalRead(RELAY_PUMP) == LOW ? 1 : 0);
    
    // Pre RELAY_VALVE (TUV)
    sendToLocalServer("ovladanie_rele_tuv", digitalRead(RELAY_VALVE) == LOW ? 1 : 0);
    
    // Pre RELAY_VALVE_RADIATOR
    sendToLocalServer("ovladanie_rele_radiatory", digitalRead(RELAY_VALVE_RADIATOR) == LOW ? 1 : 0);
    
    // Pre ovladanie_priorita_topenie
    sendToLocalServer("ovladanie_priorita_topenie", ovladanie_priorita_topenie);
  }
}


bool readAndValidateSensors() {

  teplota_tuv = pt100_tuv.temperature(RNOMINAL, RREF_TUV);
  teplota_kotla = pt100_kotol.temperature(RNOMINAL, RREF_KOTOL);
  teplota_dymovod = pt100_dymovod.temperature(RNOMINAL, RREF_DYMOVOD);

  if (isnan(teplota_kotla) || isnan(teplota_tuv) || isnan(teplota_dymovod)) {
    Serial.println("Chyba pri čítaní PT100!");
    return false;
  }

  if (teplota_kotla < -20 || teplota_kotla > 300 ||
      teplota_tuv < -20 || teplota_tuv > 300 ||
      teplota_dymovod < -20 || teplota_dymovod > 500) {

    Serial.println("PT100 mimo rozsah!");
    return false;
  }

  return true;
}


// Nová zlúčená funkcia pre automatický režim (ako navrhnuté predtým)
void handleAutomaticMode(bool useDefault) {
  // Vyber hodnoty: defaultné alebo z premenných (z Flask)
  float dymovod_threshold = useDefault ? 40 : teplota_ovladanie_cerpadla_dymovod;
  float tuv_pozadovana = useDefault ? 62 : nastavenie_teplota_pozadovana_tuv;
  float tuv_tolerancia = useDefault ? 12 : nastavenie_teplota_tolerancia_tuv;
  float kotol_vypnutie = useDefault ? 29 : teplota_vypnutie_cerpadla_kotol_pod;

  Serial.println(useDefault ? "\n*** AUTOMATICKÝ POHOTOVOSTNÝ REŽIM ***" : "\n*** AUTOMATICKÝ REŽIM ***");

  if (teplota_dymovod - 2 >= dymovod_threshold) { // Zapnutie čerpadla
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_PUMP, LOW);
    relay_cerpadlo = true;

    if (teplota_kotla >= 85) { // Bezpečnostné
      digitalWrite(RELAY_VALVE, LOW);
      digitalWrite(RELAY_VALVE_RADIATOR, LOW);
      Serial.println("---> Elektroventily zapnuté - nad 85°C");
    }
    else {
      if (teplota_tuv >= tuv_pozadovana) {
        ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
        if (!eletroventil_tuv_vypnuty) {
          if (cas_zapnutia_eletroventilu == 0) {
            cas_zapnutia_eletroventilu = millis();
          }
          if (millis() - cas_zapnutia_eletroventilu >= 120000) {
            digitalWrite(RELAY_VALVE, HIGH);
            Serial.println("---> Elektroventil TUV vypnutý");
            digitalWrite(RELAY_VALVE_RADIATOR, LOW);
            Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
            eletroventil_tuv_vypnuty = true;
            cas_zapnutia_eletroventilu = 0;
          }
        }
        digitalWrite(RELAY_VALVE_RADIATOR, LOW);
        Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
      } 
      else if (teplota_tuv < (tuv_pozadovana - tuv_tolerancia)) {
        if (teplota_dymovod < dymovod_threshold) { // ak je dymovod zimny, prepni na radiatory a potom podla teploty kotla vypne cerpadlo
          ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
          Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
          eletroventil_tuv_vypnuty = false;
          cas_zapnutia_eletroventilu = 0;
          digitalWrite(RELAY_VALVE, HIGH);
          digitalWrite(RELAY_VALVE_RADIATOR, LOW);
          Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
          Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
        } 
        else {
        ovladanie_priorita_topenie = 1; // 0 = Radiatory ; 1 = TUV
        eletroventil_tuv_vypnuty = false;
        cas_zapnutia_eletroventilu = 0;
        digitalWrite(RELAY_VALVE, LOW);
        Serial.println("---> Elektroventil TUV zapnutý");
        digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
        Serial.println("---> Elektroventil RADIÁTOROV vypnutý");
        }
      } 
      else if ((teplota_tuv > (tuv_pozadovana - tuv_tolerancia)) && (teplota_tuv < tuv_pozadovana)) {
        if (teplota_dymovod < dymovod_threshold) {
          ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
          Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
          eletroventil_tuv_vypnuty = false;
          cas_zapnutia_eletroventilu = 0;
          digitalWrite(RELAY_VALVE, HIGH);
          digitalWrite(RELAY_VALVE_RADIATOR, LOW);
          Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
          Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
        } else {
          if ((int)ovladanie_priorita_topenie == 0) { // 0 = Radiatory ; 1 = TUV
            digitalWrite(RELAY_VALVE, HIGH);
            digitalWrite(RELAY_VALVE_RADIATOR, LOW);
            Serial.println("---> Elektroventil TUV vypnutý - ovladanie_priorita_topenie");
            Serial.println("---> Elektroventil RADIÁTOROV zapnutý - ovladanie_priorita_topenie");
          } else {
            digitalWrite(RELAY_VALVE, LOW);
            digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
            Serial.println("---> Elektroventil TUV zapnutý - ovladanie_priorita_topenie");
            Serial.println("---> Elektroventil RADIÁTOROV vypnutý - ovladanie_priorita_topenie");
          }
        }
      }
    }
  } 
  
  else if ((teplota_dymovod < dymovod_threshold) && (relay_cerpadlo == true)) { 
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_VALVE, HIGH);
    digitalWrite(RELAY_VALVE_RADIATOR, LOW);
    Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
    Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
    if (teplota_kotla <= kotol_vypnutie) {
      Serial.println("---> Čerpadlo vypnuté");
      digitalWrite(RELAY_PUMP, HIGH);
      relay_cerpadlo = false;
      digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
      digitalWrite(RELAY_VALVE, HIGH);
    }
  }

  if (!relay_cerpadlo) {
    digitalWrite(RELAY_VALVE, HIGH);
    digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
    eletroventil_tuv_vypnuty = false;
    cas_zapnutia_eletroventilu = 0;
  }

  // Ak nie default, aktualizuj prepínače
  if (!useDefault) {
    updateOvladacichPrepinacov();
  }

  Serial.print("\nTeplota úžitkovej vody: ");
  Serial.print(teplota_tuv);
  Serial.print(" °C\t");
  Serial.print("Teplota v kotli: ");
  Serial.print(teplota_kotla);
  Serial.println(" °C\t");
  Serial.print("Teplota dymovodu: ");
  Serial.print(teplota_dymovod);
  Serial.println(" °C\t");
}

// *** RIADIACA FUNKCIA  ***
void sendSensor() {

  //aktualizácia wifi
  int wifiStrength = 0; // Default: 0 - žiadny signál
  if (WiFi.status() == WL_CONNECTED) {
    long rssi = WiFi.RSSI(); // Získaj silu signálu v dBm
    Serial.printf("WiFi RSSI: %ld dBm\n", rssi);
    
    if (rssi >= -50) {
      wifiStrength = 3; // Plný signál
    } else if (rssi >= -70) {
      wifiStrength = 2; // Stredný signál
    } else if (rssi >= -90) {
      wifiStrength = 1; // Slabý signál
    } else {
      wifiStrength = 0; // Žiadny signál (slabší ako -90 dBm)
    }
  }
  int wifiCode = sendToLocalServer("wifiStatus", wifiStrength);

  if (wifiCode < 0) {
    sendSensorDefault();
    return;
  }

  if (!readAndValidateSensors()) {
    return;
  }

  sendToLocalServer("teplota_kotla", teplota_kotla);
  sendToLocalServer("teplota_tuv", teplota_tuv);
  sendToLocalServer("teplota_dymovod", teplota_dymovod);

  // Ak sme v režime "Automatika", vykonáme logiku pre riadenie
  if ((int)topenie_rezim == 0) {
    handleAutomaticMode(false);
  
  } else {  // Manuálny režim

  Serial.println("\n*** MANUÁLNY REŽIM ***");

  // Čerpadlo
  if (ovladanie_rele_cerpadlo == 1) {
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_PUMP, LOW);
    relay_cerpadlo = true;
    //sendToLocalServer("status_cerpadlo", 1);  // Potvrdenie stavu
  } else {
    Serial.println("---> Čerpadlo vypnuté");
    digitalWrite(RELAY_PUMP, HIGH);
    relay_cerpadlo = false;
    //sendToLocalServer("status_cerpadlo", 0);
  }

  // TUV ventil
  if (ovladanie_rele_tuv == 1) {
    Serial.println("---> Elektroventil TUV zapnutý");
    digitalWrite(RELAY_VALVE, LOW);
    //sendToLocalServer("status_tuv", 1);
  } else {
    Serial.println("---> Elektroventil TUV vypnutý");
    digitalWrite(RELAY_VALVE, HIGH);
    //sendToLocalServer("status_tuv", 0);
  }

  // Radiátory
  if (ovladanie_rele_radiatory == 1) {
    Serial.println("---> Elektroventil radiátorov zapnutý");
    digitalWrite(RELAY_VALVE_RADIATOR, LOW);
    //sendToLocalServer("status_radiatory", 1);
  } else {
    Serial.println("---> Elektroventil radiátorov vypnutý");
    digitalWrite(RELAY_VALVE_RADIATOR, HIGH);
    //sendToLocalServer("status_radiatory", 0);
  }
}

}

void sendSensorDefault() {

  if (!readAndValidateSensors()) {
    return;
  }

  handleAutomaticMode(true);

}



void setup() {
  Serial.begin(9600);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, pass);

  Serial.print("Pripájam sa na WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi pripojené!");
  Serial.print("IP adresa: ");
  Serial.println(WiFi.localIP());

  pinMode(RELAY_PUMP, OUTPUT);
  pinMode(RELAY_VALVE, OUTPUT);
  pinMode(RELAY_VALVE_RADIATOR, OUTPUT);

  digitalWrite(RELAY_PUMP, HIGH);
  relay_cerpadlo = false;
  digitalWrite(RELAY_VALVE, HIGH);
  digitalWrite(RELAY_VALVE_RADIATOR, HIGH);

  pt100_tuv.begin(MAX31865_2WIRE);
  pt100_kotol.begin(MAX31865_2WIRE);
  pt100_dymovod.begin(MAX31865_2WIRE);

  Serial.println("PT100 senzory inicializované");

  // Inicializácia dostupnosti servera
  serverAvailable = isServerAvailable();
  if (serverAvailable) {
    sendToLocalServer("wifiStatus", 1);
  }
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    // Pohotovostný režim bez reštartu
    Serial.println("WiFi odpojené - bežím v pohotovostnom režime");

    // Pokus o reconnect WiFi periodicky
    if (millis() - lastWifiReconnectTime >= wifiReconnectInterval) {
      lastWifiReconnectTime = millis();
      Serial.print("Pokus o reconnect WiFi...");
      WiFi.reconnect();
    }

    // Spusti sendSensorDefault() periodicky
    if (millis() - lastSensorTime >= sensorInterval) {
      lastSensorTime = millis();
      sendSensorDefault();
    }

    // Kontrola, či sa WiFi obnovilo (a server)
    if (millis() - lastCheckTime >= checkIntervalWhenDown) {
      lastCheckTime = millis();
      if (WiFi.status() == WL_CONNECTED && isServerAvailable()) {
        serverAvailable = true;
        Serial.println("WiFi a server obnovené - prechádzam do normálneho režimu");
        lastSensorTime = millis();  // Okamžite spusti sendSensor
        lastWatchTime = millis();  // Okamžite spusti watch
      }
    }

    delay(100);  // Malý delay na zabránenie busy loop
  } else {
    if (!serverAvailable) {
      // Pohotovostný režim (server dole, ale WiFi hore)
      if (millis() - lastCheckTime >= checkIntervalWhenDown) {
        lastCheckTime = millis();
        if (isServerAvailable()) {
          serverAvailable = true;
          lastSensorTime = millis();  // Okamžite spusti sendSensor
          lastWatchTime = millis();  // Okamžite spusti watch
        }
      }
      if (millis() - lastSensorTime >= sensorInterval) {
        lastSensorTime = millis();
        sendSensorDefault();
      }
      delay(100);  // Malý delay na zabránenie busy loop
    } else {
      // Normálny režim
      if (millis() - lastSensorTime >= sensorInterval) {
        lastSensorTime = millis();
        sendSensor();
      }
      if (millis() - lastWatchTime >= watchInterval) {
        lastWatchTime = millis();
        watchFlaskValue("topenie_rezim", topenie_rezim, cb_topenie_rezim);
        watchFlaskValue("ovladanie_rele_cerpadlo", ovladanie_rele_cerpadlo, cb_rele_cerpadlo);
        watchFlaskValue("ovladanie_rele_tuv", ovladanie_rele_tuv, cb_rele_tuv);
        watchFlaskValue("ovladanie_rele_radiatory", ovladanie_rele_radiatory, cb_rele_radiatory);

        
        watchFlaskValue("ovladanie_priorita_topenie", ovladanie_priorita_topenie, cb_priorita_topenie);
        watchFlaskValue("wifiStatus", topenie_wifiStatus, cb_wifiStatus);
      }
      if (millis() - lastSlowWatchTime >= slowWatchInterval) {
        lastSlowWatchTime = millis();
        watchFlaskValue("nastavenie_teplota_tolerancia_tuv", nastavenie_teplota_tolerancia_tuv, cb_tolerancia_tuv);
        watchFlaskValue("nastavenie_teplota_pozadovana_tuv", nastavenie_teplota_pozadovana_tuv, cb_teplota_pozadovana_tuv);
        watchFlaskValue("teplota_vypnutie_cerpadla_kotol_pod", teplota_vypnutie_cerpadla_kotol_pod, cb_teplota_vypnutie);
        watchFlaskValue("teplota_ovladanie_cerpadla_dymovod", teplota_ovladanie_cerpadla_dymovod, cb_teplota_ovladanie_cerpadla_dymovod);
      }
    }
  }
}