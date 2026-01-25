
#include <WiFi.h>  // WiFi knižnica pre ESP32
#include <WiFiClient.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <HTTPClient.h>

char ssid[] = "ESP";  // meno Wi-Fi siete
char pass[] = "202PuskaS";  // heslo Wi-Fi siete

// === LOKÁLNY SERVER ===
const char* serverIP = "192.168.3.84";
const int serverPort = 8000;

//#define SENSOR1_PIN 4 // VODA
//#define SENSOR2_PIN 2 // KOTOL
//#define SENSOR3_PIN 15// DYMOVOD

#define ONE_WIRE_BUS 15

// Inicializácia OneWire pre každý senzor
//OneWire oneWire1(SENSOR1_PIN);
//OneWire oneWire2(SENSOR2_PIN);
//OneWire oneWire3(SENSOR3_PIN);

// Inicializácia DallasTemperature pre každý senzor
//DallasTemperature sensor1(&oneWire1);
//DallasTemperature sensor2(&oneWire2);
//DallasTemperature sensor3(&oneWire3);

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

// #define ONE_WIRE_BUS 4    // Data vodič je pripojený na pin 4 na Arduine
#define RELAY_PUMP 5   // Digitálny pin na riadenie čerpadla
#define RELAY_VALVE 17  // Digitálny pin na riadenie elektroventilu TUV
#define RELAY_VALVE_RADIATOR 18   // Digitálny pin na riadenie elektroventila radiatorov


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


// Zapisovanie do local servera
//zapisovanie v tvare : sendToLocalServer("KEY - NA AKU POZICIU VPINS", zapisovana_hodnota);
void sendToLocalServer(const String& key, float value) {
  if (WiFi.status() != WL_CONNECTED) return;

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
  float result = -1.0;

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
    if ((int)topenie_rezim == 1) {
        ovladanie_rele_cerpadlo = value;
        digitalWrite(RELAY_PUMP, value == 0 ? LOW : HIGH);
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

// Flask citanie - Zapnutie cerpadla teplota kotla nad... asi sa to ani nevyuziva v kode
void cb_teplota_zapnutie(float value) {
    teplota_zapnutie_cerpadla_kotol_nad = value;
}

// Flask citanie - nastavena teplota vody
void cb_teplota_pozadovana_tuv(float value) {
    nastavenie_teplota_pozadovana_tuv = value;
}

// Flask citanie - Vypnutie cerpadla teplota kotla pod...
void cb_teplota_vypnutie(float value) {
    teplota_vypnutie_cerpadla_kotol_pod = value;
}

// Flask citanie - nastavenie prevadzkovej teploty - topenie do radiatorov
void cb_pracovna_radiatory(float value) {
    nastavenie_teplota_kotla_pracovna_radiatory = value;
}

// Flask citanie - nastavenie prevadzkovej teploty - topenie do TUV
void cb_pracovna_tuv(float value) {
    nastavenie_teplota_kotla_pracovna_tuv = value;
}


 // Uchováva čas pre zapnutie ventilu 
unsigned long cas_zapnutia_eletroventilu = 0; // Uchováva čas pre zapnutie ventilu
bool eletroventil_tuv_vypnuty = false; // Sledovanie stavu ventilu

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

// *** SPOLOČNÁ FUNKCIA NA ČÍTANIE A VALIDÁCIU SENZOROV ***
bool readAndValidateSensors() {
  sensors.requestTemperatures();
  teplota_tuv = sensors.getTempCByIndex(0);
  teplota_kotla = sensors.getTempCByIndex(2);
  teplota_dymovod = sensors.getTempCByIndex(1);
  //sensor1.requestTemperatures();
  //sensor2.requestTemperatures();
  //sensor3.requestTemperatures();

  // Prečítaj hodnoty z každého senzora
  //float teplota_tuv = sensor1.getTempCByIndex(0);
  //float teplota_kotla = sensor2.getTempCByIndex(0);
  //float teplota_dymovod = sensor3.getTempCByIndex(0);

  if (isnan(teplota_kotla) || isnan(teplota_tuv) || isnan(teplota_dymovod)) {
    Serial.println("Chyba pri čítaní niektorého DS18B20 snímača!");
    return false;
  }
  
  if (teplota_kotla < 0 || teplota_kotla > 180 || teplota_tuv < 0 || teplota_tuv > 180 || teplota_dymovod < 0 || teplota_dymovod > 180) {
    Serial.println("Chybná hodnota pre niektorú teplotu!");
    return false;
  }

  if (teplota_tuv == teplota_kotla || teplota_dymovod == teplota_kotla || teplota_tuv == teplota_dymovod) {
    Serial.println("Chybná hodnota pre teploty!");
    return false;
  }

  return true;
}

// *** RIADIACA FUNKCIA  ***
void sendSensor() {

  //aktualizácia wifi
  sendToLocalServer("wifiStatus", 1);

  if (!readAndValidateSensors()) {
    return;
  }

  sendToLocalServer("teplota_kotla", teplota_kotla);
  sendToLocalServer("teplota_tuv", teplota_tuv);
  sendToLocalServer("teplota_dymovod", teplota_dymovod);

  // Ak sme v režime "Automatika", vykonáme logiku pre riadenie
  if ((int)topenie_rezim == 0) {
    Serial.println("\n*** AUTOMATICKÝ REŽIM ***");
  
    //if ((teplota_kotla >= teplota_zapnutie_cerpadla_kotol_nad) || ((teplota_dymovod-2) >= teplota_ovladanie_cerpadla_dymovod)) { // ak teplota kotla je vyšša než nastavena + ak teplota dymovodu je o 2°C vyššia
    if (teplota_dymovod-2 >= teplota_ovladanie_cerpadla_dymovod) { // ak teplota dymovodu je o 2°C vyššia
      Serial.println("---> Čerpadlo zapnuté");
      //Blynk.logEvent("obehove_cerpadlo_on", "Obehové čerpadlo je zapnuté");
      digitalWrite(RELAY_PUMP, LOW); // LOW - zapnuté ; HIGH - vypnuté
      
      if (teplota_kotla >= 85) { // bezpečnostné opatrenie
        digitalWrite(RELAY_VALVE, LOW);
        digitalWrite(RELAY_VALVE_RADIATOR, LOW);
        Serial.println("---> Elektroventily zapnuté");
        //Blynk.logEvent("vysoka_teplota", "Teplota kotla je vyššia ako 85 °C !!!");

      } else {
        if (teplota_tuv >= nastavenie_teplota_pozadovana_tuv) {
          ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
          if (!eletroventil_tuv_vypnuty) {
            // Nastavte čas začiatku čakania, ak ešte nebol zaznamenaný
            if (cas_zapnutia_eletroventilu == 0) {
              cas_zapnutia_eletroventilu = millis();
            }
  
            // Skontrolujte, či uplynuli 2 minúty (120000 ms)
            if (millis() - cas_zapnutia_eletroventilu >= 120000) {
              digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil TUV vypnutý");
              digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
  
              eletroventil_tuv_vypnuty = true; // Zaznamenajte, že ventil bol vypnutý
              cas_zapnutia_eletroventilu = 0; // Reset času
            }
          }
          digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
          Serial.println("---> Elektroventil RADIÁTOROV zapnutý");
  
        } else if (teplota_tuv < (nastavenie_teplota_pozadovana_tuv - nastavenie_teplota_tolerancia_tuv)) {
          
           if (teplota_dymovod < teplota_ovladanie_cerpadla_dymovod){ // ak je dymovod zimny, prepni na radiatory a potom podla teploty kotla vypne cerpadlo
              ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
              Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
              // Resetujte stav ventilu a čas pri prechode do druhého bloku
              eletroventil_tuv_vypnuty = false;
              cas_zapnutia_eletroventilu = 0;
              digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
              digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
              Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
              }
              
            else {
              ovladanie_priorita_topenie = 1; // 0 = Radiatory ; 1 = TUV
              // Resetujte stav ventilu a čas pri prechode do druhého bloku
              eletroventil_tuv_vypnuty = false;
              cas_zapnutia_eletroventilu = 0;
      
              digitalWrite(RELAY_VALVE, LOW); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil TUV zapnutý");
              digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil RADIÁTOROV vypnutý");
              }
        } else if ((teplota_tuv > (nastavenie_teplota_pozadovana_tuv - nastavenie_teplota_tolerancia_tuv)) && (teplota_tuv < nastavenie_teplota_pozadovana_tuv)) {

            if (teplota_dymovod < teplota_ovladanie_cerpadla_dymovod){ // ak je dymovod zimny, prepni na radiatory a potom podla teploty kotla vypne cerpadlo
              ovladanie_priorita_topenie = 0; // 0 = Radiatory ; 1 = TUV
              Serial.println("---> NEDOSTATOCNA TEPLOTA SPALIN NA TO, ABY SA HRIALA TUV");
              // Resetujte stav ventilu a čas pri prechode do druhého bloku
              eletroventil_tuv_vypnuty = false;
              cas_zapnutia_eletroventilu = 0;
              digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
              digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
              Serial.println("---> Elektroventil TUV vypnutý - TEPLOTA DYMOVODU");
              Serial.println("---> Elektroventil RADIÁTOROV zapnutý - TEPLOTA DYMOVODU");
              }

            else {  

              if ((int)ovladanie_priorita_topenie == 0) { // 0 = Radiatory ; 1 = TUV
                digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV vypnutý - ovladanie_priorita_topenie");
                Serial.println("---> Elektroventil RADIÁTOROV zapnutý - ovladanie_priorita_topenie");
                }
        
              else { // 0 = Radiatory ; 1 = TUV
                digitalWrite(RELAY_VALVE, LOW); // LOW - zapnuté ; HIGH - vypnuté
                digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
                Serial.println("---> Elektroventil TUV zapnutý - ovladanie_priorita_topenie");
                Serial.println("---> Elektroventil RADIÁTOROV vypnutý - ovladanie_priorita_topenie");
                }
          }
        }
      }
    } else if (teplota_kotla <= teplota_vypnutie_cerpadla_kotol_pod){
      Serial.println("---> Čerpadlo vypnuté");
      //Blynk.logEvent("obehove_cerpadlo_off", "Obehové čerpadlo je vypnuté");
      digitalWrite(RELAY_PUMP, HIGH); // LOW - zapnuté ; HIGH - vypnuté
      digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnuté ; HIGH - vypnuté
      digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnuté ; HIGH - vypnuté
  }

  updateOvladacichPrepinacov();
  
} else {  // Manuálny režim

  Serial.println("\n*** MANUÁLNY REŽIM ***");

  // Čerpadlo
  if (ovladanie_rele_cerpadlo == 1) {
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_PUMP, LOW);
    //sendToLocalServer("status_cerpadlo", 1);  // Potvrdenie stavu
  } else {
    Serial.println("---> Čerpadlo vypnuté");
    digitalWrite(RELAY_PUMP, HIGH);
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

void sendSensorDefault() {

  if (!readAndValidateSensors()) {
    return;
  }

  Serial.println("\n*** AUTOMATICKÝ POHOTOVOSTNÝ REŽIM ***");


  if (teplota_kotla >= 30) {
    Serial.println("---> Čerpadlo zapnuté");
    digitalWrite(RELAY_PUMP, LOW); // LOW - zapnute ; HIGH - vypnute

    if (teplota_kotla >= 85) { //bezpečnostne opatrenie
      digitalWrite(RELAY_VALVE, LOW);
      digitalWrite(RELAY_VALVE_RADIATOR, LOW);
      Serial.println("---> Eletroventily zapnuté");

    } else {
      //podmienky splnene a platne
      if ((teplota_tuv >= 60) || (teplota_tuv >= (teplota_kotla - 5))) {
        digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil TUV vypnutý");
        digitalWrite(RELAY_VALVE_RADIATOR, LOW); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil radiatorov zapnutý");
      } else if ((teplota_kotla - 8) >= teplota_tuv) {
        digitalWrite(RELAY_VALVE, LOW); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil TUV zapnutý");
        digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnute ; HIGH - vypnute
        Serial.println("---> Eletroventil radiatorov vypnutý");
      }
    }


  } else if (teplota_kotla <= 30) {
    Serial.println("---> Čerpadlo a elektroventily vypnuté");
    digitalWrite(RELAY_PUMP, HIGH); // LOW - zapnute ; HIGH - vypnute
    digitalWrite(RELAY_VALVE_RADIATOR, HIGH); // LOW - zapnute ; HIGH - vypnute
    digitalWrite(RELAY_VALVE, HIGH); // LOW - zapnute ; HIGH - vypnute
  }
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
  digitalWrite(RELAY_VALVE, HIGH);
  digitalWrite(RELAY_VALVE_RADIATOR, HIGH);

  sensors.begin();
  Serial.println("Senzory pripravené");

  sendToLocalServer("wifiStatus", 1);
}

// Pomocne - citanie hodnot raz za 1 sekundu
unsigned long lastFlaskPoll = 0;
const unsigned long flaskPollInterval = 1000;

void loop() {

  if (WiFi.status() != WL_CONNECTED) //kontrola, či je zariadenie pripojené
  {
    sendSensorDefault();
    ESP.restart();    //reštartovanie zariadenia v prípade, že nie je pripojené
  }
  else {
    sendSensor();
    if (millis() - lastFlaskPoll >= flaskPollInterval) {
      lastFlaskPoll = millis();

      watchFlaskValue("topenie_rezim", topenie_rezim, cb_topenie_rezim);
      watchFlaskValue("ovladanie_rele_cerpadlo", ovladanie_rele_cerpadlo, cb_rele_cerpadlo);
      watchFlaskValue("ovladanie_rele_tuv", ovladanie_rele_tuv, cb_rele_tuv);
      watchFlaskValue("ovladanie_rele_radiatory", ovladanie_rele_radiatory, cb_rele_radiatory);

      watchFlaskValue("teplota_ovladanie_cerpadla_dymovod", teplota_ovladanie_cerpadla_dymovod, cb_teplota_ovladanie_cerpadla_dymovod);
      watchFlaskValue("ovladanie_priorita_topenie", ovladanie_priorita_topenie, cb_priorita_topenie);
      watchFlaskValue("wifiStatus", topenie_wifiStatus, cb_wifiStatus);

      watchFlaskValue("nastavenie_teplota_tolerancia_tuv", nastavenie_teplota_tolerancia_tuv, cb_tolerancia_tuv);
      watchFlaskValue("teplota_zapnutie_cerpadla_kotol_nad", teplota_zapnutie_cerpadla_kotol_nad, cb_teplota_zapnutie);
      watchFlaskValue("nastavenie_teplota_pozadovana_tuv", nastavenie_teplota_pozadovana_tuv, cb_teplota_pozadovana_tuv);
      watchFlaskValue("teplota_vypnutie_cerpadla_kotol_pod", teplota_vypnutie_cerpadla_kotol_pod, cb_teplota_vypnutie);

      watchFlaskValue("nastavenie_teplota_kotla_pracovna_radiatory", nastavenie_teplota_kotla_pracovna_radiatory, cb_pracovna_radiatory);
      watchFlaskValue("nastavenie_teplota_kotla_pracovna_tuv", nastavenie_teplota_kotla_pracovna_tuv, cb_pracovna_tuv);
    }
  }
}
